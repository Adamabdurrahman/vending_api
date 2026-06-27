# 👤 Cross-Check #02 — Profile & Account Settings

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul ini mencakup semua yang berkaitan dengan akun pengguna setelah login:
1. **Lihat Profil** — Tampilkan info user yang sedang login
2. **Ubah Password** — Ganti password dari dalam aplikasi
3. **Update Profil** — Edit username, email, dll (jika ada)
4. **Logout** — Keluar dari aplikasi

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/auth/me` | GET | Get profil user login | ⬜ |
| `/api/v1/auth/change-password` | PUT/PATCH | Ubah password | ⬜ |
| `/api/v1/auth/update-profile` | PUT/PATCH | Update info profil | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity | Fungsi | Terhubung API? | Status |
|----------|--------|----------------|--------|
| `AccountSettingsActivity.java` | Tampil & edit profil | ⬜ | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

### Lihat Profil
- [ ] Nama user tampil sesuai yang terdaftar
- [ ] Role/level user tampil dengan benar (User Biasa / Superadmin)
- [ ] Email tampil

### Ubah Password
- [ ] Form ubah password tampil
- [ ] Validasi: password lama harus benar
- [ ] Validasi: password baru & konfirmasi harus sama
- [ ] Setelah ubah, bisa login dengan password baru

### Logout
- [ ] Tombol logout ada
- [ ] Setelah logout, kembali ke halaman Login
- [ ] Session terhapus (tidak bisa back ke halaman dalam)

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
