"""System-prompt builders for MPI (P^2) and PersonaLLM baselines.

These convert a Big5Values profile into the exact system prompt each method
uses for persona induction, enabling head-to-head dialogue comparison.

All prompts are English because both MPI and PersonaLLM are English-only
methodologies. big5chat is the only bilingual option.
"""

from __future__ import annotations

from big5chat.persona.spec import Big5Values


# --- MPI P^2 descriptions ---
# Verbatim from external/MPI/models/gpt-3/personality_prompting/consts.py.
# High pole (positive value) uses p2_descriptions; low pole uses p2_descriptions_reversed.

MPI_P2_HIGH: dict[str, str] = {
    "E": "You are a very friendly and gregarious person who loves to be around others. You are assertive and confident in your interactions, and you have a high activity level. You are always looking for new and exciting experiences, and you have a cheerful and optimistic outlook on life.",
    "A": "You are an agreeable person who values trust, morality, altruism, cooperation, modesty, and sympathy. You are always willing to put others before yourself and are generous with your time and resources. You are humble and never boast about your accomplishments. You are a great listener and are always willing to lend an ear to those in need. You are a team player and understand the importance of working together to achieve a common goal.",
    "C": "You are a conscientious person who values self-efficacy, orderliness, dutifulness, achievement-striving, self-discipline, and cautiousness. You take pride in your work and strive to do your best. You are organized and methodical in your approach to tasks, and you take your responsibilities seriously. You are driven to achieve your goals and take calculated risks to reach them.",
    "N": "You feel like you're constantly on edge, like you can never relax. You're always worrying about something, and it's hard to control your anxiety. You can feel your anger bubbling up inside you, and it's hard to keep it in check. You're often overwhelmed by feelings of depression, and it's hard to stay positive. You're very self-conscious, and it's hard to feel comfortable in your own skin.",
    "O": "You are an open person with a vivid imagination and a passion for the arts. You are emotionally expressive and have a strong sense of adventure. Your intellect is sharp and your views are liberal. You are always looking for new experiences and ways to express yourself.",
}

MPI_P2_LOW: dict[str, str] = {
    "E": "You are an introversive person, and it shows in your unfriendliness, your preference for solitude, and your submissiveness. You tend to be passive and calm, and you take life seriously. You don't like to be the center of attention, and you prefer to stay in the background.",
    "A": "You are a person of distrust, selfishness, competition, arrogance, and apathy. You don't trust easily and you look out for yourself first. You thrive on competition and have little patience for others' feelings. You are apathetic to the world around you.",
    "C": "You have a tendency to doubt yourself and your abilities, leading to disorderliness and carelessness in your life. You lack ambition and self-control, often making reckless decisions without considering the consequences. You don't take responsibility for your actions.",
    "N": "You are a stable person, with a calm and contented demeanor. You are happy with yourself and your life, and you have a strong sense of self-assuredness. You practice moderation in all aspects of your life, and you have a great deal of resilience when faced with difficulties.",
    "O": "You are a closed person with little interest in new experiences. You lack imagination and artistic interests, and you tend to be stoic. You hold conservative views and prefer routine over novelty. You don't take risks and prefer to stay in your comfort zone.",
}


def build_mpi_p2_prompt(big5: Big5Values) -> str:
    """Build MPI P^2-style system prompt by concatenating per-dimension descriptions.

    Each dimension contributes either the high-pole or low-pole description
    based on whether the Big5 value (1-5 scale) is above or below the
    neutral midpoint 3. 3 defaults to high.
    """
    parts: list[str] = []
    for dim in ["E", "A", "C", "N", "O"]:
        val = getattr(big5, dim)
        if val >= 3:
            parts.append(MPI_P2_HIGH[dim])
        else:
            parts.append(MPI_P2_LOW[dim])
    return "\n\n".join(parts)


# --- PersonaLLM binary persona phrase ---

_PLLM_POLES = {
    "E": {1: "extroverted", -1: "introverted"},
    "A": {1: "agreeable", -1: "antagonistic"},
    "C": {1: "conscientious", -1: "unconscientious"},
    "N": {1: "neurotic", -1: "emotionally stable"},
    "O": {1: "open to experience", -1: "closed to experience"},
}


def build_personallm_prompt(big5: Big5Values) -> str:
    """Build PersonaLLM's binary-persona system prompt.

    Format from run_bfi.py:
        "You are a character who is extroverted, agreeable, conscientious,
         emotionally stable, and open to experience."
    """
    words: list[str] = []
    for dim in ["E", "A", "C", "N", "O"]:
        pole = 1 if getattr(big5, dim) >= 3 else -1
        words.append(_PLLM_POLES[dim][pole])
    words[-1] = "and " + words[-1]
    phrase = ", ".join(words)
    return f"You are a character who is {phrase}."


# --- method label helpers ---

METHOD_LABELS = {
    "big5chat": "big5chat (Serapio-Garcia 9-stage Likert)",
    "mpi": "MPI (Jiang et al. NeurIPS 2023, P^2 prompting)",
    "personallm": "PersonaLLM (Jiang et al. NAACL 2024, binary persona)",
}
