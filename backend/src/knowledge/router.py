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
    # Savol BOSHQA bank haqida: raqobatchi bank mahsuloti, banklar ro'yxati,
    # reytingi yoki taqqoslash. Bot bunga javob bermaydi — faqat Turonbank
    OTHER_BANK = "other_bank"
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
- "other_bank" — savol BOSHQA bank (Turonbank EMAS) haqida: raqobatchi
                bankning mahsuloti, foizi, filiali; banklarning ro'yxati,
                reytingi, soni; "qaysi bank yaxshi" turidagi taqqoslash.
                MISOL: "Kapitalbank kartasi qancha turadi", "Ipoteka bankda
                foiz qancha", "O'zbekistondagi top banklar ro'yxati",
                "eng ishonchli bank qaysi", "O'zbekistonda nechta bank bor".
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

"other_bank" MI YOKI "concept" MI — SHU CHEGARANI EHTIYOT BILAN TUT:
Savolda "bank" so'zi borligi O'ZI HECH NARSANI anglatmaydi. Yagona savol shu:
javob MUAYYAN boshqa bank(lar) haqida bo'lishi kerakmi, yoki bank ishining
UMUMIY qoidasi haqidami?
- Boshqa bank nomi aytilgan bo'lsa ("Kapitalbank", "Ipoteka bank",
  "Aloqabank", "Xalq banki", "Sberbank", "Anorbank") YOKI nom aytilmasa ham
  javob banklarni sanab chiqish, reyting, "qaysisi yaxshi" bo'lsa
  -> "other_bank".
- Bank ishi, moliya, iqtisodiyot UMUMIY tarzda so'ralgan bo'lsa -> "concept".
UMUMIY SAVOLNI "other_bank" QILISH JIDDIY XATO: "bank tizimi qanday ishlaydi"
deb so'ragan odam boshqa bank haqida so'ramayapti, unga bemalol javob
beriladi. Shubhalansang — "concept" tanla.

ANIQ MISOLLAR — chegara aynan shu yerdan o'tadi:
  "bank tizimi qanday ishlaydi"              -> concept
  "tijorat banklari qanday foyda qiladi"     -> concept
  "Markaziy bank nima bilan shug'ullanadi"   -> concept
  "kredit foizi qanday hisoblanadi"          -> concept
  "banklar depozitni nima uchun oladi"       -> concept
  "O'zbekistondagi top banklar ro'yxati"     -> other_bank
  "eng yaxshi bank qaysi"                    -> other_bank
  "O'zbekistonda nechta bank bor"            -> other_bank
  "Kapitalbank kartasi qancha turadi"        -> other_bank
  "Ipoteka bankda foiz sizdagidan arzonmi"   -> other_bank

TIZIM/KOMPANIYA ni KARTA/MAHSULOT dan AJRAT (bu yerda ko'p xato bo'lgan):
Visa, Mastercard, Uzcard, Humo, UnionPay — bularning har biri IKKI xil
narsani anglatadi:
  (1) TASHKILOT/TIZIM ning o'zi — u qanday ishlaydi, kim tashkil qilgan,
      milliymi yoki xalqaromi, bosh ofisi qayerda -> HAR DOIM "concept";
  (2) Turonbankning O'SHA nomdagi KARTASI — narxi, muddati, sug'urta
      depoziti, qanday olish mumkin -> "product".
Savolda "tizim", "tizimi", "kompaniya", "kompaniyasi", "korporatsiya",
"tashkilot" so'zi bo'lsa yoki "qanday ishlaydi", "qachon tashkil topgan",
"kim tashkil qilgan", "milliymi", "xalqaromi" deb so'ralsa — bu (1),
ya'ni "concept". Foydalanuvchi bank shartlarini so'ramayapti.

ANIQ MISOLLAR — shu qolipni AYNAN takrorla:
  "Visa kompaniyasi qanday ishlaydi"          -> concept
  "Visa tizimi qanday ishlaydi"               -> concept
  "Uzcard tizimichi? U milliy kompaniyami?"   -> concept
  "Humo va Uzcard farqi nima"                 -> concept
  "Mastercard qachon tashkil topgan"          -> concept
  "Visa Gold shartlari qanday"                -> product
  "Uzcard kartasi qancha turadi"              -> product
  "qanday kartalaringiz bor"                  -> product

FOYDALANUVCHI SENI TUZATSA — QAYTA O'YLA:
"men ... haqida so'radim, ... haqida so'ramadim", "bu emas", "meni
tushunmadingiz" degan xabar — bu YANGI savol emas, oldingi savolning
TUZATILGAN holati. Foydalanuvchi ANIQ nimani rad etayotganiga qara va
niyatni O'ZGARTIR: oldin "product" degan bo'lsang va u "kartasi haqida
so'ramadim, tizimi haqida so'radim" desa -> endi "concept". Xuddi shu
niyatni qaytarish JIDDIY XATO: foydalanuvchi bir xil javobni ikki marta
oladi va tuzatishning hech qanday foydasi bo'lmaydi.

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
                   smalltalk/about_bot/concept/other/other_bank/history uchun
                   bo'sh satr
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

QISQA O'YLA. Bu — yo'naltirish qarori, tadqiqot emas. Bir-ikki jumlada
"bu odam nima bilmoqchi?" degan savolga javob ber va DARROV JSON yoz.
Variantlarni sanab chiqma, o'zing bilan bahslashma, javob matnini
tayyorlama. Uzoq o'ylasang chiqish uchun joy qolmaydi va qaror UMUMAN
yetib bormaydi.

Faqat JSON qaytar."""


class QuestionRouter:
    """Savolni modelga o'qitib, qaror oladi.

    AVVAL O'YLASHSIZ so'raymiz, o'ylash esa faqat ZAXIRA. Ilgari teskari edi
    va serverda bu har bir savolni 2 daqiqaga cho'zib yuborardi (pastdagi
    izohga qara). Yakuniy javob esa o'ylashsiz oqim bilan boradi.
    """

    # NEGA O'YLASH ZAXIRAGA TUSHIRILDI — o'lchangan fakt, taxmin emas.
    # 2026-09-10 server loglarida QOLIP shunday edi:
    #   think=True  -> HAR SAFAR aynan 120 s da httpx.ReadTimeout
    #   think=False -> o'sha zahoti 3-21 s da to'g'ri JSON
    # Model issiq turganda ham shunday bo'lgan (sarlavha 2.7 s da tayyor
    # bo'lgan, uch soniyadan keyingi router chaqiruvi baribir 120 s yegan).
    # Sababi: o'ylash tokenlari ham num_predict byudjetidan yeyiladi, ya'ni
    # model 3000 tokenni to'liq mulohazaga sarflaydi va JSON yozishga
    # ulgurmaydi. Natijada foydalanuvchi 2 daqiqa kutardi-yu, javobni baribir
    # o'ylashsiz urinish berardi.
    #
    # O'ylashsiz chiqish — faqat qaror JSON'i, ~100 token. 512 keng zaxira.
    MAX_TOKENS = 512
    # Zaxira (o'ylash) urinishi uchun byudjet. 3000 emas: byudjet qancha katta
    # bo'lsa, model shuncha uzoq o'ylaydi va aynan shu timeout'ga olib kelardi.
    MAX_TOKENS_THINK = 1024
    # Router uchun ALOHIDA timeout — config.ai.TIMEOUT_SECONDS (120 s) yakuniy
    # javob uchun mo'ljallangan, savolni TUSHUNISH esa sekundlar ichida
    # bo'lishi kerak. Ikkala urinish ham yiqilsa, foydalanuvchi 120 s emas,
    # ~55 s dan keyin PRODUCT zaxirasi bilan javob oladi.
    TIMEOUT_FAST = 20.0
    TIMEOUT_THINK = 35.0
    TEMPERATURE = 0.0
    # Kontekstga qo'shiladigan oxirgi almashuvlar soni. 4 -> 6: mavzu
    # ("kompaniya" kim edi) bir necha almashuv oldin aytilgan bo'lishi mumkin,
    # va router aynan shu bog'lanishni topa olmay xato qilardi. num_ctx=16384
    # bilan bunga joy bor.
    HISTORY_TURNS = 6
    # Har bir xabardan promptga tushadigan maksimal belgi (qara: _build_prompt)
    HISTORY_MSG_CHARS = 600

    def __init__(self, ai_client: BaseAIClient) -> None:
        self.ai_client = ai_client

    def _build_prompt(self, question: str, history: list[ChatTurn] | None) -> str:
        parts: list[str] = []
        if history:
            recent = history[-self.HISTORY_TURNS :]
            lines: list[str] = []
            for t in recent:
                text = " ".join(t.content.split())
                if not text:
                    continue
                # Xabar QISQARTIRILADI. Routerga xabarning MAVZUSI kerak,
                # to'liq matni emas: "kompaniya" kim ekanini aniqlash uchun
                # javobning boshi yetarli. 20 bandli mahsulot ro'yxati esa
                # (~3000 belgi) promptni shishirib, o'ylashni cho'zib
                # yuboradi — aynan shu chiqish uchun joy qoldirmasdi.
                if len(text) > self.HISTORY_MSG_CHARS:
                    text = text[: self.HISTORY_MSG_CHARS].rstrip() + "..."
                lines.append(f"{t.role}: {text}")
            if lines:
                parts.append("Oldingi suhbat:\n" + "\n".join(lines))
        parts.append(f"Foydalanuvchi savoli:\n{question}")
        return "\n\n".join(parts)

    async def _ask(
        self,
        prompt: str,
        question: str,
        *,
        think: bool,
        max_tokens: int,
        timeout: float,
    ) -> dict[str, Any] | None:
        """Modelga bir marta murojaat qiladi. JSON kelmasa None qaytaradi.

        Chiqish token chegarasiga tegib uzilganini ALOHIDA logga yozamiz —
        busiz router jimgina PRODUCT'ga tushib qolgani umuman sezilmaydi
        (savol tushunilmagan bo'lsa ham javob "normal" ko'rinadi)."""
        try:
            result = await self.ai_client.generate_json(
                prompt,
                schema=ROUTER_SCHEMA,
                temperature=self.TEMPERATURE,
                max_tokens=max_tokens,
                system_prompt=ROUTER_SYSTEM,
                think=think,
                timeout=timeout,
            )
        except Exception:
            logger.exception("Router chaqiruvi muvaffaqiyatsiz: %r", question)
            return None

        used = int((result.usage or {}).get("completion_tokens", 0) or 0)
        if used >= max_tokens - 16:
            logger.warning(
                "Router chiqishi token chekloviga tegdi (%d/%d, think=%s): %r",
                used,
                max_tokens,
                think,
                question,
            )

        data = result.data
        if not isinstance(data, dict) or "raw" in data or not data.get("intent"):
            logger.warning(
                "Router JSON qaytarmadi (think=%s): %s",
                think,
                json.dumps(data)[:300],
            )
            return None
        return data

    async def classify(
        self, question: str, history: list[ChatTurn] | None = None
    ) -> Route:
        """Savol niyatini aniqlaydi.

        Model javob bermasa yoki xato qaytarsa — PRODUCT ga tushamiz: bu eng
        zararsiz zaxira, chunki u oddiy RAG qidiruvi (xodim ro'yxatini
        tasodifan chiqarib yubormaydi).
        """
        prompt = self._build_prompt(question, history)
        fallback = Route(intent=Intent.PRODUCT, search_query=question)

        # ASOSIY URINISH — O'YLASHSIZ. Chiqish qisqa, sxema bo'yicha majburlangan
        # va amalda deyarli har doim to'g'ri JSON beradi (serverda 3-21 s).
        data = await self._ask(
            prompt,
            question,
            think=False,
            max_tokens=self.MAX_TOKENS,
            timeout=self.TIMEOUT_FAST,
        )
        if data is None:
            # ZAXIRA — O'YLASH BILAN. Bu yerga faqat o'ylashsiz urinish JSON
            # bermagan (yoki timeout bo'lgan) holatda tushamiz. Ko'r-ko'rona
            # PRODUCT zaxirasiga tushishdan oldingi oxirgi imkoniyat.
            logger.info("Router o'ylash bilan qayta urinilmoqda: %r", question)
            data = await self._ask(
                prompt,
                question,
                think=True,
                max_tokens=self.MAX_TOKENS_THINK,
                timeout=self.TIMEOUT_THINK,
            )
        if data is None:
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
