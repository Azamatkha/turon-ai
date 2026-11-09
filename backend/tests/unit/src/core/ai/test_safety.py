import pytest

from src.core.ai.safety import find_profanity, has_profanity


@pytest.mark.parametrize(
    "text",
    [
        "Jalab bot nega javob bermaysan",
        "сука опять не работает",
        "ты долбоёб",
        "what the fuck is this",
        "s1kay seni",  # raqam bilan yashirilgan
        "suuuka",  # uzaytirib yozilgan
        "ОНАНГНИ",
        "jalablar",  # qo'shimcha bilan
        "блять кредит где",
        "naxuy kerak",
    ],
)
def test_profanity_detected(text: str) -> None:
    assert has_profanity(text), find_profanity(text)


@pytest.mark.parametrize(
    "text",
    [
        "Kredit foizi qancha?",
        "Нужен хлеб и кредит",  # "хлеб" ichida "еб"
        "halol va harom daromad",
        "Sukut saqlash qoidasi",
        "Shitob bilan ishlash",
        "Skeyt-park filiali qayerda",
        "Сукно ishlab chiqarish uchun kredit",
        "Xuyduk tumanidagi filial",
        "Bitcoin nima?",
        "Mudarris lavozimi",
        "Ипотека, заем и ссуда",
        "",
    ],
)
def test_clean_text_not_flagged(text: str) -> None:
    assert not has_profanity(text), find_profanity(text)
