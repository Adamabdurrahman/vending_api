# Panduan Pengisian Bagian B — F500 Document (Capstone Design Implementation)

> **Catatan untuk AI Agent yang membaca file ini:**
> Dokumen ini **BUKAN** isi final Bagian B. Ini adalah instruksi kerja. Tugasmu:
> 1. Pelajari panduan ini secara penuh.
> 2. Eksplorasi project sesuai langkah di Bagian 3.
> 3. Tulis isi final "Bagian B" mengikuti struktur & format di Bagian 4–5.
> 4. Jika ada ketidaksesuaian antara dokumen rencana (plan) dan kode aktual, **laporkan ke user, jangan ditulis seolah konsisten.**

---

## 1. Konteks Project

Project capstone ini terdiri dari dua repository:

| Komponen | Peran | Lokasi |
|---|---|---|
| **Otak** (Backend / API) | Logika bisnis, API, database, kemungkinan integrasi hardware/payment | `C:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api` |
| **Layar** (Frontend / Display) | Antarmuka yang dilihat & dipakai pengguna (Android) | `C:\Users\isyaa\AndroidStudioProjects\CapstoneProject` |

Catatan: nama folder backend (`vending_api`) mengindikasikan sistem ini berkaitan dengan **vending machine** — tapi domain pasti, fitur, dan detail bisnisnya **harus dikonfirmasi dari dokumen plan/kode**, bukan diasumsikan begitu saja dari nama folder.

Selain dua repo di atas, ada folder **`plan`** yang berisi kumpulan file markdown hasil diskusi sebelumnya dengan AI lain — kemungkinan besar sudah berisi draf setara F100/F200 (problem statement, main functionality, constraints, tech stack, dst). **Lokasi file-nya tidak diketahui pasti** — agent wajib mencarinya dulu, jangan menyimpulkan sendiri dari kode sebelum dokumen ini dicek.

---

## 2. Prioritas Sumber Informasi

Jangan mengarang isi Bagian B. Ikuti urutan prioritas ini:

1. **Dokumen plan yang sudah ada** (folder `plan`, atau file apa pun yang namanya memuat kata seperti `F100`, `F200`, `requirement`, `spec`, `prd`). Ini sumber utama — kemungkinan besar sudah berisi jawaban untuk sebagian besar sub-bab Bagian B.
2. **Kode aktual** di kedua repo — dipakai untuk memverifikasi dan melengkapi bagian yang belum tercakup di dokumen plan, atau sebagai sumber utama jika dokumen plan tidak ditemukan untuk topik tertentu.
3. **Cross-check** dokumen plan vs implementasi aktual. Jika plan menyebut fitur X tapi tidak ditemukan di kode (atau sebaliknya, ada fitur di kode yang tidak pernah direncanakan), **catat sebagai temuan terbuka**, jangan ditulis seakan semuanya sudah konsisten dan selesai.

---

## 3. Langkah Eksplorasi (Wajib Dilakukan Sebelum Menulis Apa Pun)

1. **Cari dokumen plan**: scan folder `plan` (dan subfolder-nya) untuk semua file `.md`. Baca isinya, identifikasi mana yang relevan untuk: main functionality, tipe user/actor, constraints, tech stack development, tech stack/infra operasional.
2. **Eksplorasi `vending_api` (Otak)**:
   - Baca `README.md` jika ada.
   - Baca file dependency (`package.json`, `requirements.txt`, `pom.xml`, dsb.) → catat bahasa, framework, versi.
   - Baca folder routes/controllers/endpoints → catat **semua fungsi/endpoint yang benar-benar diimplementasikan**, bukan yang direncanakan saja.
   - Baca file konfigurasi deployment (`Dockerfile`, `docker-compose.yml`, `.env.example`, `render.yaml`, `vercel.json`, dsb.) → ini sumber utama untuk Bagian B.5 (Operational Environment).
   - Cek integrasi eksternal: payment gateway, komunikasi serial/IoT ke mesin vending, database yang dipakai, dsb.
3. **Eksplorasi `CapstoneProject` (Layar)**:
   - Baca `README.md` jika ada.
   - Baca `app/build.gradle` (atau `.gradle.kts`) → catat dependency, `minSdkVersion`, `targetSdkVersion`.
   - Baca `AndroidManifest.xml` → catat permission yang diminta (indikasi fitur: kamera, NFC, Bluetooth, lokasi, dsb.).
   - Daftarkan semua Activity/Fragment/Screen yang ada → ini calon daftar use case dari sisi user.
4. **Cross-check fitur**: setiap fitur yang akan ditulis di B.1 (Main Functionality) harus punya jejak di **kedua sisi** — ada endpoint di backend **dan** ada screen/UI di frontend. Kalau cuma ada di salah satu sisi, tandai sebagai "belum lengkap/in-progress", jangan diklaim selesai.

---

## 4. Struktur & Kebutuhan Konten Tiap Sub-bab

Bagian B mengikuti struktur berikut (sama seperti F200 Part B):

```
B. RESTATE THE SPECIFICATIONS STATED IN THE F-200 DOCUMENT
   1. Main Functionality
   2. User Characteristics
   3. Constraints
   4. Product Development Environment
   5. Product Operational Environment
```

### B.1 — Main Functionality

**Definisi:** Daftar fungsi/fitur utama sistem, sesuai yang dispesifikasikan di F200.

**Sumber:** Dokumen plan (utama) → diverifikasi dengan endpoint backend + screen frontend yang benar-benar ada.

**Pertanyaan kunci yang harus terjawab:**
- Apa saja fitur inti yang ditawarkan sistem ke setiap tipe user?
- Apakah setiap fitur di sini akan benar-benar diuji nanti di Bagian C (Functional Testing)? (Lihat Quality Check di Bagian 6 — ini WAJIB selaras.)

**Format:**
```markdown
### 1. Main Functionality

Fungsi utama sistem ini adalah:

- **[Nama Fitur]**: [Deskripsi singkat 1-2 kalimat, jelaskan apa yang dilakukan & untuk siapa]
- **[Nama Fitur]**: [...]
```

---

### B.2 — User Characteristics

**Definisi:** Tipe-tipe user/aktor yang berinteraksi dengan sistem, beserta profil mereka (akses, skill, pengalaman, dsb).

**Sumber:** Dokumen plan + inferensi dari kode (role/permission di backend, layar/login type di frontend).

**Pertanyaan kunci:**
- Ada berapa tipe user/aktor? (contoh untuk sistem vending: Customer/pembeli, Admin/operator mesin, mungkin teknisi)
- Untuk tiap tipe: apa tanggung jawabnya, hak aksesnya, level pendidikan/skill yang diasumsikan, pengalaman, dan jenis training yang dibutuhkan?

**Format (contoh konkret, isi sesuai temuan aktual):**

```markdown
### 2. User Characteristics

Sistem ini melayani [N] tipe user utama: [Tipe A], [Tipe B], dst.

- **[Tipe A, misal: Admin/Operator]**: [deskripsi peran, tanggung jawab, akses]
- **[Tipe B, misal: Customer]**: [deskripsi peran, tanggung jawab, akses]

| Users | Responsibility | Access rights | Education Levels | Skill Levels | Experience | Type of Training |
|---|---|---|---|---|---|---|
| [Tipe A] | [tanggung jawab utama] | [Full access / Limited / No access] | [level pendidikan minimum yang diasumsikan] | [basic/moderate/advanced digital literacy] | [none/moderate/expert] | [jenis training, atau "N/A"] |
| [Tipe B] | [tanggung jawab utama] | [akses] | [pendidikan] | [skill] | [pengalaman] | [training] |
```

---

### B.3 — Constraints

**Definisi:** Batasan-batasan yang harus dipenuhi sistem.

**Sumber:** Dokumen plan + inferensi dari kode (misal: ada library payment tertentu → ada constraint kepatuhan; ada hardware fisik → ada constraint ukuran/daya).

**Kategori yang WAJIB dipertimbangkan** (cek satu per satu, isi yang relevan saja — jangan dipaksakan semua kalau tidak relevan, tapi jangan dilewatkan begitu saja tanpa dicek):
- **Technical** — keterbatasan device/hardware tempat sistem berjalan.
- **Privacy/Security** — kepatuhan data (misal regulasi data Indonesia, keamanan transaksi).
- **Adoption/Usability** — seberapa mudah dipakai oleh target user.
- **Connectivity** — kebutuhan internet/koneksi real-time.
- **Hardware/Physical** *(khusus relevan untuk sistem fisik seperti vending machine)* — dimensi, daya listrik, ketahanan terhadap lingkungan, kompatibilitas mekanisme dispenser/sensor/payment terminal.
- **Cost** *(pertimbangkan jika ada API berbayar, biaya komponen hardware, dsb — sering terlewat tapi penting untuk project nyata)*.
- **Regulatory** *(jika ada, misal terkait produk yang dijual, standar kelistrikan, dsb)*.

**Format:**
```markdown
### 3. Constraints

Berikut adalah batasan-batasan dari sistem:

- **[Kategori] Constraints**: [deskripsi batasan konkret, jangan generik — kaitkan dengan keputusan desain/implementasi nyata]
- **[Kategori] Constraints**: [...]
```

---

### B.4 — Product Development Environment

**Definisi:** Hardware, software, dan koneksi yang dipakai **saat membangun** sistem (lingkungan developer).

**Sumber:** File dependency & konfigurasi di kedua repo (lihat langkah eksplorasi poin 2 & 3). **Setiap teknologi yang disebut harus bisa dibuktikan ada di file dependency/config aktual** — jangan menulis tech stack yang "kedengarannya cocok" tapi tidak ada bukti pemakaiannya di kode.

**Format:**
```markdown
### 4. Product Development Environment

a. **Hardware**: [dev workstation, perangkat Android untuk testing, board/mikrokontroler jika ada, dsb — hanya yang benar-benar dipakai]
b. **Software**: [bahasa, framework, library inti — diambil dari package.json/requirements.txt/build.gradle aktual]
c. **Connection**: [kebutuhan koneksi saat development, misal API testing, emulator, dsb]
```

---

### B.5 — Product Operational Environment

**Definisi:** Hardware, software, dan koneksi yang dipakai **saat sistem berjalan di produksi/digunakan end-user**.

⚠️ **Wajib diperhatikan**: Bagian ini harus **sedetail B.4**, jangan jadi generik/template kosong hanya karena B.4 sudah detail. Cek konfigurasi deployment aktual (Dockerfile, hosting platform, dsb) dan hardware fisik aktual (mesin vending, payment terminal, dsb) — jangan tulis kalimat umum seperti "cloud server" tanpa menyebut platform/spesifikasi nyata jika informasinya tersedia.

**Sumber:** File deployment config (`Dockerfile`, `render.yaml`, `vercel.json`, dsb), dan spesifikasi hardware fisik vending machine jika disebut di dokumen plan.

**Format:**
```markdown
### 5. Product Operational Environment

a. **Hardware**: [hardware fisik di produksi — mesin vending, sensor, payment terminal, server/cloud yang menghosting backend]
b. **Software**: [platform hosting backend aktual, cara distribusi app Android (APK/Play Store/instalasi langsung)]
c. **Connection**: [kebutuhan koneksi saat operasional — jenis koneksi internet mesin vending, requirement uptime server, dsb]
```

---

## 5. Format Output Final (Gabungan)

Setelah semua sub-bab terisi, struktur akhir Bagian B harus seperti ini di dalam dokumen F500:

```markdown
## B. RESTATE THE SPECIFICATIONS STATED IN THE F-200 DOCUMENT

### 1. Main Functionality
...

### 2. User Characteristics
...

### 3. Constraints
...

### 4. Product Development Environment
...

### 5. Product Operational Environment
...
```

---

## 6. Checklist Kualitas — Cek Sebelum Dianggap Selesai

Sebelum final, agent harus mengecek ulang poin-poin ini (poin ini didasarkan pada gap yang sering ditemukan di dokumen F500 sejenis):

- [ ] **Traceability B.1 ↔ Bagian C**: Setiap fitur di Main Functionality nantinya harus muncul di pengujian fungsional (Bagian C). Jika ada fitur di kode yang sangat substansial (misal authentication, invoice/transaksi) tapi tidak disebut di B.1, tambahkan — jangan biarkan testing "membahas sesuatu yang tidak pernah disebut sebagai fungsi utama".
- [ ] **Konsistensi detail B.4 vs B.5**: Level kedetailan operational environment tidak boleh jauh lebih tipis dibanding development environment.
- [ ] **Tech stack berbasis bukti**: Setiap teknologi yang disebut di B.4/B.5 harus bisa ditunjuk file/baris konfigurasi aktualnya, bukan asumsi.
- [ ] **Constraint berbasis keputusan desain nyata**: Constraint yang ditulis sebaiknya terkait langsung dengan keputusan implementasi yang benar-benar diambil (misal: kenapa pakai library X, kenapa minSdkVersion sekian), bukan kalimat generik yang bisa berlaku untuk app apa saja.
- [ ] **Tidak ada klaim yang bertentangan dengan kode**: Jika dokumen plan menyebut sesuatu yang ternyata tidak ada di kode (atau sebaliknya), ini sudah dicatat & dilaporkan ke user, bukan disembunyikan/diselaraskan secara sepihak.
