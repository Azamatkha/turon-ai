from pydantic import Field

from src.core.schemas import Base


class UploadTextRequest(Base):
    # Sarlavha majburiy — u bilan vektor bazaga yoziladi va har bo'lakka qo'shiladi
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1)


class UploadResult(Base):
    chunks: int          # nechta bo'lakka bo'lindi
    vector_dim: int      # embedding vektor o'lchami (masalan 1024)
    total_points: int    # kolleksiyadagi jami point soni (tasdiq uchun)


class PdfUploadResult(UploadResult):
    """PDF yuklash natijasi — admin panelda nima bo'lganini ko'rsatish uchun."""
    title: str           # bazaga yozilgan sarlavha (LLM aniqlagan bo'lishi mumkin)
    pages: int           # PDF'dagi sahifalar soni
    ocr_pages: int       # shundan nechtasi OCR qilindi (skanerlangan sahifalar)
    chars: int           # tozalangandan keyingi matn uzunligi


class EmployeeIn(Base):
    """Bitta xodim yozuvi (JSON orqali yuklash uchun — Excel'siz)."""
    department: str = Field(min_length=1)   # bo'lim (sheet nomi)
    division: str = ""                      # ichki bo'linma (ixtiyoriy)
    position: str = ""                      # lavozim
    fish: str = ""                          # F.I.SH
    ip: str = ""                            # ichki raqam (IP)
    phone: str = ""                         # telefon


class ScrapeRequest(Base):
    url: str = Field(min_length=1)   # parse qilinadigan sahifa manzili


class KnowledgeItem(Base):
    title: str           # yuklangan ma'lumot sarlavhasi
    chunks: int          # shu sarlavha ostidagi bo'laklar soni
    lang: str            # tili (hozircha "uz")
    preview: str         # birinchi bo'lakning qisqa ko'rinishi
    # Yuklangan vaqti (ISO). Eski yozuvlarda bo'lmasligi mumkin — bo'sh satr.
    uploaded_at: str = ""


class KnowledgeChunk(Base):
    chunk_index: int
    text: str


class KnowledgeDetail(Base):
    title: str
    lang: str
    chunks: list[KnowledgeChunk]   # barcha bo'laklar (chunk_index bo'yicha tartiblangan)


class UpdateKnowledgeRequest(Base):
    old_title: str = Field(min_length=1)   # o'zgartirishdan oldingi sarlavha
    title: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1)


class ChatTurn(Base):
    role: str       # "user" yoki "assistant"
    content: str


class QuestionRequest(Base):
    question: str = Field(min_length=1)
    history: list[ChatTurn] = []   # oldingi suhbat (mavzu davomiyligi uchun)


class RateRow(Base):
    """Bitta valyuta qatori. `delta_*` — oldingi yangilanishga nisbatan
    o'zgarish; None bo'lsa o'zgarmagan yoki taqqoslash uchun ma'lumot yo'q."""

    code: str                       # USD, EUR, ...
    name: str                       # AQSh dollari
    buy: float | None = None
    sell: float | None = None
    cb: float | None = None         # Markaziy bank kursi
    delta_buy: float | None = None
    delta_sell: float | None = None
    delta_cb: float | None = None


class RateChannel(Base):
    """Kurs kanali: ayirboshlash shoxobchasi / ilova / bankomat."""

    key: str                        # tab1 / tab2 / tab3
    label: str
    rows: list[RateRow] = []


class RatesResult(Base):
    stamp: str = ""                 # "11.08.2026 11:10:00 dan ma'lumotlar"
    channels: list[RateChannel] = []
    source_url: str = ""


class SourceRef(Base):
    title: str      # javob qaysi hujjatdan olindi
    score: float    # o'xshashlik bahosi (0..1)


class AnswerResult(Base):
    answer: str
    sources: list[SourceRef]
    # Debug: token statistikasi. finish_reason == "length" bo'lsa, javob
    # max_tokens tugagani sabab kesilib qolgan bo'lishi mumkin.
    finish_reason: str = ""
    completion_tokens: int = 0
    max_tokens: int = 0
