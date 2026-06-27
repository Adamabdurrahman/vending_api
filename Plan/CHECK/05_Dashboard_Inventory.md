# 🏭 Cross-Check #05c — Dashboard: Inventory

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Dashboard inventory untuk memantau stok per mesin & per varian:
1. **Ringkasan Stok** — Total stok semua mesin, stok rendah
2. **Stok Per Mesin** — Detail stok tiap slot di setiap mesin
3. **Stok Per Varian** — Berapa unit tiap varian tersedia
4. **Stock In** — Input stok masuk ke gudang
5. **Stock Movement** — Riwayat pergerakan stok

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| *(belum dikonfirmasi)* | GET | Ringkasan inventory | ⬜ |
| *(belum dikonfirmasi)* | GET | Stok per mesin | ⬜ |
| *(belum dikonfirmasi)* | GET | Stok per varian | ⬜ |
| *(belum dikonfirmasi)* | POST | Stock In (tambah stok gudang) | ⬜ |
| *(belum dikonfirmasi)* | GET | Riwayat stock movement | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Adapter | Fungsi | Terhubung API? | Status |
|------------------|--------|----------------|--------|
| `InventoryDashboardActivity.java` | Dashboard inventory utama | ⬜ | ⬜ |
| `InventoryActivity.java` | Halaman inventory detail | ⬜ | ⬜ |
| `InventoryVariantAdapter.java` | Adapter stok per varian | — | ⬜ |
| `StockInActivity.java` | Form tambah stok gudang | ⬜ | ⬜ |
| `StockInVariantAdapter.java` | Adapter form stock in | — | ⬜ |
| `StockMovementAdapter.java` | Adapter riwayat pergerakan | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Dashboard inventory loading tanpa error
- [ ] Ringkasan stok (total, rendah) tampil
- [ ] Stok per varian tampil dengan detail
- [ ] Navigasi ke detail per mesin berfungsi
- [ ] Tombol "Stock In" berfungsi
- [ ] Form stock in: pilih varian, input qty berhasil
- [ ] Riwayat pergerakan stok tampil
- [ ] Filter "Per Varian" berfungsi sesuai ekspektasi

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
