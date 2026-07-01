# 👤 Cross-Check #02 — Profile & Account Settings

**Status:** 📋 Analisis Selesai — Menunggu Validasi Kamu
**Tanggal Analisis:** 2026-06-29
**File Terkait Index:** [CROSSCHECK_INDEX.md](./CROSSCHECK_INDEX.md)

---

## Ruang Lingkup

Modul ini mencakup semua yang berkaitan dengan akun pengguna setelah login:
1. **Lihat Profil** — Tampilkan info user yang sedang login
2. **Update Profil** — Edit username, email primer, email sekunder
3. **Upload Foto** — Ganti foto profil dari galeri
4. **Ubah Password** — Ganti password dari dialog
5. **Delete Account** — Soft delete akun (status → 'N')

---

## 🔧 API Side (vending_api)

> Semua endpoint di group **"Pengaturan Akun"** menggunakan `id_recnum_mur` sebagai identifier.
> Base path: `/account/{id_recnum_mur}/...`

| # | Endpoint | Method | Deskripsi | Status |
|---|----------|--------|-----------|--------|
| 1 | `/account/{id}` | GET | Ambil data profil user | ✅ Ada |
| 2 | `/account/{id}/update` | PUT | Update username + email | ✅ Ada |
| 3 | `/account/{id}/change-password` | PUT | Ganti password | ✅ Ada |
| 4 | `/account/{id}/upload-photo` | POST | Upload foto profil (multipart) | ✅ Ada |
| 5 | `/account/{id}/delete` | DELETE | Soft delete akun (status → 'N') | ✅ Ada |

### Catatan Detail API

**GET `/account/{id}`** — Return fields:
- `id_recnum_mur`, `username`, `email_primary`, `email_secondary`, `photo_url`
- ⚠️ **Tidak ada** `nohp`, `level_user`, `status_active` di response ini

**PUT `/account/{id}/update`** — Menerima:
- `username`, `email_primary`, `email_secondary`

**PUT `/account/{id}/change-password`** — Menerima:
- `new_password` (plain text — tidak ada validasi old password!)
- ⚠️ **Tidak ada validasi password lama** — siapapun yang punya session bisa ganti password tanpa konfirmasi

**POST `/account/{id}/upload-photo`** — Multipart:
- File disimpan di `/uploads/profiles/user_{id}.{ext}`
- Return: `photo_url` sebagai path, contoh: `/uploads/profiles/user_1.jpg`

**DELETE `/account/{id}/delete`** — Soft delete:
- Mengubah `status_active` → `'N'`
- Return ke Login dengan `FLAG_ACTIVITY_CLEAR_TASK`

---

## 📱 Android Side (CapstoneProject)

| Activity/Method | Fungsi | Endpoint Dipanggil | Status |
|-----------------|--------|-------------------|--------|
| `AccountSettingsActivity.java` | Container utama | — | ✅ Ada |
| `fetchProfileData()` | Load profil | `GET /account/{id}` | ✅ Sesuai |
| `updateProfile()` | Simpan perubahan | `PUT /account/{id}/update` | ✅ Sesuai |
| `showChangePasswordDialog()` | Dialog ganti password | `PUT /account/{id}/change-password` | ✅ Sesuai |
| `uploadPhoto()` | Upload foto galeri | `POST /account/{id}/upload-photo` | ✅ Sesuai |
| `confirmDeleteAccount()` | Dialog hapus akun | `DELETE /account/{id}/delete` | ✅ Sesuai |

### Detail Temuan Android

**Identifikasi User:**
- ✅ Menggunakan `sessionManager.getRecnumId()` → `id_recnum_mur` (integer)
- ✅ Ini sudah sesuai dengan parameter API

**Fetch Profile:**
- ✅ Field yang ditampilkan: `username`, `email_primary`, `email_secondary`, `photo_url`
- ✅ Foto dimuat via Glide: `BASE_URL + profile.photo_url`
- ✅ `BASE_URL` hardcoded: `"http://10.0.2.2:8000"` — konsisten dengan RetrofitClient

**Update Profile:**
- ✅ `UpdateProfileRequest` berisi `username`, `email_primary`, `email_secondary`
- ✅ Sesuai dengan schema API

**Change Password:**
- ✅ Dialog inflate dari `R.layout.dialog_change_password`
- ✅ Validasi: new password == confirm password (di sisi Android)
- ⚠️ Tidak ada input "password lama" — siapapun yang bisa buka halaman ini bisa ganti password
- ⚠️ Tidak ada validasi panjang minimum password

**Upload Photo:**
- ✅ Menggunakan `ActivityResultLauncher` (cara modern)
- ✅ File disalin ke cache dulu sebelum diupload (menghindari URI permission issue)
- ✅ Multipart upload berfungsi dengan `MediaType.parse("image/*")`

**Delete Account:**
- ✅ Dialog konfirmasi ada sebelum delete
- ✅ Setelah berhasil → redirect ke Login dengan clear stack
- ⚠️ Pesan dialog masih dalam Bahasa Inggris ("Are you sure you want to permanently delete your account?")

**Navigasi:**
- ⚠️ Tombol back menggunakan `btnMenu` (ID lama — bukan `btnBack`) → `finish()`
  - Ini **tidak crash** tapi tidak konsisten dengan naming convention modul lain yang sudah diupgrade

---

## 🔍 Temuan & Potensi Masalah

| # | Level | Temuan | Rekomendasi |
|---|-------|--------|-------------|
| 1 | ⚠️ Minor | Tidak ada validasi password lama saat ganti password | Tambahkan field "Password Lama" di dialog |
| 2 | ⚠️ Minor | Tombol back masih ID `btnMenu` (bukan `btnBack`) | Rename ID di XML & Java |
| 3 | ⚠️ Minor | Dialog delete & change password masih Bahasa Inggris | Translate ke Bahasa Indonesia |
| 4 | ⚠️ Minor | Tidak ada validasi panjang minimum password baru | Tambahkan validasi minimal 6 karakter |
| 5 | ℹ️ Info | `email_secondary` bisa null — perlu guard di setText | Sudah aman karena `setText(null)` → field kosong |
| 6 | ✅ OK | Semua 5 endpoint terhubung dengan benar | — |
| 7 | ✅ OK | Upload foto menggunakan cara modern (ActivityResultLauncher) | — |
| 8 | ✅ OK | Soft delete aman — data tidak dihapus dari DB | — |

---

## ✅ Checklist Validasi (Diisi oleh Kamu setelah cek di device)

### Lihat Profil
- [ ] Halaman Account Settings berhasil dibuka dari sidebar
- [ ] Username tampil sesuai akun yang login
- [ ] Email primer tampil dengan benar
- [ ] Email sekunder tampil (atau kosong jika tidak ada)
- [ ] Foto profil tampil (default icon jika belum ada foto)

### Update Profil
- [ ] Bisa edit username
- [ ] Bisa edit email primer
- [ ] Tombol "Save Changes" berhasil menyimpan
- [ ] Toast sukses muncul setelah save

### Upload Foto
- [ ] Klik icon kamera/edit foto → pilihan "Choose from Gallery" muncul
- [ ] Setelah pilih foto dari galeri, foto ter-upload
- [ ] Foto baru tampil di halaman profile

### Ganti Password
- [ ] Tombol "Change Password" membuka dialog
- [ ] Dialog punya field "New Password" dan "Confirm Password"
- [ ] Kalau tidak match → Toast pesan error muncul
- [ ] Kalau match → password berhasil diubah, bisa login dengan password baru

### Delete Account
- [ ] Tombol "Delete Account" membuka dialog konfirmasi
- [ ] Setelah konfirmasi → redirect ke Login
- [ ] Akun yang dihapus tidak bisa login lagi

---

## 📝 Catatan Validasi (Diisi oleh Kamu)

```
[Tanggal] — [Catatan dari kamu]
...
```

---

**Status Akhir:** 📋 Menunggu validasi kamu
