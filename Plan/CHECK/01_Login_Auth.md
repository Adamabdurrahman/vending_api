# 🔐 Cross-Check #01 — Autentikasi (Login, Register, Lupa Password)

**Status:** 📋 Analisis Selesai — Menunggu Validasi Kamu
**Tanggal Analisis:** 2026-06-29
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul ini mencakup semua flow autentikasi pengguna:
1. **Login** — Masuk dengan username & password
2. **Register** — Daftar akun baru, menunggu approval admin
3. **Lupa Password** — Reset password via OTP email

---

## 🔧 API Side (vending_api) — FastAPI / Python

> Backend ini adalah **FastAPI (Python)**, bukan Node.js.
> Semua endpoint didefinisikan di `main.py`.
> Base URL saat ini: `http://10.0.2.2:8000/` (emulator Android → localhost PC)

| # | Endpoint | Method | Deskripsi | Status |
|---|----------|--------|-----------|--------|
| 1 | `/login` | POST | Login dengan username + password | ✅ Ada |
| 2 | `/api/v1/auth/register` | POST | Register user baru (status pending) | ✅ Ada |
| 3 | `/api/v1/auth/verify-token` | POST | Verifikasi OTP aktivasi akun | ✅ Ada |
| 4 | `/api/v1/auth/reset-password/request` | POST | Request OTP untuk reset password | ✅ Ada |
| 5 | `/api/v1/auth/reset-password/confirm` | POST | Konfirmasi OTP + password baru | ✅ Ada |
| 6 | `/api/v1/admin/approve-user` | POST | Admin approve user (+ kirim OTP) | ✅ Ada |
| 7 | `/api/v1/admin/users` | GET | List semua user (admin) | ✅ Ada |

### Catatan Detail API

**Login (`POST /login`):**
- Menerima: `{ username, password }` (plain text, belum di-hash!)
- Return: `{ id_recnum_mur, Id, username, email_primary, level_user, status_active, photo_url }`
- Status aktif user: `"1"` = aktif, `"P"` = pending admin, `"T"` = pending OTP
- Jika status `"T"` → return error `PENDING_OTP` + `user_id` agar bisa redirect ke OTP form

**Register (`POST /api/v1/auth/register`):**
- Menerima: `{ username, password, level_user, email_primary, nohp }`
- Status awal user baru: pending (`P`)
- Harus menunggu admin approve sebelum bisa login

**Verify Token (`POST /api/v1/auth/verify-token`):**
- Menerima: `{ user_id, token }` — token 6 digit OTP dari email
- Mengubah status user dari `T` → `1` (aktif)

**Reset Password:**
- Step 1 (`request`): Menerima `{ username, email }` → kirim OTP ke email, return `{ user_id, otp_test_debug }`
- Step 2 (`confirm`): Menerima `{ user_id, token, new_password }` → reset berhasil

---

## 📱 Android Side (CapstoneProject)

| Activity | Fungsi | Endpoint Dipanggil | Status |
|----------|--------|-------------------|--------|
| `LoginPageActivity.java` | Form login | `POST /login` | ✅ Sesuai |
| `RegisterActivity.java` | Form register + OTP | `POST /api/v1/auth/register` + `verify-token` | ✅ Sesuai |
| `ForgotPasswordActivity.java` | Request OTP + reset | `POST /api/v1/auth/reset-password/request` + `confirm` | ✅ Sesuai |

### Detail Temuan Android

**LoginPageActivity:**
- ✅ Input: etEmail (digunakan sebagai `username`) + etPassword
- ✅ Memanggil `RetrofitClient.getApiService().login(request)`
- ✅ Session disimpan via `SessionManager.saveLoginSession()`
- ✅ Field yang disimpan: `id_recnum_mur`, `Id`, `username`, `email_primary`, `level_user`, `status_active` — **cocok dengan response API**
- ✅ Handle error `PENDING_OTP` → redirect ke RegisterActivity dengan extra `SHOW_OTP=true`
- ⚠️ Loading menggunakan `ProgressBar` lama (bukan premium overlay seperti modul lain)
- ⚠️ Label field masih "Email" padahal input yang diterima API adalah `username`

**RegisterActivity:**
- ✅ Dua layout state: form register → form OTP (toggle visibility)
- ✅ Field register: `username`, `email_primary`, `nohp`, `password`, `level_user=1`
- ✅ Setelah register sukses → switch ke OTP form
- ✅ OTP Verify: kirim `{ user_id, token }` ke `/api/v1/auth/verify-token`
- ✅ Bisa menerima redirect dari Login (jika `SHOW_OTP=true`) langsung ke form OTP
- ✅ `progressOverlay` premium sudah digunakan

**ForgotPasswordActivity:**
- ✅ Dua layout state: request OTP → konfirmasi reset
- ✅ Step 1: kirim `{ username, email }` ke `/api/v1/auth/reset-password/request`
- ✅ Menangkap `otp_test_debug` dari response untuk testing (Toast debug OTP) 
- ✅ Step 2: kirim `{ user_id, token, new_password }` ke `/api/v1/auth/reset-password/confirm`
- ✅ Setelah sukses → redirect ke Login dengan `FLAG_ACTIVITY_CLEAR_TASK`
- ✅ `progressOverlay` premium sudah digunakan

---

## 🔍 Temuan & Potensi Masalah

| # | Level | Temuan | Rekomendasi |
|---|-------|--------|-------------|
| 1 | ⚠️ Minor | Label field login masih "Email" padahal API pakai `username` | Ubah hint menjadi "Username" |
| 2 | ⚠️ Minor | `LoginPageActivity` masih pakai `ProgressBar` biasa, bukan overlay premium | Upgrade ke `overlayLoading` seperti modul lain |
| 3 | ℹ️ Info | Password disimpan **plain text** di database (tidak di-hash) | Bukan masalah Android, tapi perlu diketahui untuk keamanan |
| 4 | ✅ OK | Semua 5 endpoint auth terhubung dengan benar | — |
| 5 | ✅ OK | Session Manager menyimpan semua field yang dibutuhkan | — |
| 6 | ✅ OK | Flow PENDING_OTP sudah ditangani dengan baik (dialog + redirect) | — |
| 7 | ✅ OK | Debug OTP Toast sudah ada untuk kemudahan testing | — |

---

## ✅ Checklist Validasi (Diisi oleh Kamu setelah cek di device)

### Login
- [ ] Form input username & password tampil benar
- [ ] Tombol login berfungsi
- [ ] Error: username tidak ditemukan → tampil pesan yang jelas
- [ ] Error: password salah → tampil pesan yang jelas
- [ ] Error: akun pending admin → tampil pesan sesuai
- [ ] Error: akun pending OTP → muncul dialog & redirect ke form OTP
- [ ] Setelah login sukses → masuk ke SidebarMenuActivity
- [ ] Session tersimpan (nama user tampil di sidebar)

### Register
- [ ] Form register: username, email, nomor HP, password tampil
- [ ] Setelah register → form OTP muncul + ada pesan "menunggu verifikasi Superadmin"
- [ ] Input OTP 6 digit → akun aktif & redirect ke Login
- [ ] Redirect dari Login (jika PENDING_OTP) langsung ke form OTP berfungsi

### Lupa Password
- [ ] Form input username & email tampil
- [ ] Setelah kirim → form OTP + password baru muncul
- [ ] Toast debug OTP muncul (untuk testing)
- [ ] Setelah konfirmasi → redirect ke Login, bisa login dengan password baru

---

## 📝 Catatan Validasi (Diisi oleh Kamu)

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** 📋 Menunggu validasi kamu
