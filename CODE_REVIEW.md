# Turon-AI — Code Review

**Sana:** 2026-08-11
**Ko'rib chiqilgan:** `backend/src/` (~15 800 qator), `frontend/src/` (~18 800 qator)
**Usul:** qo'lda o'qish — xavfsizlik, to'g'rilik, accessibility, responsivlik, unumdorlik, o'lik kod

---

## Qisqacha xulosa

Loyiha **yaxshi qurilgan**. Backend'da use-case pattern izchil qo'llangan, har bir endpoint
huquq tekshiruvidan o'tadi, chat sessiyalari `user_id` bo'yicha filtrlangan (boshqaning
suhbatini o'qib bo'lmaydi), LLM promptlari juda puxta yozilgan. Kodda izohlar ko'p va ular
"nima" emas, "nega" ni tushuntiradi — bu kamdan-kam uchraydi.

Asosiy muammolar **frontend tomonda** va ular ikkita katta guruhga bo'linadi:

| Guruh | Holat |
|---|---|
| **Responsivlik** | 36 ta CSS modulidan **35 tasida** bironta ham `@media` yo'q |
| **Accessibility** | 55 ta komponentdan **24 tasida** bironta ham `aria-*` yo'q; admin panelda umuman yo'q |
| **Unumdorlik** | Chat orqasida doimiy ishlaydigan to'liq ekranli WebGL shader + canvas |
| **O'lik kod** | ~1 100 qator hech qayerda import qilinmagan komponentlar |

Backend'da bitta jiddiy bo'shliq bor: **eng qimmat endpoint (LLM) rate limit'siz.**

---

## 1. Kritik — darhol tuzatish kerak

### 1.1 `/v1/chat/ask` va `/ask/stream` rate limit'siz

`src/chat/routers.py:199,214`

Auth endpointlari himoyalangan (`RateLimiter(times=5, seconds=60)`), lekin **eng qimmat
endpointlar — LLM chaqiradiganlari — umuman cheklanmagan.**

```python
@router.post("/ask/stream")
async def ask_stream(
    data: QuestionRequest,
    current_user: Annotated[User, Depends(get_current_user)],   # <- faqat auth
    ...
```

**Nima bo'ladi:** bitta xodim (yoki o'g'irlangan token) skript bilan sekundiga o'nlab
savol yuborsa, Ollama serveri navbatga to'lib qoladi va **butun bank uchun chat ishlamay
qoladi**. Login'ni himoya qilib, inference'ni ochiq qoldirish — teskari ustuvorlik:
login arzon, inference qimmat.

**Yechim:** `RateLimiter(times=20, minutes=1, identifier=get_user_id_from_token)`.
IP bo'yicha emas, **user_id bo'yicha** — chunki bank ichida hamma bitta NAT ortida
o'tiradi va IP limiti butun ofisni birdan bloklab qo'yardi.

---

### 1.2 Responsivlik amalda yo'q

36 ta `.module.css` faylidan `@media` faqat 2 tasida: `LoginPage.module.css` va
`NotificationsBell.module.css`.

Eng og'riqli joylar:

**Chat sidebar qat'iy 282px** — `Sidebar.tsx:118`:
```tsx
style={{ flex: `0 0 ${open ? SW : COLL}px`, width: (open ? SW : COLL) + "px" }}
```
375px kenglikdagi telefonda sidebar ekranning **75%** ini egallaydi. Mobil uchun u
overlay (drawer) bo'lishi va default holda **yopiq** turishi kerak.

**`height: 100vh`** — `ChatPage.module.css:8`. Mobil brauzerda `100vh` manzil satrini
ham hisobga oladi, natijada **xabar yozish maydoni ekran ostiga tushib ketadi.**
`100dvh` kerak (LoginPage'da to'g'ri ishlatilgan — demak muammo ma'lum, faqat
chatga qo'llanmagan).

**Admin jadvallari** — `UsersTable.module.css` da `overflow-x` yo'q; tor ekranda
butun sahifa yon tomonga suriladi.

---

### 1.3 Formalar `<form>` emas

`LoginForm.tsx`, `ProfileModal.tsx`, admin modallari — hammasi `<div>` + `onClick`
tugma:

```tsx
<div className={styles.formBox}>
  <input ... onKeyDown={onKey} />          {/* Enter qo'lda ushlangan */}
  <button onClick={submit}>{t.signIn}</button>   {/* type="submit" emas */}
</div>
```

**Oqibatlari:**
- Parol menejerlari (bank kompyuterlarida korporativ menejer bo'lishi mumkin) formani
  tanimaydi — avtomatik to'ldirish ishlamaydi;
- Ekran o'quvchisi "forma" deb e'lon qilmaydi;
- Enter faqat qo'lda yozilgan `onKey` tufayli ishlaydi — har bir maydonga alohida ulash kerak.

---

### 1.4 `<label>` maydonga bog'lanmagan

`LoginForm.tsx:72,93` va boshqa ko'p joyda:
```tsx
<label className={styles.fieldLabel}>{t.login}</label>
<input className={styles.input} value={login} ... />   {/* id yo'q */}
```

`htmlFor` / `id` juftligi yo'q. Ekran o'quvchisi maydonni **"nomsiz matn maydoni"** deb
o'qiydi. Yorliqni bosganda maydon fokuslanmaydi (kutilgan xatti-harakat).

---

### 1.5 `tabIndex={-1}` haqiqiy tugmalarda

`LoginForm.tsx:107` (parolni ko'rsatish) va `:128` ("Yordam"):
```tsx
<button onClick={() => setPwVisible(v => !v)} tabIndex={-1} ...>
```

`tabIndex={-1}` elementni **klaviatura navigatsiyasidan butunlay chiqarib tashlaydi.**
Faqat klaviatura bilan ishlaydigan foydalanuvchi parolini ko'ra olmaydi. Bu WCAG 2.1
**2.1.1 (Keyboard)** ning to'g'ridan-to'g'ri buzilishi.

---

### 1.6 Xato xabari e'lon qilinmaydi

`LoginForm.tsx:60`:
```tsx
{error && <div className={styles.errorBox}> ... </div>}
```

`role="alert"` yoki `aria-live` yo'q. Ko'zi ojiz foydalanuvchi "Kirish" ni bosadi,
hech narsa eshitmaydi va **nega kira olmayotganini bilmaydi.**

Xuddi shu muammo chat javoblarida: bot javobi kelganda `aria-live` bo'lmagani uchun
ekran o'quvchisi yangi xabar kelganini aytmaydi.

---

## 2. Muhim

### 2.1 Profil saqlanmaydi, lekin "saqlandi" deydi

`ChatPage.tsx:110`:
```tsx
// Ism/login hozircha faqat ekranda yangilanadi (backendda /me yangilash endpointi hali yo'q)
setFullName(pFullName.trim());
setUsername(u);
setSaved(true);          // <- foydalanuvchiga "saqlandi" ko'rinadi
```

Izoh halol, lekin **UX yolg'on gapiradi**: foydalanuvchi ismini o'zgartiradi, "saqlandi"
belgisini ko'radi, sahifani yangilaydi — eski ism qaytadi. Backend endpointi tayyor
bo'lgunicha bu maydonlar `disabled` bo'lishi va sababi yozilishi kerak.

### 2.2 Mock ma'lumot ishlab turgan kodda

`ChatPage.tsx:7` — `import { TAKEN_USERNAMES } from "../services/seedData"`.
Login band-emasligi **qattiq yozilgan mock ro'yxat** bo'yicha tekshirilyapti. Haqiqiy
tekshiruv backend'da bo'lishi kerak.

### 2.3 Skroll foydalanuvchini pastga tortadi

`ChatPage.tsx:80`:
```tsx
useEffect(() => {
  const el = scrollRef.current;
  if (el) el.scrollTop = el.scrollHeight;
}, [chats, thinking]);
```

`chats` **har qanday** o'zgarishida pastga sakraydi. Foydalanuvchi eski xabarni o'qiyotgan
bo'lsa ham tortib tushiradi. Faqat foydalanuvchi allaqachon pastda turganda skroll
qilish kerak.

### 2.4 Fayl to'liq xotiraga o'qiladi

`knowledge/routers.py:176,201`:
```python
content = await file.read()      # butun PDF/Excel RAM'ga
```

Ilova darajasida hajm tekshiruvi yo'q. nginx `client_max_body_size` himoya qiladi, lekin
u **infratuzilma sozlamasi** — nginx'siz ishga tushirilsa (dev, test, boshqa deploy)
himoya yo'qoladi. `config.app.REPORT_MAX_BYTES` kabi cheklov shu yerda ham kerak.

### 2.5 `knowledge/usecases.py` — 2 625 qator

Bitta faylda 9 ta use-case. `CLAUDE.md` da e'lon qilingan pattern —
`usecases/<action>.py` — boshqa hamma domenda saqlangan, faqat shu yerda buzilgan.
Fayl juda katta bo'lgani uchun uni o'qish ham, unga test yozish ham qiyin.

### 2.6 Oqim xatosi klientga xom uzatiladi

`chat/routers.py:234`:
```python
except Exception as exc:
    payload = {"type": "error", "message": str(exc)}
```

`str(exc)` ichida ichki manzil, DSN bo'lagi yoki stack ma'lumoti bo'lishi mumkin.
Klientga umumiy matn, log'ga to'liq xato kerak.

---

## 3. Unumdorlik

### 3.1 Chat orqasida doimiy WebGL shader

`ChatPage.tsx:157` — `GradientWaves` bu **raymarching shader**: har bir piksel uchun,
har bir kadrda 40 qadam (`detail="low"`). Ustiga yana `DotField` — sichqoncha
harakatiga javob beradigan ikkinchi canvas.

Kodning o'zida ham tan olingan (`ChatPage.tsx:177`):
> `"low" — 40 qadamli raymarch. Bu to'liq ekranli, har kadrda hisoblanadigan shader;
> ofis kompyuterlarida "medium" og'irlik qiladi.`

Bank ofis kompyuterida (integratsiyalangan grafika) bu **noutbuk batareyasini yeydi va
kulerni aylantiradi** — foydasi esa faqat bezak, ustiga maska bilan yarmi o'chirilgan.
Minimalistik dizayn uchun bu birinchi olib tashlanadigan narsa.

### 3.2 Universal `transition`

`index.css:94`:
```css
body, body * {
  transition: background-color .28s ease, color .22s ease, border-color .28s ease;
}
```

DOM'dagi **har bir element** uchun transition. Uzun chat tarixi yoki 200 qatorli
foydalanuvchilar jadvali bo'lsa, brauzer har bir qator uchun animatsiya hisoblaydi.
Mavzu almashish silliq bo'lishi uchun buni faqat kerakli elementlarga (yoki `html`
darajasidagi qisqa muddatli klassga) qo'yish yetarli.

### 3.3 O'lik kod — ~1 100 qator

Hech qayerdan import qilinmagan:

| Fayl | Qator |
|---|---|
| `components/LightRays.tsx` + `.css` | 454 |
| `components/Grainient.tsx` + `.css` | 316 |
| `components/Iridescence.tsx` + `.css` | 171 |
| `components/GlowOrbs.tsx` + `.css` | ~160 |

`package.json` da **`gsap`** bor — kodda **umuman ishlatilmagan**. `ogl` esa faqat
yuqoridagi o'lik komponentlar va `GradientWaves` uchun.

### 3.4 Ikki marta yozilgan scrollbar

`index.css:162` (`*::-webkit-scrollbar`, 10px) va `index.css:301`
(`::-webkit-scrollbar`, 9px) — bir-biriga zid ikki qoida. Ikkinchisi birinchisini
qisman bosadi, natija brauzerga qarab o'zgaradi.

### 3.5 `index.css:178` — formatlash buzilgan

```css
  background-clip: content-box;
}html,
body,
```
`}` va `html` yopishib qolgan.

---

## 4. Dizayn va matn

### 4.1 `-webkit-autofill` dark rejimda buziladi

`index.css:198`:
```css
input:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 40px #fff inset;   /* har doim oq */
  -webkit-text-fill-color: #003978;            /* har doim to'q ko'k */
}
```
Dark rejimda brauzer to'ldirgan maydon **oq plita** bo'lib qoladi.

### 4.2 Fokus ko'rinmaydi

Butun loyihada `:focus-visible` stili yo'q. Ba'zi joyda `outline: none` bor.
Klaviatura bilan yurgan foydalanuvchi **qayerda turganini ko'rmaydi.**

### 4.3 Tooltip'lar faqat sichqoncha uchun

`[data-tip]` CSS tooltip'i faqat `:hover` da chiqadi — klaviatura fokusida chiqmaydi va
ekran o'quvchisiga ko'rinmaydi. `aria-label` ba'zi joyda qo'shilgan, lekin izchil emas.

### 4.4 Ranglar ikki joyda takrorlangan

`constants/colors.ts` ning o'zida yozilgan:
> `CSS Modules JS konstantalarini import qila olmaydi, shuning uchun bu qiymatlar
> .module.css fayllarida ham takrorlangan`

Bu **CSS o'zgaruvchilari** bilan hal qilinadi: `:root` da bir marta e'lon qilinadi,
CSS ham, JS ham (`getComputedStyle` yoki oddiygina `var(--...)`) o'sha bitta manbadan
oladi. Hozir brend rangini o'zgartirish uchun 30+ faylni qo'lda tahrirlash kerak.

---

## 5. Promptlar

Promptlar — loyihaning **eng kuchli qismi**. `STRICT_RAG_SYSTEM` da real
foydalanishdan chiqqan aniq muammolar hal qilingan: apostrof variantlari (`o'`/`oʻ`/`o‘`),
x/h almashishi, Humo/Uzcard xalqaro emasligi, "Toshkent shahri" ≠ "Toshkent viloyati",
har mahsulotning o'z havolasi. Bu darajadagi domen bilimini prompt'ga tushirish kam
uchraydi.

Yaxshilash mumkin bo'lgan joylar:

**5.1 Qoidalar tartibi.** `STRICT_RAG_SYSTEM` ~200 qator. Eng muhim qoidalar
(grounding, til) boshida, lekin "COMPLETENESS" — javob sifatiga eng ko'p ta'sir
qiladigan qoida — **170-qatorda**. Modellar prompt boshi va oxiriga kuchliroq e'tibor
beradi; kritik qoidalar oxirida ham takrorlanishi kerak.

**5.2 Router promptida olmosh yechilmaydi.** `ROUTER_SYSTEM` `search_query` so'raydi,
lekin "ularni", "shuni" kabi olmoshlarni oldingi javobga bog'lash haqida bironta ham
qoida yo'q — bu faqat alohida `QUERY_REWRITE_SYSTEM` da bor. Router tarixni ko'radi
(`HISTORY_TURNS = 4`), demak u ham to'ldira olardi.

**5.3 Sarlavha uzunligi kirillda.** `GenerateTitleUseCase.MAX_LEN = 60` — lotin
sarlavhasiga qo'llanadi, keyin `to_cyrillic()` ishlaydi. Kirill transliteratsiyasi
uzunroq chiqadi (`sh` → `ш` qisqartiradi, lekin `x` → `х`, `o'` → `ў`), natijada
kesish chegarasi kirillda boshqacha ishlaydi.

**5.4 Fallback promptga tushmaydi.** `QuestionRouter.classify()` xato bo'lsa
`Intent.PRODUCT` ga tushadi — bu to'g'ri va izohlangan qaror. Lekin bu holat
`logger.exception` dan boshqa hech qayerda ko'rinmaydi; router necha marta yiqilayotganini
o'lchaydigan metrika yo'q.

---

## 6. Kichik kamchiliklar

| # | Joy | Muammo |
|---|---|---|
| 6.1 | `user/auth/usecases/login.py:38` | Docstring "User must be verified" deydi — kodda bunday tekshiruv **yo'q** (dizayn bo'yicha ataylab, docstring eskirgan) |
| 6.2 | `main/config.py:290` | `config = get_settings()` import vaqtida — env to'liq bo'lmasa modul import'da yiqiladi, xato xabari tushunarsiz |
| 6.3 | `main/config.py:136` | `OLLAMA_MODEL = "qwen3.5:latest"` — `:latest` suzuvchi teg, model jimgina almashishi mumkin |
| 6.4 | `knowledge/routers.py:261` | `scrape_url` ixtiyoriy URL qabul qiladi — SSRF yuzasi (faqat admin, past xavf) |
| 6.5 | `package.json` | `eslint.config.js` bor, lekin `eslint` devDependencies'da yo'q va `lint` skripti yo'q |
| 6.6 | `frontend/src/services/*` | Tokenlar `localStorage` da — XSS orqali o'g'irlanishi mumkin. Ichki tarmoq uchun qabul qilinadigan xavf, lekin CSP qo'shilishi kerak |
| 6.7 | `knowledge/router.py:186` | `if not isinstance(data, dict) or "raw" in data` — `"raw"` sehrli satr, `parsing.py` bilan bog'lanish nozik |

---

## 7. Nima yaxshi

Adolat yuzasidan — bular saqlanishi kerak:

- **Huquq tekshiruvi izchil.** Har bir admin endpointida `require_permission(...)`;
  chat endpointlarida `get_single(..., user_id=user_id)` — foydalanuvchi boshqaning
  suhbatini **hech qanday yo'l bilan** ko'ra olmaydi.
- **Timing attack himoyasi.** `login.py:79` — foydalanuvchi topilmasa ham dummy hash
  bilan `verify_password` chaqiriladi. Buni ko'p loyiha unutadi.
- **Refresh token rotatsiyasi** Redis'da atomik Lua skripti bilan — qayta ishlatilgan
  token aniqlanadi.
- **`prefers-reduced-motion`** `index.css:316` da global qo'llangan — animatsiyalar
  bir joyda o'chiriladi.
- **Izohlar "nega" ni tushuntiradi.** `ChatPage.tsx:153`, `knowledge/router.py:1-12`,
  `prompts.py:369` — har bir nostandart qaror sababi bilan yozilgan. Bu kodni 6 oydan
  keyin o'qiydigan odam uchun bebaho.
- **LLM'ga ishonilmaydigan joyda ishonilmagan.** `EMPLOYEE_NOT_FOUND_REPLY`
  izohida: model "topilmadi" deyish o'rniga soxta xodim va telefon raqamlarini o'ylab
  topgani uchun javob koddan qaytariladi. Bu — to'g'ri xulosa.

---

## 8. BAJARILGAN TUZATISHLAR

Quyidagilar shu review doirasida **tuzatildi**. `npx tsc --noEmit` va
`vite build` toza o'tadi; o'zgarishlar brauzerda tekshirildi.
**Git'ga hech narsa qo'shilmadi** — barcha o'zgarishlar working tree'da.

### Backend

| # | Nima qilindi | Fayl |
|---|---|---|
| 1.1 | **`/chat/ask` va `/ask/stream` ga rate limit** — 20/daqiqa, **user_id bo'yicha** (IP emas: bank NAT ortida, IP limiti butun ofisni bloklardi). `/chat/title` — 30/daqiqa | `chat/routers.py` |
| 2.4 | **Fayl yuklashda hajm cheklovi** — `read_upload_limited()` 64 KB bo'laklab o'qiydi va cheklovdan oshgan zahoti to'xtaydi. Ilgari `await file.read()` butun faylni xotiraga solardi | `core/storage/media.py`, `knowledge/routers.py`, `config.py` |
| 2.6 | **Xom xato klientga chiqmaydi** — `str(exc)` o'rniga tushunarli o'zbekcha matn; xatoning o'zi `logger.exception` ga | `chat/routers.py` |
| 6.1 | Login docstring'i tuzatildi — `is_verified` tekshiruvi **ataylab** yo'qligi izohlandi | `auth/usecases/login.py` |

### Promptlar

| # | Nima qilindi | Fayl |
|---|---|---|
| 5.1 | **`STRICT_RAG_SYSTEM` oxiriga "5 ta eng muhim qoida" bloki** — model prompt boshi va oxiriga kuchliroq e'tibor beradi ("lost in the middle"); grounding, to'liqlik, til, mavzuda qolish endi oxirida ham turadi | `knowledge/prompts.py` |
| 5.2 | **Router promptiga olmosh yechish qoidasi** — "ularni", "foizlari qanday" endi router'ning o'zida oldingi javobga bog'lanadi; imlo variantlari (o'/oʻ/o, x↔h) ham qo'shildi | `knowledge/router.py` |
| — | `EMPLOYEE_SYSTEM` ga ism imlosini moslash + "hech narsa to'qib chiqarma" yakuniy bloki | `knowledge/prompts.py` |
| 5.3 | Sarlavha prompti: 45 belgi cheklovi, **xodim ismi/ichki raqami sarlavhaga chiqmaydi** (yon panelda boshqalarga ko'rinib qolardi) | `chat/prompts.py` |
| — | **Prompt byudjeti hisobi yozildi** — system prompt ~4 000 token, `num_ctx` 8 192; zaxira ~470 token. Sig'masa Ollama promptning boshini (ya'ni system prompt'ni) **jimgina** kesadi | `knowledge/usecases.py` |

### Frontend — dizayn tizimi

| Nima qilindi | Natija |
|---|---|
| **Shrift: Manrope → Onest** | Kirill + lotin to'liq; uzun o'zbekcha so'zlar siqilmaydi. Fallback: Segoe UI Variable → Segoe UI → system-ui |
| **To'liq dizayn tokenlari** (`index.css`) | Rang shkalalari (blue 50–950), tipografika, bo'shliq, radius, soya, motion — bitta manbada. `--adm-*` eski o'zgaruvchilar yangi tokenlarga **bog'landi**, ya'ni admin panel buzilmadi |
| **Ranglar kuchaytirildi** | To'yinganlik oshirildi; dark rejim aksenti `#5FA3D6` → `#63B3F0` (qora-ko'k fonda 7:1 — WCAG AAA); sidebar ikkilamchi matn `.55` → `.72` opacity (3:1 dan past edi) |
| **Minimalistik uslub** | Tugma va maydonlardagi gradientlar → tekis rang; soyalar yumshatildi; login foni bitta yumshoq radialga tushirildi |

### Frontend — accessibility

| # | Nima qilindi |
|---|---|
| 1.3 | Login **haqiqiy `<form>`** ga o'tkazildi — `onSubmit`, `type="submit"`. Parol menejerlari endi formani tanidi |
| 1.4 | **`label htmlFor` + `input id`** — login, parol, chat maydoni, profil maydonlari. Ekran o'quvchisi endi maydon nomini o'qiydi |
| 1.5 | **`tabIndex={-1}` olib tashlandi** — brauzerda tekshirildi: ilgari 2 ta tugmaga klaviatura bilan yetib bo'lmasdi, endi **7 tadan 7 tasi** yetib boradi |
| 1.6 | **`role="alert"` + `aria-live`** login xatosida; **`role="log"` + `aria-live="polite"`** xabarlar oqimida — bot javobi endi e'lon qilinadi |
| 4.2 | **`:focus-visible` global qo'shildi** — sichqoncha bilan bosganda chiqmaydi, Tab bilan kelganda chiqadi |
| — | **Skip-link** ("Asosiy qismga o'tish") — sidebar'dagi o'nlab suhbatni bosib o'tmasdan chatga o'tish |
| — | `aria-hidden` dekorativ SVG'larda; `aria-pressed`, `aria-expanded`, `aria-busy`, `aria-invalid`, `aria-describedby` |
| — | Modal `role="dialog"` overlay'dan **ichki panelga** ko'chirildi + `aria-labelledby` |
| — | Tooltip endi **klaviatura fokusida ham** chiqadi (`:focus-visible`) |
| — | `eslint-plugin-jsx-a11y` qo'shildi — a11y xatolari endi kod yozilayotganda ushlanadi |

### Frontend — responsivlik

Ilgari **36 ta CSS modulidan 35 tasida** `@media` yo'q edi. Endi:

- **Chat**: `100vh` → `100dvh`; sidebar tor ekranda **drawer** (fixed + scrim, Esc bilan yopiladi, sukut bo'yicha yopiq); composer/xabarlar/header breakpointlari; `env(safe-area-inset-bottom)` (iPhone)
- **Login**: karta telefonda to'liq ekran (radius 0); brend paneli planshetda gorizontal "kepka"ga, telefonda faqat logotipga tushadi; past ekran (yotiq telefon) uchun alohida qoida
- **Admin**: sidebar drawer; **jadval gorizontal skroll** (`min-width` bilan — ilgari ustunlar bir-biriga yopishardi); `.chartRow` bir ustunga
- **iOS zoom tuzatildi** — maydonlar mobil kenglikda 16px (kichikroq bo'lsa Safari sahifani zumlab yuboradi)
- `clamp()` bilan silliq tipografika (sarlavhalar breakpoint'da "sakramaydi")

### Frontend — unumdorlik

| Nima | Natija |
|---|---|
| **`flag-icons` to'liq importi → faqat 13 ta bayroq** (`styles/flags.css`) | CSS **525 KB → 123 KB** (gzip 106 → 23 KB) · assetlar **4.8 MB → 652 KB** · SVG **142 → 4 ta** |
| **WebGL shader va canvas fonlari olib tashlandi** (chat + admin) | To'liq ekranli raymarching shader (40 qadam/piksel/kadr) va sichqonchaga javob beradigan canvas o'rnida statik CSS gradient. GPU yuki nol |
| **Universal `transition` toraytirildi** | `body, body *` (har bir DOM elementi) → faqat qatlam elementlari |
| Scrollbar qoidasi ikki nusxadan bittaga; `index.css:178` formatlash buzilishi | — |

### Frontend — to'g'rilik

| # | Nima qilindi |
|---|---|
| 2.1 | **Profil endi yolg'on aytmaydi** — ism/login `readOnly` + sabab yozildi ("Ism va loginni administrator o'zgartiradi"). Ilgari "Saqlandi" chiqardi, lekin sahifa yangilanishi bilan eski qiymat qaytardi |
| 2.2 | **Mock ma'lumot olib tashlandi** — login band-emasligi `seedData.TAKEN_USERNAMES` (qo'lda yozilgan ro'yxat) bo'yicha tekshirilardi |
| 2.3 | **Skroll tuzatildi** — endi faqat foydalanuvchi pastga yaqin turganda pastga suriladi; eski xabarni o'qiyotganda tortib tushirmaydi |
| 4.1 | `-webkit-autofill` mavzu tokenlariga bog'landi — dark rejimda oq plita bo'lmaydi |
| — | Lotin matnga aralashib ketgan kirill harflari tuzatildi (`tilга`, `tanilади`, `qolган`) |
| 6.5 | `lint` / `lint:fix` / `typecheck` skriptlari + eslint devDependencies |
| 3.3 | **`gsap` `package.json` dan olib tashlandi** (kodda umuman ishlatilmagan) |

> **`npm install` kerak** — eslint va jsx-a11y paketlari qo'shildi:
> ```bash
> npm --prefix frontend install
> ```

---

## 9. Qolgan ishlar (tavsiya)

Bular **ataylab qilinmadi** — ular arxitektura qarori yoki backend endpointi talab qiladi:

1. **O'lik komponentlarni o'chirish** — `LightRays.tsx`, `GradientWaves.tsx`,
   `Grainient.tsx`, `Iridescence.tsx`, `GlowOrbs.tsx` (~1 400 qator) endi
   **hech qayerdan import qilinmaydi**. Vite ularni bundle'ga qo'shmaydi, ya'ni
   runtime zarari yo'q — faqat repo tartibsizligi. Ular bilan birga **`ogl`**
   paketi ham keraksiz qoladi. O'chirish sizning qaroringiz, shuning uchun
   fayllarga tegilmadi.
2. **Profil endpointi** — `PATCH /v1/users/me` (ism/login). Qo'shilgach
   `ProfileModal` dagi `readOnly` ni olib tashlang va `ChatPage.saveProfile`
   ichiga so'rovni qo'shing (izohlar joyida qoldirilgan).
3. **`knowledge/usecases.py` ni bo'lish** (2 625 qator) — `usecases/<action>.py`
   pattern'iga, boshqa domenlardagi kabi.
4. **CSP header** — tokenlar `localStorage` da; ichki tarmoq uchun qabul
   qilinadigan xavf, lekin CSP XSS yuzasini toraytiradi.
5. **`OLLAMA_MODEL` ni pin qilish** — `qwen3.5:latest` suzuvchi teg.
6. **Prompt byudjeti zaxirasi kam** (~470 token). Yangi qoida qo'shishdan
   oldin `knowledge/usecases.py` dagi hisobni qayta chiqaring yoki
   `OLLAMA_NUM_CTX` ni 12288 ga oshiring (Ollama serverida ko'proq RAM).
