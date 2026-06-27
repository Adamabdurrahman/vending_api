# 🍼 Cross-Check #04c — Module: Master Variant

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen varian produk susu yang dijual di vending machine:
1. **Lihat Daftar Varian** — Tampil semua varian dengan info stok & prediksi
2. **Tambah Varian** — Buat varian rasa baru (Superadmin)
3. **Edit Varian** — Ubah nama, harga, status aktif
4. **Hapus Varian** — Hapus varian (Superadmin)

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/variants` | GET | List semua varian | ⬜ |
| `/api/v1/variants` | POST | Tambah varian | ⬜ |
| `/api/v1/variants/:id` | PUT | Edit varian | ⬜ |
| `/api/v1/variants/:id` | DELETE | Hapus varian | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Adapter | Fungsi | Terhubung API? | Status |
|------------------|--------|----------------|--------|
| `MasterVariantActivity.java` | List + CRUD varian | ⬜ | ⬜ |
| `MasterVariantAdapter.java` | Card varian dengan detail stok | — | ⬜ |
| `item_variant_card.xml` | UI card varian | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Daftar varian tampil dari API
- [ ] Summary (Total Varian, Aktif) tampil di header
- [ ] Card varian: nama, info prediksi, gudang, stok VM tampil
- [ ] Detail bulanan (3 bulan) tampil di card
- [ ] Badge "Beli: X" tampil
- [ ] FAB "+" hanya tampil untuk Superadmin
- [ ] Tambah varian berhasil
- [ ] Edit varian berhasil
- [ ] Hapus varian berhasil

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
