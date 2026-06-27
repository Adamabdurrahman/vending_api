# ⚙️ Cross-Check #03a — Operational: Kalender Operasional

**Status:** ⬜ Belum dimulai
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul Kalender Operasional mencakup:
1. **Lihat Kalender** — Tampilkan kalender per tahun & bulan
2. **Generate Tahun** — Buat kalender untuk tahun baru otomatis (Superadmin)
3. **Hapus Tahun** — Hapus seluruh data kalender satu tahun (Superadmin)
4. **Edit Hari** — Ubah tipe hari (kerja/libur nasional/cuti bersama/shutdown/Ramadan)

---

## 🔧 API Side (vending_api)

> *Akan diisi saat analisis dimulai*

| Endpoint | Method | Deskripsi | Ada di API? |
|----------|--------|-----------|-------------|
| `/api/v1/calendar` | GET | Get kalender per tahun | ⬜ |
| `/api/v1/calendar/generate` | POST | Generate tahun baru | ⬜ |
| `/api/v1/calendar/:year` | DELETE | Hapus tahun | ⬜ |
| `/api/v1/calendar/day/:date` | PUT/PATCH | Edit tipe hari | ⬜ |

---

## 📱 Android Side (CapstoneProject)

> *Akan diisi saat analisis dimulai*

| Activity/Fragment | Fungsi | Terhubung API? | Status |
|-------------------|--------|----------------|--------|
| `CalendarOperationalActivity.java` | Tampilan utama kalender | ⬜ | ⬜ |
| `CalendarMonthFragment.java` | Grid bulan (ViewPager2) | ⬜ | ⬜ |
| `EditDayBottomSheet.java` | Bottom sheet edit hari | ⬜ | ⬜ |

---

## 🔍 Temuan Analisis

> *Akan diisi oleh Antigravity saat analisis*

---

## ✅ Checklist Validasi (Diisi oleh Kamu)

### Lihat Kalender
- [ ] Kalender tampil dengan grid bulan yang benar
- [ ] Navigasi prev/next bulan berfungsi
- [ ] Spinner tahun tampil & bisa diganti
- [ ] Total hari kerja tampil di header
- [ ] Warna tiap hari sesuai tipe (kerja/libur/dll)
- [ ] Legend (keterangan warna) tampil

### Tambah / Generate Tahun (Superadmin)
- [ ] Tombol "+ Tahun" muncul (Superadmin)
- [ ] Dialog input tahun tampil
- [ ] Generate berhasil, data kalender muncul

### Hapus Tahun (Superadmin)
- [ ] Tombol hapus muncul (Superadmin)
- [ ] Dialog konfirmasi tampil
- [ ] Setelah hapus, kalender terhapus dari tampilan

### Edit Hari
- [ ] Klik satu hari membuka BottomSheet
- [ ] Bisa ganti tipe hari
- [ ] Setelah simpan, warna hari berubah sesuai

---

## 📝 Catatan Validasi

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** ⬜ Menunggu
