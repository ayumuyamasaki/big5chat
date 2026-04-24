"""Baseline method adapters for comparison experiments.

Two prior approaches are re-implemented here using the modern OpenAI API,
so that MPI (Jiang et al. NeurIPS 2023) and PersonaLLM (Jiang et al. NAACL 2024)
methodologies can be compared head-to-head with our Serapio-Garcia pipeline
under identical provider / seed / persona conditions.

Why re-implement rather than run the original code?
- MPI uses the deprecated OpenAI Completions API (`text-davinci-003` was
  retired in Jan 2024). It cannot be executed against today's API.
- PersonaLLM uses the openai-python 0.x SDK plus a `multiprocessing.Pool`
  that hangs on Windows. It imports a local `gpt.is_answer_in_valid_form`
  helper that is not in the repo.

Both adapters reuse the data files shipped in the cloned repos
(`external/MPI/inventories/mpi_120.csv` and
`external/PersonaLLM/prompts/bfi_scores.txt`) verbatim so that the
methodological comparison remains faithful.
"""

from big5chat.baselines.mpi import MPIEvaluator, MPIResult
from big5chat.baselines.personallm import PersonaLLMEvaluator, PersonaLLMResult

__all__ = [
    "MPIEvaluator",
    "MPIResult",
    "PersonaLLMEvaluator",
    "PersonaLLMResult",
]
