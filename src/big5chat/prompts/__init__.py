"""Prompt assembly layer (Layer 2).

Turns a PersonaSpec into the complete system prompt + postamble package.
"""

from big5chat.prompts.assembler import PromptAssembler
from big5chat.prompts.postambles import POSTAMBLES_EN, POSTAMBLES_JA, postamble
from big5chat.prompts.variants import PROMPT_VARIANTS_EN, PROMPT_VARIANTS_JA

__all__ = [
    "PromptAssembler",
    "POSTAMBLES_EN",
    "POSTAMBLES_JA",
    "postamble",
    "PROMPT_VARIANTS_EN",
    "PROMPT_VARIANTS_JA",
]
