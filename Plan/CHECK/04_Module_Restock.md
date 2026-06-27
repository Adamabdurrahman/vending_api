# 🥤 Cross-Check #04g — Module: Restock Management

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen pengisian stok vending machine per slot:
1. **Pilih Mesin** — Filter restock berdasarkan mesin
2. **Lihat Daftar Restock** — Tampil stok tiap slot dengan info auditor
3. **Filter Stok Rendah** — Tampil hanya slot dengan stok < 10
4. **Tambah / Edit Restock** — Isi ulang stok slot tertentu
5. **Hapus** — Hapus record restock

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/restock` | GET | List restock (filter by vm) | ⬜ |
| `/api/v1/restock` | POST | Tambah restock | ⬜ |
| `/api/v1/restock/:id` | PUT | Edit restock | ⬜ |
| `/api/v1/restock/:id` | DELETE | Hapus restock | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Adapter | Fungsi | Terhubung API? | Status |
|------------------|--------|----------------|--------|
| `RestockManagementActivity.java` | List + CRUD restock | ⬜ | ⬜ |
| `RestockAdapter.java` | Card list restock | — | ⬜ |
| `item_restock.xml` | UI card restock | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Spinner mesin tampil (dibungkus MaterialCardView)
- [ ] Setelah pilih mesin, daftar restock termuat dari API
- [ ] Summary Slot & Total Qty tampil di header
- [ ] Checkbox "Stok Rendah < 10" berfungsi sebagai filter
- [ ] Card restock: nama slot, stok qty, status, auditor & tanggal tampil
- [ ] Badge status "Aktif" tampil
- [ ] Stripe hijau tampil di kiri card
- [ ] FAB "+" berfungsi untuk tambah restock
- [ ] Edit restock (ubah qty) berhasil
- [ ] Hapus restock berhasil dengan konfirmasi
- [ ] Empty state tampil jika tidak ada data

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
