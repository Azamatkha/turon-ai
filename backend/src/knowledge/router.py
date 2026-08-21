"""Savolni TUSHUNISH bosqichi — javob berishdan oldingi "o'ylash".

Ilgari savol regex va prefiks o'xshashligi bilan yo'naltirilardi. U ko'r-ko'rona
ishlardi: masalan "sen qaysi madel orqali **javob** beryapsan" savolidagi
"javob" so'zi "**Javohir**" ismiga to'rt harf bilan o'xshab qolib, foydalanuvchi
5 ta xodim ro'yxatini olardi — model esa umuman chaqirilmasdi.

Endi savolni model o'qiydi va nima so'ralayotganini o'zi aniqlaydi. Model
faqat QARORNI beradi (niyat + ajratilgan ma'lumot); xodim ro'yxati kabi aniq
ma'lumotni baribir kod yig'adi, shunda IP va telefon raqamlari hech qachon
to'qib chiqarilmaydi.
"""

from enum import StrEnum
import json
from typing import Any

from loggers import get_logger
from src.core.ai.interfaces import BaseAIClient
from src.knowledge.schemas import ChatTurn

logger = get_logger(__name__)


class Intent(StrEnum):
    """Savol nima haqida ekani."""

    # Xodim/bo'lim kontaktlari: ism, ichki raqam (IP), telefon, bo'lim tarkibi
    EMPLOYEE = "employee"
    # Bank mahsulotlari va qoidalari: kredit, karta, omonat, o'tkazma...
    PRODUCT = "product"
    # Bank/moliya sohasining UMUMIY bilimi — Turonbank fakti EMAS: to'lov
    # tizimlari, moliyaviy atamalar, tashkilotlar tarixi, iqtisodiy tushunchalar
    CONCEPT = "concept"
    # Valyuta kurslari
    RATES = "rates"
    # Filial / BXM / manzil / ish vaqti
    BRANCH = "branch"
    # Salomlashish, minnatdorchilik, bo'sh gap
    SMALLTALK = "smalltalk"
    # Botning o'zi haqida: kimsan, qaysi model, nima qila olasan
    ABOUT_BOT = "about_bot"
    # Savol SUHBATNING O'ZIGA tegishli: "sen bergan manzil qanday",
    # "yuqorida nima dedingiz", "oldingi javobingni tushuntir"
    HISTORY = "history"
    # Bankka aloqasi yo'q yoki tushunarsiz
    OTHER = "other"


class Route:
    """Router qarori."""

    def __init__(
        self,
        intent: Intent,
        search_query: str,
        person_name: str = "",
        ip_number: str = "",
        department: str = "",
        reply: str = "",
    ) -> None:
        self.intent = intent
        # Vektor qidiruv uchun tozalangan/to'ldirilgan so'rov
        self.search_query = search_query
        # Ajratilgan ma'lumotlar (faqat EMPLOYEE uchun mazmunli)
        self.person_name = person_name
        self.ip_number = ip_number
        self.department = department
        # SMALLTALK / ABOUT_BOT uchun tayyor javob
        self.reply = reply

    def __repr__(self) -> str:
        return (
            f"Route(intent={self.intent}, query={self.search_query!r}, "
            f"name={self.person_name!r}, ip={self.ip_number!r}, "
            f"dept={self.department!r})"
        )


ROUTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [i.value for i in Intent],
        },
        "person_name": {"type": "string"},
        "ip_number": {"type": "string"},
        "department": {"type": "string"},
        "search_query": {"type": "string"},
        "reply": {"type": "string"},
    },
    "required": ["intent", "search_query"],
}


ROUTER_SYSTEM = """Sen — Turonbank ichki AI yordamchisining YO'NALTIRUVCHI qismisan.
Sening vazifang javob yozish EMAS. Foydalanuvchi ASLIDA nima so'rayotganini
tushunib, qaror qaytarish.

Avval savolni diqqat bilan o'qi va o'zingdan so'ra: bu odam nima bilmoqchi?
So'zlarga emas, MA'NOGA qara.

Niyat (intent) turlari:
- "employee"  — muayyan XODIM yoki BO'LIM kontakti so'ralyapti: ism bo'yicha,
                ichki raqam (IP) bo'yicha, telefon yoki bo'lim tarkibi.
                MISOL: "Azamat Xamdamovning raqami", "1036 kimniki",
                "HR bo'limi xodimlari".
- "product"   — TURONBANKNING mahsuloti yoki qoidasi: kredit, karta, omonat,
                o'tkazma, komissiya, shartlar, hujjatlar. Ya'ni javob bank
                bazasidan olinishi kerak bo'lgan ANIQ FAKT.
                MISOL: "Visa Gold shartlari", "ta'lim krediti foizi qancha",
                "qanday kartalar bor".
- "concept"   — bank/moliya/iqtisodiyot sohasiga oid UMUMIY savol; javobi
                Turonbank bazasida emas, umumiy bilimda.
                MISOL: "Mastercard qanday kompaniya", "Visa qachon tashkil
                topgan", "Visa bosh ofisi qayerda", "annuitet nima",
                "ekvayring qanday ishlaydi", "inflatsiya nima", "Humo va
                Uzcard farqi nima", "SWIFT nima uchun kerak".
- "rates"     — valyuta kurslari.
- "branch"    — filial / bank xizmatlari markazi (BXM) / manzil / ish vaqti.
- "smalltalk" — salomlashish, rahmat, xayrlashuv, bo'sh gap.
- "about_bot" — SENING o'zing haqingda: kimsan, qanday ishlaysan, qaysi model,
                nima qila olasan, kim yaratgan.
- "history"   — savol SUHBATNING O'ZI haqida: sen oldin nima deganing,
                qayerdan olganing, javobingni takrorlash yoki tushuntirish.
                MISOL: "sen bergan manzil qanday", "buni qayerdan olding",
                "yuqorida nima dedingiz", "oldingi javobingni takrorla",
                "shu javobingdagi ikkinchi bandni tushuntir".
                DIQQAT — chegara: "foizlari qanday", "muddati qancha" kabi
                savol suhbatdagi MAVZU haqida (bazadan qidirish kerak), sening
                javobing haqida emas -> bu "history" EMAS, "product".
                "history" ni faqat gap SENING javobing haqida ketganda tanla.
- "other"     — bank/moliya/iqtisodiyot sohasiga UMUMAN aloqasi yo'q
                (sport, siyosat, ob-havo, dasturlash, tibbiyot, ko'ngilochar)
                yoki savol butunlay tushunarsiz.
                MISOL: "Ronaldo qaysi jamoada o'ynaydi", "ertaga havo qanday".

"product" MI YOKI "concept" MI — SHU CHEGARANI ANIQ TUT:
Savolning JAVOBI qayerda turishiga qara.
- Javob Turonbankning o'z hujjatida bo'lishi kerakmi (bankdagi stavka,
  muddat, summa, komissiya, mahsulot sharti, filial, xodim)? -> "product".
- Javob umumiy bilimdami (tashkilot nima bilan shug'ullanadi, qachon
  tashkil topgan, bosh ofisi qayerda, atama nimani anglatadi, ikki narsa
  nima bilan farq qiladi)? -> "concept". Savolda "Visa", "Mastercard",
  "Humo" kabi nom uchragani uni "product" qilmaydi — Turonbankning O'SHA
  nomdagi mahsuloti shartlari so'ralgandagina "product" bo'ladi.
- Ikkalasi ham so'ralgan bo'lsa ("Visa nima va sizda qanday Visa kartalar
  bor") -> "product": bank qismi bazadan olinishi shart.
- Soha tashqarisidagi savolni HECH QACHON "concept" qilma — u "other".

DIQQAT — eng ko'p uchraydigan xato:
Savolda odam ismiga O'XSHAB ketadigan oddiy so'z bo'lishi mumkin
("javob", "salom", "model", "hisob"). Bu xodim so'rovi EMAS.
"employee" ni faqat foydalanuvchi HAQIQATAN kimningdir kontaktini
so'rayotganiga ishonch hosil qilganingda tanla.

SUHBATNI DAVOM ETTIRISH (juda muhim):
Senga oldingi suhbat ham beriladi. Foydalanuvchi qisqa savol bersa, u
ODATDA hozirgina gaplashilgan mavzu haqida bo'ladi. Niyatni ham,
"search_query" ni ham SHUNGA qarab aniqla:
- "foizlari qanday", "muddati?", "qancha?", "ularni", "shuni", "birinchisi",
  "yana" — bular oldingi javobdagi narsalarga ishora qiladi.
- Olmoshni O'ZING YECHIB, "search_query" ga haqiqiy nomlarni yoz.
  MISOL: sen ipoteka kreditlarini sanab bergansan, foydalanuvchi
  "foizlari qanday ularni" deb yozdi ->
  search_query: "Yangi hayot, Kelajak uyi, Yanada oson ipoteka krediti
  yillik foiz stavkasi"
  "foizlari qanday ularni" ni O'Z HOLICHA qoldirsang, qidiruv butunlay
  boshqa mavzuni (masalan omonatlarni) topib keladi — bu jiddiy xato.
- Mavzu o'zgarganini faqat foydalanuvchi ANIQ boshqa narsa so'raganda qabul
  qil; qisqalik mavzu o'zgardi degani EMAS.
- SUHBATNING MAVZUSI KIM/NIMA EKANINI YO'QOTMA. Foydalanuvchi "kompaniya",
  "u", "bu tashkilot" desa — bu HOZIRGINA gaplashilgan tashkilot, avtomatik
  ravishda "Turonbank" EMAS.
  MISOL: suhbat Visa haqida ketayotgan edi, foydalanuvchi "kompaniya bosh
  ofisi qayerda" dedi -> bu VISA ning bosh ofisi, intent "concept".
  Buni Turonbank haqida deb tushunish JIDDIY XATO: foydalanuvchi Visa
  so'raganda unga bankning manzili berilardi.

Maydonlar:
- "intent"       — yuqoridagilardan bittasi.
- "person_name"  — savolda aniq ODAM ISMI bo'lsa, o'shani yoz. Aks holda "".
- "ip_number"    — savolda ichki raqam (3-5 xonali) bo'lsa. Aks holda "".
- "department"   — bo'lim/departament nomi aytilgan bo'lsa. Aks holda "".
- "search_query" — bazadan qidirish uchun tozalangan, O'ZI YETARLI so'rov:
                   ortiqcha so'zlarsiz, olmoshlar yechilgan, kerak bo'lsa
                   rasmiy atama bilan to'ldirilgan.
                   smalltalk/about_bot/concept/other/history uchun bo'sh satr
                   qoldir — bu niyatlarda bazadan qidirilmaydi.
- "reply"        — FAQAT "smalltalk" va "about_bot" uchun: qisqa, xushmuomala
                   javob (1-2 gap), foydalanuvchi tilida. Boshqa hollarda "".

FOYDALANUVCHI O'ZBEKCHANI QANDAY YOZSA, SHUNDAY TUSHUN:
- apostrof har xil yoziladi yoki umuman tushib qoladi: o' / oʻ / o‘ / ` / o.
  "Bo'lim", "boʻlim", "bolim" — BIR XIL so'z;
- x va h almashadi: "shoxobcha"/"shahobcha", "Xamdamov"/"Hamdamov";
- kirill va lotin bir xil ma'noda ("кредит" = "kredit");
- xato terilgan so'zlar normal ("kridit", "madel") — ko'zda tutilgan so'zni
  o'zing top, "tushunmadim" dema.

Sen Turonbank uchun ishlaysan. "about_bot" da: sen Turonbankning ichki AI
yordamchisisan, bank hujjatlari va xodimlar ma'lumotlari asosida javob berasan.
Qaysi model ekaningni aytma — buning o'rniga nima qila olishingni ayt.

Faqat JSON qaytar."""


class QuestionRouter:
    """Savolni modelga o'qitib, qaror oladi.

    O'ylash (think) SHU YERDA yoqilgan: chiqish qisqa, shuning uchun kechikish
    kam, foyda esa katta — asosiy xato aynan savolni tushunmaslikdan kelib
    chiqardi. Yakuniy javob esa o'ylashsiz oqim bilan boradi.
    """

    MAX_TOKENS = 800
    TEMPERATURE = 0.0
    # Kontekstga qo'shiladigan oxirgi almashuvlar soni
    HISTORY_TURNS = 4

    def __init__(self, ai_client: BaseAIClient) -> None:
        self.ai_client = ai_client

    def _build_prompt(self, question: str, history: list[ChatTurn] | None) -> str:
        parts: list[str] = []
        if history:
            recent = history[-self.HISTORY_TURNS :]
            lines = [f"{t.role}: {t.content}" for t in recent if t.content.strip()]
            if lines:
                parts.append("Oldingi suhbat:\n" + "\n".join(lines))
        parts.append(f"Foydalanuvchi savoli:\n{question}")
        return "\n\n".join(parts)

    async def classify(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> Route:
        """Savol niyatini aniqlaydi.

        Model javob bermasa yoki xato qaytarsa — PRODUCT ga tushamiz: bu eng
        zararsiz zaxira, chunki u oddiy RAG qidiruvi (xodim ro'yxatini
        tasodifan chiqarib yubormaydi).
        """
        fallback = Route(intent=Intent.PRODUCT, search_query=question)
        try:
            result = await self.ai_client.generate_json(
                self._build_prompt(question, history),
                schema=ROUTER_SCHEMA,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
                system_prompt=ROUTER_SYSTEM,
                think=True,
            )
        except Exception:
            logger.exception("Router chaqiruvi muvaffaqiyatsiz: %r", question)
            return fallback

        data = result.data
        if not isinstance(data, dict) or "raw" in data:
            logger.warning("Router JSON qaytarmadi: %s", json.dumps(data)[:300])
            return fallback

        raw_intent = str(data.get("intent", "")).strip().lower()
        try:
            intent = Intent(raw_intent)
        except ValueError:
            logger.warning("Router noma'lum intent qaytardi: %r", raw_intent)
            return fallback

        query = str(data.get("search_query", "")).strip() or question
        route = Route(
            intent=intent,
            search_query=query,
            person_name=str(data.get("person_name", "")).strip(),
            ip_number=str(data.get("ip_number", "")).strip(),
            department=str(data.get("department", "")).strip(),
            reply=str(data.get("reply", "")).strip(),
        )
        logger.info("Router: %r -> %r", question, route)
        return route
