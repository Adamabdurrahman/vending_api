# 🔐 Cross-Check #01 — Autentikasi (Login, Register, Lupa Password)

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul ini mencakup semua flow autentikasi pengguna:
1. **Login** — Masuk dengan username & password
2. **Register** — Daftar akun baru, menunggu approval admin
3. **Lupa Password** — Reset password via OTP email

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/auth/login` | POST | Login user | ⬜ |
| `/api/v1/auth/register` | POST | Register user baru | ⬜ |
| `/api/v1/auth/forgot-password` | POST | Request OTP lupa password | ⬜ |
| `/api/v1/auth/reset-password` | POST | Reset password dengan OTP | ⬜ |
| `/api/v1/auth/verify-otp` | POST | Verifikasi OTP aktivasi akun | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity | Fungsi | Terhubung API? | Status |
|----------|--------|----------------|--------|
| `LoginPageActivity.java` | Form login | ⬜ | ⬜ |
| `RegisterActivity.java` | Form register | ⬜ | ⬜ |
| `ForgotPasswordActivity.java` | Form lupa password | ⬜ | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

### Login
- [ ] Form input username & password tampil benar
- [ ] Tombol login berfungsi
- [ ] Error handling: salah password tampil pesan yang jelas
- [ ] Setelah login, navigasi ke halaman utama (sidebar)
- [ ] Session tersimpan (tidak logout saat app ditutup)

### Register
- [ ] Form register tampil lengkap
- [ ] Validasi input (username, email, password)
- [ ] Setelah register, ada info "menunggu approval admin"
- [ ] Admin bisa approve dari `MasterDataUserActivity`
- [ ] Setelah diapprove, OTP dikirim ke email

### Lupa Password
- [ ] Form input email tampil benar
- [ ] OTP berhasil dikirim ke email
- [ ] Form input OTP + password baru tampil
- [ ] Setelah reset, bisa login dengan password baru

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
