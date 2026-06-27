# ⏰ Cross-Check #04e — Module: Shift Management

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen shift kerja karyawan:
1. **Lihat Daftar Shift** — Tampil semua shift dengan jam & bagian
2. **Tambah Shift** — Buat shift baru (Superadmin)
3. **Edit Shift** — Ubah nama, jam, bagian, status aktif
4. **Hapus Shift** — Hapus data shift

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/shifts` | GET | List semua shift | ⬜ |
| `/api/v1/shifts` | POST | Tambah shift | ⬜ |
| `/api/v1/shifts/:id` | PUT | Edit shift | ⬜ |
| `/api/v1/shifts/:id` | DELETE | Hapus shift | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Adapter | Fungsi | Terhubung API? | Status |
|------------------|--------|----------------|--------|
| `ShiftManagementActivity.java` | List + CRUD shift | ⬜ | ⬜ |
| `ShiftAdapter.java` | Card list shift | — | ⬜ |
| `item_shift.xml` | UI card shift | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Daftar shift tampil dari API
- [ ] Total Shift tampil di header ("Total Shift: X")
- [ ] Card shift: nama shift, bagian, jam kerja tampil
- [ ] Badge "Aktif" tampil dengan warna hijau
- [ ] Stripe biru tampil di kiri card
- [ ] SwipeRefresh berfungsi
- [ ] FAB "+" hanya muncul untuk Superadmin
- [ ] Dialog form tambah/edit shift tampil lengkap
- [ ] Validasi format jam (HH:MM) berfungsi
- [ ] Hapus shift berhasil dengan konfirmasi

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
