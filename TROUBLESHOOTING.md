# Nosozliklarni bartaraf etish (Turon-AI)

Bu yerda **haqiqatan uchragan** xatolar va ularning yechimi yozilgan.
Yangi muammo hal qilinganda shu faylga qo'shib boring.

Barcha buyruqlar `backend/` papkasidan ishga tushiriladi. Qisqartma:

```bash
docker compose --env-file .env -f infra/docker-compose.yml
```

Quyida uni `DC`, dev rejim variantini (`+ -f infra/docker-compose.override.yml`)
`DC_DEV` deb yozamiz.

---

## 1. `dependency failed to start: container template-app is unhealthy`

Bu **umumiy** xabar — asl sabab har doim log ichida. Birinchi qadam **doim** bir xil:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.override.yml logs --tail=80 app
```

Log oxiridagi `Traceback` ning **eng oxirgi qatori** — asl xato.

### 1.1 `ModuleNotFoundError: No module named 'qdrant_client'`

**Sabab:** paket `infra/requirements/base.in` da bor, lekin kompilyatsiya qilingan
`base.txt` ga tushmagan. Docker image `dev.txt` → `base.txt` dan o'rnatadi, `.in`
fayllarni umuman o'qimaydi.

**Yechim:** `base.txt` ga qo'lda qo'shish (`prod.txt` da xuddi shunday qilingan):

```
qdrant-client
    # via -r base.in
```

so'ng image'ni **qayta yig'ish** (`--build` shart, aks holda eski image ishlatiladi):

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.override.yml up --build -d
```

**Oldini olish:** `.in` faylni tahrirlagandan keyin `make req-compile` ishga tushiring —
u `.in` dan `.txt` ni qayta hosil qiladi. Qo'lda `.in` ga yozib, `.txt` ni unutish —
eng ko'p uchraydigan xato.

### 1.2 Boshqa `ModuleNotFoundError`

Xuddi shu tartib: paket `base.in` da bormi tekshiring → `base.txt` ga qo'shing →
`--build` bilan qayta yig'ing.

---

## 2. Admin parolini eslay olmayapman

**Jadvalni o'chirish SHART EMAS.** Tayyor skript bor:

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec app python -m scripts.reset_admin_password "YangiParol123!"
```

Skript `.env` dagi `SUPER_ADMIN_USERNAME` bo'yicha adminni topadi; topilmasa —
birinchi `ADMIN` rolli foydalanuvchini oladi. Parolni yangilaydi va hisobni
faollashtiradi.

Argumentsiz chaqirilsa `.env` dagi `SUPER_ADMIN_PASSWORD` ishlatiladi:

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec app python -m scripts.reset_admin_password
```

### Agar admin umuman yo'q bo'lsa

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec app python -m scripts.create_superadmin
```

### Foydalanuvchilarni ko'rish

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec postgres psql -U admin -d turonai_db -c "SELECT username, role, is_active FROM users;"
```

### Hamma foydalanuvchini o'chirish (oxirgi chora)

`DROP TABLE` **qilmang** — alembic holati buziladi. Faqat qatorlarni tozalang:

```bash
docker compose --env-file .env -f infra/docker-compose.yml exec postgres psql -U admin -d turonai_db -c "TRUNCATE TABLE users CASCADE;"
```

`CASCADE` — users'ga bog'langan chat sessiyalari, hisobotlar va bildirishnomalarni
ham o'chiradi.

---

## 3. `Can't locate revision identified by '<hash>'`

**Sabab:** migratsiya **prod rejimda** (`make up`) yaratilgan. Prod rejimda kod
image ichiga **nusxalanadi**, bind-mount qilinmaydi — shuning uchun konteyner ichida
yaratilgan fayl host'ga tushmaydi va konteyner o'chgach yo'qoladi. Baza esa endi
mavjud bo'lmagan revisiyaga ishora qiladi.

**Yechim:** migratsiyani **doim dev rejimda** yarating:

```bash
docker compose --env-file .env -f infra/docker-compose.yml -f infra/docker-compose.override.yml exec app alembic revision --autogenerate -m "xabar"
```

Buzilgan holatni tiklash (ma'lumot yo'qoladi):

```bash
docker compose --env-file .env -f infra/docker-compose.yml down -v
```

> `make migration` Windows'da ishlamaydi — u `read -p` ishlatadi.

---

## 4. Postgres ulanmayapti

- Ilova ichida host **`postgres`** (compose servis nomi), `localhost` **emas**.
  `localhost:5432` faqat Windows'dagi vositalar (pgAdmin) uchun.
- `POSTGRES_*` qiymatlari faqat **birinchi** ishga tushishda (bo'sh volume) qo'llanadi.
  O'zgartirgandan keyin `DC down -v` kerak.
- `POSTGRES_PASSWORD` da `@ : / #` ishlatmang — DSN satr birlashtirish bilan
  quriladi va bu belgilar URL'ni buzadi.
- Windows'da mahalliy Postgres ham 5432 portni egallagan bo'lsa, avval to'xtating:
  `Stop-Service postgresql-x64-18`.

---

## 5. Frontend backendni ko'rmayapti

- `frontend/.env` da `VITE_API_URL=http://localhost:8000` (nginx porti, 8001 emas).
- `.env` o'zgarsa Vite'ni **qayta ishga tushiring** — u faqat startda o'qiydi.
- Brauzer konsolida CORS xatosi bo'lsa: backend `.env` dagi `CORS_ALLOWED_ORIGINS`
  ichida `http://localhost:5173` borligini tekshiring.

---

## 6. Foydali buyruqlar

```bash
docker compose --env-file .env -f infra/docker-compose.yml ps
```

```bash
docker compose --env-file .env -f infra/docker-compose.yml logs -f app
```

Servislar sog'ligini bitta so'rovda tekshirish:

```bash
curl http://localhost:8000/health/
```

- Swagger: http://localhost:8000/docs
- RabbitMQ: http://localhost:15672
