# Panduan Pengisian Bagian D — F500 (Testing Other Specifications)

> Dokumen ini adalah panduan pembelajaran (bukan bagian dari laporan resmi) yang menjelaskan
> apa yang **seharusnya** diisi pada Bagian D dokumen F500, beserta insight dari hasil analisa
> terhadap dokumen capstone "Driving SME Growth with AI-Based Seller Support Solutions for
> Selly". Tujuannya agar AI/penyusun memahami standar pengisian yang benar dan dapat
> mengidentifikasi gap pada dokumen yang sudah dibuat.

---

## 1. Posisi Bagian D dalam Struktur F500

Berdasarkan outline resmi (lihat halaman "PART 5 — TESTING (F500)"), Bagian D terdiri dari **2 sub-bab**:

```
D. TESTING OTHER SPECIFICATIONS:
   1. Non-functional specifications such as size, weight, etc.,
      that are included in the document (PART C NO. 5 F200)
   2. A photo/recording of the test is shown in the document
```

Bagian D **bukan tempat untuk mengulang functional testing** (itu sudah ada di Bagian C).
Bagian D fokus pada **karakteristik kualitas sistem** yang tidak berupa "fungsi" tapi tetap
menjadi syarat penerimaan produk — biasanya berbentuk *Non-Functional Requirements (NFR)*.

---

## 2. Sub-bab D.1 — Non-Functional Specifications

### 2.1 Apa yang harus dijadikan acuan

Isi sub-bab ini **wajib menurunkan kembali** apa yang sudah dituliskan di:
- **F200 Part C No. 5** (non-functional requirement / constraint yang didefinisikan saat desain)
- **F200/F100 Part B — Constraints** (lihat Bagian B dokumen ini): Technical, Privacy, Adoption, Connectivity

Artinya: **setiap constraint yang disebutkan di Bagian B HARUS punya bukti pengujian di Bagian D.**
Tidak boleh ada constraint yang disebutkan di awal tapi tidak pernah diuji di akhir — ini adalah
inkonsistensi yang biasanya jadi catatan revisi dosen pembimbing.

### 2.2 Daftar Non-Functional yang Lazim Diuji

| Kategori NFR | Pertanyaan yang Dijawab | Contoh Metode Pengujian | Contoh Bukti |
|---|---|---|---|
| **Performance / Response Time** | Seberapa cepat sistem merespons? | Stopwatch manual / log durasi request-response | Video rekaman waktu, atau log dengan kolom durasi (ms/detik) |
| **Reliability / Uptime** | Apakah sistem stabil dalam pemakaian lama? | Continuous run test (mis. 1 jam non-stop) | Log tanpa error, screenshot monitoring |
| **Security** | Apakah data sensitif (password, dsb) terlindungi? | Inspeksi database, cek metode enkripsi | Screenshot DB dengan hash, bukan plaintext |
| **Scalability / Data Volume** | Apakah sistem tetap berjalan saat data banyak? | Uji dengan jumlah data besar (mis. 50+ invoice) | Log/screenshot hasil dengan jumlah data tercatat |
| **Technical Constraint (low-end device)** | Apakah aplikasi tetap lancar di device spesifikasi rendah? | Uji di device dengan RAM/CPU rendah | Spesifikasi device + screenshot/video saat dijalankan |
| **Connectivity Constraint** | Bagaimana sistem berperilaku saat koneksi lemah/putus? | Uji dengan throttling jaringan / mode pesawat | Screenshot pesan error/fallback behavior |
| **Privacy / Data Protection Compliance** | Apakah pengolahan data sesuai regulasi (mis. UU PDP Indonesia)? | Audit kebijakan data, enkripsi data pribadi | Dokumentasi kebijakan privasi + bukti teknis (hashing/encryption) |
| **Usability/Adoption (jika belum dibahas di UAT)** | Apakah mudah dipelajari user baru tanpa training panjang? | First-time-user test / time-to-complete-task | Rekaman onboarding user baru |
| **Size / Storage Footprint** | Seberapa besar aplikasi (APK size, storage usage)? | Cek ukuran file instalasi & penggunaan storage | Screenshot info aplikasi di device |

> **Catatan:** Tidak semua baris di atas wajib ada — disesuaikan dengan constraint yang memang
> disebutkan di Bagian B. Tapi **semua constraint di Bagian B wajib punya pasangan di tabel ini.**

### 2.3 Format Tabel yang Disarankan untuk Setiap Item NFR

Gunakan format konsisten seperti pada Bagian C (functional testing), agar mudah dibandingkan:

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | (nama NFR, mis. "Response Time") | (deskripsi singkat skenario uji) | (langkah uji, boleh dengan timestamp) | (target kuantitatif, mis. "<40 detik") | (hasil aktual yang terukur) | (tanggal) | Success/Fail |

Jika NFR tidak berbentuk skenario step-by-step (misalnya Security atau Uptime), boleh memakai
format naratif + bukti visual, **tapi tetap harus menyebutkan**:
1. Nama spesifikasi yang diuji
2. Target/kriteria keberhasilan (angka atau kondisi spesifik)
3. Hasil aktual
4. Status (Success/Fail)
5. Tautan/bukti pendukung

---

## 3. Sub-bab D.2 — Photo/Recording of the Test

### 3.1 Tujuan
Membuktikan bahwa pengujian non-functional benar-benar dilakukan, bukan klaim tanpa bukti.

### 3.2 Syarat Bukti yang Valid

| Syarat | Penjelasan |
|---|---|
| **Dapat diverifikasi** | Link Google Drive/foto harus bisa diakses, tidak private/expired |
| **Timestamp jelas** | Screenshot/log harus menunjukkan waktu pengujian (untuk korelasi dengan tabel di D.1) |
| **Relevan dengan klaim** | Misalnya jika klaim "response time < 40 detik", bukti harus menunjukkan **durasi**, bukan hanya status code 200 |
| **Sumber teridentifikasi** | Jika berupa data dari database/log, sertakan konteks (nama tabel, endpoint, dsb) |

### 3.3 Bentuk Bukti yang Umum Dipakai
- Screenshot tabel database (mis. untuk Security/hashing)
- Screenshot log API/server (mis. untuk response time — **harus ada durasi, bukan cuma timestamp request**)
- Video rekaman proses end-to-end (lebih kuat dari screenshot karena menunjukkan waktu berjalan nyata)
- Tangkapan layar device dengan spesifikasi rendah saat menjalankan aplikasi (untuk technical constraint)

---

## 4. Insight dari Dokumen Capstone yang Sudah Dianalisa

Berikut pemetaan antara apa yang **seharusnya** ada (sesuai outline) vs apa yang **sudah** ada
di dokumen "Selly" yang sudah dibuat:

| Item yang Diharapkan | Status di Dokumen | Catatan/Gap |
|---|---|---|
| Security (password hashing) | ✅ Ada | Bukti kuat: screenshot DB dengan hash bcrypt (`$2a$10$...`) |
| Data transaction / response time | ⚠️ Ada tapi lemah | Log API hanya menampilkan **timestamp request**, bukan **durasi proses**. Judul "logged response time" belum benar-benar terbukti dengan angka durasi |
| Technical constraint (low-end device) | ❌ Tidak ada | Disebutkan di Bagian B sebagai constraint, tapi tidak ada bukti pengujian di Bagian D |
| Connectivity constraint (internet requirement) | ❌ Tidak ada | Sama seperti di atas — disebut di constraint, tidak diuji |
| Privacy constraint (regulasi data Indonesia) | ⚠️ Implisit saja | Hanya terwakili lewat password hashing, belum membahas kepatuhan regulasi secara eksplisit |
| Adoption constraint (mudah digunakan) | ⚠️ Dibahas di Bagian C (UAT), bukan D | Sebaiknya tetap direferensikan singkat di D agar traceability constraint → testing lengkap |
| Penomoran sub-bab D.1 / D.2 | ❌ Tidak eksplisit | Heading "Non-functional specifications" dan "Photo/recording" tidak ditulis sebagai sub-judul terpisah, langsung lompat ke contoh kasus |
| Size/Storage footprint | ❌ Tidak ada | Wajar untuk software, tapi sebaiknya tetap dijelaskan singkat (atau ditandai N/A dengan alasan) agar sesuai kalimat outline "size, weight, etc." |

### Kesimpulan Insight
Dokumen yang sudah dibuat **kuat dari sisi bukti visual** (screenshot nyata, bukan mock-up),
tetapi **lemah dari sisi traceability** — yaitu memastikan semua constraint yang dijanjikan di
Bagian B benar-benar punya bukti uji yang berpadanan di Bagian D, dan strukturnya mengikuti
penomoran sesuai outline.

---

## 5. Checklist Sebelum Menganggap Bagian D Selesai

- [ ] Setiap constraint di Bagian B (Technical, Privacy, Adoption, Connectivity) punya bukti uji di D.1
- [ ] Setiap NFR punya kriteria kuantitatif/kualitatif yang jelas (bukan hanya "berhasil")
- [ ] Bukti response time menunjukkan **durasi**, bukan hanya status/timestamp request
- [ ] Sub-bab D.1 dan D.2 ditulis sebagai heading terpisah dan eksplisit
- [ ] Semua link bukti (Google Drive, dsb) dapat diakses publik/oleh pembimbing
- [ ] Tidak ada duplikasi konten dari Bagian C (functional testing) ke Bagian D
