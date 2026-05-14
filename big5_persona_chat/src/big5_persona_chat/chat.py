"""公開チャット API。

ゲーム等の利用側からは、以下の 3 系統が使える:

1. 1ショット同期:  chat(model, language, persona, text) -> str
2. 1ショット非同期: await achat(...)
3. セッション:    ChatSession(...).send(text) / asend(text)

トークン数等のメタ情報も欲しい場合は chat_raw / achat_raw を使う。
"""

from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel

from big5_persona_chat.persona._user import Persona
from big5_persona_chat.persona.spec import PersonaSpec
from big5_persona_chat.prompts.assembler import PromptAssembler
from big5_persona_chat.providers import LLMProvider, get_provider


Language = Literal["en", "ja", "zh"]


class ChatReply(BaseModel):
    """raw 系 API の戻り値。"""

    content: str
    model_id: str
    provider: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    stop_reason: str | None = None


def _to_spec(persona: Persona | PersonaSpec, language: Language) -> PersonaSpec:
    """Persona/PersonaSpec のいずれを受け取っても PersonaSpec に揃える。"""
    if isinstance(persona, PersonaSpec):
        if persona.language != language:
            return persona.with_updates(language=language)
        return persona
    return persona.to_persona_spec(language)


def _build_system_prompt(spec: PersonaSpec) -> str:
    return PromptAssembler().assemble(spec)


def _no_running_loop_or_raise(sync_fn_name: str) -> None:
    """同期 API が実行中のイベントループ内から呼ばれていないかを確認する。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    raise RuntimeError(
        f"{sync_fn_name}() は実行中のイベントループから呼べません。"
        f"非同期版 (a{sync_fn_name}) を使用してください。"
    )


async def achat_raw(
    *,
    model: str,
    language: Language,
    persona: Persona | PersonaSpec,
    text: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 400,
    seed: int | None = None,
    api_key: str | None = None,
) -> ChatReply:
    """1ショット非同期チャット(メタ情報込み)。"""
    spec = _to_spec(persona, language)
    system_prompt = _build_system_prompt(spec)
    provider: LLMProvider = get_provider(model, api_key=api_key) if api_key else get_provider(model)
    resp = await provider.complete(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        temperature=temperature,
        top_p=top_p,
        seed=seed if provider.supports_seed else None,
        max_tokens=max_tokens,
    )
    return ChatReply(
        content=resp.content,
        model_id=resp.model_id,
        provider=resp.provider,
        input_tokens=resp.input_tokens,
        output_tokens=resp.output_tokens,
        stop_reason=resp.stop_reason,
    )


async def achat(
    *,
    model: str,
    language: Language,
    persona: Persona | PersonaSpec,
    text: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 400,
    seed: int | None = None,
    api_key: str | None = None,
) -> str:
    """1ショット非同期チャット(本文のみ返却)。"""
    reply = await achat_raw(
        model=model,
        language=language,
        persona=persona,
        text=text,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
        api_key=api_key,
    )
    return reply.content


def chat_raw(
    *,
    model: str,
    language: Language,
    persona: Persona | PersonaSpec,
    text: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 400,
    seed: int | None = None,
    api_key: str | None = None,
) -> ChatReply:
    """1ショット同期チャット(メタ情報込み)。内部で asyncio.run を呼ぶ。"""
    _no_running_loop_or_raise("chat_raw")
    return asyncio.run(
        achat_raw(
            model=model,
            language=language,
            persona=persona,
            text=text,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
            api_key=api_key,
        )
    )


def chat(
    *,
    model: str,
    language: Language,
    persona: Persona | PersonaSpec,
    text: str,
    temperature: float = 0.7,
    top_p: float = 0.95,
    max_tokens: int = 400,
    seed: int | None = None,
    api_key: str | None = None,
) -> str:
    """1ショット同期チャット(本文のみ返却)。"""
    _no_running_loop_or_raise("chat")
    return asyncio.run(
        achat(
            model=model,
            language=language,
            persona=persona,
            text=text,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            seed=seed,
            api_key=api_key,
        )
    )


class ChatSession:
    """マルチターン対話セッション。

    内部で会話履歴 (system を除いた user/assistant の交互列) を保持する。
    `reinject_every` を指定すると、N ターン毎にペルソナ要約を system ロールで
    再注入し、長い対話でのペルソナ忘却を抑制する。
    """

    def __init__(
        self,
        *,
        model: str,
        language: Language,
        persona: Persona | PersonaSpec,
        temperature: float = 0.7,
        top_p: float = 0.95,
        max_tokens: int = 400,
        seed: int | None = None,
        api_key: str | None = None,
        reinject_every: int | None = None,
    ):
        self.model = model
        self.language: Language = language
        self.persona = persona
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.seed = seed
        self.reinject_every = reinject_every

        self._spec = _to_spec(persona, language)
        self._assembler = PromptAssembler()
        self._system_prompt = self._assembler.assemble(self._spec)
        self._provider: LLMProvider = (
            get_provider(model, api_key=api_key) if api_key else get_provider(model)
        )
        # system を含まない user/assistant 交互の履歴
        self._history: list[dict[str, str]] = []
        self._turn_count = 0

    @property
    def history(self) -> list[dict[str, str]]:
        """会話履歴のコピーを返す(system プロンプトは含まない)。"""
        return [dict(m) for m in self._history]

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    def reset(self) -> None:
        """履歴をクリアする。system プロンプトと設定は保持。"""
        self._history.clear()
        self._turn_count = 0

    def _build_messages(self, user_text: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt}
        ]
        messages.extend(self._history)

        # 再注入: N ターン毎にペルソナ要約を system ロールで挿入
        if (
            self.reinject_every is not None
            and self._turn_count > 0
            and self._turn_count % self.reinject_every == 0
        ):
            messages.append(
                {
                    "role": "system",
                    "content": self._reinjection_text(),
                }
            )

        messages.append({"role": "user", "content": user_text})
        return messages

    def _reinjection_text(self) -> str:
        summary = self._assembler.persona_summary(self._spec)
        if self.language == "ja":
            return f"思い出してください: あなたは{summary}人物です。この人物像を保ち続けてください。"
        if self.language == "zh":
            return f"请记住: 你是一个{summary}的人。请继续保持这个人物形象。"
        return f"Reminder: you are {summary}. Maintain this persona consistently."

    async def asend(self, text: str) -> str:
        """非同期: 1 メッセージ送信して応答を取得。"""
        messages = self._build_messages(text)
        resp = await self._provider.complete(
            messages=messages,
            temperature=self.temperature,
            top_p=self.top_p,
            seed=self.seed if self._provider.supports_seed else None,
            max_tokens=self.max_tokens,
        )
        self._history.append({"role": "user", "content": text})
        self._history.append({"role": "assistant", "content": resp.content})
        self._turn_count += 1
        return resp.content

    def send(self, text: str) -> str:
        """同期: 1 メッセージ送信して応答を取得。"""
        _no_running_loop_or_raise("ChatSession.send")
        return asyncio.run(self.asend(text))
