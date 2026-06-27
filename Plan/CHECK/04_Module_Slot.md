# 📦 Cross-Check #04f — Module: Slot Management

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Manajemen slot (posisi) di dalam vending machine:
1. **Pilih Mesin** — Filter slot berdasarkan mesin vending
2. **Lihat Daftar Slot** — Tampil semua slot dengan varian & kapasitas
3. **Tambah Slot** — Buat slot baru di mesin (Superadmin)
4. **Edit Slot** — Ubah varian yang ada di slot, kapasitas
5. **Hapus Slot** — Hapus slot dari mesin

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/slots` | GET | List slot (filter by vm) | ⬜ |
| `/api/v1/slots` | POST | Tambah slot | ⬜ |
| `/api/v1/slots/:id` | PUT | Edit slot | ⬜ |
| `/api/v1/slots/:id` | DELETE | Hapus slot | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Adapter | Fungsi | Terhubung API? | Status |
|------------------|--------|----------------|--------|
| `SlotManagementActivity.java` | List + CRUD slot | ⬜ | ⬜ |
| `SlotAdapter.java` | Card list slot | — | ⬜ |
| `item_slot.xml` | UI card slot | — | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

- [ ] Spinner mesin tampil (dibungkus MaterialCardView)
- [ ] Setelah pilih mesin, daftar slot termuat dari API
- [ ] Summary Total Slot & Kapasitas tampil di header
- [ ] Card slot: nama slot, varian, kapasitas (sebagai badge) tampil
- [ ] Stripe indigo tampil di kiri card
- [ ] FAB "+" muncul (sesuai role)
- [ ] Tambah slot berhasil
- [ ] Edit slot berhasil (ganti varian / kapasitas)
- [ ] Hapus slot berhasil dengan konfirmasi
- [ ] Empty state tampil jika belum ada slot

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
