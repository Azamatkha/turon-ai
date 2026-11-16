""""Qaysi model?" savoliga to'g'ridan-to'g'ri javob va kontekstsiz javobdagi
fakt xatolarini tekshiruvchi rad etishi (promptlar mazmuni)."""

from src.knowledge.answer_helpers import _bot_reply
from src.knowledge.prompts import (
    ABOUT_BOT_REPLY,
    CAPABILITIES_REPLY,
    CONCEPT_SYSTEM,
    LANGUAGE_SYSTEM,
    RU_CANNED_REPLIES,
)
from src.knowledge.router import Intent, Route
from src.knowledge.verifier import VERIFY_SYSTEM


def test_about_bot_answers_model_question_first() -> None:
    text = _bot_reply(Route(Intent.ABOUT_BOT, "qaysi model"), None, "uz")
    assert text == ABOUT_BOT_REPLY
    assert text.startswith("Men Turon-AI")
    assert "model nomi" in text
    # Ro'yxat ham saqlangan
    assert "Kalkulyator" in text


def test_about_bot_russian_and_cyrillic() -> None:
    ru = _bot_reply(Route(Intent.ABOUT_BOT, "какая модель"), None, "ru")
    assert ru == RU_CANNED_REPLIES[ABOUT_BOT_REPLY]
    assert ru != RU_CANNED_REPLIES[CAPABILITIES_REPLY]
    assert "название модели" in ru
    cyr = _bot_reply(Route(Intent.ABOUT_BOT, "qaysi model"), None, "uz_cyrl")
    assert cyr.startswith("Мен")


def test_first_greeting_keeps_plain_capabilities() -> None:
    text = _bot_reply(Route(Intent.SMALLTALK, "salom"), None, "uz")
    assert CAPABILITIES_REPLY in text
    assert "model nomi" not in text


def test_verifier_rejects_contradicted_general_facts() -> None:
    assert "7. FACTUAL ERROR" in VERIFY_SYSTEM
    assert "draft or proposal" in VERIFY_SYSTEM
    # Tasdiqlab bo'lmaydigan (yangi) narsa rad etish sababi emas
    assert "never for events after your training knowledge" in VERIFY_SYSTEM


def test_answer_prompts_have_history_rule() -> None:
    for prompt in (LANGUAGE_SYSTEM, CONCEPT_SYSTEM):
        assert "HISTORY, LAWS AND REFORMS" in prompt
