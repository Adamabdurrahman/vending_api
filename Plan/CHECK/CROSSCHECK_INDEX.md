# 📋 CROSSCHECK INDEX — CapstoneProject vs vending_api

> **Tujuan:** Dokumen terpusat untuk memantau status cross-check antara backend `vending_api` dan Android `CapstoneProject`.
> **Cara kerja:** Setiap modul dicek oleh Antigravity → kamu validasi di device → update status di sini.

---

## 🔑 Legend Status

| Simbol | Arti |
|--------|------|
| ⬜ | Belum dimulai |
| 🔍 | Sedang dianalisis oleh Antigravity |
| 📋 | Analisis selesai, menunggu validasi kamu |
| ✅ | Divalidasi & sesuai |
| ⚠️ | Ada revisi kecil (dicatat di file modul) |
| ❌ | Ada masalah besar / belum diimplementasi |

---

## 📊 Status Per Modul

### 🔐 Autentikasi
| No | Modul | File Detail | Status | Divalidasi Tanggal |
|----|-------|-------------|--------|--------------------|
| 1 | Login | [01_Login_Auth.md](./01_Login_Auth.md) | ✅ | — |
| 2 | Register | [01_Login_Auth.md](./01_Login_Auth.md) | ✅ | — |
| 3 | Lupa Password | [01_Login_Auth.md](./01_Login_Auth.md) | ✅ | — |

### 👤 Profil & Akun
| No | Modul | File Detail | Status | Divalidasi Tanggal |
|----|-------|-------------|--------|--------------------|
| 4 | Account Settings / Profile | [02_Profile_Account.md](./02_Profile_Account.md) | ⚠️ | 29 Jun 2026 |

### ⚙️ Operational Menu
| No | Modul | File Detail | Status | Divalidasi Tanggal |
|----|-------|-------------|--------|--------------------|
| 5 | Kalender Operasional | [03_Operational_Menu.md](./03_Operational_Menu.md) | ✅ | — |
| 6 | Insert Manual (Upload Excel) | [03_Operational_Menu.md](./03_Operational_Menu.md) | ✅ | — |
| 7 | Master Data User (Akun) | [04_Module_MasterVM.md](./04_Module_MasterVM.md) | ✅ | 30 Jun 2026 |

### 📦 Module Menu
| No | Modul | File Detail | Status | Divalidasi Tanggal |
|----|-------|-------------|--------|--------------------|
| 8 | Employee Management | [04_Module_Employee.md](./04_Module_Employee.md) | Dihide | — |
| 9 | Manage Alat VM (Mesin) | [04_Module_MasterVM.md](./04_Module_MasterVM.md) | ✅ | 30 Jun 2026 |
| 10 | Master Variant | [04_Module_MasterVariant.md](./04_Module_MasterVariant.md) | ✅ | 30 Jun 2026|
| 11 | Shift Management | [04_Module_Shift.md](./04_Module_Shift.md) | ✅ | 30 Jun 2026|
| 12 | Slot Management | [04_Module_Slot.md](./04_Module_Slot.md) |✅ | 30 Jun 2026|
| 13 | Restock Management | [04_Module_Restock.md](./04_Module_Restock.md) | ✅ | 30 Jun 2026|

### 📈 Dashboard Menu
| No | Modul | File Detail | Status | Divalidasi Tanggal |
|----|-------|-------------|--------|--------------------|
| 14 | Dashboard Summary | [05_Dashboard_Summary.md](./05_Dashboard_Summary.md) | ✅ | — |
| 15 | Prediction Dashboard | [05_Dashboard_Prediction.md](./05_Dashboard_Prediction.md) | ✅ | 1 Jul 2026 |
| 16 | Inventory Dashboard | [05_Dashboard_Inventory.md](./05_Dashboard_Inventory.md) | ✅ | 1 Jul 2026 |

---

## 📝 Catatan Validasi (Diisi Saat Kamu Cek di Device)

> Tulis disini catatan umum atau hal yang perlu didiskusikan lebih lanjut.

```
[Tanggal] — [Modul] — [Catatan]
29 Juni 2026 - Login - pada bagian login semuanya aman namun mungkin untuk diakhir atau kapan perlu setup agar password itu gak menggunakan string tapi di hash supaya menjamin keamanan, progress bar lama 
29 Juni 2026 - Profile - Tidak ada validasi password lama saat ganti password — rawan jika device dicuri
ID tombol back masih btnMenu (naming lama), tidak konsisten
Teks dialog masih Bahasa Inggris ("Are you sure...", "Change Password")
Tidak ada validasi panjang minimum password baru
30 Juni 2026 - Profile - Ganti foto profil menyebabkan layar putih — ditunda, dicatat sebagai minor issue untuk difix di akhir batch
30 Juni 2026 - Operational - Kalender Operasional dan Manual Insert sudah dicek dan aman di HP fisik, sekedar perubahan sedikit pada bagian headernya di menu kalender dan manual insert untuk tombol back ke sidebar itu menggunakan panah dan bukannya hamburger sama seperti yang ada di menu profile, lalu ada juga di bagian kanannya itu ada gambar kalender mungkin bisa dihapus saja karena tidak penting
30 Juni 2026 - Master Data VM - sudah selesai pada bagian UI dan fungsionalitasnya semua berjalan lancar
30 Juni 2026 - Master Variant - sudah selesai pada bagian UI dan fungsionalitasnya semua berjalan lancar
30 Juni 2026 - Shift Management - sudah selesai pada bagian UI dan fungsionalitasnya semua berjalan lancar
30 Juni 2026 - slot dan restock management sudah selesai pada bagian UI dan fungsionalitasnya semua berjalan lancar
```

---

## 📅 Progress Timeline

| Tahap | Deskripsi | Status |
|-------|-----------|--------|
| Phase 1 | Setup file CHECK + Design.md | ✅ Selesai |
| Phase 2 | Redesign semua Module UI (light theme) | ✅ Selesai |
| Phase 3 | Cross-check Autentikasi | ✅ Selesai |
| Phase 4 | Cross-check Profile | ✅ Selesai (ada 1 minor issue: foto) |
| Phase 5 | Cross-check Operational | ✅ Selesai |
| Phase 6 | Cross-check Module | ✅ Selesai |
| Phase 7 | Cross-check Dashboard | ⬜ |
