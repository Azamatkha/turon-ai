# Ichki raqamlar (IP qidiruv) — mobil ilova uchun qo'llanma

Vebdagi "Yordamchi dasturlar → Ichki raqamlar" bilan **bir xil** funksiya.
Backend tayyor, mobilda faqat ekranni yasash kerak.

**Maqsad:** xodim bo'limni tanlaydi, o'sha bo'lim xodimlari ro'yxati chiqadi.
Xodimni bosganda uning ismi, lavozimi, bo'limi va **IP (ichki) raqami** ko'rinadi.
Telefon raqami **ko'rsatilmaydi** (backend ham qaytarmaydi).

---

## 1. API

Ikkala endpoint ham oddiy `Authorization: Bearer <access_token>` bilan ishlaydi.
Access token ilovada allaqachon bor (login'dan keladi). Faqat **tasdiqlangan**
(Face-ID'dan o'tgan) user foydalana oladi, tasdiqlanmagan userga `403` qaytadi.

Base URL — ilova hozir ishlatayotgan manzil (`https://face-ids.turonbank.uz`).

### 1.1. Bo'limlar ro'yxati

```
GET /v1/users/directory/departments
```

Javob (`200`), alifbo tartibida:

```json
[
  "Axborot texnologiyalari departamenti (IT departamenti)",
  "Buxgalteriya",
  "Navoiy BXM"
]
```

Ekran ochilganda **bir marta** chaqiriladi.

### 1.2. Xodimlar

```
GET /v1/users/directory?department=<bo'lim>&q=<qidiruv>
```

| Parametr | Majburiy | Izoh |
|---|---|---|
| `department` | yo'q* | 1.1 dagi nom, **harfma-harf bir xil** (URL-encode qiling) |
| `q` | yo'q* | ism, familiya yoki IP raqam bo'yicha qidiruv, **kamida 2 belgi** |

\* Ikkalasidan **kamida bittasi** bo'lishi shart, aks holda `400` qaytadi.
Ikkalasi birga berilsa, tanlangan bo'lim ichida qidiradi.

Javob (`200`):

```json
[
  {
    "id": "5f1c...",
    "full_name": "Ali Valiyev",
    "position": "Bosh mutaxassis",
    "department": "Axborot texnologiyalari departamenti (IT departamenti)",
    "ip_number": "1036"
  }
]
```

- `position`, `department`, `ip_number` **`null` bo'lishi mumkin**. Masalan,
  xodim IP raqamini kiritmagan bo'lsa, `ip_number: null` keladi.
- Ro'yxat familiya bo'yicha tartiblangan, ko'pi bilan 200 qator.
- Kartochka uchun **alohida so'rov kerak emas**, hamma ma'lumot shu javobda.

### 1.3. Xatolar

Xato javobining tanasi doim bir xil:

```json
{ "error": "Instance processing error", "message": "Bo'limni tanlang yoki kamida 2 ta belgi kiriting" }
```

| Kod | Qachon | Mobil nima qiladi |
|---|---|---|
| `400` | bo'lim ham, 2+ belgili `q` ham yo'q | So'rov yubormang (2-bo'limdagi qoida), bu holat bo'lmasligi kerak |
| `401` | token eskirgan | Ilovadagi odatiy refresh oqimi, keyin so'rovni qaytarish |
| `403` | user tasdiqlanmagan | Verifikatsiya ekraniga yo'naltirish |
| `429` | daqiqada 120 so'rovdan oshdi | "Biroz kuting" xabari |
| `5xx` / tarmoq | server yoki tunnel xatosi | "Ma'lumotni yuklab bo'lmadi" + qayta urinish tugmasi |

---

## 2. Ekran oqimi

```
[Bo'lim ▼]                       ← dropdown (1.1)
[🔍 Ism, familiya yoki IP raqam] ← matn maydoni
─────────────────────────────
 A  Ali Valiyev            1036  ← ro'yxat (1.2), o'ngda IP
    Bosh mutaxassis
 B  Botir Karimov          1041
    Muhandis
```

1. Ekran ochilganda `departments` yuklanadi va dropdown'ga qo'yiladi. Birinchi
   element "Bo'limni tanlang" bo'lib, tanlanmagan holatni bildiradi.
2. **Qachon so'rov yuboriladi:** bo'lim tanlangan **yoki** qidiruvda 2+ belgi bor.
   Aks holda ro'yxat o'rnida "Bo'limni tanlang yoki xodim ismini kiriting" matni turadi.
3. Qidiruv maydonida har harfda so'rov yubormang, **300 ms debounce** qiling.
4. Bo'lim tanlanmagan holda ism bo'yicha qidirilsa, ro'yxat qatorida lavozim
   yonida **bo'lim ham** ko'rsatilsin (`Muhandis · IT departamenti`), chunki
   natija turli bo'limlardan keladi.
5. Qatorni bosganda kartochka ochiladi (bottom sheet yoki yangi ekran):
   ism, lavozim, bo'lim va katta harfda IP raqam. `ip_number == null` bo'lsa,
   "Kiritilmagan" deb yoziladi.
6. **Holatlar:** yuklanmoqda, bo'sh ("Xodim topilmadi"), xato (qayta urinish bilan).
7. Bo'lim nomlari juda uzun bo'lishi mumkin, shuning uchun dropdown `isExpanded: true`
   bo'lsin va matn ellipsis bilan kesilsin.

Matnlar 3 tilda (veb bilan bir xil):

| Kalit | uz | uz_cyrl | ru |
|---|---|---|---|
| sarlavha | Ichki raqamlar | Ички рақамлар | Внутренние номера |
| bo'lim | Bo‘lim | Бўлим | Подразделение |
| bo'lim tanlanmagan | Bo‘limni tanlang | Бўлимни танланг | Выберите подразделение |
| qidiruv | Ism, familiya yoki IP raqam | Исм, фамилия ёки IP рақам | Имя, фамилия или IP-номер |
| yo'riqnoma | Bo‘limni tanlang yoki xodim ismini kiriting | Бўлимни танланг ёки ходим исмини киритинг | Выберите подразделение или введите имя сотрудника |
| bo'sh | Xodim topilmadi | Ходим топилмади | Сотрудник не найден |
| xato | Ma’lumotni yuklab bo‘lmadi. Keyinroq urinib ko‘ring. | Маълумотни юклаб бўлмади. Кейинроқ уриниб кўринг. | Не удалось загрузить данные. Попробуйте позже. |
| lavozim | Lavozimi | Лавозими | Должность |
| IP | IP (ichki) raqam | IP (ички) рақам | IP (внутренний) номер |
| IP yo'q | Kiritilmagan | Киритилмаган | Не указан |

---

## 3. Flutter kodi (namuna)

Faqat `http` paketi ishlatilgan. Ilovada `dio` yoki boshqa HTTP klient bo'lsa,
`DirectoryApi` ichini o'shaga moslang. Token olish va 401'da refresh ilovadagi
mavjud mexanizm orqali qilinadi, bu yerda `getToken` sifatida beriladi.

### 3.1. Model

```dart
class DirectoryEntry {
  final String id;
  final String fullName;
  final String? position;
  final String? department;
  final String? ipNumber;

  const DirectoryEntry({
    required this.id,
    required this.fullName,
    this.position,
    this.department,
    this.ipNumber,
  });

  factory DirectoryEntry.fromJson(Map<String, dynamic> json) => DirectoryEntry(
        id: json['id'] as String,
        fullName: json['full_name'] as String,
        position: json['position'] as String?,
        department: json['department'] as String?,
        ipNumber: json['ip_number'] as String?,
      );
}
```

### 3.2. API servis

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class DirectoryApiException implements Exception {
  final int statusCode;
  final String? message;
  DirectoryApiException(this.statusCode, this.message);
}

class DirectoryApi {
  DirectoryApi({required this.baseUrl, required this.getToken, http.Client? client})
      : _client = client ?? http.Client();

  final String baseUrl; // masalan: https://face-ids.turonbank.uz
  final Future<String> Function() getToken;
  final http.Client _client;

  /// Backend bilan bir xil chegara (usecases/directory.py -> MIN_SEARCH_LEN)
  static const minSearchLen = 2;

  Future<List<String>> departments() async {
    final res = await _get(Uri.parse('$baseUrl/v1/users/directory/departments'));
    return (jsonDecode(utf8.decode(res.bodyBytes)) as List).cast<String>();
  }

  Future<List<DirectoryEntry>> search({String? department, String? q}) async {
    final params = <String, String>{
      if (department != null && department.isNotEmpty) 'department': department,
      if (q != null && q.trim().length >= minSearchLen) 'q': q.trim(),
    };
    final uri = Uri.parse('$baseUrl/v1/users/directory')
        .replace(queryParameters: params); // URL-encode shu yerda qilinadi
    final res = await _get(uri);
    final list = jsonDecode(utf8.decode(res.bodyBytes)) as List;
    return list
        .map((e) => DirectoryEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<http.Response> _get(Uri uri) async {
    final res = await _client.get(uri, headers: {
      'Authorization': 'Bearer ${await getToken()}',
      'Accept': 'application/json',
    });
    if (res.statusCode != 200) {
      String? msg;
      try {
        msg = (jsonDecode(utf8.decode(res.bodyBytes)) as Map)['message'] as String?;
      } catch (_) {}
      throw DirectoryApiException(res.statusCode, msg);
    }
    return res;
  }
}
```

> `utf8.decode(res.bodyBytes)` — `res.body` EMAS. Aks holda kirill va
> `o‘`/`g‘` harflari buzilib chiqishi mumkin.

### 3.3. Ekran

```dart
import 'dart:async';
import 'package:flutter/material.dart';

class DirectoryScreen extends StatefulWidget {
  const DirectoryScreen({super.key, required this.api});
  final DirectoryApi api;

  @override
  State<DirectoryScreen> createState() => _DirectoryScreenState();
}

class _DirectoryScreenState extends State<DirectoryScreen> {
  List<String> _departments = [];
  String? _department;
  String _query = '';
  List<DirectoryEntry> _items = [];
  bool _loading = false;
  bool _failed = false;
  Timer? _debounce;
  int _requestId = 0; // eski (kechikkan) javob yangisini bosib ketmasin

  bool get _canSearch =>
      (_department?.isNotEmpty ?? false) ||
      _query.trim().length >= DirectoryApi.minSearchLen;

  @override
  void initState() {
    super.initState();
    _loadDepartments();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _loadDepartments() async {
    try {
      final list = await widget.api.departments();
      if (mounted) setState(() => _departments = list);
    } catch (_) {
      if (mounted) setState(() => _failed = true);
    }
  }

  void _scheduleSearch() {
    _debounce?.cancel();
    if (!_canSearch) {
      setState(() => _items = []);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), _search);
  }

  Future<void> _search() async {
    final id = ++_requestId;
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final res = await widget.api.search(department: _department, q: _query);
      if (!mounted || id != _requestId) return;
      setState(() => _items = res);
    } catch (_) {
      if (!mounted || id != _requestId) return;
      setState(() => _failed = true);
    } finally {
      if (mounted && id == _requestId) setState(() => _loading = false);
    }
  }

  void _openCard(DirectoryEntry u) {
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (_) => Padding(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(radius: 28, child: Text(u.fullName.isEmpty ? '?' : u.fullName[0])),
            const SizedBox(height: 12),
            Text(u.fullName, style: Theme.of(context).textTheme.titleLarge, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            _fact('Lavozimi', u.position ?? '—'),
            _fact('Bo‘lim', u.department ?? '—'),
            const Divider(height: 32),
            Text('IP (ichki) raqam', style: Theme.of(context).textTheme.labelMedium),
            const SizedBox(height: 4),
            u.ipNumber != null
                ? SelectableText(u.ipNumber!,
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(fontWeight: FontWeight.w800))
                : const Text('Kiritilmagan'),
          ],
        ),
      ),
    );
  }

  Widget _fact(String label, String value) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Column(children: [
          Text(label, style: Theme.of(context).textTheme.labelMedium),
          Text(value, textAlign: TextAlign.center),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Ichki raqamlar')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          DropdownButtonFormField<String>(
            value: _department,
            isExpanded: true, // bo'lim nomlari uzun
            decoration: const InputDecoration(labelText: 'Bo‘lim'),
            items: [
              const DropdownMenuItem(value: null, child: Text('Bo‘limni tanlang')),
              ..._departments.map((d) => DropdownMenuItem(
                    value: d,
                    child: Text(d, overflow: TextOverflow.ellipsis),
                  )),
            ],
            onChanged: (v) {
              setState(() => _department = v);
              _scheduleSearch();
            },
          ),
          const SizedBox(height: 12),
          TextField(
            maxLength: 60,
            decoration: const InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Ism, familiya yoki IP raqam',
              counterText: '',
            ),
            onChanged: (v) {
              _query = v;
              _scheduleSearch();
            },
          ),
          const SizedBox(height: 8),
          Expanded(child: _buildList()),
        ]),
      ),
    );
  }

  Widget _buildList() {
    if (_failed) {
      return Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const Text('Ma’lumotni yuklab bo‘lmadi. Keyinroq urinib ko‘ring.'),
          TextButton(
            onPressed: _departments.isEmpty ? _loadDepartments : _search,
            child: const Text('Qayta urinish'),
          ),
        ]),
      );
    }
    if (!_canSearch) {
      return const Center(child: Text('Bo‘limni tanlang yoki xodim ismini kiriting'));
    }
    if (_loading && _items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_items.isEmpty) {
      return const Center(child: Text('Xodim topilmadi'));
    }
    return ListView.separated(
      itemCount: _items.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (_, i) {
        final u = _items[i];
        // Bo'lim tanlanmagan (ism bo'yicha qidiruv) — bo'lim ham ko'rinsin
        final sub = [u.position, if (_department == null) u.department]
            .whereType<String>()
            .where((s) => s.isNotEmpty)
            .join(' · ');
        return ListTile(
          leading: CircleAvatar(child: Text(u.fullName.isEmpty ? '?' : u.fullName[0])),
          title: Text(u.fullName, overflow: TextOverflow.ellipsis),
          subtitle: Text(sub.isEmpty ? '—' : sub, overflow: TextOverflow.ellipsis),
          trailing: u.ipNumber == null
              ? null
              : Text(u.ipNumber!,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          onTap: () => _openCard(u),
        );
      },
    );
  }
}
```

Matnlar namunada o'zbekcha yozilgan. Ilovadagi lokalizatsiya tizimiga
(2-bo'limdagi jadval) almashtiring.

---

## 4. Tekshirish ro'yxati

- [ ] Bo'lim tanlanganda shu bo'lim xodimlari chiqadi
- [ ] Bo'lim tanlanmay, 2+ harf yozilganda butun bank bo'yicha qidiradi (qatorda bo'lim ham ko'rinadi)
- [ ] 1 ta harf yozilganda so'rov **ketmaydi**
- [ ] Tez yozilganda har harfga so'rov ketmaydi (debounce)
- [ ] IP raqam bo'yicha qidiruv ishlaydi (`q=1036`)
- [ ] `ip_number: null` bo'lgan xodimda "Kiritilmagan" chiqadi
- [ ] Kirill/lotin nomlar (`o‘`, `ғ`, `Ҳ`) buzilmay ko'rinadi
- [ ] Uzun bo'lim nomi dropdown'ni ekrandan chiqarib yubormaydi
- [ ] Token eskirganda (401) refresh bo'lib, so'rov qaytariladi
- [ ] Internet uzilganda xato + "Qayta urinish" chiqadi

Backend kodi: `backend/src/user/usecases/directory.py`, `backend/src/user/routers.py`.
To'liq API hujjati: admin paneldagi API Docs → **Users** bo'limi.
