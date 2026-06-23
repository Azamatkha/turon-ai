from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    savol: str = Field(min_length=1, description="Foydalanuvchi savoli")
    top_k: int | None = Field(default=None, ge=1, le=20)


class Manba(BaseModel):
    manba: str
    sarlavha: str
    ishonch: float


class AskResponse(BaseModel):
    javob: str
    manbalar: list[Manba]
