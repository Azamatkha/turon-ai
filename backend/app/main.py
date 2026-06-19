from fastapi import FastAPI          # veb-server yaratuvchi kutubxona

app = FastAPI(title="Turon-AI")      # "app" — bizning veb-serverimiz


@app.get("/")                        # kimdir http://localhost:8000/ ni ochsa:
def health():
    return {"status": "Turon-AI tirik"}   # "server ishlayapti" deb javob beradi
# ↑ Hozircha faqat "tirikmi?" tekshiruvi. KEYINGI bosqichda shu faylga
#   /ask endpoint qo'shamiz: savol -> retriever -> AI -> javob.