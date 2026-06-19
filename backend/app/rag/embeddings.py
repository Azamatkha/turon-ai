from sentence_transformers import SentenceTransformer   # matnni vektorga aylantiruvchi AI model

_model = None   # model shu yerda saqlanadi (global), bir marta yuklab qayta ishlatamiz


def model_ol():
    global _model
    if _model is None:                                # agar model hali yuklanmagan bo'lsa:
        print("bge-m3 yuklanyapti (birinchi marta sekin)...")
        _model = SentenceTransformer("BAAI/bge-m3")   # modelni yuklaymiz (~2.3 GB)
    return _model                                     # keyingi safar shu tayyor modelni qaytaradi
# ↑ "Bir marta yukla, ko'p marta ishlat" tamoyili. 2.3 GB ni har safar yuklamaymiz.


def vektorla(matnlar: list[str]) -> list[list[float]]:
    return model_ol().encode(matnlar, normalize_embeddings=True).tolist()
    #            ↑ matnlar ro'yxatini 1024 ta raqamli vektorlar ro'yxatiga aylantiradi
    #              normalize_embeddings=True -> o'xshashlikni to'g'ri o'lchash uchun shart
# ↑ ["salom", "xayr"]  ->  [[0.1, -0.2, ...], [0.3, 0.0, ...]]   (har biri 1024 ta raqam)