# 👥 Cross-Check #04b — Module: Master Data VM (User Management)

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen akun user aplikasi (hanya Superadmin):
1. **Lihat Daftar User** — Tampil semua akun terdaftar
2. **Approve User** — Setujui pendaftaran user baru
3. **Edit User** — Ubah role/level dan password user
4. **Nonaktifkan / Hapus** — Tolak atau nonaktifkan akun

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/users` | GET | List semua user | ⬜ |
| `/api/v1/users/approve` | POST | Approve user + kirim OTP | ⬜ |
| `/api/v1/users/:id` | PUT | Edit role / password user | ⬜ |
| `/api/v1/users/:id/reject` | DELETE/PATCH | Nonaktifkan user | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity | Fungsi | Terhubung API? | Status |
|----------|--------|----------------|--------|
| `MasterDataUserActivity.java` | Manajemen user | ⬜ | ⬜ |
| `UserAdapter.java` | Card list user | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Hanya bisa diakses oleh Superadmin (level 9)
- [ ] List user tampil dari API
- [ ] Tombol Approve muncul untuk user yang pending
- [ ] OTP sukses dikirim ke email setelah approve
- [ ] Dialog tampilkan OTP (untuk testing)
- [ ] Edit role berfungsi (User ↔ Superadmin)
- [ ] Nonaktifkan akun berfungsi

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
