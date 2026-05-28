# 🚀 FastAPI Backend API Migration Overview & Strategy

Dokumen ini mendefinisikan arsitektur induk, keputusan teknologi, dan strategi migrasi dari ASP.NET MVC web dashboard ke REST API berbasis **FastAPI (Python)** untuk dikonsumsi oleh aplikasi **Android Studio**.

---

## 1. Arsitektur Integrasi Sistem

Aplikasi Android tidak boleh terhubung langsung ke SQL Server karena alasan keamanan dan keterbatasan library mobile. FastAPI bertindak sebagai gerbang (API Gateway) yang aman dan berkinerja tinggi.

```
┌─────────────────┐             ┌─────────────────┐
│ Android Studio  │   HTTP GET  │  FastAPI (API)  │
│ (Kotlin/Java)   │ ◄─────────► │ (Python 3.10+)  │
│ Mobile App      │   JWT Auth  │  Host: Staging  │
└─────────────────┘             └────────┬────────┘
                                         │
                                   pyodbc│ (SQL Auth)
                                         ▼
┌─────────────────┐             ┌─────────────────┐
│   ASP.NET MVC   │   ADO.NET   │   SQL Server    │
│ (Web Dashboard) ├────────────►│  db_vending_    │
│ (Existing)      │             │    machine      │
└─────────────────┘             └─────────────────┘
```

- **Database**: Satu database SQL Server (`db_vending_machine`) diakses oleh dua sistem backend secara paralel.
- **Client Web**: Tetap menggunakan ASP.NET MVC.
- **Client Mobile**: Menggunakan FastAPI.

---

## 2. Pilihan Driver Database: `pyodbc` (Sync)

Diputuskan untuk menggunakan **`pyodbc`** sebagai driver SQL Server:
- **Alasan**: Sangat matang, memiliki performa stabil untuk SQL Server di Windows/Linux, mendukung parameterization penuh untuk mencegah SQL Injection, dan sintaksnya sangat mirip dengan ADO.NET (`SqlConnection` & `SqlCommand`) yang sudah digunakan di C#.
- **Koneksi Pooling**: Menggunakan library bawaan Python (`contextlib` & connection pool decorator) untuk mencegah overhead membuka/menutup koneksi database berulang kali.

---

## 3. Struktur Folder Project FastAPI (Rekomendasi)

Berikut adalah struktur folder standar industri untuk FastAPI agar scalable dan mudah dikembangkan secara gradual:

```
vending_api/
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # Entry point aplikasi FastAPI
│   │
│   ├── core/
│   │   ├── config.py           # Konfigurasi aplikasi & .env reader
│   │   ├── security.py         # JWT token generator & hashing password
│   │   └── database.py         # Pool koneksi pyodbc & DB helper
│   │
│   ├── models/                 # Pydantic schemas (Data Validation)
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   └── calendar.py
│   │
│   ├── routers/                # API Endpoints (Controllers)
│   │   ├── auth.py             # Route /api/v1/auth
│   │   ├── dashboard.py        # Route /api/v1/dashboard
│   │   ├── calendar.py         # Route /api/v1/calendar
│   │   └── manual_insert.py    # Route /api/v1/manual-insert
│   └── services/               # SQL Query & Logika Bisnis (SQL theft)
│       ├── dashboard_service.py
│       └── calendar_service.py
│
├── requirements.txt            # Python Dependencies
└── .env                        # Environment variables (DB password, JWT secret)
```

---

## 4. Keamanan & Autentikasi (JWT Token)

### A. Apakah FastAPI memiliki JWT Bawaan?
**Tidak sepenuhnya.**
FastAPI menyediakan modul helper bernama `fastapi.security` (seperti `OAuth2PasswordBearer` untuk membaca token dari header authorization), tetapi **tidak memiliki library kriptografi bawaan** untuk membuat (sign) dan membaca (decode) token JWT tersebut.

Untuk mengimplementasikannya, kita perlu memasang library tambahan di Python:
1. `python-jose` (atau `PyJWT`): Untuk enkripsi, pembuatan, dan verifikasi JWT token.
2. `passlib[bcrypt]`: Untuk melakukan hashing password akun pengguna (jika nanti ada fitur register/login admin di Android).

### B. Mengapa JWT Token Sangat Penting untuk Android?

1. **Keamanan Tanpa Session (Stateless)**: Aplikasi mobile tidak bisa menyimpan session berbasis cookie seperti web browser. JWT berbentuk string ringkas (`Header.Payload.Signature`) yang dikirim di setiap request header (`Authorization: Bearer <TOKEN>`).
2. **Perlindungan Terhadap Database**: SQL Server kamu berisi password dan data sensitif vending. Tanpa JWT, siapa pun bisa menembak API FastAPI kamu dan mencuri data. JWT memastikan hanya aplikasi Android yang sudah login yang bisa memanggil endpoint.
3. **Mencegah Man-in-the-Middle Attack**: Signature dalam JWT menjamin bahwa data di dalam token tidak dimodifikasi oleh perantara/hacker saat transit.

### C. Alur Kerja Autentikasi JWT pada Android & FastAPI

```
┌───────────┐                POST /auth/login               ┌───────────┐
│  Android  ├──────────────────────────────────────────────►│  FastAPI  │
│  Studio   │           {username, password}                │  Backend  │
│  (Kotlin) │◄──────────────────────────────────────────────┤           │
└─────┬─────┘         Response: {access_token}              └───────────┘
      │
      │ Simpan token di EncryptedSharedPreferences / DataStore
      ▼
┌───────────┐         GET /dashboard/metrics                ┌───────────┐
│  Android  ├──────────────────────────────────────────────►│  FastAPI  │
│  Studio   │       Header: [Authorization: Bearer ...]     │  Backend  │
│  (Kotlin) │◄──────────────────────────────────────────────┤           │
└───────────┘             Response: JSON Data               └───────────┘
```

---

## 5. Rencana Instalasi Dependencies (Python)

File `requirements.txt` awal yang akan digunakan:
```txt
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
pyodbc>=4.0.39
pydantic[email]>=2.0
python-dotenv>=1.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
```
