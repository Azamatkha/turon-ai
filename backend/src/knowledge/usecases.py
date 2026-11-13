"""Savolga javob berish (RAG) usecase'i.

Yordamchi funksiyalar — `answer_helpers.py`, bilim bazasiga yozish
usecase'lari — `ingest_usecases.py`. Ular bu yerdan qayta eksport
qilinadi: eski `from src.knowledge.usecases import ...` importlari ishlayveradi.
"""

from collections.abc import AsyncIterator
import json
import math
import re
from typing import Any

from loggers import get_logger
from src.core.ai.embeddings import OllamaEmbedder
from src.core.ai.interfaces import BaseAIClient
from src.core.ai.safety import has_profanity
from src.core.errors.exceptions import (
    InfrastructureException,
)
from src.core.utils.uzbek_script import (
    StreamingScriptFixer,
    StreamingTransliterator,
    fix_mixed_script,
    to_cyrillic,
    to_latin,
)
from src.core.vectorstore.qdrant_store import QdrantStore
from src.knowledge import web_search
from src.knowledge.answer_helpers import (
    _BARE_IP_RE,
    _BRANCH_LABEL,
    _BROAD_QUESTION_STOPWORDS,
    _CATEGORY_GENERIC,
    _CATEGORY_KEYWORDS,
    _CLARIFY_MAX_OPTIONS,
    _CURRENCY_ALIASES,
    _EMPLOYEE_HINT_MAX_CHARS,
    _GENERIC_TITLE_WORDS,
    _RATE_CHANNEL_HINTS,
    _RESPONSIBLE_STEMS,
    _asks_about_organization,
    _asks_for_advice,
    _asks_general_meaning,
    _blind_employee_guess,
    _bot_reply,
    _branch_other_topic,
    _category_from_text,
    _clarify_reply,
    _clean_concept_answer,
    _ConceptLineFilter,
    _declined_clarify_titles,
    _dedupe_source_links,
    _employees_from_payloads,
    _expand_query,
    _format_employee_answer,
    _format_history,
    _guard_input,
    _has_employee_intent,
    _is_generic_employee_request,
    _is_meaningless_query,
    _is_ru_doc,
    _is_web_lookup,
    _is_web_not_found,
    _keyword_hit,
    _last_turn_was_clarify,
    _localize,
    _match_by_number,
    _match_employees,
    _mentions_catalog_title,
    _merge_results,
    _narrow_by_title,
    _norm_apostrophes,
    _norm_for_match,
    _numbers_in,
    _question_region,
    _rates_calculation,
    _rates_to_cyrillic,
    _region_of,
    _resolve_clarification,
    _resolve_list_choice,
    _strip_stray_followup,
    _text_words,
    _translit_preserving_titles,
    _web_eligible,
    _web_prompt,
    _web_sources,
    _with_lang,
    _word_match,
    _words,
)
from src.knowledge.directory import users_by_ip, users_with_ip, users_with_keywords
from src.knowledge.ingest_usecases import (
    DeleteKnowledgeUseCase,
    GetKnowledgeDetailUseCase,
    ListKnowledgeUseCase,
    ScrapeUrlUseCase,
    SetKnowledgeValidityUseCase,
    UpdateKnowledgeUseCase,
    UploadEmployeesUseCase,
    UploadKnowledgeUseCase,
    UploadPdfUseCase,
)
from src.knowledge.lang import ReplyLang, detect_reply_lang
from src.knowledge.prompts import (
    CONCEPT_SYSTEM,
    CONCEPT_WEB_ADDENDUM,
    EMPLOYEE_ASK_REPLY,
    EMPLOYEE_NOT_FOUND_REPLY,
    EMPLOYEE_SYSTEM,
    HARMFUL_REPLY,
    HISTORY_SYSTEM,
    INJECTION_REPLY,
    LANGUAGE_SYSTEM,
    NO_INFO_REPLY,
    OFF_TOPIC_REPLY,
    OTHER_BANK_REPLY,
    PROFANITY_REPLY,
    QUERY_REWRITE_SYSTEM,
    RAG_WEB_ADDENDUM,
    RATES_PANEL_HINT,
    RATES_SYSTEM,
    STRICT_RAG_SYSTEM,
    VERIFY_FAILED_REPLY,
    WEB_LOOKUP_TOKEN,
    WEB_NOT_FOUND_TOKEN,
    WEB_RAG_SYSTEM,
)
from src.knowledge.rates_scraper import RATES_TITLE, RATES_URL, channel_lines
from src.knowledge.router import Intent, QuestionRouter, Route
from src.knowledge.schemas import (
    AnswerResult,
    ChatTurn,
    SourceRef,
)
from src.knowledge.validity import is_expired, penalize_expired
from src.knowledge.verifier import verify_answer
from src.main.config import config

logger = get_logger(__name__)

__all__ = [
    "AnswerQuestionUseCase",
    "DeleteKnowledgeUseCase",
    "GetKnowledgeDetailUseCase",
    "ListKnowledgeUseCase",
    "ScrapeUrlUseCase",
    "SetKnowledgeValidityUseCase",
    "UpdateKnowledgeUseCase",
    "UploadEmployeesUseCase",
    "UploadKnowledgeUseCase",
    "UploadPdfUseCase",
]

class AnswerQuestionUseCase:
    """RAG: savolni embed qiladi, Qdrant'dan eng yaqin bo'laklarni topadi va
    ularni kontekst sifatida Qwen'ga berib javob oldiradi."""

    # Bitta mahsulotning bir necha bo'lagi bo'ladi (masalan omonatning aniq
    # shartlari alohida qisqa bo'lakda) — hammasi tushishi uchun yetarlicha keng.
    # 8 -> 10: chegara kontekst byudjeti edi, u num_ctx=16384 bilan ikki
    # baravar bo'shadi. Ortiqcha bo'laklar baribir MAX_CONTEXT_CHARS da
    # kesiladi, ya'ni bu "topilsa tushsin" zaxirasi.
    TOP_K = 10
    TEMPERATURE = 0.2
    # 2048 token ~ 6500 belgi o'zbekcha matn. Bu limit num_ctx ichidan JOY
    # BAND QILADI — 8192 oynada 1536 dan oshirib bo'lmasdi, 16384 da esa
    # bemalol. Odatdagi javob 500 tokendan qisqa; limit faqat eng batafsil
    # mahsulot javobi o'rtasidan uzilmasligi uchun kerak.
    MAX_TOKENS = 2048
    # Xodimlar ro'yxati uchun alohida, kattaroq limit: katta bo'limda 30+ xodim
    # bo'ladi va 2048 token yetmay, javob o'rtasida kesilib qolardi.
    EMPLOYEE_MAX_TOKENS = 6000
    # Umumiy (soha) savoli — javob 2-5 gap. Kichik limit ATAYIN: joy
    # yetishmagani uchun emas, javob qisqa bo'lishi KERAK bo'lgani uchun —
    # model uzoq "ma'ruza" yozib ketmasin.
    CONCEPT_MAX_TOKENS = 500
    # Til savoli (so'z ma'nosi, tarjima, matnni tuzatish). Odatda 100-200
    # token; 1200 — foydalanuvchi uzunroq matnni tuzattirganda kesilmasin.
    LANGUAGE_MAX_TOKENS = 1200
    # Promptga qo'shiladigan oxirgi xabarlar soni. 6 -> 8: chegara byudjet
    # edi, u 16384 oyna bilan bo'shadi. Mavzu bir necha almashuv oldin
    # aytilgan bo'lishi mumkin ("kompaniya" -> Visa) — kengroq oyna
    # olmoshlarni to'g'ri yechishga bevosita yordam beradi.
    HISTORY_LIMIT = 8
    # --- Prompt byudjeti (belgilarda) ---------------------------------- #
    # num_ctx = 32768 token (config.ai.OLLAMA_NUM_CTX; 96 GB GPU'ga o'tilganda
    # 16384 dan ko'tarildi). Quyidagi hisob 16384 uchun yozilgan va hozir ham
    # sig'adi — zaxira endi ~21 000 token. Chegaralarni oshirish mumkin, lekin
    # uzunroq prompt javobni sekinlashtiradi, shuning uchun hozircha tegmadik.
    # O'zbek lotinida ~3.2 belgi = 1 token.
    #
    # HAMMASI SHU OYNAGA SIG'ISHI KERAK — system prompt, kontekst, katalog,
    # suhbat tarixi VA javob. Sig'masa Ollama promptning BOSHINI jimgina
    # kesib tashlaydi, ya'ni birinchi bo'lib SYSTEM PROMPT yo'qoladi va model
    # barcha qoidalarni "unutadi" (javob inglizcha chiqadi, raqamlar to'qib
    # chiqariladi). Xato xabari berilmaydi — shuning uchun byudjet shu yerda
    # aniq yozilgan.
    #
    # Joriy hisob (eng yomon holat — hamma chegara to'lgan):
    #   STRICT_RAG_SYSTEM  ~3 885 token   (prompts.py — o'lchash: len(s)/3.2)
    #   MAX_CONTEXT_CHARS   3 000 token   (9600 belgi)
    #   MAX_CATALOG_CHARS     940 token   (3000 belgi)
    #   MAX_HISTORY_CHARS     940 token   (3000 belgi)
    #   MAX_TOKENS (javob)  2 048 token
    #   ────────────────────────────────
    #   JAMI               ~10 815 token  -> 16384 dan ~5 570 token zaxira
    #
    # TARIX (nega bu izoh shu qadar batafsil): prompt bir vaqtlar oynadan
    # oshib ketib, system prompt jimgina kesilardi. Xato har savolda emas,
    # faqat "og'ir" savolda yuz bergani uchun beqaror ko'rinardi.
    #
    # Chegaralar avval juda tor edi (kontekst 4000, tarix 1200, xabar 300
    # belgi) — chunki oyna 8192 edi va o'sha 8192 ga hammasi zo'rg'a
    # sig'ardi. Oqibati: mahsulot konteksti kesilib, javobda shartlarning
    # bir qismi yetishmasdi; suhbat tarixi kesilib, model oldingi mavzuni
    # ("kompaniya" kim edi) yo'qotardi. Model GPU'da ishlagani aniqlangach
    # oyna 16384 ga ko'tarildi va chegaralar shunga yarasha bo'shatildi.
    #
    # DIQQAT: STRICT_RAG_SYSTEM ga yangi qoida qo'shishdan yoki quyidagi
    # CHARS chegaralarini oshirishdan OLDIN shu hisobni qayta chiqaring.
    MAX_CONTEXT_CHARS = 9600
    MAX_CATALOG_CHARS = 3000
    MAX_HISTORY_CHARS = 3000
    MAX_HISTORY_MSG_CHARS = 800
    # Umumiy (soha) savolida kontekst ham, katalog ham promptga kirmaydi —
    # ~4000 token bo'shaydi. Tarixni kengroq beramiz: mavzuni ("kompaniya" kimi)
    # aniqlash aynan tarixdan bilinadi, kesilgan javobda esa u yo'qolib
    # ketishi mumkin.
    CONCEPT_HISTORY_CHARS = 4800
    CONCEPT_HISTORY_MSG_CHARS = 1200
    # Savol suhbatning O'ZI haqida bo'lsa — javob tarixda turibdi, shuning
    # uchun tarix yana kengroq beriladi va xabar deyarli kesilmaydi.
    HISTORY_ANSWER_MAX_TOKENS = 700
    HISTORY_CTX_CHARS = 6400
    HISTORY_CTX_MSG_CHARS = 2000
    # Eng yaqin bo'lakning cosine o'xshashligi shundan past bo'lsa — savol bazaga
    # aloqasiz (bema'ni yoki mavzudan tashqari) deb hisoblaymiz va LLM'ni umuman
    # chaqirmasdan tayyor "ma'lumotim yo'q" javobini qaytaramiz (tez javob uchun).
    #
    # PAST chegara ATAYIN: avval 0.35 edi va bu erkin yozilgan (tugma orqali
    # emas) savollarning ko'pini LLM'ga yetib bormasdan turib rad etardi —
    # foydalanuvchi "faqat tugmalar ishlayapti" deb shikoyat qilgan sabab shu.
    # Endi faqat CHINDAN aloqasiz (bema'ni) savol kesiladi; qolganida
    # kontekst LLM'ga beriladi va u yetarli ma'lumot yo'qligini o'zi aytadi.
    # Chegara `.env` dan boshqariladi (RAG_MIN_SCORE): real ballarni loglardan
    # ko'rib, javoblarni qattiqroq yoki yumshoqroq qilish mumkin — kodni qayta
    # qurmasdan.
    MIN_SCORE = config.ai.RAG_MIN_SCORE

    def __init__(
        self,
        embedder: OllamaEmbedder,
        store: QdrantStore,
        ai_client: BaseAIClient,
    ) -> None:
        self.embedder = embedder
        self.store = store
        self.ai_client = ai_client
        # Savolni javobdan OLDIN tushunadigan bosqich (o'ylash shu yerda yoqiq)
        self.router = QuestionRouter(ai_client)
        # Oxirgi execute_stream natijasi — savollar statistikasi (question_logs)
        # uchun. Router oqim tugagach o'qiydi; javob oqimiga aralashmaydi.
        self.last_intent: str | None = None
        self.last_outcome: str = "answered"
        self.last_top_score: float | None = None
        # "flagged" bo'lganda sabab: "harmful" (router) yoki "profanity" (lug'at)
        self.last_flag: str | None = None
        # Bitta so'rov davomidagi baza keshi (_scroll_points)
        self._points: list[dict[str, Any]] | None = None
        # Bilim bazasining qaysi tilidagi hujjatlardan javob beriladi: ruscha
        # savolda "ru" (ruscha hujjat bo'lsa), aks holda "uz". execute /
        # execute_stream boshida o'rnatiladi.
        self._kb_lang = "uz"
        # Javob tekshiruvi (qara: execute_stream, verifier.py)
        self.last_verdict: str | None = None
        self.last_verdict_note: str | None = None
        self._retry_hint: str | None = None
        self._last_context: str | None = None
        self._effective_question: str | None = None
        self._buf_text = ""
        self._buf_done: dict[str, Any] | None = None

    @staticmethod
    def _category_label(source_url: str, title: str = "", text: str = "") -> str:
        """Mahsulot turkumini aniqlaydi — katalogni guruhlash uchun
        (kartalar / kreditlar / omonatlar / filiallar ...).

        Asosiy belgi — HAVOLA. Havola bo'lmasa (qo'lda kiritilgan yoki eski
        tahrirdan keyin havolasi yo'qolgan yozuv) turkum MATNDAN aniqlanadi:
        aks holda yozuv "Boshqa xizmatlar"ga tushib, "Omonatlar" kabi
        ro'yxatlarda umuman ko'rinmasdi."""
        # Filiallar saytda "filial" deb emas, "bank xizmatlari markazi/ofisi"
        # deb nomlangan — turkumni SARLAVHA bo'yicha aniqlaymiz.
        t = title.lower()
        if "bank xizmatlari markazi" in t or "bank xizmatlari ofisi" in t:
            return _BRANCH_LABEL
        url = source_url.lower()
        # Nomi boshqacha bo'lgan bo'linmalar ham bor ("Biznesni rivojlantirish
        # markazi") — ular sarlavha bo'yicha aniqlanmay, filiallar ro'yxatiga
        # umuman tushmasdi. URL'dagi /branches/ bo'limi ishonchli belgi.
        if "/branches/" in url:
            return _BRANCH_LABEL
        if "plastic-card" in url or "/cards" in url or "karta" in url:
            return "Bank kartalari"
        if "credit" in url or "loan" in url or "kredit" in url:
            return "Kreditlar"
        if "deposit" in url or "omonat" in url:
            return "Omonatlar"
        if "transfer" in url or "otkazma" in url or "o-tkazma" in url:
            return "Pul o'tkazmalari"
        if not url:
            return _category_from_text(title, text)
        return "Boshqa xizmatlar"

    async def _catalog_groups(self) -> dict[str, list[str]]:
        """Bazadagi BARCHA mahsulotlarning to'liq ro'yxati (title bo'yicha noyob),
        turkumlarga ajratilgan (faqat nomlar, URL'siz). _build_catalog (LLM uchun
        matn) va _broad_category_reply (keng savolga deterministik javob) shu
        yerdan foydalanadi."""
        detailed = await self._catalog_groups_detailed()
        return {cat: [t for t, _ in items] for cat, items in detailed.items()}

    async def _catalog_groups_detailed(self) -> dict[str, list[tuple[str, str]]]:
        """_catalog_groups bilan bir xil, lekin har bir mahsulot uchun uning
        BUTUN matni ham qaytariladi: (nom, to'liq matn).

        Matn kerak, chunki foydalanuvchi turkum ichida QO'SHIMCHA shart bilan
        so'rashi mumkin ("Toshkentdagi filiallar") — manzil/hudud faqat
        mahsulot matnida bo'ladi, nomida emas."""
        # BUTUN baza sahifalab o'qiladi. Ilgari `scroll_all(limit=2000)` edi —
        # ya'ni katalog faqat BIRINCHI 2000 bo'lakdan yig'ilardi. Baza o'sgach
        # (xodimlar bo'laklari ham shu 2000 tani yeydi) ayrim mahsulotlar
        # ro'yxatdan tushib qolardi: "Omonatlar" so'ralganda «Meros omonati»
        # chiqmay qo'ygan edi, garchi bazada tursa ham.
        payloads = await self._scroll_points()

        def build(ru: bool) -> dict[str, list[tuple[str, str]]]:
            # title bo'yicha noyob mahsulotlar (birinchi uchragan source_url
            # bilan). Xodimlar (doc_type=employee) mahsulot katalogiga kirmaydi.
            urls: dict[str, str] = {}
            texts: dict[str, list[str]] = {}
            for p in payloads:
                if p.get("doc_type") == "employee" or _is_ru_doc(p) != ru:
                    continue
                title = str(p.get("title", "")).strip()
                if not title:
                    continue
                urls.setdefault(title, str(p.get("source_url", "")))
                # Bitta mahsulot bir necha bo'lakdan iborat — hammasini
                # yig'amiz, manzil qaysi bo'lakda bo'lishidan qat'i nazar topilsin.
                texts.setdefault(title, []).append(str(p.get("chunk_text", "")))

            groups: dict[str, list[tuple[str, str]]] = {}
            for title, url in urls.items():
                body = " ".join(texts[title])
                label = self._category_label(url, title, body)
                groups.setdefault(label, []).append((title, body))
            return groups

        uz_groups = build(ru=False)
        if self._kb_lang != "ru":
            return uz_groups
        # Ruscha savol: turkum ruscha hujjatlar bilan TO'LIQ qamralgan bo'lsa
        # (kamida o'zbekchadagicha) — ruscha nomlar. Aks holda o'zbekcha
        # ro'yxat qoladi: ruschasi qisman qo'shilgan turkumda mahsulotlar
        # ro'yxatdan tushib qolmasin (model o'zbekcha matnni tarjima qiladi).
        # Bitta mahsulotning ikki tildagi nomi BIR ro'yxatga aralashmaydi.
        ru_groups = build(ru=True)
        merged: dict[str, list[tuple[str, str]]] = {}
        for label in {**uz_groups, **ru_groups}:
            uz_items = uz_groups.get(label, [])
            ru_items = ru_groups.get(label, [])
            merged[label] = ru_items if len(ru_items) >= len(uz_items) else uz_items
        return merged

    async def _build_catalog(self, question: str = "") -> str:
        """Semantik qidiruv faqat eng yaqin bir nechtasini topadi — bu esa keng
        savolga ("barcha kredit turlari") TO'LIQ javob berish uchun katalogni
        matn ko'rinishida beradi.

        Katalog SAVOLGA TEGISHLI turkum bilan cheklanadi. Ilgari har safar
        BUTUN katalog (filiallar bilan birga — yuzlab nom) qo'shilardi va
        yolg'iz o'zi ~2200 token joy egallab, promptni num_ctx dan chiqarib
        yubordi. Filiallar ro'yxati bundan tashqari deterministik yo'l bilan
        (_branch_reply) beriladi, ya'ni promptda takrorlanishi shart emas."""
        groups = await self._catalog_groups()
        if not groups:
            return ""
        q = _norm_apostrophes(to_latin(question).lower())
        wanted = [
            label
            for label, keywords in _CATEGORY_KEYWORDS.items()
            if label in groups and any(kw in q for kw in keywords)
        ]
        if wanted:
            # Aniq turkum so'ralgan — o'sha turkum TO'LIQ beriladi (sanab
            # o'tish savoliga bitta mahsulot ham tushib qolmasligi kerak).
            groups = {label: groups[label] for label in wanted}
        else:
            groups = {k: v for k, v in groups.items() if k != _BRANCH_LABEL}

        blocks: list[str] = []
        used = 0
        for cat, items in groups.items():
            block = f"### {cat}\n" + "\n".join(f"- {t}" for t in items)
            if blocks and used + len(block) > self.MAX_CATALOG_CHARS:
                break
            blocks.append(block)
            used += len(block)
        return "\n\n".join(blocks)

    async def _catalog_title_match(
        self, question: str
    ) -> tuple[str | None, list[str]]:
        """Savolda bazadagi mahsulot NOMI aytilganmi.

        Qaytaradi: (aniq_nom, qisman_mos_nomlar).
          * aniq_nom — nomning BARCHA so'zi savolda bor ("meros omonati" ->
            «Meros omonati»): javob bazadan beriladi;
          * qisman — nomning o'ziga xos so'zi bor, lekin nom to'liq aytilmagan
            ("meros"): javob to'qilmaydi, aniqlashtirib so'raladi.

        Turkum so'zigina mos kelgan nomlar (`_GENERIC_TITLE_WORDS`) qisman
        moslikka KIRMAYDI — aks holda "kredit" so'zi bor har qanday umumiy
        savolga qayta savol berilardi.
        """
        groups = await self._catalog_groups_detailed()
        if not groups:
            return None, []
        qwords = set(
            _words(_norm_for_match(_norm_apostrophes(to_latin(question).lower())))
        )
        if not qwords:
            return None, []

        exact, exact_len = None, 0
        partial: list[str] = []
        for items in groups.values():
            for title, _ in items:
                toks = [t for t in _words(_norm_for_match(to_latin(title))) if len(t) >= 3]
                if not toks:
                    continue
                common = [t for t in toks if t in qwords]
                if not common:
                    continue
                if len(common) == len(toks):
                    # To'liqroq nom ustun ("Tez pul mikroqarz" > "Mikroqarz")
                    if len(title) > exact_len:
                        exact, exact_len = title, len(title)
                else:
                    # Qisman moslik faqat nomning O'ZIGA XOS qismi TO'LIQ
                    # aytilganda: "meros" -> «Meros omonati» (yetishmagani
                    # faqat turkum so'zi). Ilgari BITTA tasodifiy so'z yetardi:
                    # "...banklar BILAN hamkorlik" -> «Biz bilan bog'lanish»,
                    # "tez" -> «Tez pul mikroqarz» — bot savol ma'nosini
                    # tashlab, o'sha sahifa haqida so'rab qolardi.
                    distinct = [t for t in toks if t not in _GENERIC_TITLE_WORDS]
                    if distinct and all(t in qwords for t in distinct):
                        partial.append(title)
        # Bittadan ko'p bo'lsa ham chegaradan ortig'i kerak emas: chaqiruvchi
        # faqat "nechta" ekanini biladi va ko'p bo'lsa aniqlashtirmaydi.
        return exact, partial[: _CLARIFY_MAX_OPTIONS + 1]

    async def _broad_category_reply(
        self, question: str, want_cyrillic: bool
    ) -> tuple[str | None, str | None]:
        """(tayyor_javob, aniqlangan_mahsulot_nomi) qaytaradi.

        Ikkinchi qiymat — savol turkum ichida ayni BITTA mahsulotga toraysa
        ("Yunusobod filiali" -> bitta ofis) qaytariladi: bunda ro'yxat berib
        "qaysi biri?" deb so'rash ma'nosiz, chaqiruvchi savolni shu nom bilan
        almashtirib to'g'ridan-to'g'ri batafsil javob beradi.

        Savol aniq bir mahsulotni emas, balki butun turkumni so'rasa (masalan
        "omonatlar", "kredit turlari") — nomlarni katalogdan DETERMINISTIK
        tarzda, LLM'ni chaqirmasdan, raqamlangan ro'yxat qilib qaytaradi.

        LLM'ga qoldirilganda format izchil bo'lmay qolgan (masalan "Omonatlar"
        uchun ba'zan vergul bilan sanab o'tish, ba'zan raqamlangan ro'yxat
        chiqib turgan) — bu yerda natijani kodning o'zi kafolatlaydi. Bunga
        qo'shimcha: keyingi "3-bandni tanladim" javobi ham FAQAT raqamlangan
        "N. nom" formatidan ishlaydi (_resolve_list_choice), shuning uchun
        format barqarorligi funksional jihatdan ham muhim.

        Mahsulot NOMLARI (Visa, MasterCard, UzCard kabi brend nomlari ham bor)
        kirillcha bo'lsa ham HAR DOIM lotincha qoladi — ularni harf-baharf
        kirillga o'girish g'alati ko'rinardi; faqat atrofidagi savol matni
        o'giriladi."""
        groups = await self._catalog_groups_detailed()
        if not groups:
            return None, None

        # Turkum kalit so'zlari va mahsulot nomlari LOTINCHA — savol kirillcha
        # yozilgan bo'lsa ("Кредит турлари") lotinga keltiramiz, aks holda
        # hech biri mos kelmay, ro'yxat o'rniga LLM javob berib qolardi.
        q = _norm_apostrophes(to_latin(question).lower())

        # Savolda aniq mahsulot NOMI tilga olinganmi. Uchta muhim nuqta:
        #  1) Qo'shtirnoqlar olib tashlanadi — nomlarda ular har xil ("Tez pul",
        #     “Green Avto”), foydalanuvchi esa ro'yxatdan nusxa ko'chiradi.
        #  2) Nomning BARCHA so'zi savolda bo'lishi shart. Ilgari faqat
        #     dastlabki 2 ta so'z tekshirilardi: `"Tez pul" mikroqarz` da bu
        #     faqat "mikroqarz" bo'lib, "mikroqarz" so'zi bor BIRINCHI nom
        #     (butunlay boshqa mahsulot) tanlanardi.
        #  3) Topilgan nom QAYTARILADI (ilgari tashlab yuborilardi) — shunda
        #     chaqiruvchi taxminiy vektor qidiruv o'rniga aynan shu sarlavha
        #     bo'laklarini oladi.
        qwords_n = set(_words(_norm_for_match(q)))
        best_title, best_title_score = "", 0
        for items in groups.values():
            for title, _ in items:
                toks = [t for t in _words(_norm_for_match(to_latin(title))) if len(t) >= 3]
                if not toks or not all(t in qwords_n for t in toks):
                    continue
                # Uzunroq/to'liqroq nom ustun ("Tez pul mikroqarz" > "Mikroqarz")
                score = sum(len(t) for t in toks)
                if score > best_title_score:
                    best_title_score, best_title = score, title
        if best_title:
            return None, best_title

        # Savol MASLAHAT so'rayapti ("mashina uchun qaysi kreditni tavsiya
        # qilasan") — tayyor ro'yxat javob emas. Modelga beramiz.
        if _asks_for_advice(q):
            return None, None

        for label, keywords in _CATEGORY_KEYWORDS.items():
            items = groups.get(label)
            if not items or not any(kw in q for kw in keywords):
                continue

            # Filiallar — yagona turkum, unda toraytirish ISHONCHLI bajariladi:
            # shart har doim HUDUD bo'ladi va hudud ma'lumotning o'zida yozilgan.
            if label == _BRANCH_LABEL:
                # Savol ro'yxat emas, filiallar HAQIDA boshqa narsani so'rasa
                # ("filiallar tarmog'ini kengaytirish rejalari") — modelga.
                if _branch_other_topic(q, items):
                    return None, None
                return self._branch_reply(q, items, want_cyrillic)

            # Savolda turkum nomidan TASHQARI so'z bormi. Turkumning O'ZINI
            # bildiruvchi so'z (_CATEGORY_GENERIC) hisobga olinmaydi, lekin
            # TUR nomi ("ipoteka", "avtokredit", "mikroqarz") hisobga olinadi.
            # Ilgari bu yerda butun _CATEGORY_KEYWORDS chiqarib tashlanardi va
            # "ipoteka" ham o'sha ro'yxatda turgani uchun "Ipoteka kreditlari"
            # so'rovi "qo'shimcha shartsiz" deb qabul qilinib, BARCHA 20 ta
            # kredit qaytarilardi.
            # MUHIM: apostrofni OLIB TASHLAB bo'laklaymiz. `_words` apostrofni
            # so'z chegarasi deb biladi va "o'tkazmalari" -> "o" + "tkazmalari"
            # bo'lib ketardi.
            generic = _CATEGORY_GENERIC.get(label, keywords)
            extra = [
                w for w in _words(q.replace("'", ""))
                if len(w) >= 4
                and w not in _BROAD_QUESTION_STOPWORDS
                and not any(w.startswith(g) or g.startswith(w) for g in generic)
            ]
            shown = items
            if extra:
                narrowed = _narrow_by_title(extra, items)
                # Qo'shimcha so'z mahsulot NOMLARINI ajratmadi — demak bu shart
                # mahsulot XUSUSIYATI ("milliy valyutadagi omonatlar",
                # "xalqaro kartalar"). Uni so'z moslash bilan hal qilib
                # bo'lmaydi (dollardagi "Turon Oltin" milliy valyuta ro'yxatiga
                # tushib qolgan edi) — modelga beramiz, u matnni o'qiydi.
                if narrowed is None:
                    return None, None
                # Ayni bitta mahsulot qoldi — ro'yxat berib "qaysi biri?" deb
                # so'rash keraksiz, darrov shu bo'yicha javob beriladi.
                if len(narrowed) == 1:
                    return None, narrowed[0][0]
                shown = narrowed

            numbered = "\n".join(f"{i}. {t}" for i, (t, _) in enumerate(shown, 1))
            closing = (
                "Shu turlardan qaysi biri bo'yicha batafsil ma'lumot beray? "
                "Nomini yoki tartib raqamini yozing."
            )
            if want_cyrillic:
                closing = to_cyrillic(closing)
            return f"{numbered}\n\n{closing}", None
        return None, None

    @staticmethod
    def _branch_reply(
        q: str, items: list[tuple[str, str]], want_cyrillic: bool
    ) -> tuple[str | None, str | None]:
        """Filiallar ro'yxati, kerak bo'lsa HUDUD bo'yicha toraytirilgan.

        Toraytirish ma'lumotdan ajratilgan hudud bo'yicha ketadi (_region_of),
        savoldagi so'zlar bo'yicha emas — sabab _ADMIN_RE izohida."""
        regions = {
            title: _region_of(f"{title} {text}") for title, text in items
        }
        known = {key for key, _, _ in regions.values() if key}
        want_key, want_level = _question_region(q, known)

        shown = items
        note = ""
        if want_key:
            matched = [
                (t, x)
                for t, x in items
                if regions[t][0] == want_key
                and (not want_level or regions[t][1] == want_level)
            ]
            if not matched:
                # Bu hududda filial yo'q — ro'yxat o'rniga model javob bersin.
                return None, None
            # Ayni bitta filial qoldi — "qaysi biri?" deb so'rash keraksiz.
            if len(matched) == 1:
                return None, matched[0][0]
            shown = matched
            _, level, display = regions[matched[0][0]]
            level_word = "shahridagi" if level == "shahar" else "viloyatidagi"
            note = (
                f"{display.capitalize()} {level_word} bank xizmatlari "
                f"markazlari va ofislari:\n\n"
            )

        numbered = "\n".join(f"{i}. {t}" for i, (t, _) in enumerate(shown, 1))
        closing = (
            "Qaysi biri bo'yicha batafsil ma'lumot beray? "
            "Nomini yoki tartib raqamini yozing."
        )
        if want_cyrillic:
            closing = to_cyrillic(closing)
            note = to_cyrillic(note)
        return f"{note}{numbered}\n\n{closing}", None

    async def _lookup_by_ip_field(self, q_lower: str) -> list[dict[str, Any]]:
        """Savoldagi 3-5 xonali raqamni Qdrant'da `ip` payload maydoni bo'yicha
        ANIQ qidiradi. scroll natijasiga bog'liq emas."""
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for n in re.findall(r"\b\d{3,5}\b", q_lower):
            for p in await self.store.search_by_field("ip", n, limit=60):
                if p.get("doc_type") != "employee":
                    continue
                key = f"{p.get('fish', '')}|{p.get('ip', '')}"
                if key not in seen:
                    seen.add(key)
                    out.append(p)
        return out

    async def _directory_hits(self, question: str) -> list[dict[str, Any]]:
        """Xodimlar MA'LUMOTNOMASI (users jadvali) — vektor bazadan OLDIN.

        * ichki raqam so'rovi ("2206", "2206 kimniki", "ip 2206") — xodimlar
          o'zi kiritgan IP raqam bo'yicha;
        * "EDO ga kim qaraydi" — admin qo'ygan kalit so'z bo'yicha.
        Bo'sh ro'yxat — topilmadi, odatdagi yo'l (router, vektor baza) davom
        etadi."""
        q_lower = question.lower()
        if len(q_lower) > _EMPLOYEE_HINT_MAX_CHARS:
            return []
        nums = set(re.findall(r"\b\d{3,4}\b", q_lower))
        # Raqam faqat aniq IP so'rovida: "2025-yil" yoki "1000 dollar" ichki
        # raqam emas.
        if nums and (_has_employee_intent(q_lower) or _BARE_IP_RE.fullmatch(q_lower)):
            return await users_by_ip(nums)
        qwords = _text_words(q_lower)
        if not any(w.startswith(_RESPONSIBLE_STEMS) for w in qwords):
            return []
        return [
            rec
            for kws, rec in await users_with_keywords()
            if any(_keyword_hit(k, qwords) for k in kws)
        ]

    async def _employee_route(
        self, question: str
    ) -> tuple[str, list[dict[str, Any]]] | None:
        """Savol xodim (telefon/IP) haqida bo'lsa yo'naltiradi:
        ("answer", [xodimlar]) — mos xodim(lar) topildi;
        ("ask", []) — umumiy so'rov, aniqlashtirish kerak;
        None — bu xodim savoli emas (mahsulot RAG'ga o'tadi)."""
        # Xodimlarni doc_type filtri bilan TO'LIQ sahifalab olamiz — 5000'lik
        # scroll_all cheklovi kolleksiya kattalashganda xodimlarni "yo'qotib"
        # qo'yardi (shuning uchun bir xil savol goh topib, goh topmasdi).
        q_lower = question.lower()
        # 1-MANBA: xodimlarning o'zi kiritgan raqamlar ro'yxati (users jadvali).
        # U vektor bazadagi yuklangan fayldan yangiroq. Xuddi shu qoidalar
        # (raqam -> bo'lim -> ism) bilan qidiriladi; topilmasa vektor bazaga.
        users = await users_with_ip()
        by_number = _match_by_number(users, q_lower)
        if by_number:
            return "answer", by_number[:60]

        # ASOSIY YO'L: filtrsiz to'liq sahifalab olib, Python'da ajratamiz.
        # Ilgari bu yerda Qdrant payload filtri (scroll_by_field) ishlatilardi —
        # lekin xodim qidiruvi ishlamay qolgani shunga ishora qilmoqda, chunki
        # ayni shu yozuvlarni vektor qidiruv muammosiz topadi. Python filtri
        # hech qanday Qdrant indeksiga bog'liq emas va ilgari ishlagan usul.
        all_points = await self._scroll_points()
        emps = [p for p in all_points if p.get("doc_type") == "employee"]
        if not emps:
            # Strukturaviy maydonlar yo'q — xodimlarni MATNDAN ajratib olamiz.
            # Ma'lumot qanday yuklangan bo'lishidan qat'i nazar ishlaydi.
            emps = _employees_from_payloads(all_points)
        if not emps and not users:
            # Ro'yxat baribir bo'sh — hech bo'lmasa raqam bo'yicha ANIQ
            # payload qidiruvini sinab ko'ramiz.
            direct = await self._lookup_by_ip_field(q_lower)
            return ("answer", direct[:60]) if direct else None

        # Eng kuchli signal: savoldagi raqam biror xodimning IP/telefoniga aniq
        # mos kelsa — bu direktoriya so'rovi. Katalog-title bostiruvidan OLDIN
        # tekshiramiz, aks holda yalang'och "2206" mahsulot RAG'iga ketib qolardi.
        by_number = _match_by_number(emps, q_lower)
        if not by_number:
            # Zaxira: Qdrant'dan TO'G'RIDAN-TO'G'RI `ip` maydoni bo'yicha.
            # scroll bilan hamma xodimni yuklab Python'da solishtirish
            # kolleksiya kattalashganda ishonchsiz; bu esa aniq payload
            # filtri — bitta so'rov, hech narsa tushib qolmaydi.
            by_number = await self._lookup_by_ip_field(q_lower)
        if by_number:
            return "answer", by_number[:60]
        # Savolda bazadagi mahsulot/filial NOMI bo'lsa (va aniq xodim-niyat
        # bildirilmagan bo'lsa) — bu mahsulot savoli. Xodim qidiruvini umuman
        # sinamaymiz: aks holda "Yunusobod" kabi joy nomi xodim ismining
        # boshiga tasodifan mos kelib, butunlay boshqa javob qaytarardi.
        if not _has_employee_intent(q_lower):
            catalog = await self._scroll_points()
            titles = {
                str(p.get("title", ""))
                for p in catalog
                if p.get("doc_type") != "employee"
            }
            if _mentions_catalog_title(q_lower, sorted(t for t in titles if t)):
                return None

        # Avval users ro'yxatidan, keyin vektor bazadagi xodimlardan
        matched = _match_employees(users, q_lower) if users else []
        if not matched and emps:
            matched = _match_employees(emps, q_lower)
        if matched:
            # Javobni endi kod tuzadi (model emas), shuning uchun token cheklovi
            # yo'q — katta bo'lim ham to'liq chiqadi.
            return "answer", matched[:200]
        if _is_generic_employee_request(question.lower()):
            return "ask", []
        # Savol ANIQ xodim haqida, lekin moslik topilmadi. Mahsulot RAG'iga
        # o'tkazmaymiz: u yerda vektor qidiruv BOSHQA bo'lim xodimlarini
        # qaytarardi va model shular asosida mavjud bo'lmagan xodimlarni,
        # ketma-ket soxta IP va telefon raqamlarini to'qib chiqargan edi.
        # Bu holda model umuman chaqirilmaydi — tayyor matn qaytariladi.
        if _has_employee_intent(q_lower):
            return "none", []
        return None

    REWRITE_MAX_TOKENS = 120

    async def _results_by_title(
        self, title: str
    ) -> list[tuple[dict[str, Any], float]]:
        """Sarlavha ANIQ ma'lum bo'lganda (ro'yxatdan raqam tanlangan yoki
        turkum ichida bitta mahsulot qoldi) — vektor qidiruvga tayanmaymiz.

        Sabab: "16" deb tanlaganda savol "Sirdaryo bank xizmatlari markazi"ga
        almashtirilardi, lekin embedding qidiruvi BOSHQA filialning bo'lagini
        qaytarib, Sirdaryo sarlavhasi ostida Termiz manzili chiqib ketardi.
        Aniq sarlavha bor joyda taxminiy qidiruvning hojati yo'q."""
        payloads = await self.store.search_by_field("title", title, limit=40)
        if not payloads:
            # Ro'yxatdan tanlangan nom lotinga o'girilgan bo'ladi
            # (_resolve_list_choice), ruscha hujjat sarlavhasi esa kirillcha
            # ("Автокредит ..." -> "Avtokredit ..."). Bazadagi sarlavhani
            # lotinlashtirilgan ko'rinishi bo'yicha topamiz.
            key = _norm_for_match(to_latin(title))
            for p in await self._scroll_points():
                stored = str(p.get("title", ""))
                if stored and stored != title and _norm_for_match(to_latin(stored)) == key:
                    payloads = await self.store.search_by_field(
                        "title", stored, limit=40
                    )
                    break
        payloads.sort(key=lambda p: int(p.get("chunk_index", 0)))
        return [(p, 1.0) for p in payloads]

    # Leksik qidiruvdan qo'shiladigan bo'laklar soni. Vektor natijalari
    # ustiga qo'shiladi, ularni almashtirmaydi.
    LEXICAL_TOP_K = 4

    async def _load_rates(self) -> dict[str, Any] | None:
        """Bazadagi oxirgi kurs ma'lumoti (kunlik Celery vazifasi yozadi)."""
        payloads = await self.store.search_by_field("title", RATES_TITLE, limit=40)
        data: dict[str, Any] | None = None
        for payload in payloads:
            raw = payload.get("rates_json")
            if not raw:
                continue
            try:
                data = json.loads(str(raw))
            except json.JSONDecodeError:
                logger.warning("rates_json o'qib bo'lmadi — RAG yo'liga o'tamiz")
                data = None
            break
        if not data or not data.get("channels"):
            return None
        return data

    @staticmethod
    def _rates_wanted(q: str) -> tuple[set[str], set[str]]:
        """Savolda aytilgan valyutalar va kanallar (bo'sh = hammasi)."""
        wanted_codes = {
            code
            for code, aliases in _CURRENCY_ALIASES.items()
            if any(a in q for a in aliases)
        }
        wanted_channels = {
            key
            for key, hints in _RATE_CHANNEL_HINTS.items()
            if any(h in q for h in hints)
        }
        return wanted_codes, wanted_channels

    @staticmethod
    def _rates_table(
        data: dict[str, Any],
        wanted_codes: set[str],
        wanted_channels: set[str],
    ) -> str:
        blocks: list[str] = []
        for channel in data["channels"]:
            if wanted_channels and channel.get("key") not in wanted_channels:
                continue
            rows = channel.get("rows", [])
            if wanted_codes:
                rows = [r for r in rows if str(r.get("code")) in wanted_codes]
            lines = channel_lines(rows)
            if not lines:
                continue
            blocks.append(
                f"{channel['label']}:\n" + "\n".join(f"* {line}" for line in lines)
            )
        if not blocks:
            return ""

        stamp = str(data.get("stamp", "")).strip()
        head = f"Valyuta kurslari — {stamp}" if stamp else "Valyuta kurslari"
        return f"{head}\n\n" + "\n\n".join(blocks) + f"\n\nBatafsil: {RATES_URL}"

    # Kurs javobi qisqa (2-6 qator)
    RATES_MAX_TOKENS = 600

    async def _rates_reply(
        self,
        question: str,
        search_query: str,
        history: list[ChatTurn] | None,
        lang: ReplyLang,
    ) -> tuple[str, int] | None:
        """Valyuta savoliga javob: (matn, model_tokenlari). Kurs bazada yo'q
        bo'lsa None — chaqiruvchi odatdagi RAG yo'liga o'tadi.

        Ishni ikkiga bo'lamiz:
          * KOD — faktlar: kerakli valyuta/kanal jadvali va savolda summa
            bo'lsa, konvertatsiya hisobi. Raqamlar shu yerda tug'iladi.
          * MODEL — shu faktlardan AYNAN berilgan savolga javob yozadi.
        Bundan oldin (2026-11-02 gacha) javobni faqat kod tuzardi — undan
        ham oldin modelga qoldirilganda u sanani buzar, kirish so'zi qo'shar
        va eski sekin serverda ~40 s ketardi. Kod esa savoldan bitta valyuta nomini
        ushlab, doim butun jadvalni chiqarardi: "120 dollar necha so'm?" ga
        ham hisob berilmasdi, "unda so'mda qancha?" ga esa (xabarda "dollar"
        yo'q) hamma valyutalar chiqardi.

        Routerning search_query'si ham qo'shiladi: u suhbatdan olmoshlarni
        yechadi ("shu summa" -> "120 AQSh dollari so'mda").

        Model javobidagi har bir son faktlarda (yoki savol/tarixda) bo'lishi
        SHART — aks holda model raqamni buzgan yoki o'zi hisoblagan bo'ladi va
        biz kod tuzgan javobga (hisob + jadval) qaytamiz."""
        data = await self._load_rates()
        if data is None:
            return None
        q = _norm_apostrophes(to_latin(f"{question} {search_query}").lower())
        wanted_codes, wanted_channels = self._rates_wanted(q)
        table = self._rates_table(data, wanted_codes, wanted_channels)
        if not table:
            return None
        calc = _rates_calculation(q, data, wanted_codes, wanted_channels)
        hint = _localize(RATES_PANEL_HINT, lang)
        if not wanted_codes and not wanted_channels and not calc:
            # Umumiy savol ("valyuta kursi") — model 2-3 valyutani qisqa aytib
            # qo'yardi. Bunda hisob ham, tanlov ham yo'q: kodning o'zi asosiy
            # kanal (ayirboshlash shoxobchasi) bo'yicha BARCHA valyutalarni
            # beradi, qolgan kanallar uchun kurs oynasiga yo'llaymiz.
            first = data["channels"][0].get("key")
            full = self._rates_table(data, set(), {first} if first else set())
            return (full or table) + hint, 0
        facts = f"{calc}\n\n{table}" if calc else table

        convo = _format_history(
            history, self.HISTORY_LIMIT, self.MAX_HISTORY_MSG_CHARS, self.MAX_HISTORY_CHARS
        )
        prompt = f"FACTS:\n{facts}\n\nQUESTION: {question}"
        if convo:
            prompt = f"Previous conversation:\n{convo}\n\n{prompt}"
        try:
            gen = await self.ai_client.generate_text_with_usage(
                prompt,
                system_prompt=_with_lang(RATES_SYSTEM, lang),
                temperature=self.TEMPERATURE,
                max_tokens=self.RATES_MAX_TOKENS,
            )
        except InfrastructureException as exc:
            logger.warning("Kurs javobi: model ishlamadi (%s) — jadval beriladi", exc)
            return facts + hint, 0

        text = gen.text.strip()
        allowed = _numbers_in(facts) | _numbers_in(question) | _numbers_in(search_query)
        allowed |= _numbers_in(convo)
        # Ro'yxat raqami, "1-2 kun" kabi kichik sonlar — tekshirmaymiz
        stray = {n for n in _numbers_in(text) if n >= 10 and n not in allowed}
        if not text or stray or gen.finish_reason == "length":
            logger.warning(
                "Kurs javobi rad etildi (begona sonlar: %s, finish=%s) — jadval beriladi",
                sorted(stray)[:5],
                gen.finish_reason,
            )
            return facts + hint, gen.completion_tokens
        return text + hint, gen.completion_tokens

    async def _scroll_points(self) -> list[dict[str, Any]]:
        """Bazadagi barcha bo'laklar — bitta so'rov davomida BIR MARTA o'qiladi.

        Use case har HTTP so'rovga qaytadan yaratiladi (routers.py), shuning
        uchun kesh eskirib qolmaydi. Ilgari xodim qidiruvi va leksik qidiruv
        bazani alohida-alohida o'qib chiqardi."""
        if self._points is None:
            self._points = await self.store.scroll_all_pages()
        return self._points

    # Ruscha hujjat o'zbekchasidan shuncha ballgacha past bo'lsa ham afzal
    # ko'riladi (javob tarjimasiz, asl ruscha matndan bo'lgani yaxshi).
    RU_PREFER_MARGIN = 0.05

    async def _search_chunks(
        self, question: str, search_q: str
    ) -> tuple[list[tuple[dict[str, Any], float]], list[tuple[dict[str, Any], float]]]:
        """Gibrid (vektor + leksik) qidiruv -> (birlashgan natija, leksik natija).

        O'zbekcha savol — faqat o'zbekcha hujjatlardan. Ruscha savol — ikkala
        tilda qidiriladi: ruscha hujjatlar RUSCHA savolning o'zi bilan,
        o'zbekchasi router yozgan o'zbekcha `search_query` bilan. Ruscha
        natija yetarlicha yaqin bo'lsa va o'zbekchasidan sezilarli past
        bo'lmasa — o'sha olinadi. Aks holda o'zbekcha (model tarjima qiladi):
        ruscha hujjatlar QISMAN qo'shilgan bo'lsa, so'ralgan mahsulot o'rniga
        boshqa ruscha hujjat tanlanib qolmasin."""
        query_vector = await self.embedder.embed(_expand_query(search_q))
        uz_results = await self.store.search(query_vector, top_k=self.TOP_K, lang="uz")
        # GIBRID QIDIRUV: vektor qidiruvi bo'lak SARLAVHASIGA tortiladi,
        # leksik qidiruv esa matn ICHIDAGI so'zni topadi. Ikkalasining
        # natijasi birga beriladi — shunda "qachon tashkil qilingan"
        # savoliga sarlavhada bunday so'z bo'lmasa ham javob topiladi.
        uz_lexical = await self._lexical_results(f"{question} {search_q}")
        if self._kb_lang == "ru":
            ru_vector = await self.embedder.embed(question)
            ru_results = await self.store.search(ru_vector, top_k=self.TOP_K, lang="ru")
            ru_top = ru_results[0][1] if ru_results else 0.0
            uz_top = uz_results[0][1] if uz_results else 0.0
            if ru_top >= self.MIN_SCORE and ru_top >= uz_top - self.RU_PREFER_MARGIN:
                logger.info("Ruscha hujjatlardan javob (ru %.3f, uz %.3f)", ru_top, uz_top)
                ru_lexical = await self._lexical_results(question, ru=True)
                return penalize_expired(_merge_results(ru_results, ru_lexical)), ru_lexical
        # Muddati o'tgan hujjatlar yangilaridan keyin turadi (knowledge/validity.py)
        return penalize_expired(_merge_results(uz_results, uz_lexical)), uz_lexical

    async def _lexical_results(
        self, query: str, ru: bool = False
    ) -> list[tuple[dict[str, Any], float]]:
        """SO'Z bo'yicha qidiruv — vektor qidiruvga QO'SHIMCHA, o'rniga emas.

        NEGA KERAK: embedding modeli ingliz tiliga moslashtirilgan
        (mxbai-embed-large), o'zbekcha savolda esa u bo'lakning SARLAVHASIGA
        yaqinlashadi, matn ICHIDAGI gapga emas. Shuning uchun "Turonbank
        qachon tashkil qilingan?" savoliga "ma'lumot topilmadi" qaytardi —
        garchi "Umumiy ma'lumotlar" bo'lagi ICHIDA "1990-yil noyabr oyida
        tashkil etilgan" jumlasi turgan bo'lsa ham. Foydalanuvchi aynan
        sarlavhani ("Umumiy ma'lumotlar") yozgandagina javob kelardi — ya'ni
        bot savolni emas, sarlavhani qidirardi.

        Ball IDF bo'yicha: kam uchraydigan so'z ("tashkil") ko'p uchraydigan
        so'zdan ("bank") ancha og'irroq baholanadi."""
        qwords = {
            w
            for w in _text_words(query)
            if len(w) >= 4 and w not in _BROAD_QUESTION_STOPWORDS
        }
        if not qwords:
            return []
        # Faqat kerakli tildagi hujjatlar (`ru` — ruscha, aks holda o'zbekcha)
        points = [
            p for p in await self._scroll_points()
            if p.get("doc_type") != "employee" and _is_ru_doc(p) == ru
        ]
        if not points:
            return []

        matches: list[tuple[dict[str, Any], set[str]]] = []
        doc_freq: dict[str, int] = dict.fromkeys(qwords, 0)
        for p in points:
            words = _text_words(
                f"{p.get('title', '')} {p.get('chunk_text', '')}"
            )
            hit = {q for q in qwords if any(_word_match(q, w) for w in words)}
            if hit:
                matches.append((p, hit))
                for w in hit:
                    doc_freq[w] += 1
        if not matches:
            return []

        total = len(points)
        scored = [
            (p, sum(math.log(total / doc_freq[w]) + 0.5 for w in hit))
            for p, hit in matches
        ]
        scored.sort(key=lambda pair: -pair[1])
        # Ballni 0..1 oralig'iga keltiramiz — vektor ballari bilan bir
        # shkalada ko'rinsin (ular manbalar ro'yxatida ko'rsatiladi).
        return [(p, s / (s + 3.0)) for p, s in scored[: self.LEXICAL_TOP_K]]

    async def _search_query(
        self, question: str, history: list[ChatTurn] | None
    ) -> str:
        """Qidiruv uchun MUSTAQIL savol qaytaradi (foydalanuvchi savoli emas).

        Suhbat bo'lmasa — savolning o'zi. Suhbat bo'lsa, modeldan savolni
        oldingi javobga bog'lab to'liq holga keltirishni so'raymiz: "foizlari
        qanday ularni" kabi savolda qidirish uchun hech narsa yo'q va vektor
        qidiruv butunlay boshqa mavzuni topib kelardi.

        Xatolikka chidamli: qayta yozish ishlamasa asl savol bilan davom
        etamiz (javobsiz qolishdan ko'ra yaxshi)."""
        if not history:
            return question
        recent = history[-self.HISTORY_LIMIT :]
        convo = "\n".join(
            f"{'User' if t.role == 'user' else 'Assistant'}: {t.content}"
            for t in recent
        )
        prompt = f"Conversation:\n{convo}\n\nLatest user message: {question}"
        try:
            rewritten = await self.ai_client.generate_text(
                prompt,
                system_prompt=QUERY_REWRITE_SYSTEM,
                temperature=0.0,
                max_tokens=self.REWRITE_MAX_TOKENS,
            )
        except Exception:
            return question
        cleaned = " ".join(rewritten.split()).strip().strip('"').strip()
        # Model izoh yozib yuborsa yoki bo'sh qaytarsa — asl savolga qaytamiz.
        if not cleaned or len(cleaned) > 400:
            return question
        return cleaned

    def _no_search_call(
        self, intent: Intent, question: str, history: list[ChatTurn] | None
    ) -> tuple[str, str, int]:
        """QIDIRUVSIZ javob beriladigan niyatlar uchun (prompt, system, limit).

        Ikkala niyatda ham bazaga borilmaydi, shuning uchun promptda kontekst
        ham, katalog ham yo'q — ~1800 token bo'shaydi va o'sha joyni suhbat
        tarixiga beramiz. Tarix bu yerda AYNAN eng muhim ma'lumot:
          * CONCEPT — mavzu kim/nima ekani ("kompaniya bosh ofisi qayerda"
            degan savolda gap Visa haqida ketayotgani faqat tarixdan bilinadi);
          * HISTORY — javobning O'ZI tarixda turibdi.
        Shuning uchun xabarlar MAX_HISTORY_MSG_CHARS (300) emas, kengroq
        chegara bilan kesiladi — 300 belgida javobning kerakli qismi
        (masalan manzil) kesilib qolardi."""
        if intent is Intent.HISTORY:
            system, max_toks = HISTORY_SYSTEM, self.HISTORY_ANSWER_MAX_TOKENS
            msg_chars, total_chars = (
                self.HISTORY_CTX_MSG_CHARS,
                self.HISTORY_CTX_CHARS,
            )
        elif intent is Intent.LANGUAGE:
            # Til savoli — tarix concept'dagi kabi (mavzu: "shu so'z" qaysi
            # so'z edi), limit esa kattaroq: matnni tuzatish so'ralishi mumkin
            system, max_toks = LANGUAGE_SYSTEM, self.LANGUAGE_MAX_TOKENS
            msg_chars, total_chars = (
                self.CONCEPT_HISTORY_MSG_CHARS,
                self.CONCEPT_HISTORY_CHARS,
            )
        else:
            system, max_toks = CONCEPT_SYSTEM, self.CONCEPT_MAX_TOKENS
            msg_chars, total_chars = (
                self.CONCEPT_HISTORY_MSG_CHARS,
                self.CONCEPT_HISTORY_CHARS,
            )
        convo = _format_history(history, self.HISTORY_LIMIT, msg_chars, total_chars)
        prompt = (
            f"Previous conversation:\n{convo}\n\nQUESTION: {question}"
            if convo
            else f"QUESTION: {question}"
        )
        return prompt, system, max_toks

    def _employee_prompt(
        self,
        question: str,
        history: list[ChatTurn] | None,
        emps: list[dict[str, Any]],
    ) -> str:
        context = "\n\n".join(str(e.get("chunk_text", "")) for e in emps)
        base = f"EMPLOYEE DATA:\n{context}\n\nQUESTION: {question}"
        if history:
            recent = history[-self.HISTORY_LIMIT :]
            convo = "\n".join(
                f"{'User' if t.role == 'user' else 'Assistant'}: {t.content}"
                for t in recent
            )
            return f"Previous conversation:\n{convo}\n\n{base}"
        return base

    async def _assemble(
        self,
        question: str,
        history: list[ChatTurn] | None,
        results: list[tuple[dict[str, Any], float]],
        include_catalog: bool = True,
    ) -> tuple[str, list[SourceRef]]:
        """Topilgan bo'laklar + katalog + suhbat tarixidan yakuniy promptni va
        manbalar ro'yxatini quradi (execute/execute_stream uchun umumiy).

        PROMPT HAJMI QAT'IY CHEKLANADI. Ilgari cheklov yo'q edi va prompt
        muntazam ravishda num_ctx (8192 token) dan oshib ketardi:
          system ~3600 + katalog ~2200 + kontekst ~2000 + tarix ~1300
          + javobga 2048 = ~11 000 token.
        Ollama ortiqchasini JIMGINA kesadi, chat qolipi buziladi va model
        bitta token chiqarib to'xtaydi — foydalanuvchi ko'rgan "1 token",
        "21 token" javoblar aynan shundan. Ustiga sekin (CPU) serverda har
        ortiqcha 1000 token promptni o'qishga qo'shimcha kutish qo'shadi."""
        # Batafsil kontekst (tanlangan mavzuga oid eng yaqin bo'laklar) —
        # aniq mahsulot bo'yicha to'liq (raqam/shart) javob berish uchun.
        # MUHIM: manba havolasi "SOURCE_URL:" yorlig'i bilan beriladi — avval
        # "(Manba: url)" edi va model uni javobga AYNAN ko'chirib, "Batafsil:
        # url(Manba: url)" kabi ikki marta havola chiqarardi (dubl link bug).
        blocks: list[str] = []
        used = 0
        for payload, _ in results:
            title = payload.get("title", "")
            source_url = payload.get("source_url", "")
            header = f"[{title}]\nSOURCE_URL: {source_url}" if source_url else f"[{title}]"
            if is_expired(payload):
                header += (
                    f"\nNOTE: this document was valid until {payload.get('valid_until')}; "
                    "say in your answer that the information may be outdated and "
                    "should be confirmed."
                )
            block = f"{header}\n{payload.get('chunk_text', '')}"
            # Byudjet tugasa qolgan bo'laklar tashlab yuboriladi — ular
            # baribir eng uzoq (eng kam mos) natijalar.
            if blocks and used + len(block) > self.MAX_CONTEXT_CHARS:
                break
            blocks.append(block)
            used += len(block)
        context = "\n\n---\n\n".join(blocks)

        # Katalog — turkumdagi HAMMA mahsulotni sanash uchun (keng savol).
        # ANIQ mahsulot javobida (foydalanuvchi ro'yxatdan tanlagan) katalog
        # keraksiz: u ~2000 token joy egallab, javobni kesilishga olib kelardi.
        catalog = await self._build_catalog(question) if include_catalog else ""
        catalog_block = (
            f"CATALOG (all products in the database, grouped by category — use this "
            f"list for broad/category questions):\n{catalog}\n\n"
            if catalog
            else ""
        )
        base = (
            f"{catalog_block}"
            f"CONTEXT (nearest blocks for the selected topic):\n{context}\n\n"
            f"QUESTION: {question}"
        )

        # Oldingi suhbat. Har xabar QISQARTIRILADI: bot javobi 20 bandli
        # ro'yxat bo'lishi mumkin (~1500 belgi) va shunday ikkita javob
        # promptning yarmini yeb qo'yardi. Mavzu bog'liqligi uchun xabarning
        # boshi yetarli.
        convo = _format_history(
            history,
            self.HISTORY_LIMIT,
            self.MAX_HISTORY_MSG_CHARS,
            self.MAX_HISTORY_CHARS,
        )
        prompt = f"Previous conversation:\n{convo}\n\n{base}" if convo else base

        logger.info(
            "Prompt: %d belgi (~%d token) | kontekst %d, katalog %d, tarix %d",
            len(prompt),
            round(len(prompt) / 3.2),
            len(context),
            len(catalog_block),
            len(convo),
        )

        # Manbalarni sarlavha bo'yicha takrorlanmas qilib yig'amiz
        sources: list[SourceRef] = []
        seen: set[str] = set()
        for payload, score in results:
            title = str(payload.get("title", ""))
            if title and title not in seen:
                seen.add(title)
                sources.append(SourceRef(title=title, score=round(score, 3)))

        return prompt, sources

    def _web_query(self, question: str, decision: Route | None) -> str:
        # Tashqariga xom savol emas — router tozalagan qidiruv so'rovi
        if decision is not None and len(decision.search_query.strip()) >= 3:
            return decision.search_query
        return question

    async def _web_stream(
        self,
        question: str,
        decision: Route | None,
        lang: ReplyLang,
        want_cyrillic: bool,
        router_tokens: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Bazada topilmadi — ruxsat etilgan saytlardan javob.

        Javob berilsa `last_outcome = "web"`. Sahifa topilmasa yoki model
        NOT_FOUND desa — hech qanday delta yubormaydi (chaqiruvchi odatdagi
        "ma'lumot topilmadi"ni qaytaradi)."""
        yield {"type": "status", "step": "web"}
        hits = await web_search.search(self._web_query(question, decision))
        if not hits:
            return
        sources = _web_sources(hits)
        src_dump = [s.model_dump() for s in sources]
        tr = StreamingTransliterator() if want_cyrillic else None
        sf = StreamingScriptFixer() if lang == "uz" else None

        def conv(text: str) -> str:
            if tr is not None:
                return tr.feed(text)
            if sf is not None:
                return sf.feed(text)
            return text

        # Boshidagi bir necha belgini ushlab turamiz: model NOT_FOUND yozsa,
        # foydalanuvchiga hech narsa chiqmasin.
        buf = ""
        decided = False
        yield {"type": "status", "step": "write"}
        web_prompt = _web_prompt(question, hits)
        # Tekshiruvchi javobni shu sahifalarga solishtiradi (o'z eski
        # bilimiga emas)
        self._last_context = web_prompt
        async for ev in self.ai_client.stream_generate(
            web_prompt,
            system_prompt=self._system(WEB_RAG_SYSTEM, lang),
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        ):
            if ev.get("type") == "delta":
                if decided:
                    yield {**ev, "text": conv(ev["text"])}
                    continue
                buf += ev["text"]
                if len(buf.strip()) < len(WEB_NOT_FOUND_TOKEN) + 2:
                    continue
                if _is_web_not_found(buf):
                    logger.info("Veb sahifalarda javob yo'q: %r", question[:120])
                    return
                decided = True
                self.last_outcome = "web"
                # Manba foydalanuvchiga matn bilan emas — "Manbalar"
                # chiplarida (havolalar) ko'rinadi; logda esa shu yerda
                logger.info(
                    "Javob internetdan: %r <- %s",
                    question[:120],
                    ", ".join(h.url for h in hits),
                )
                yield {"type": "delta", "text": conv(buf)}
            elif ev.get("type") == "done":
                if not decided:
                    if not buf.strip() or _is_web_not_found(buf):
                        return
                    self.last_outcome = "web"
                    logger.info(
                        "Javob internetdan: %r <- %s",
                        question[:120],
                        ", ".join(h.url for h in hits),
                    )
                    yield {"type": "delta", "text": conv(buf)}
                rest = tr.flush() if tr is not None else sf.flush() if sf is not None else ""
                if rest:
                    yield {"type": "delta", "text": rest}
                ev["max_tokens"] = self.MAX_TOKENS
                ev["sources"] = src_dump
                ev["completion_tokens"] = int(ev.get("completion_tokens", 0)) + router_tokens
                yield ev

    async def _web_answer(
        self,
        question: str,
        decision: Route | None,
        lang: ReplyLang,
        want_cyrillic: bool,
        router_tokens: int,
    ) -> AnswerResult | None:
        """`_web_stream` ning oqimsiz (mobil /ask) varianti."""
        hits = await web_search.search(self._web_query(question, decision))
        if not hits:
            return None
        gen = await self.ai_client.generate_text_with_usage(
            _web_prompt(question, hits),
            system_prompt=_with_lang(WEB_RAG_SYSTEM, lang),
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
        )
        text = gen.text.strip()
        if not text or _is_web_not_found(text):
            return None
        if want_cyrillic:
            text = to_cyrillic(text)
        elif lang == "uz":
            text = fix_mixed_script(text)
        self.last_outcome = "web"
        logger.info(
            "Javob internetdan: %r <- %s", question[:120], ", ".join(h.url for h in hits)
        )
        return AnswerResult(
            answer=text,
            sources=_web_sources(hits),
            finish_reason=gen.finish_reason,
            completion_tokens=gen.completion_tokens + router_tokens,
            max_tokens=gen.max_tokens,
        )

    def _flag(self, kind: str) -> None:
        """So'rov xavfli deb belgilandi: statistikada "flagged", sabab — `kind`.
        Router (chat/routers.py) buni ko'rib, adminga bildirishnoma yuboradi."""
        self.last_outcome = "flagged"
        self.last_flag = kind
        self.last_intent = kind
        logger.warning("So'rov belgilandi (%s)", kind)

    # Tekshiruvdan o'tkazilmaydigan natijalar: tayyor himoya javoblari va
    # "topilmadi" (tekshiradigan narsa yo'q)
    _UNVERIFIED_OUTCOMES = frozenset({"blocked", "flagged", "no_info"})
    _UNVERIFIED_INTENTS = frozenset({Intent.SMALLTALK.value, Intent.ABOUT_BOT.value})

    async def _collect(
        self,
        question: str,
        history: list[ChatTurn] | None,
        retry_hint: str | None,
        pass_status: bool,
        retry_route: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Xom javobni YIG'ADI: status hodisalari darhol o'tadi (agar
        `pass_status`), matn va "done" esa self._buf_* ga yoziladi."""
        self._buf_text = ""
        self._buf_done = None
        async for ev in self._execute_stream_raw(
            question, history, retry_hint, retry_route
        ):
            kind = ev.get("type")
            if kind == "delta":
                self._buf_text += ev.get("text", "")
            elif kind == "done":
                self._buf_done = ev
            elif kind == "status":
                if pass_status:
                    yield ev
            else:
                yield ev

    def _needs_verify(self) -> bool:
        return (
            bool(config.ai.ANSWER_VERIFY)
            and self.last_outcome not in self._UNVERIFIED_OUTCOMES
            and self.last_intent not in self._UNVERIFIED_INTENTS
            and bool(self._buf_text.strip())
        )

    async def execute_stream(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        """Javob TEKSHIRUV bilan: xom javob yig'iladi, model uni savolga
        mosligini baholaydi (qara: verifier.py), mos bo'lmasa kamchilikni
        aytib qayta yozdiriladi. Foydalanuvchiga faqat tekshirilgan javob
        chiqadi — bosqichlar ("o'ylamoqda…") esa real vaqtda ko'rinib turadi.

        `last_verdict`: "ok" | "fixed" (2-urinish o'tdi) | "failed" (ikkalasi
        ham o'tmadi, halol "topilmadi" berildi) | "unchecked" (tekshiruv
        bajarilmadi) | None (tekshirilmaydigan javob)."""
        self.last_verdict = None
        self.last_verdict_note = None
        extra_tokens = 0
        async for ev in self._collect(question, history, None, True):
            yield ev

        if self._needs_verify():
            yield {"type": "status", "step": "verify"}
            v = await verify_answer(
                self.ai_client,
                question,
                self._buf_text,
                history,
                interpreted=self._effective_question,
                context=self._last_context,
            )
            if v is None:
                self.last_verdict = "unchecked"
            elif v.ok:
                self.last_verdict = "ok"
                extra_tokens += v.tokens
            else:
                extra_tokens += v.tokens
                first_problem = v.problem or "the answer does not match the question"
                logger.warning(
                    "Tekshiruv: javob rad etildi | %r | %s", question[:200], first_problem
                )
                self.last_verdict_note = first_problem
                # Qayta yozish — qisqa yo'llarsiz, kamchilik ko'rsatilgan holda
                yield {"type": "status", "step": "rewrite"}
                # Tekshiruvchi aytgan manbadan: baza / umumiy bilim / internet
                async for ev in self._collect(
                    question, history, first_problem, False, v.source
                ):
                    yield ev
                if not self._needs_verify():
                    # 2-urinish "topilmadi" bo'ldi — halol javob, tekshiruv shart emas
                    self.last_verdict = "fixed"
                else:
                    v2 = await verify_answer(
                        self.ai_client,
                        question,
                        self._buf_text,
                        history,
                        interpreted=self._effective_question,
                        context=self._last_context,
                    )
                    if v2 is not None:
                        extra_tokens += v2.tokens
                    if v2 is None or v2.ok:
                        self.last_verdict = "fixed"
                    else:
                        # Ikkinchisi ham noto'g'ri — to'qima o'rniga halol javob
                        logger.warning(
                            "Tekshiruv: qayta yozilgan javob ham rad etildi | %r | %s",
                            question[:200],
                            v2.problem,
                        )
                        self.last_verdict = "failed"
                        self.last_verdict_note = f"{first_problem} | {v2.problem}"
                        self.last_outcome = "no_info"
                        lang = detect_reply_lang(question, history)
                        self._buf_text = _localize(VERIFY_FAILED_REPLY, lang)
                        if self._buf_done is not None:
                            self._buf_done = {**self._buf_done, "sources": []}

        if self._buf_text:
            yield {"type": "delta", "text": self._buf_text}
        done = dict(self._buf_done or {
            "type": "done",
            "completion_tokens": 0,
            "finish_reason": "stop",
            "max_tokens": self.MAX_TOKENS,
            "sources": [],
        })
        done["completion_tokens"] = int(done.get("completion_tokens") or 0) + extra_tokens
        yield done

    def _system(self, system: str, lang: ReplyLang) -> str:
        """Tizim prompti + til + (qayta yozishda) tekshiruvchi ko'rsatgan
        kamchilik."""
        out = _with_lang(system, lang)
        if self._retry_hint:
            out += (
                "\n\nIMPORTANT — REVIEW FEEDBACK: a previous draft answer to this "
                f"question was rejected by a reviewer: {self._retry_hint}\n"
                "Answer exactly what the user asked. Keep the user's own terms. "
                "Use only facts from the provided blocks; if they do not contain "
                "the answer, say honestly that the information was not found."
            )
        return out

    async def _execute_stream_raw(
        self,
        question: str,
        history: list[ChatTurn] | None = None,
        retry_hint: str | None = None,
        retry_route: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """execute bilan bir xil RAG mantiqi, lekin javobni token-token (oqim)
        qaytaradi — foydalanuvchi real vaqtda ko'rishi uchun. Har bir bo'lak:
        {"type":"delta","text":...}; oxirida token statistikasi bilan
        {"type":"done", ...}.

        Bosqich hodisalari {"type":"status","step":...} — frontend "O'ylayapman…"
        qatorida ko'rsatadi. Faqat HAQIQATAN boshlangan ish uchun yuboriladi:
          analyze   — savol tahlili (router);
          rates     — valyuta kurslari olinmoqda;
          employees — xodimlar ro'yxatidan qidiruv;
          search    — bilim bazasidan qidiruv;
          write     — model javob yozmoqda.
        Tayyor (modelsiz) javoblarda faqat "analyze" bo'ladi.

        `retry_hint` — tekshiruvchi oldingi javobni rad etgan (qara:
        execute_stream). Bunda so'zga qarab ishlaydigan QISQA YO'LLAR
        (ma'lumotnoma, turkum/filial ro'yxati, xodim yo'li, "mavzudan tashqari",
        aniqlashtirish) o'chiriladi — javob to'liq qidiruv + model orqali,
        kamchilik ko'rsatilgan holda qayta yoziladi.

        `retry_route` — tekshiruvchi aytgan TO'G'RI manba:
          general_knowledge — bazasiz, model bilimidan (Markaziy bank nima,
                              atama ma'nosi) — bazadagi "Bank haqida" hujjati
                              begona mavzuga tortmasin;
          web               — ruxsat etilgan saytlardan (yangiliklar, bugungi
                              rasmiy ma'lumot); topilmasa — halol "topilmadi";
          knowledge_base / none — bilim bazasidan to'liq qidiruv."""
        self.last_intent = None
        self.last_outcome = "answered"
        self.last_top_score = None
        self.last_flag = None
        # Tekshiruvchi uchun: model qaysi kontekstga tayanib yozdi va savol
        # qanday talqin qilindi
        self._last_context = None
        self._effective_question = None
        self._retry_hint = retry_hint
        force = retry_hint is not None
        route_general = force and retry_route == "general_knowledge"
        route_web = force and retry_route == "web"
        yield {"type": "status", "step": "analyze"}
        # Himoya: PII maskalanadi, ochiq prompt-injection modelga umuman
        # bormaydi (qara: src/core/ai/guard.py)
        question, history, blocked = _guard_input(question, history)
        if blocked:
            self.last_outcome = "blocked"
            yield {
                "type": "delta",
                "text": _localize(INJECTION_REPLY, detect_reply_lang(question, history)),
            }
            yield {
                "type": "done",
                "completion_tokens": 0,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return
        # So'kinish/haqorat — model chaqirilmaydi, adminga xabar boradi (router)
        if has_profanity(question):
            self._flag("profanity")
            yield {
                "type": "delta",
                "text": _localize(PROFANITY_REPLY, detect_reply_lang(question, history)),
            }
            yield {
                "type": "done",
                "completion_tokens": 0,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return
        # Javob tili — savol (raqamga almashtirilishidan OLDIN) qaysi tilda
        # yozilganiga qarab: o'zbek lotin / o'zbek kirill / rus. AI o'zbekcha
        # javobni hamisha lotincha yozadi, kirill kerak bo'lsa shu yerda
        # o'giramiz; ruscha javobni esa model o'zi yozadi (RU_REPLY_OVERRIDE).
        lang = detect_reply_lang(question, history)
        # Ruscha savolga ruscha hujjatlar (bo'lsa) — katalog va qidiruv shunga qaraydi
        self._kb_lang = "ru" if lang == "ru" else "uz"
        want_cyrillic = lang == "uz_cyrl"

        # Ichki barcha mantiq (xodim qidiruvi, turkum kalit so'zlari, embedding
        # qidiruvi, baza) LOTINCHA ishlaydi — o'zbekcha savolni shu yerdayoq
        # lotinga keltiramiz. Aks holda kirillcha savol embedding'ga kirillcha
        # ketib, mos kontekst topilmay "ma'lumotim yo'q" qaytardi.
        # RUSCHA savol o'girilMAYDI: "какой процент" -> "kakoy protsent"
        # ma'nosiz matnga aylanardi. Qidiruv baribir o'zbekcha ketadi —
        # router search_query'ni o'zbek lotinida yozadi.
        if lang != "ru":
            question = to_latin(question)

        # Foydalanuvchi ro'yxatdan raqam bilan tanlagan bo'lsa ("53") — savolni
        # o'sha band nomiga almashtiramiz (qidiruv ham, prompt ham shuni ko'radi).
        # Bu MAHSULOT ro'yxatidan tanlov ekani ANIQ — shuning uchun xodim
        # yo'nalishini SINAMAYMIZ ham (aks holda "Humo" kabi mahsulot nomi
        # "Humoyun" degan xodimga tasodifan mos kelib, noto'g'ri yo'nalardi).
        # Ro'yxatdan tanlov ('19') yoki aniqlashtiruvchi savolimizga javob
        # ('ha', 'meros omonati') — ikkalasi ham savolni MAHSULOT NOMIga
        # aylantiradi va routerni chetlab o'tadi.
        resolved = _resolve_list_choice(question, history) or _resolve_clarification(
            question, history
        )
        question = resolved or question
        self._effective_question = question

        # Xodimlar ma'lumotnomasi (o'zi kiritgan IP, admin qo'ygan kalit so'z)
        # — vektor bazadan va routerdan OLDIN: aniq moslik, model kerak emas.
        if not resolved and not force:
            hits = await self._directory_hits(question)
            if hits:
                yield {"type": "status", "step": "employees"}
                self.last_intent = Intent.EMPLOYEE.value
                self._last_context = None
                emp_text = _format_employee_answer(hits[:60])
                yield {
                    "type": "delta",
                    "text": to_cyrillic(emp_text) if want_cyrillic else emp_text,
                }
                yield {
                    "type": "done",
                    "completion_tokens": 0,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [],
                }
                return

        # Savolni TUSHUNISH: nima so'ralayotganini model aniqlaydi. Ilgari bu
        # regex bilan qilinardi va mahsulot belgisi yo'q HAR QANDAY savol ism
        # qidiruviga tushib ketardi ("javob" -> "Javohir"). Endi xodim yo'li
        # faqat model shuni tasdiqlaganda ochiladi.
        decision = None if resolved else await self.router.classify(question, history)
        # Router yozgan tokenlar. Tayyor (modelsiz) javoblarda ham token
        # hisoblagichi shu sonni ko'rsatadi — ilgari 0 yuborilardi va frontend
        # hisoblagichni umuman yashirardi ("goh chiqadi, goh chiqmaydi").
        router_tokens = decision.tokens if decision is not None else 0
        self.last_intent = decision.intent.value if decision is not None else None

        # Xavfli/noqonuniy so'rov (yashirin bo'lsa ham — router MA'NOSINI
        # baholaydi). Hech qanday qisqa yo'l (xodim, katalog) undan oldin
        # turmasligi kerak — shuning uchun eng boshida.
        if decision is not None and decision.intent is Intent.HARMFUL:
            self._flag("harmful")
            yield {"type": "delta", "text": _localize(HARMFUL_REPLY, lang)}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Salomlashish yoki bot haqidagi savol — bazaga umuman bormaymiz
        if decision is not None and decision.intent in (
            Intent.SMALLTALK,
            Intent.ABOUT_BOT,
        ):
            text = _bot_reply(decision, history, lang)
            yield {"type": "delta", "text": text}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Tekshiruvchi: bu savolga javob INTERNETDAN (yangilik, bugungi rasmiy
        # ma'lumot) olinishi kerak. Baza bunga javob bermaydi — u yerdan
        # qayta qidirish yana eski hujjatni ("Tarix") qaytarardi.
        if route_web:
            if config.web_search.WEB_SEARCH_ENABLED and not _is_meaningless_query(
                question
            ):
                async for ev in self._web_stream(
                    question, decision, lang, want_cyrillic, router_tokens
                ):
                    yield ev
                if self.last_outcome == "web":
                    return
            else:
                logger.info(
                    "Javob internetdan kerak, lekin veb-qidiruv o'chiq "
                    "(WEB_SEARCH_ENABLED=false): %r",
                    question[:200],
                )
            self.last_outcome = "no_info"
            yield {"type": "delta", "text": _localize(NO_INFO_REPLY, lang)}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # XAVFSIZLIK TO'RI. Quyidagi uch yo'l (other / concept / history)
        # bazaga UMUMAN bormaydi — ya'ni router xato baholasa, bazada BOR
        # ma'lumot foydalanuvchiga yetib bormaydi. Xodim so'rovi bunga eng
        # sezgir: savolda aniq belgi bo'lsa ("ip", "xodim", "ichki raqam",
        # "2206 kimniki"), routerning fikridan qat'i nazar qisqa yo'llarni
        # ochmaymiz — xodim qidiruvini deterministik kod bajaradi va u
        # routerdan ishonchliroq (shu sabab u yerda ham router "maslahatchi").
        skip_shortcuts = force or _has_employee_intent(question.lower())

        # Bank/moliyaga UMUMAN aloqasi yo'q savol (sport, siyosat, ob-havo...) —
        # bazaga bormaymiz, modelni ham chaqirmaymiz. Ilgari bu savol RAG'ga
        # tushib, "ma'lumot topilmadi, 1234 ga qo'ng'iroq qiling" javobini
        # olardi — bank call-markazini sport savoliga yo'naltirish noto'g'ri.
        #
        # BOSHQA BANK haqidagi savol ham shu yerda kesiladi: bot faqat
        # Turonbank bo'yicha gapiradi, raqobatchi bank yoki banklar ro'yxati
        # so'ralganda model umuman chaqirilmaydi (qara: OTHER_BANK_REPLY).
        if (
            decision is not None
            and not skip_shortcuts
            and decision.intent in (Intent.OTHER, Intent.OTHER_BANK)
        ):
            reply = (
                OTHER_BANK_REPLY
                if decision.intent is Intent.OTHER_BANK
                else OFF_TOPIC_REPLY
            )
            yield {"type": "delta", "text": _localize(reply, lang)}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Bank/moliya sohasining UMUMIY savoli — javob model bilimidan, bank
        # bazasidan EMAS. Qidiruv umuman bajarilmaydi: kontekst promptga
        # kirmasa, model unga tortilib "ASOSIY SHARTLAR" va "Batafsil: <url>"
        # qo'shib yubormaydi. Manba ham ko'rsatilmaydi — bazadan olinmagan.
        # UMUMIY SAVOL BO'LSA HAM AVVAL BAZAGA QARAYMIZ. Router "umumiy
        # tushuncha" desa, ilgari qidiruv umuman bajarilmasdi: "meros omonati"
        # savoliga bot "bank tizimida bunday mahsulot yo'q" degan, holbuki
        # bazada «Meros omonati» bor edi. Endi katalog nomlari tekshiriladi.
        catalog_title: str | None = None
        if (
            decision is not None
            and not skip_shortcuts
            and decision.intent is Intent.CONCEPT
            and not _asks_about_organization(question)
        ):
            catalog_title, partial_titles = await self._catalog_title_match(question)
            if catalog_title is not None:
                logger.info(
                    "Umumiy savol bazadagi mahsulotga bog'landi: %r -> %r",
                    question,
                    catalog_title,
                )
            elif (
                1 <= len(partial_titles) <= _CLARIFY_MAX_OPTIONS
                and not _last_turn_was_clarify(history)
                and not _asks_general_meaning(question)
                and not set(partial_titles) & _declined_clarify_titles(history)
            ):
                # Nom to'liq aytilmagan — javob TO'QILMAYDI, so'raymiz
                logger.info(
                    "Aniqlashtirish so'raldi: %r -> %s", question, partial_titles
                )
                yield {
                    "type": "delta",
                    "text": _clarify_reply(partial_titles, want_cyrillic),
                }
                yield {
                    "type": "done",
                    "completion_tokens": router_tokens,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [],
                }
                return

        if route_general or (
            decision is not None
            and not skip_shortcuts
            and catalog_title is None
            and decision.intent in (Intent.CONCEPT, Intent.HISTORY, Intent.LANGUAGE)
        ):
            # Tekshiruvchi "umumiy bilimdan" desa — router nima deganidan
            # qat'i nazar CONCEPT (bazasiz) yo'li
            nosearch_intent = (
                Intent.CONCEPT
                if route_general or decision is None
                else decision.intent
            )
            if route_general:
                self.last_intent = Intent.CONCEPT.value
            prompt, system, max_toks = self._no_search_call(
                nosearch_intent, question, history
            )
            # Joriy/tekshiriladigan fakt (bugungi stavka, soliq, qonun) —
            # model to'qimaydi, NEEDS_WEB deydi va kod internetdan qidiradi.
            web_ok = nosearch_intent is Intent.CONCEPT and _web_eligible(
                decision, question
            )
            if web_ok:
                system = system + CONCEPT_WEB_ADDENDUM
            # Kirillga o'girilmaydigan javobda aralash alifboli so'zni
            # ("молияiy") tuzatamiz. Kirillga o'girilganda kerak emas —
            # u yerda matn baribir bir alifboga keltiriladi. Ruscha javobda
            # ikkalasi ham O'CHIQ: tuzatuvchi kirill harflarni lotinga
            # "to'g'rilab" yuborardi.
            tr = StreamingTransliterator() if want_cyrillic else None
            sf = StreamingScriptFixer() if lang == "uz" else None
            lf = _ConceptLineFilter()
            # web_ok bo'lsa javob boshini ushlab turamiz: NEEDS_WEB
            # foydalanuvchiga chiqmasin
            head = "" if web_ok else None
            needs_web = False
            yield {"type": "status", "step": "write"}
            async for ev in self.ai_client.stream_generate(
                prompt,
                system_prompt=self._system(system, lang),
                temperature=self.TEMPERATURE,
                max_tokens=max_toks,
            ):
                if head is not None and ev.get("type") in ("delta", "done"):
                    if ev.get("type") == "delta":
                        head += ev["text"]
                        if len(head.strip()) <= len(WEB_LOOKUP_TOKEN):
                            continue
                    if _is_web_lookup(head):
                        needs_web = True
                        break
                    # Oddiy javob — ushlangan bosh qismi odatdagi yo'ldan o'tadi
                    if ev.get("type") == "delta":
                        ev = {**ev, "text": head}
                    elif head:
                        ev = dict(ev)
                        lf_head = lf.feed(head)
                        if tr is not None:
                            lf_head = tr.feed(lf_head)
                        elif sf is not None:
                            lf_head = sf.feed(lf_head)
                        if lf_head:
                            yield {"type": "delta", "text": lf_head}
                    head = None
                if ev.get("type") == "delta":
                    text = lf.feed(ev["text"])
                    if tr is not None:
                        text = tr.feed(text)
                    elif sf is not None:
                        text = sf.feed(text)
                    if not text:
                        continue
                    ev = {**ev, "text": text}
                if ev.get("type") == "done":
                    # Filtrda qolgan qoldiqni chiqaramiz, so'ng transliterator
                    # (yoki alifbo tuzatuvchi) buferini bo'shatamiz — tartib
                    # muhim: filtr lotincha matn ustida ishlaydi.
                    rest = lf.flush()
                    if tr is not None:
                        rest = tr.feed(rest) + tr.flush()
                    elif sf is not None:
                        rest = sf.feed(rest) + sf.flush()
                    if rest:
                        yield {"type": "delta", "text": rest}
                    ev["max_tokens"] = max_toks
                    ev["sources"] = []
                    # Javob + router tokenlari — so'rovga ketgan jami
                    ev["completion_tokens"] = (
                        int(ev.get("completion_tokens", 0)) + router_tokens
                    )
                yield ev
            if needs_web:
                async for ev in self._web_stream(
                    question, decision, lang, want_cyrillic, router_tokens
                ):
                    yield ev
                if self.last_outcome != "web":
                    self.last_outcome = "no_info"
                    yield {"type": "delta", "text": _localize(NO_INFO_REPLY, lang)}
                    yield {
                        "type": "done",
                        "completion_tokens": router_tokens,
                        "finish_reason": "stop",
                        "max_tokens": self.MAX_TOKENS,
                        "sources": [],
                    }
            return

        # Valyuta kursi — faktlarni kod, javobni model yozadi (_rates_reply)
        if decision is not None and decision.intent is Intent.RATES:
            yield {"type": "status", "step": "rates"}
            rates = await self._rates_reply(
                question, decision.search_query, history, lang
            )
            if rates:
                text, rate_tokens = rates
                if want_cyrillic:
                    text = _rates_to_cyrillic(text)
                elif lang == "uz":
                    text = fix_mixed_script(text)
                yield {"type": "delta", "text": text}
                yield {
                    "type": "done",
                    "completion_tokens": router_tokens + rate_tokens,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [SourceRef(title=RATES_TITLE, score=1.0).model_dump()],
                }
                return

        # Xodim (telefon/IP) savoli — alohida yo'l (mahsulot RAG'siz).
        #
        # MUHIM: router bu yerda QAROR QILMAYDI, faqat maslahat beradi. Ilgari
        # xodim qidiruvi "router EMPLOYEE desa" ochilardi va model ishonchsiz
        # ishlagani uchun butun ma'lumotnoma yopilib qolardi: yalang'och
        # familiya ("Xamdamboyev") yozilganda router "bu kontakt so'rovi emas"
        # deb, bazada BOR xodim "topilmadi" bo'lardi — bir xil savol goh
        # ishlab, goh ishlamasdi. Endi qidiruvni har doim kod bajaradi (u
        # deterministik), router esa faqat salomlashishni ajratadi.
        #
        # ISTISNO: router YIQILGAN bo'lsa va savolda xodim belgisi yo'q
        # bo'lsa — ism bo'yicha taxmin qilmaymiz (qara: _blind_employee_guess).
        # Ism moslash lotincha ishlaydi, shuning uchun ruscha savol ham
        # lotinga o'girib beriladi ("Азамат" -> "Azamat").
        #
        # Xodim qidiruvi har savolda (tez, kod bilan) ishlaydi — bosqich esa
        # faqat savol rostdan xodim haqida bo'lganda ko'rsatiladi, aks holda
        # mahsulot savolida ham "xodimlardan qidiryapman" chiqib turardi.
        if skip_shortcuts or (
            decision is not None and decision.intent is Intent.EMPLOYEE
        ):
            yield {"type": "status", "step": "employees"}
        route = (
            None
            if force or resolved or _blind_employee_guess(decision, question)
            else await self._employee_route(to_latin(question))
        )
        if route is not None:
            kind, emps = route
            if kind in ("ask", "none"):
                # Model UMUMAN chaqirilmaydi — tayyor matn. "none" holatida
                # modelga "topilmadi" deyishni ishonib topshirib bo'lmaydi:
                # u yo'q xodimlarni to'qib chiqargan edi.
                canned = (
                    EMPLOYEE_ASK_REPLY if kind == "ask" else EMPLOYEE_NOT_FOUND_REPLY
                )
                if kind == "none":
                    self.last_outcome = "no_info"
                yield {"type": "delta", "text": _localize(canned, lang)}
                yield {
                    "type": "done",
                    "completion_tokens": router_tokens,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [],
                }
                return
            # Javobni KOD tuzadi — model chaqirilmaydi. Model ro'yxatni
            # yarmida to'xtatib qo'ygan (16 tadan 8 tasi) va oldinroq soxta
            # xodimlarni to'qigan edi.
            # Xodim javobi keshlanmaydi: intent "employee" CACHEABLE emas.
            # Router savolni "concept" degan bo'lsa ham kontakt keshga
            # tushib, keyin boshqa savolga ham shu javob qaytib qolardi.
            self.last_intent = Intent.EMPLOYEE.value
            emp_text = _format_employee_answer(emps)
            yield {
                "type": "delta",
                "text": to_cyrillic(emp_text) if want_cyrillic else emp_text,
            }
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Turkumning BARCHA mahsulotini so'ragan keng savol — LLM'ni chaqirmasdan,
        # katalogdan deterministik raqamlangan ro'yxat qaytaramiz (format har doim
        # bir xil bo'lsin: LLM'ga qoldirilsa ba'zan vergul bilan ham chiqib turardi).
        broad_reply, only_title = (
            (None, None)
            if force
            else await self._broad_category_reply(question, want_cyrillic)
        )
        # Turkum ichida bitta mahsulot aniqlandi — savolni uning to'liq nomiga
        # almashtiramiz (qidiruv ham, prompt ham shuni ko'radi).
        question = only_title or question
        self._effective_question = question
        if broad_reply is not None:
            yield {"type": "delta", "text": broad_reply}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Harfsiz (ma'nosiz) so'rov — xodim/mahsulot yo'nalishidan o'tib kelgan
        # bo'lsa, embedding qidiruviga bermaymiz (uzoq LLM chaqiruvisiz).
        if _is_meaningless_query(question):
            text = _localize(NO_INFO_REPLY, lang)
            yield {"type": "delta", "text": text}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Qidiruvda rasmiy sinonimlar bilan kengaytiramiz ("filial" -> "bank
        # xizmatlari markazi/ofisi"), promptdagi SAVOL esa asl holicha qoladi.
        # Savolni suhbat asosida MUSTAQIL savolga aylantiramiz — faqat qidiruv
        # uchun. Promptdagi SAVOL foydalanuvchi yozganidek qoladi.
        # Sarlavha aniq ma'lum (ro'yxatdan raqam tanlangan yoki turkum ichida
        # bitta mahsulot qoldi) — o'sha sarlavhaning bo'laklarini to'g'ridan-
        # to'g'ri olamiz, taxminiy qidiruv boshqa mahsulotni qaytarmasin.
        # VALYUTA KURSI — alohida yo'nalish. Kurs bazada QAT'IY bitta sarlavha
        # ostida turadi (RATES_TITLE, kunlik Celery vazifasi yozadi), shuning
        # uchun uni taxminiy embedding bilan qidirishning hojati yo'q. Ilgari
        # qidirilardi va "Valyuta kursi" savoliga kurs bo'laklari o'rniga
        # kanallar nomi yozilgan bo'lak tushib, javob "...shoxobchasida,
        # ilovada va bankomatda" + "ma'lumot topilmadi" bo'lib chiqardi.
        exact_title = resolved or only_title or catalog_title
        if not exact_title and decision is not None and decision.intent is Intent.RATES:
            exact_title = RATES_TITLE
        results: list[tuple[dict[str, Any], float]] = []
        lexical: list[tuple[dict[str, Any], float]] = []
        yield {"type": "status", "step": "search"}
        if exact_title:
            results = await self._results_by_title(exact_title)
        if not results:
            # Router savolni allaqachon o'qib, tozalangan qidiruv so'rovini
            # bergan — o'shani ishlatamiz. Ilgari bu yerda YANA bitta LLM
            # chaqiruvi (_search_query) ketardi va aynan shu ishni qaytadan
            # qilardi: sekin (CPU) serverda har savol 3 ta chaqiruvga aylanib,
            # javob bir necha daqiqa kutdirardi. Router javob bermasa — eski
            # yo'l zaxira bo'lib qoladi.
            search_q = (
                decision.search_query
                if decision is not None and len(decision.search_query.strip()) >= 3
                else await self._search_query(question, history)
            )
            # Gibrid qidiruv va hujjat tilini tanlash — _search_chunks
            results, lexical = await self._search_chunks(question, search_q)
            # Savol xodim haqida bo'lmasa — xodim bo'laklari kontekstga
            # UMUMAN kirmaydi. Ular tasodifiy o'xshashlik bilan tushib,
            # mahsulot javobiga begona ism va telefon raqamlarini olib
            # kirardi (yo'nalishlar aralashib ketardi).
            if not (
                (decision is not None and decision.intent is Intent.EMPLOYEE)
                or _has_employee_intent(question.lower())
            ):
                results = [
                    (p, s) for p, s in results if p.get("doc_type") != "employee"
                ]

        top_score = results[0][1] if results else 0.0
        self.last_top_score = round(top_score, 3) if results else None
        # Ballar logda: chegarani (RAG_MIN_SCORE) taxmin bilan emas, real
        # raqamlarga qarab sozlash uchun.
        logger.info(
            "Qidiruv ballari: %s",
            " | ".join(
                f"{str(p.get('title', '?'))[:40]} {s:.3f}" for p, s in results[:3]
            )
            or "natija yo'q",
        )
        # Leksik moslik topilgan bo'lsa — cosine ball past bo'lsa ham javobni
        # kesmaymiz: bo'lak ichida savoldagi so'zlar aynan uchragan.
        if not results or (top_score < self.MIN_SCORE and not lexical):
            # Bazada topilmadi — ruxsat etilgan saytlardan qidirib ko'ramiz
            if _web_eligible(decision, question):
                async for ev in self._web_stream(
                    question, decision, lang, want_cyrillic, router_tokens
                ):
                    yield ev
                if self.last_outcome == "web":
                    return
            # Bazada topilmadi — admin "javobsiz savollar" ro'yxatiga tushadi
            self.last_outcome = "no_info"
            text = _localize(NO_INFO_REPLY, lang)
            yield {"type": "delta", "text": text}
            yield {
                "type": "done",
                "completion_tokens": router_tokens,
                "finish_reason": "stop",
                "max_tokens": self.MAX_TOKENS,
                "sources": [],
            }
            return

        # Vektor qidiruv XODIM bo'laklarini qaytargan bo'lsa (masalan bo'lim nomi
        # bo'yicha "IT DEPARTAMENT"), MAHSULOT promptidan foydalanmaymiz — aks
        # holda javob oxiriga "Yana qaysi kredit bo'yicha ma'lumot kerak?" kabi
        # mahsulot savoli qo'shilib ketardi.
        #
        # LEKIN bu yo'l faqat savol HAQIQATAN xodim haqida bo'lganda ochiladi.
        # Ilgari yagona shart "natijalarning yarmi xodim bo'lagi" edi va
        # o'xshashlik tasodifi yetarli bo'lardi: "Ayirboshlash SHAHOBCHASIDA"
        # savoli embedding fazosida "SHAHRISABZ BXM" xodimlariga yaqin chiqib,
        # valyuta kursi o'rniga xodimlar ro'yxati qaytarilgan edi.
        wants_employees = (
            decision is not None and decision.intent is Intent.EMPLOYEE
        ) or _has_employee_intent(question.lower())
        emp_hits = [p for p, _ in results if p.get("doc_type") == "employee"]
        if wants_employees and emp_hits and len(emp_hits) * 2 >= len(results):
            prompt = self._employee_prompt(question, history, emp_hits)
            system = EMPLOYEE_SYSTEM
            max_toks = self.EMPLOYEE_MAX_TOKENS
            sources = []
        else:
            # Sarlavha aniq ma'lum (foydalanuvchi ro'yxatdan tanlagan yoki
            # turkumda bitta mahsulot qoldi) — bu ANIQ mahsulot javobi va
            # katalog kerak emas. Katalog ~2000 token joy egallab, javobning
            # o'zi uchun joy qoldirmasdi.
            prompt, sources = await self._assemble(
                question, history, results, include_catalog=not exact_title
            )
            system = STRICT_RAG_SYSTEM
            max_toks = self.MAX_TOKENS
        # Tekshiruvchi javobni shu kontekstga solishtiradi (to'qilgan raqam)
        self._last_context = prompt
        # Bazadan bo'laklar topildi, lekin ular savolga umuman javob bermasa
        # (masalan bazada yo'q mahsulot) — model NEEDS_WEB deydi va javob
        # ruxsat etilgan saytlardan (turonbank.uz ham) olinadi.
        web_ok = system is STRICT_RAG_SYSTEM and _web_eligible(decision, question)
        if web_ok:
            system = system + RAG_WEB_ADDENDUM
        head: str | None = "" if web_ok else None
        needs_web = False
        src_dump = [{"title": s.title, "score": s.score} for s in sources]
        # Aralash alifboli so'zni tuzatish — concept yo'lidagi bilan bir xil
        # sabab: model bitta so'z ichida kirill va lotinni aralashtirib
        # yuboradi va promptdagi taqiq buni to'xtata olmaydi.
        # Ruscha javobda ikkalasi ham o'chiq (concept yo'lidagi izohga qara).
        tr = StreamingTransliterator() if want_cyrillic else None
        sf = StreamingScriptFixer() if lang == "uz" else None
        yield {"type": "status", "step": "write"}
        async for ev in self.ai_client.stream_generate(
            prompt,
            system_prompt=self._system(system, lang),
            temperature=self.TEMPERATURE,
            max_tokens=max_toks,
        ):
            # Javob boshini ushlab turamiz: NEEDS_WEB foydalanuvchiga chiqmasin
            if head is not None and ev.get("type") in ("delta", "done"):
                if ev.get("type") == "delta":
                    head += ev["text"]
                    if len(head.strip()) <= len(WEB_LOOKUP_TOKEN):
                        continue
                if _is_web_lookup(head):
                    needs_web = True
                    break
                if ev.get("type") == "delta":
                    ev = {**ev, "text": head}
                elif head:
                    yield {
                        "type": "delta",
                        "text": tr.feed(head) if tr is not None else sf.feed(head) if sf is not None else head,
                    }
                head = None
            if ev.get("type") == "delta":
                if tr is not None:
                    ev = {**ev, "text": tr.feed(ev["text"])}
                elif sf is not None:
                    ev = {**ev, "text": sf.feed(ev["text"])}
            if ev.get("type") == "done":
                if tr is not None:
                    rest = tr.flush()
                elif sf is not None:
                    rest = sf.flush()
                else:
                    rest = ""
                if rest:
                    yield {"type": "delta", "text": rest}
                ev["max_tokens"] = self.MAX_TOKENS
                ev["sources"] = src_dump
                ev["completion_tokens"] = (
                    int(ev.get("completion_tokens", 0)) + router_tokens
                )
            yield ev
        if needs_web:
            async for ev in self._web_stream(
                question, decision, lang, want_cyrillic, router_tokens
            ):
                yield ev
            if self.last_outcome != "web":
                self.last_outcome = "no_info"
                yield {"type": "delta", "text": _localize(NO_INFO_REPLY, lang)}
                yield {
                    "type": "done",
                    "completion_tokens": router_tokens,
                    "finish_reason": "stop",
                    "max_tokens": self.MAX_TOKENS,
                    "sources": [],
                }

    async def execute(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> AnswerResult:
        # Himoya — stream yo'li bilan bir xil (qara: _guard_input)
        self.last_outcome = "answered"
        self.last_flag = None
        question, history, blocked = _guard_input(question, history)
        if blocked:
            self.last_outcome = "blocked"
            return AnswerResult(
                answer=_localize(INJECTION_REPLY, detect_reply_lang(question, history)),
                sources=[],
                finish_reason="stop",
            )
        if has_profanity(question):
            self._flag("profanity")
            return AnswerResult(
                answer=_localize(PROFANITY_REPLY, detect_reply_lang(question, history)),
                sources=[],
                finish_reason="stop",
            )
        # Javob tili — stream yo'li bilan bir xil (o'zbek lotin/kirill, rus)
        lang = detect_reply_lang(question, history)
        # Ruscha savolga ruscha hujjatlar (bo'lsa) — katalog va qidiruv shunga qaraydi
        self._kb_lang = "ru" if lang == "ru" else "uz"
        want_cyrillic = lang == "uz_cyrl"

        # Ichki barcha mantiq (xodim qidiruvi, turkum kalit so'zlari, embedding
        # qidiruvi, baza) LOTINCHA ishlaydi — o'zbekcha savolni shu yerdayoq
        # lotinga keltiramiz. Ruscha savol o'girilmaydi (stream yo'liga qara).
        if lang != "ru":
            question = to_latin(question)

        # Foydalanuvchi ro'yxatdan raqam bilan tanlagan bo'lsa ("53") — savolni
        # o'sha band nomiga almashtiramiz (qidiruv ham, prompt ham shuni ko'radi).
        # Bu MAHSULOT ro'yxatidan tanlov ekani ANIQ bo'lsa, xodim yo'nalishini
        # sinamaymiz ham (aks holda "Humo" kabi mahsulot nomi "Humoyun" degan
        # xodimga tasodifan mos kelib, noto'g'ri yo'nalardi).
        # Ro'yxatdan tanlov ('19') yoki aniqlashtiruvchi savolimizga javob
        # ('ha', 'meros omonati') — ikkalasi ham savolni MAHSULOT NOMIga
        # aylantiradi va routerni chetlab o'tadi.
        resolved = _resolve_list_choice(question, history) or _resolve_clarification(
            question, history
        )
        question = resolved or question

        # Xodimlar ma'lumotnomasi — stream yo'li bilan bir xil
        if not resolved:
            hits = await self._directory_hits(question)
            if hits:
                emp_text = _format_employee_answer(hits[:60])
                return AnswerResult(
                    answer=to_cyrillic(emp_text) if want_cyrillic else emp_text,
                    sources=[],
                    finish_reason="stop",
                    completion_tokens=0,
                    max_tokens=self.MAX_TOKENS,
                )

        # Savolni TUSHUNISH — stream yo'li bilan bir xil mantiq
        decision = None if resolved else await self.router.classify(question, history)
        router_tokens = decision.tokens if decision is not None else 0
        self.last_intent = decision.intent.value if decision is not None else None
        if decision is not None and decision.intent is Intent.HARMFUL:
            self._flag("harmful")
            return AnswerResult(
                answer=_localize(HARMFUL_REPLY, lang),
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        if decision is not None and decision.intent in (
            Intent.SMALLTALK,
            Intent.ABOUT_BOT,
        ):
            text = _bot_reply(decision, history, lang)
            return AnswerResult(
                answer=text,
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        # Xavfsizlik to'ri — stream yo'li bilan bir xil: savolda aniq xodim
        # belgisi bo'lsa, bazaga bormaydigan qisqa yo'llar ochilmaydi.
        skip_shortcuts = _has_employee_intent(question.lower())

        # Soha tashqarisidagi va BOSHQA BANK haqidagi savol — stream yo'li
        # bilan bir xil: tayyor matn, model chaqirilmaydi.
        if (
            decision is not None
            and not skip_shortcuts
            and decision.intent in (Intent.OTHER, Intent.OTHER_BANK)
        ):
            reply = (
                OTHER_BANK_REPLY
                if decision.intent is Intent.OTHER_BANK
                else OFF_TOPIC_REPLY
            )
            return AnswerResult(
                answer=_localize(reply, lang),
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        # Qidiruvsiz javob beriladigan niyatlar: soha umumiy savoli (model
        # bilimidan) va suhbatning o'zi haqidagi savol (javob tarixda).
        # Stream yo'lidagi bilan bir xil: umumiy savol bo'lsa ham avval
        # katalog nomlari tekshiriladi (mobil aynan shu yo'ldan keladi).
        catalog_title: str | None = None
        if (
            decision is not None
            and not skip_shortcuts
            and decision.intent is Intent.CONCEPT
            and not _asks_about_organization(question)
        ):
            catalog_title, partial_titles = await self._catalog_title_match(question)
            if catalog_title is not None:
                logger.info(
                    "Umumiy savol bazadagi mahsulotga bog'landi: %r -> %r",
                    question,
                    catalog_title,
                )
            elif (
                1 <= len(partial_titles) <= _CLARIFY_MAX_OPTIONS
                and not _last_turn_was_clarify(history)
                and not _asks_general_meaning(question)
                and not set(partial_titles) & _declined_clarify_titles(history)
            ):
                logger.info(
                    "Aniqlashtirish so'raldi: %r -> %s", question, partial_titles
                )
                return AnswerResult(
                    answer=_clarify_reply(partial_titles, want_cyrillic),
                    sources=[],
                    finish_reason="stop",
                    completion_tokens=router_tokens,
                    max_tokens=self.MAX_TOKENS,
                )

        if (
            decision is not None
            and not skip_shortcuts
            and catalog_title is None
            and decision.intent in (Intent.CONCEPT, Intent.HISTORY, Intent.LANGUAGE)
        ):
            prompt, system, max_toks = self._no_search_call(
                decision.intent, question, history
            )
            web_ok = decision.intent is Intent.CONCEPT and _web_eligible(
                decision, question
            )
            if web_ok:
                system = system + CONCEPT_WEB_ADDENDUM
            gen = await self.ai_client.generate_text_with_usage(
                prompt,
                system_prompt=_with_lang(system, lang),
                temperature=self.TEMPERATURE,
                max_tokens=max_toks,
            )
            if web_ok and _is_web_lookup(gen.text):
                web = await self._web_answer(
                    question, decision, lang, want_cyrillic, router_tokens
                )
                if web is not None:
                    return web
                self.last_outcome = "no_info"
                return AnswerResult(
                    answer=_localize(NO_INFO_REPLY, lang),
                    sources=[],
                    finish_reason="stop",
                    completion_tokens=router_tokens,
                    max_tokens=self.MAX_TOKENS,
                )
            text = _clean_concept_answer(gen.text)
            if want_cyrillic:
                text = to_cyrillic(text)
            elif lang == "uz":
                text = fix_mixed_script(text)
            return AnswerResult(
                answer=text,
                sources=[],
                finish_reason=gen.finish_reason,
                completion_tokens=gen.completion_tokens + router_tokens,
                max_tokens=gen.max_tokens,
            )

        # Valyuta kursi — faktlarni kod, javobni model yozadi (_rates_reply)
        if decision is not None and decision.intent is Intent.RATES:
            rates = await self._rates_reply(
                question, decision.search_query, history, lang
            )
            if rates:
                text, rate_tokens = rates
                if want_cyrillic:
                    text = _rates_to_cyrillic(text)
                elif lang == "uz":
                    text = fix_mixed_script(text)
                return AnswerResult(
                    answer=text,
                    sources=[SourceRef(title=RATES_TITLE, score=1.0)],
                    finish_reason="stop",
                    completion_tokens=router_tokens + rate_tokens,
                    max_tokens=self.MAX_TOKENS,
                )

        # Xodim (telefon/IP) savoli — alohida yo'l (mahsulot RAG'siz).
        #
        # MUHIM: router bu yerda QAROR QILMAYDI, faqat maslahat beradi. Ilgari
        # xodim qidiruvi "router EMPLOYEE desa" ochilardi va model ishonchsiz
        # ishlagani uchun butun ma'lumotnoma yopilib qolardi: yalang'och
        # familiya ("Xamdamboyev") yozilganda router "bu kontakt so'rovi emas"
        # deb, bazada BOR xodim "topilmadi" bo'lardi — bir xil savol goh
        # ishlab, goh ishlamasdi. Endi qidiruvni har doim kod bajaradi (u
        # deterministik), router esa faqat salomlashishni ajratadi.
        # Router yiqilganda ko'r-ko'rona ism taxmini yo'q — stream yo'li bilan
        # bir xil (qara: _blind_employee_guess).
        route = (
            None
            if resolved or _blind_employee_guess(decision, question)
            else await self._employee_route(to_latin(question))
        )
        if route is not None:
            kind, emps = route
            if kind in ("ask", "none"):
                # Stream yo'li bilan bir xil: model chaqirilmaydi (to'qib
                # chiqarishning oldini olish uchun), tayyor matn qaytadi.
                canned = (
                    EMPLOYEE_ASK_REPLY if kind == "ask" else EMPLOYEE_NOT_FOUND_REPLY
                )
                return AnswerResult(
                    answer=_localize(canned, lang),
                    sources=[],
                    finish_reason="stop",
                    completion_tokens=router_tokens,
                    max_tokens=self.MAX_TOKENS,
                )
            # Stream yo'li bilan bir xil: javobni kod tuzadi, model chaqirilmaydi.
            # Xodim javobi keshlanmaydi: intent "employee" CACHEABLE emas.
            # Router savolni "concept" degan bo'lsa ham kontakt keshga
            # tushib, keyin boshqa savolga ham shu javob qaytib qolardi.
            self.last_intent = Intent.EMPLOYEE.value
            emp_text = _format_employee_answer(emps)
            return AnswerResult(
                answer=to_cyrillic(emp_text) if want_cyrillic else emp_text,
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        # Turkumning BARCHA mahsulotini so'ragan keng savol — LLM'ni chaqirmasdan,
        # katalogdan deterministik raqamlangan ro'yxat qaytaramiz (format har doim
        # bir xil bo'lsin: LLM'ga qoldirilsa ba'zan vergul bilan ham chiqib turardi).
        broad_reply, only_title = await self._broad_category_reply(
            question, want_cyrillic
        )
        # Turkum ichida bitta mahsulot aniqlandi — savolni uning to'liq nomiga
        # almashtiramiz (qidiruv ham, prompt ham shuni ko'radi).
        question = only_title or question
        if broad_reply is not None:
            return AnswerResult(
                answer=broad_reply,
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        # Harfsiz (ma'nosiz) so'rov — embedding qidiruviga bermaymiz, darrov
        # "ma'lumot yo'q" (uzoq LLM chaqiruvining oldini oladi).
        if _is_meaningless_query(question):
            return AnswerResult(
                answer=_localize(NO_INFO_REPLY, lang),
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        # Qidiruvda rasmiy sinonimlar bilan kengaytiramiz ("filial" -> "bank
        # xizmatlari markazi/ofisi"), promptdagi SAVOL esa asl holicha qoladi.
        # Savolni suhbat asosida MUSTAQIL savolga aylantiramiz — faqat qidiruv
        # uchun. Promptdagi SAVOL foydalanuvchi yozganidek qoladi.
        # Sarlavha aniq ma'lum (ro'yxatdan raqam tanlangan yoki turkum ichida
        # bitta mahsulot qoldi) — o'sha sarlavhaning bo'laklarini to'g'ridan-
        # to'g'ri olamiz, taxminiy qidiruv boshqa mahsulotni qaytarmasin.
        # VALYUTA KURSI — alohida yo'nalish. Kurs bazada QAT'IY bitta sarlavha
        # ostida turadi (RATES_TITLE, kunlik Celery vazifasi yozadi), shuning
        # uchun uni taxminiy embedding bilan qidirishning hojati yo'q. Ilgari
        # qidirilardi va "Valyuta kursi" savoliga kurs bo'laklari o'rniga
        # kanallar nomi yozilgan bo'lak tushib, javob "...shoxobchasida,
        # ilovada va bankomatda" + "ma'lumot topilmadi" bo'lib chiqardi.
        exact_title = resolved or only_title or catalog_title
        if not exact_title and decision is not None and decision.intent is Intent.RATES:
            exact_title = RATES_TITLE
        results: list[tuple[dict[str, Any], float]] = []
        lexical: list[tuple[dict[str, Any], float]] = []
        if exact_title:
            results = await self._results_by_title(exact_title)
        if not results:
            # Router savolni allaqachon o'qib, tozalangan qidiruv so'rovini
            # bergan — o'shani ishlatamiz. Ilgari bu yerda YANA bitta LLM
            # chaqiruvi (_search_query) ketardi va aynan shu ishni qaytadan
            # qilardi: sekin (CPU) serverda har savol 3 ta chaqiruvga aylanib,
            # javob bir necha daqiqa kutdirardi. Router javob bermasa — eski
            # yo'l zaxira bo'lib qoladi.
            search_q = (
                decision.search_query
                if decision is not None and len(decision.search_query.strip()) >= 3
                else await self._search_query(question, history)
            )
            # Gibrid qidiruv va hujjat tilini tanlash — _search_chunks
            results, lexical = await self._search_chunks(question, search_q)

        # Mos kontekst yo'q (yoki eng yaqini ham juda uzoq) — LLM'ni chaqirmasdan
        # darrov "ma'lumotim yo'q" deb qaytaramiz. Bu bema'ni/aloqasiz savolga
        # modelning uzoq (bir necha daqiqa) "o'ylab" javob berishini oldini oladi.
        top_score = results[0][1] if results else 0.0
        # Ballar logda: chegarani (RAG_MIN_SCORE) taxmin bilan emas, real
        # raqamlarga qarab sozlash uchun.
        logger.info(
            "Qidiruv ballari: %s",
            " | ".join(
                f"{str(p.get('title', '?'))[:40]} {s:.3f}" for p, s in results[:3]
            )
            or "natija yo'q",
        )
        # Leksik moslik topilgan bo'lsa — cosine ball past bo'lsa ham javobni
        # kesmaymiz: bo'lak ichida savoldagi so'zlar aynan uchragan.
        if not results or (top_score < self.MIN_SCORE and not lexical):
            if _web_eligible(decision, question):
                web = await self._web_answer(
                    question, decision, lang, want_cyrillic, router_tokens
                )
                if web is not None:
                    return web
            self.last_outcome = "no_info"
            return AnswerResult(
                answer=_localize(NO_INFO_REPLY, lang),
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        # Xodim bo'laklari qaytgan bo'lsa — xodim prompti (stream tarafi bilan
        # bir xil mantiq): mahsulot formati/"Yana qaysi kredit" qo'shilmasin.
        emp_hits = [p for p, _ in results if p.get("doc_type") == "employee"]
        if emp_hits and len(emp_hits) * 2 >= len(results):
            prompt = self._employee_prompt(question, history, emp_hits)
            system = EMPLOYEE_SYSTEM
            max_toks = self.EMPLOYEE_MAX_TOKENS
            sources = []
        else:
            # Sarlavha aniq ma'lum (foydalanuvchi ro'yxatdan tanlagan yoki
            # turkumda bitta mahsulot qoldi) — bu ANIQ mahsulot javobi va
            # katalog kerak emas. Katalog ~2000 token joy egallab, javobning
            # o'zi uchun joy qoldirmasdi.
            prompt, sources = await self._assemble(
                question, history, results, include_catalog=not exact_title
            )
            system = STRICT_RAG_SYSTEM
            max_toks = self.MAX_TOKENS
        web_ok = system is STRICT_RAG_SYSTEM and _web_eligible(decision, question)
        if web_ok:
            system = system + RAG_WEB_ADDENDUM

        gen = await self.ai_client.generate_text_with_usage(
            prompt,
            system_prompt=_with_lang(system, lang),
            temperature=self.TEMPERATURE,
            max_tokens=max_toks,
        )
        if web_ok and _is_web_lookup(gen.text):
            web = await self._web_answer(
                question, decision, lang, want_cyrillic, router_tokens
            )
            if web is not None:
                return web
            self.last_outcome = "no_info"
            return AnswerResult(
                answer=_localize(NO_INFO_REPLY, lang),
                sources=[],
                finish_reason="stop",
                completion_tokens=router_tokens,
                max_tokens=self.MAX_TOKENS,
            )

        answer = _dedupe_source_links(_strip_stray_followup(gen.text.strip()))
        if want_cyrillic:
            answer = _translit_preserving_titles(answer, [s.title for s in sources])
        elif lang == "uz":
            answer = fix_mixed_script(answer)
        return AnswerResult(
            answer=answer,
            sources=sources,
            finish_reason=gen.finish_reason,
            completion_tokens=gen.completion_tokens + router_tokens,
            max_tokens=gen.max_tokens,
        )
