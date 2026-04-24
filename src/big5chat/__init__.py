"""Big5 persona chatbot research framework.

Based on ConstructionPlan.md design:
- Serapio-Garcia 2025 style Likert-modified persona prompts
- 3-layer evaluation (Self-Report BFI + Expert Rating + TRAIT MCQ)
- Identity drift control via N-turn re-injection
- Japanese / English bilingual support
"""

__version__ = "0.1.0"

from big5chat.persona import Big5Values, PersonaSpec, StyleParams

__all__ = ["Big5Values", "PersonaSpec", "StyleParams", "__version__"]
