# ⏰ Cross-Check #06 — Shift Management

**Status:** ⚠️ Ada 1 Potensi Mismatch — Perlu Diverifikasi
**Tanggal Analisis:** 2026-06-30
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul Shift Management mencakup CRUD untuk data shift kerja:
- Lihat semua shift (list)
- Tambah shift baru (Superadmin only)
- Edit nama, bagian, jam mulai/akhir, status aktif
- Hapus shift
- Validasi format waktu HH:MM

---

## 🔧 API Side

**Base path:** `/api/v1/shift/...`
**Tabel DB:** `master_shift` (melalui `shift_service`)

| # | Endpoint | Method | Android Call | Status |
|---|----------|--------|-------------|--------|
| 1 | `/api/v1/shift` | GET | `getAllShifts()` | ✅ |
| 2 | `/api/v1/shift/{id}` | GET | `getShiftById(id)` | ✅ |
| 3 | `/api/v1/shift` | POST | `createShift(body)` | ✅ |
| 4 | `/api/v1/shift/{id}` | PUT | `updateShift(id, body)` | ✅ |
| 5 | `/api/v1/shift/{id}` | DELETE | `deleteShift(id)` | ✅ |

---

## 📱 Android Side

### Model `ShiftResponse.java` vs API (`schemas.ShiftResponse`)

| Field API | Field Java | SerializedName | Match? |
|-----------|-----------|----------------|--------|
| `id_recnum_mst` | `idRecnumMst` | ✅ | ✅ |
| `nama_shift` | `namaShift` | ✅ | ✅ |
| `nama_bagian` | `namaBagian` | ✅ | ✅ |
| `jam_mulai` | `jamMulai` | ✅ | ✅ |
| `jam_akhir` | `jamAkhir` | ✅ | ✅ |
| `status_active` | `statusActive` | ✅ | ✅ |
| `update_time` | `updateTime` | ✅ | ✅ |
| `user_input` | `userInput` | ✅ | ✅ |

### Request Body dari Android (Create/Update)

```java
body.put("nama_shift", namaShift);
body.put("nama_bagian", namaBagian);
body.put("jam_mulai", jamMulai);      // String "HH:MM"
body.put("jam_akhir", jamAkhir);      // String "HH:MM"
body.put("status_active", isActive ? "1" : "0");  // ⚠️ String, bukan int!
body.put("user_input", sessionManager.getUsername());
```

---

## 🔍 Temuan

| # | Level | Temuan | Rekomendasi |
|---|-------|--------|-------------|
| 1 | ⚠️ **Perlu Cek** | `status_active` dikirim sebagai **String** `"1"/"0"` dari Android, tapi perlu konfirmasi apakah API/DB menerima String atau Integer | Test langsung — kalau berhasil berarti API sudah handle konversi |
| 2 | ✅ OK | Validasi format jam `HH:MM` pakai regex sebelum submit | — |
| 3 | ✅ OK | Semua field wajib (nama, bagian, jam mulai, jam akhir) divalidasi | — |
| 4 | ✅ OK | FAB tambah hanya muncul untuk Superadmin (level 9) | — |
| 5 | ✅ OK | GET all mengembalikan `List<ShiftResponse>` langsung (bukan wrapper) | — |
| 6 | ✅ OK | Konfirmasi dialog sebelum hapus ada | — |
| 7 | ⚠️ Minor | `getAllShifts()` return `List` langsung — perlu verifikasi apakah API juga return array langsung (bukan `{total, data:[]}` seperti Machine) | Kalau tampil normal saat test = aman |

---

## ✅ Checklist Validasi

- [ ] Halaman Shift terbuka, list tampil
- [ ] Total shift di header sesuai
- [ ] SwipeRefresh berfungsi
- [ ] Tambah shift baru berhasil (Superadmin)
- [ ] Validasi format jam `HH:MM` bekerja (coba isi format salah)
- [ ] Edit shift berhasil (termasuk toggle Status Aktif)
- [ ] Hapus shift + dialog konfirmasi berfungsi

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan]
...
```
