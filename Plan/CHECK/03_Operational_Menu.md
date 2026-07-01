# ⚙️ Cross-Check #03 — Operational Menu

**Status:** 📋 Analisis Selesai — Menunggu Validasi Kamu
**Tanggal Analisis:** 2026-06-29
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul ini mencakup dua sub-menu Operational:
1. **Kalender Operasional** — Lihat, generate, edit, dan hapus kalender per tahun
2. **Insert Manual** — Download template Excel + Upload data sales manual

---

## 🗓️ Sub-Modul 1: Kalender Operasional

### API Side

| # | Endpoint | Method | Deskripsi | Status |
|---|----------|--------|-----------|--------|
| 1 | `/api/v1/calendar?year={year}` | GET | Ambil data seluruh kalender 1 tahun | ✅ Ada |
| 2 | `/api/v1/calendar/day` | POST | Edit status 1 hari (hari kerja/libur/ramadan) | ✅ Ada |
| 3 | `/api/v1/calendar/generate` | POST | Generate kalender 365/366 hari untuk 1 tahun | ✅ Ada |
| 4 | `/api/v1/calendar/year/{year}` | DELETE | Hapus seluruh data kalender 1 tahun | ✅ Ada |

### Android Side

| Method | Fungsi | Endpoint Dipanggil | Status |
|--------|--------|-------------------|--------|
| `fetchCalendar(year)` | Load data kalender 1 tahun | `GET /api/v1/calendar` | ✅ Sesuai |
| `onDayClicked()` → `EditDayBottomSheet` | Edit status hari | `POST /api/v1/calendar/day` | ✅ Sesuai |
| `generateYear(year)` | Generate kalender baru | `POST /api/v1/calendar/generate` | ✅ Sesuai |
| `deleteYear(year)` | Hapus tahun kalender | `DELETE /api/v1/calendar/year/{year}` | ✅ Sesuai |

### Detail Implementasi Kalender

**Tampilan:**
- ✅ ViewPager2 dengan 12 halaman (1 fragment per bulan)
- ✅ Navigasi bulan via tombol prev/next + swipe
- ✅ Spinner tahun (auto-populated dari `available_years` response API)
- ✅ Header menampilkan total hari kerja

**Spinner Tahun:**
- ✅ Tidak trigger re-fetch saat pertama kali di-set (`firstCall` guard)
- ✅ Hanya re-fetch jika tahun benar-benar berubah

**Generate Tahun:**
- ✅ Dialog input dengan saran tahun berikutnya
- ✅ Validasi range 2020–2100
- ✅ Double-confirm dialog sebelum generate
- ✅ Auto-refresh setelah generate berhasil

**Delete Tahun:**
- ✅ Warning dialog dengan teks peringatan jelas
- ✅ Setelah hapus: jika masih ada tahun lain → fetch tahun pertama di list
- ✅ Jika tidak ada tahun lagi → tampilan dikosongkan dengan graceful

**Edit Hari:**
- ✅ `EditDayBottomSheet` sebagai bottom sheet fragment
- ✅ Setelah update berhasil: refetch seluruh tahun untuk refresh

**Error Handling:**
- ✅ `NetworkUtils.checkAndShowError()` sebelum request
- ✅ `overlayLoading` premium overlay saat loading
- ✅ `runOnUiThread` untuk update UI setelah response

---

## 📊 Sub-Modul 2: Insert Manual

### API Side

| # | Endpoint | Method | Deskripsi | Status |
|---|----------|--------|-----------|--------|
| 1 | `/api/v1/manual-insert/template` | GET | Download template Excel | ✅ Ada |
| 2 | `/api/v1/manual-insert/upload` | POST | Upload Excel → insert ke DB | ✅ Ada |

### Android Side

| Method | Fungsi | Endpoint Dipanggil | Status |
|--------|--------|-------------------|--------|
| `downloadTemplate()` | Download template Excel | `GET /api/v1/manual-insert/template` | ✅ Sesuai |
| `uploadExcel(uri)` | Upload file Excel | `POST /api/v1/manual-insert/upload` | ✅ Sesuai |

### Detail Implementasi Manual Insert

**Download Template:**
- ✅ Streaming download (ResponseBody) — tidak load ke memory sekaligus
- ✅ Android 10+: MediaStore Downloads API (tanpa READ_EXTERNAL_STORAGE permission)
- ✅ Android 9-: FileProvider + ExternalStorage
- ✅ Auto-buka file dengan aplikasi spreadsheet setelah download
- ✅ Handle jika tidak ada app spreadsheet → Toast informatif

**Upload Excel:**
- ✅ File picker filter ke `.xlsx` dan `.xls` saja
- ✅ Validasi ekstensi di sisi Android setelah pilih file
- ✅ File di-copy ke cache dulu sebelum upload (menghindari URI permission issue)
- ✅ Multipart upload dengan MIME type Excel yang benar
- ✅ Temp file dihapus setelah upload selesai (cleanup)
- ✅ Dialog ringkasan upload: total / berhasil / duplikat / invalid

**UX Detail:**
- ✅ Drop zone bisa diklik untuk buka file picker
- ✅ Tampilan berubah setelah file dipilih (icon, teks, tombol proses muncul)
- ✅ Tombol "X" untuk clear selection dan reset tampilan

---

## 🔍 Temuan & Potensi Masalah

| # | Level | Temuan | Rekomendasi |
|---|-------|--------|-------------|
| 1 | ✅ OK | Semua 6 endpoint operational terhubung dengan benar | — |
| 2 | ✅ OK | Kalender: guard `firstCall` pada Spinner mencegah double-fetch | — |
| 3 | ✅ OK | Manual Insert: kompatibel Android 9 dan 10+ | — |
| 4 | ✅ OK | Cleanup temp file setelah upload | — |
| 5 | ✅ OK | Premium overlay loading tersedia di kedua activity | — |
| 6 | ⚠️ Minor | Kalender: bulan yang tampil saat open langsung ke bulan saat ini — kalau data tahun berbeda dari tahun sekarang, posisi mungkin tidak tepat | Sudah di-handle dengan `if currentMonth < itemCount`, cukup aman |
| 7 | ℹ️ Info | Manual Insert upload menggunakan `is_manual_insert=1` flag di DB | Ini sudah sesuai untuk membedakan data manual vs data sistem |

---

## ✅ Checklist Validasi (Diisi oleh Kamu setelah cek di device)

### Kalender Operasional
- [ ] Halaman terbuka dan kalender tahun ini langsung tampil
- [ ] Navigasi prev/next bulan berfungsi (tombol & swipe)
- [ ] Spinner tahun berfungsi (ganti tahun → data berubah)
- [ ] Klik hari → bottom sheet edit muncul
- [ ] Edit status hari → kalender di-refresh
- [ ] Tombol "+" → dialog generate tahun baru → kalender ter-generate
- [ ] Tombol delete → warning → kalender tahun terhapus

### Insert Manual
- [ ] Tombol "Download Template" → file terdownload ke Downloads
- [ ] File Excel bisa dibuka dengan aplikasi spreadsheet
- [ ] Klik drop zone → file picker terbuka (filter Excel)
- [ ] Setelah pilih file → nama file tampil di drop zone
- [ ] Tombol "X" → selection ter-reset
- [ ] Tombol "Upload" → proses upload → dialog ringkasan muncul

---

## 📝 Catatan Validasi (Diisi oleh Kamu)

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** 📋 Menunggu validasi kamu
