# Agent Guide — Bagian C: Functional Testing (F500 Capstone)

## Konteks Proyek

Dokumen ini adalah panduan untuk AI agent dalam memahami, mengisi, atau melengkapi **Bagian C (Functional Testing)** dari dokumen F500 Capstone Design di President University. Proyek yang dirujuk adalah:

> **"Driving SME Growth with AI-Based Seller Support Solutions for Selly"**
> Mahasiswa: Joseph Tedja Nugraha Wibawa (Auto Text RAG) & Jaya Iskandar MF (Personalized Marketing Campaign Generator)
> Pembimbing: Dr. Adhi Setyo Santoso, ST., MBA.

---

## Apa Itu Bagian C?

Bagian C adalah bagian **pengujian fungsional** dari dokumen F500. Tujuannya adalah membuktikan bahwa semua fitur yang didefinisikan dalam dokumen spesifikasi (F100 dan F200) telah diimplementasikan dan berjalan sesuai harapan.

Bagian C terdiri dari **4 sub-bab**:

| Sub-bab | Nama | Sumber Rujukan |
|---------|------|----------------|
| C.1 | Testing results of every function in the specification | Part C F100, Part C No.4 F200, Part D F200 |
| C.2 | Qualitative testing (questionnaire/UAT) | — |
| C.3 | Detail the test procedures carried out according to the design | — |
| C.4 | Procedures for the demo are created and verified | — |

---

## Sub-bab C.1 — Hasil Pengujian Setiap Fungsi

### Deskripsi
Agent harus membuat tabel pengujian untuk **setiap fungsi/fitur** yang ada dalam spesifikasi. Pengujian dibagi menjadi dua jenis:
- **Positive Testing**: Skenario ideal di mana input valid dan sistem berjalan normal.
- **Negative Testing**: Skenario di mana input tidak valid, tidak lengkap, atau tindakan dibatalkan, untuk memastikan sistem menangani error dengan benar.

### Struktur Tabel Wajib

Setiap tabel pengujian harus memiliki kolom berikut:

| Kolom | Penjelasan |
|-------|-----------|
| `Notes` | Jenis pengujian: `Positive Testing` atau `Negative Testing` |
| `Topic` | Nama aksi spesifik yang diuji (misal: "Log in", "Delete agent") |
| `Scenario` | Deskripsi singkat skenario yang dijalankan |
| `Test Steps` | Langkah-langkah bertimestamp (format: `(HH.MM.SS) Deskripsi aksi`) |
| `Expected Result` | Apa yang seharusnya terjadi di backend/sistem |
| `System Response` | Apa yang ditampilkan di UI/aplikasi kepada pengguna |
| `Date Tested` | Tanggal pengujian (format: `DD/MM/YYYY`) |
| `Status` | Hasil: `Success` atau `Fail` |

### Kategori Fitur yang Harus Diuji

Berikut adalah kategori fitur beserta jumlah minimum test case dan pola pengujian yang diharapkan:

#### i. User Authentication
- Register (positive: data valid → navigasi ke homepage)
- Register (negative: data tidak lengkap/invalid → error message)
- Log in (positive: kredensial valid → navigasi ke homepage)
- Log in (negative: kredensial invalid → error message, tetap di halaman login)
- Log out (positive: berhasil logout → navigasi ke login page)
- Session Refresh (positive: buka app tanpa logout → langsung ke homepage)
- Session Refresh (negative: buka app setelah logout → tetap di login page)

#### ii. Business Knowledge Base Input
- Generate default knowledge base (positive)
- Submit knowledge base valid (positive: data tersimpan, KB pertama otomatis diaktifkan)
- Submit knowledge base tidak lengkap (negative: validasi sisi klien, error per field)

#### iii. Business Knowledge Base Management
- View list knowledge base (positive)
- View detail knowledge base (positive: nama + list chunks tampil)
- Activate knowledge base (positive: item aktif naik ke atas list)
- Delete knowledge base — konfirmasi (positive)
- Delete knowledge base — batalkan di dialog (negative: item tetap ada)

#### iv. Knowledge Base Chunks Management
- View detail chunk (positive)
- Edit chunk — data valid (positive: konten terupdate)
- Edit chunk — konten dikosongkan (negative: error "Chunk content cannot be empty")
- Delete chunk (positive: item terhapus dari list)

#### v. Knowledge Base Chunks Input
- Buat chunk baru — konten valid (positive)
- Buat chunk baru — konten kosong (negative: error "Chunk content cannot be empty")

#### vi. Agent Input
- Generate default agent (positive)
- Submit agent valid (positive)
- Submit agent tidak lengkap (negative: validasi field Agent name & Agent content)

#### vii. Agent Management
- View list agent (positive)
- View detail agent (positive: nama, command, temperature tampil)
- Activate agent (positive: item aktif naik ke atas)
- Delete agent — konfirmasi (positive)
- Delete agent — batalkan di dialog (negative: item tetap ada)

#### viii. Keyboard Interface Usage
- Abort instalasi keyboard (negative: keyboard sebelumnya tetap aktif)
- Pilih keyboard lain saat instalasi (negative: keyboard yang dipilih menjadi aktif)
- Install Selly keyboard (positive: Selly keyboard tampil di text input)
- Query ke RAG via keyboard (positive: hasil relevan muncul dalam hitungan detik, bisa disalin & dikirim)

#### ix. Invoice Analysis Mechanism
- Buat invoice valid (positive)
- Buat invoice tidak valid — nomor HP non-standar atau products kosong (negative: error message)
- View list invoice (positive)
- View detail invoice (positive)
- Update/edit invoice (positive)
- Delete invoice (positive)
- Conduct clustering — invoice ≥ 3 (positive: navigasi ke cluster result screen)
- Conduct clustering — invoice < 3 (negative: error "no. of invoices must be >3")

#### x. Automated Marketing Campaign
- Generate AI-suggested offer message (positive: field terisi otomatis dalam <5 detik)
- Edit offer message secara manual (positive: overwrite teks)
- Send offer message via WhatsApp (positive: redirect ke WhatsApp dengan konten ter-copy)

---

### Referensi Flowchart (Part C No.4 F200)

Setelah semua tabel pengujian di atas selesai, agent harus menyertakan **flowchart sistem** dan menyatakan bahwa semua skenario pada flowchart sudah diuji. Flowchart mencakup dua alur utama:

1. **Alur RAG**: Login → Cek KB → Buka Sosmed → Copy pertanyaan customer → Tekan "Ask RAG" → Terima jawaban → Modifikasi jika perlu → Kirim ke customer
2. **Alur Marketing Campaign**: Login → Cek Campaign → Otorisasi Invoice → Accumulate Invoice → Clustering → Generate Pesan → Kirim via WhatsApp

---

### Pengujian Spesifikasi Kinerja (Part D F200)

Selain test case per fitur, agent wajib menyertakan pengujian untuk **metrik kinerja non-fungsional** berikut:

#### 1. Response Time RAG
- **Target**: Sistem menghasilkan respons dalam <40 detik
- **Cara uji**: Lakukan query ke RAG system, catat waktu dari menekan tombol "Ask RAG" hingga hasil muncul
- **Format tabel**: Sama seperti test case biasa, tambahkan catatan durasi aktual di kolom System Response atau Notes
- **Bukti**: Sertakan link rekaman video Google Drive

#### 2. Akurasi AI (RAG Accuracy)
- **Target**: ≥85% akurasi berdasarkan manual review, dengan knowledge base yang memiliki >10 chunks
- **Cara uji**: Siapkan knowledge base dengan ≥12 chunks, buat daftar pertanyaan mencakup semua chunk + 1 pertanyaan di luar konteks, evaluasi apakah jawaban RAG sesuai dengan chunk yang dituju
- **Format tabel tambahan** (di luar tabel test case standar):

  | No | Targeted Chunk | Question | RAG Response | Status |
  |----|---------------|----------|-------------|--------|
  | 1  | [Judul chunk] | [Pertanyaan] | [Ringkasan jawaban RAG] | Success/Fail |
  | ... | | | | |
  | N+1 | None (out of context) | [Pertanyaan tidak relevan] | [RAG menolak/menjawab tidak tahu] | Success/Fail |

- **Bukti**: Sertakan link folder Google Drive berisi rekaman semua instance pengujian

#### 3. Kecepatan Generate Marketing Campaign
- **Target**: AI-generated responses dalam <5 detik
- **Cara uji**: Klik tombol "Generate AI offer", catat waktu hingga field terisi
- **Bukti**: Catat durasi aktual di kolom System Response

#### 4. System Uptime & Reliability
- **Target**: Berjalan tanpa crash mayor selama 1 jam continuous testing
- **Cara uji**: Jalankan full-flow aplikasi selama 1 jam secara berurutan (Auth → Agent/KB management → RAG → Input 50+ invoice → Clustering → Campaign)
- **Format tabel**: Satu tabel dengan langkah-langkah bertimestamp per fase

---

## Sub-bab C.2 — Qualitative Testing

### Deskripsi
Berisi hasil **User Acceptance Testing (UAT)** yang dilakukan bersama pengguna nyata atau stakeholder. UAT bertujuan memvalidasi bahwa produk sesuai dengan kebutuhan pengguna di dunia nyata.

### Yang Harus Ada

1. **Penjelasan singkat UAT** — definisi UAT, tujuan, dan konteks pelaksanaan (dilakukan di mana, bersama siapa)

2. **Tabel UAT Fitur** dengan format:

   | No | Use Cases / Processes | Acknowledged by | Test date | Status |
   |----|-----------------------|----------------|-----------|--------|
   | 1  | [Nama fitur/proses]   | [Nama reviewer] | DD/MM/YY | Success |

   Di bawah setiap baris, tambahkan sub-baris **Parameters** yang merinci kapabilitas spesifik yang dikonfirmasi (contoh: "Seller can register with a new email address").

3. **Tabel Key Points & Feedback Kualitatif** dengan format:

   | Key Points | Quotes and Analysis |
   |-----------|---------------------|
   | [Nama fitur] | [Kutipan/parafrase komentar peserta UAT + analisis singkat] |

4. **Tanda tangan dan tanggal** dari pihak yang mengakui hasil UAT

### Tips untuk Agent
- Pastikan setiap fitur dari spesifikasi F200 tercakup dalam tabel UAT
- Feedback kualitatif harus mencerminkan respons nyata pengguna, bukan hanya konfirmasi teknis
- Jika ada feedback/saran dari pengguna yang sudah diimplementasikan, sebutkan hasilnya

---

## Sub-bab C.3 — Detail Prosedur Pengujian

### Deskripsi
Sub-bab ini menyatakan bahwa prosedur pengujian telah dilakukan sesuai desain.

### Format yang Diterima
Pernyataan singkat yang mengacu pada tabel pengujian di C.1, contoh:

> "Prosedur pengujian rinci telah dilaksanakan dan didokumentasikan dalam setiap tabel pengujian pada sub-bab C.1 di atas. Setiap tabel mencakup langkah-langkah bertimestamp, hasil yang diharapkan, respons sistem aktual, tanggal pengujian, dan status hasil."

---

## Sub-bab C.4 — Prosedur Demo

### Deskripsi
Sub-bab ini mengonfirmasi bahwa prosedur demo telah dibuat dan diverifikasi.

### Format yang Diterima
Pernyataan singkat yang mengacu pada tabel pengujian di C.1, contoh:

> "Prosedur demo telah dibuat dan diverifikasi melalui setiap tabel pengujian pada sub-bab C.1. Setiap skenario pengujian berfungsi sekaligus sebagai skrip demo yang dapat direplikasi."

---

## Aturan Umum untuk Agent

### Format Tabel
- Gunakan tabel Markdown dengan kolom yang konsisten
- Setiap test case berada di baris terpisah
- Timestamps di Test Steps menggunakan format `(HH.MM.SS)` dan menggambarkan aksi secara kronologis
- Tidak boleh ada test case tanpa kolom `Status`

### Urutan Pengisian
1. Mulai dari C.1 — isi semua kategori fitur secara berurutan (i sampai x)
2. Tambahkan tabel akurasi RAG setelah test case keyboard interface
3. Tambahkan tabel pengujian kinerja (response time, uptime) setelah semua test case fungsional
4. Lanjutkan ke C.2 dengan tabel UAT dan key points
5. Tutup dengan C.3 dan C.4 sebagai pernyataan konfirmasi

### Konsistensi yang Harus Dijaga
- Nama fitur harus konsisten antara tabel pengujian dan tabel UAT
- Tanggal pengujian harus realistis dan kronologis
- Status `Success` hanya diisi jika System Response sesuai dengan Expected Result
- Jika ada test case yang `Fail`, harus ada penjelasan di kolom Notes atau paragraf terpisah

### Bukti Tambahan yang Perlu Dirujuk
Untuk pengujian kinerja, agent harus menyertakan atau merujuk ke:
- Link rekaman video (Google Drive atau platform lain)
- Screenshot log server (terutama untuk response time dan uptime)
- Screenshot database (terutama untuk keamanan — hashed password)

---

## Checklist Kelengkapan Bagian C

Gunakan checklist ini untuk memastikan Bagian C sudah lengkap sebelum finalisasi:

- [ ] C.1.i — Tabel User Authentication (min. 5 test case)
- [ ] C.1.ii — Tabel Knowledge Base Input (min. 3 test case)
- [ ] C.1.iii — Tabel Knowledge Base Management (min. 5 test case)
- [ ] C.1.iv — Tabel Chunks Management (min. 4 test case)
- [ ] C.1.v — Tabel Chunks Input (min. 2 test case)
- [ ] C.1.vi — Tabel Agent Input (min. 3 test case)
- [ ] C.1.vii — Tabel Agent Management (min. 5 test case)
- [ ] C.1.viii — Tabel Keyboard Interface (min. 4 test case, termasuk RAG query)
- [ ] C.1.ix — Tabel Invoice & Clustering (min. 8 test case)
- [ ] C.1.x — Tabel Marketing Campaign (min. 3 test case)
- [ ] C.1b — Flowchart sistem disertakan + pernyataan semua skenario sudah diuji
- [ ] C.1c — Tabel Response Time RAG + link bukti video
- [ ] C.1c — Tabel Akurasi RAG (min. 13 query, 12 chunks + 1 out of context) + link bukti
- [ ] C.1c — Tabel Kecepatan Campaign Generation
- [ ] C.1c — Tabel System Uptime 1 jam
- [ ] C.2 — Narasi UAT (lokasi, tanggal, peserta)
- [ ] C.2 — Tabel UAT Fitur (min. 8 fitur, ditandatangani stakeholder)
- [ ] C.2 — Tabel Key Points & Quotes
- [ ] C.2 — Tanda tangan dan tanggal pengakuan
- [ ] C.3 — Pernyataan prosedur pengujian
- [ ] C.4 — Pernyataan prosedur demo