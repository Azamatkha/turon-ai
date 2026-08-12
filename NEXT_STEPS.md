# Keyingi qadamlar

**Oxirgi yangilanish:** 2026-08-12

Bu fayl ikki qismdan iborat:
1. **Nima qilindi** — shu sessiyada kiritilgan o'zgarishlar (ertaga tekshirish uchun).
2. **Nima qolgan** — muhimlik bo'yicha tartiblangan takliflar.

Kengroq tahlil: [CODE_REVIEW.md](CODE_REVIEW.md).
Xatolar va yechimlari: [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 1. Shu sessiyada nima qilindi

> Hech narsa commit qilinmadi — hammasi working tree'da. `git diff` bilan ko'ring.
> Yoqmagan qismini `git checkout -- <fayl>` bilan qaytarasiz.

### Backend

| Nima | Fayl |
|---|---|
| **`PATCH /v1/users/me`** — foydalanuvchi o'z ismi va loginini o'zgartiradi. Login band bo'lsa 409. `user_id` **tokendan** olinadi, tanadan emas | `user/usecases/update_own_profile.py`, `user/routers.py`, `user/schemas.py` |
| **Parol o'zgartirishda joriy parol majburiy** — ilgari o'g'irlangan token bilan parolni almashtirib, egasini hisobidan butunlay chiqarib yuborish mumkin edi | `user/auth/schemas.py`, `user/usecases/update_password.py` |
| **Admin foydalanuvchi tahrirlashda login band-emasligi tekshiriladi** — ilgari band login yuborilsa Postgres unique indeksi buzilib, tushunarsiz xato chiqardi | `user/usecases/admin_update_user.py` |
| **Email/ism mantiqini bitta joyga yig'ish** — `EMAIL_DOMAIN` uchta use-case'da alohida yozilgan edi | `user/constants.py` (yangi) |
| **Login o'zgarsa email ham yangilanadi** — email login'dan hosil qilinadi, aks holda keyinchalik unique indeks buzilardi | `update_own_profile.py`, `admin_update_user.py` |
| **`is_deleted=False` filtri** login qidiruvida — unique indeks ham qisman (partial), aks holda o'chirilgan xodimning logini abadiy band bo'lib qolardi | register / create / update use-case'lar |
| Testlar yangilandi + **2 ta yangi test** (noto'g'ri joriy parol, joriy parolsiz so'rov) | `tests/unit/src/user/...` |

### Frontend

| Nima | Natija |
|---|---|
| **Profilda ism va login endi haqiqatan saqlanadi** | Ilgari "Saqlandi" chiqardi, lekin sahifa yangilanishi bilan eski qiymat qaytardi (readOnly qilib qo'yilgan edi) |
| **Parol o'zgartirishda joriy parol so'raladi**; muvaffaqiyatdan keyin login sahifasiga o'tkaziladi | Backend hamma sessiyani bekor qiladi — bo'lmasa foydalanuvchi sababsiz 401 olardi |
| **O'lik kod o'chirildi:** `LightRays`, `GradientWaves`, `Grainient`, `Iridescence`, `GlowOrbs` (~1 489 qator) + `ogl` paketi | `DotField` **qoldirildi** — u login va 404 sahifasida ishlatiladi |
| Adashib qolgan `frontend/frontend/` papkasi o'chirildi | — |
| **ESLint tuzatildi** | Konfig butunlay yiqilardi: `reactHooks.configs.flat.recommended` 5.2.0 da mavjud emas → `'recommended-latest'` |
| i18n: `currentPassword*` kalitlari qo'shildi (uz / uz_cyrl / ru), ishlatilmaydigan `profileReadOnly` va `taken` olib tashlandi | — |

**Tekshirildi:** `tsc --noEmit` toza · `vite build` toza (479 KB / gzip 153 KB) ·
backend fayllari sintaksis tekshiruvidan o'tdi.
**Tekshirilmadi:** backend Docker'da ishga tushirilmadi (ertaga work PC da).

### Ertaga birinchi navbatda

```bash
npm --prefix frontend install
```

(`ogl` olib tashlangani uchun `package-lock.json` yangilanishi kerak.)

```bash
make deploy-dev
```

so'ng `make test` — backend testlari o'zgargan.

---

## 2. Qolgan ishlar

### Muhim

**2.1 `knowledge/usecases.py` — 2 643 qator, 9 ta use-case bitta faylda.**
`CLAUDE.md` da e'lon qilingan `usecases/<action>.py` pattern boshqa hamma domenda
saqlangan. Bu fayl juda katta bo'lgani uchun unga test yozish ham, o'qish ham qiyin.
Bo'lish **mexanik** ish, lekin importlar ko'p — konteyner ishlab turganda,
bittalab qilish kerak.

**2.2 Fayl yuklashda hajm cheklovi ilova darajasida.**
`read_upload_limited()` qo'shilgan, lekin `knowledge` domenidagi hamma yuklash
nuqtasi undan foydalanayotganini tekshirish kerak.

**2.3 `OLLAMA_MODEL = "qwen3.5:latest"` — suzuvchi teg.**
`:latest` server tomonda jimgina almashishi mumkin va javob sifati bir kunda
o'zgarib qolishi mumkin. Aniq versiyaga pin qiling (`qwen3.5:14b-instruct-q4_K_M`
kabi) — `src/main/config.py:136`.

**2.4 Prompt byudjeti zaxirasi kam (~470 token).**
System prompt ~4 000 token, `num_ctx` 8 192. Sig'masa Ollama promptning
**boshini** (ya'ni system prompt'ni) jimgina kesadi va model qoidalarni
"unutadi". Yangi qoida qo'shishdan oldin `OLLAMA_NUM_CTX` ni 12288 ga oshiring.

### O'rtacha

**2.5 ESLint xatolari:** 11 ta xato, 57 ta ogohlantirish (hammasi eski koddan).
Eng ko'p uchraydigani — `<div onClick>` (klaviatura bilan ishlamaydi) va
`no-autofocus`. `npx eslint src` bilan ro'yxatni oling.

**2.6 Bo'limni (`department`) foydalanuvchi o'zi o'zgartira olmaydi.**
Ataylab: bank uchun bu HR ma'lumoti. Agar kerak bo'lsa
`UpdateOwnProfileModel` ga qo'shing — lekin `role` ni **hech qachon** qo'shmang.

**2.7 Tokenlar `localStorage` da.** Ichki tarmoq uchun qabul qilinadigan xavf.
`httpOnly` cookie'ga o'tish — katta ish (CSRF himoyasi ham kerak bo'ladi).
Xavfsizlik header'lari (CSP kiritilgan) allaqachon
`src/core/middleware.py` da bor.

**2.8 Chat `/ask/stream` uchun rate limit user_id bo'yicha** — kiritilgan,
lekin real yuk ostida 20/daqiqa yetarli-yetmasligini o'lchash kerak.

### Kichik

- `main/config.py:290` — `config = get_settings()` import vaqtida ishlaydi; env
  to'liq bo'lmasa modul import'da yiqiladi va xato xabari tushunarsiz bo'ladi.
- `knowledge/routers.py` `scrape_url` ixtiyoriy URL qabul qiladi — SSRF yuzasi
  (faqat admin, past xavf, lekin ichki manzillarni bloklash arzon).
- `services/seedData.ts` hali ham repo'da — endi hech qayerdan ishlatilmasa
  o'chirilsin.
- `/health/` hammasi ishlasa "ok", aks holda 500 beradi — qaysi komponent
  yiqilganini ko'rsatmaydi. Har bir komponent holatini alohida qaytaradigan
  endpoint diagnostikani osonlashtirardi.

---

## 3. Stage 2 — RAG (eslatma)

Vector qidiruv `qdrant_store.py` da tayyor. `qdrant-client` `base.txt` ga
qo'shilgach ilova ishga tushadi. Keyingi qadamlar:
hujjatlarni indekslash → retriever → LLM → javob (havolalar bilan).
