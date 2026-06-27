# 🏧 Cross-Check #04d — Module: Machine Management

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen unit vending machine fisik:
1. **Lihat Daftar Mesin** — Tampil semua VM dengan info ref & IP
2. **Tambah Mesin** — Daftarkan VM baru (Superadmin)
3. **Edit Mesin** — Ubah nama, ref, IP mesin
4. **Hapus Mesin** — Hapus data VM

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/machines` | GET | List semua mesin | ⬜ |
| `/api/v1/machines` | POST | Tambah mesin | ⬜ |
| `/api/v1/machines/:id` | PUT | Edit mesin | ⬜ |
| `/api/v1/machines/:id` | DELETE | Hapus mesin | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Adapter | Fungsi | Terhubung API? | Status |
|------------------|--------|----------------|--------|
| `MachineManagementActivity.java` | List + CRUD mesin | ⬜ | ⬜ |
| `MachineAdapter.java` | Card list mesin | — | ⬜ |
| `item_machine.xml` | UI card mesin | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Daftar mesin tampil dari API
- [ ] Card mesin: nama, kode ref, IP address tampil
- [ ] Stripe indigo tampil di kiri card
- [ ] FAB "+" muncul (sesuai role)
- [ ] Tambah mesin berhasil
- [ ] Edit mesin berhasil
- [ ] Hapus mesin berhasil dengan konfirmasi

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
