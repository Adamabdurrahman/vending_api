# 👷 Cross-Check #04a — Module: Employee Management

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen data karyawan (hanya Superadmin yang bisa tambah/edit/hapus):
1. **Lihat Daftar Karyawan** — Tampil list dengan pagination
2. **Tambah Karyawan** — Input data karyawan baru
3. **Edit Karyawan** — Ubah data karyawan
4. **Hapus Karyawan** — Hapus data karyawan

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/employees` | GET | List karyawan (pagination) | ⬜ |
| `/api/v1/employees` | POST | Tambah karyawan | ⬜ |
| `/api/v1/employees/:id` | PUT | Edit karyawan | ⬜ |
| `/api/v1/employees/:id` | DELETE | Hapus karyawan | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity | Fungsi | Terhubung API? | Status |
|----------|--------|----------------|--------|
| `EmployeeActivity.java` | List + CRUD karyawan | ⬜ | ⬜ |
| `item_employee.xml` | Tampilan card karyawan | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Daftar karyawan tampil dari API (bukan data dummy)
- [ ] Pagination berfungsi (Prev/Next)
- [ ] Avatar & status dot (aktif/blocked) tampil
- [ ] NIK dan RFID tampil di card
- [ ] FAB "+" hanya tampil untuk Superadmin
- [ ] Tambah karyawan berhasil
- [ ] Edit karyawan berhasil
- [ ] Hapus karyawan berhasil dengan konfirmasi

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
