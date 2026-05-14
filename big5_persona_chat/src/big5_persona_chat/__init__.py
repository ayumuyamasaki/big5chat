"""big5_persona_chat: Big5 性格付きチャットボットの最小モジュール。

主要 API:
    chat / achat                — 1ショット同期/非同期チャット
    chat_raw / achat_raw        — 同上(トークン数等のメタ情報込み)
    ChatSession                 — マルチターン対話セッション
    Big5                        — Big5 数値プロファイル (-4..+4)
    Persona                     — ユーザー向け薄ペルソナ仕様
    PersonaSpec                 — 内部完全仕様(言語ロック)
"""

from big5_persona_chat.chat import (
    ChatReply,
    ChatSession,
    achat,
    achat_raw,
    chat,
    chat_raw,
)
from big5_persona_chat.persona import Big5, Persona, PersonaSpec, StyleParams

__all__ = [
    "chat",
    "achat",
    "chat_raw",
    "achat_raw",
    "ChatReply",
    "ChatSession",
    "Big5",
    "Persona",
    "PersonaSpec",
    "StyleParams",
]

__version__ = "0.1.0"
