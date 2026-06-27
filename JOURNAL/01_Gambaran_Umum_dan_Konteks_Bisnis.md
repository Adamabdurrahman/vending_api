# 01 — Gambaran Umum dan Konteks Bisnis

## 1. Latar Belakang

PT GS Battery merupakan perusahaan manufaktur baterai yang beroperasi di Indonesia. Sebagai bagian dari kewajiban perusahaan terhadap kesejahteraan karyawan, PT GS Battery menyediakan susu UHT secara gratis kepada seluruh karyawan sebanyak dua kali dalam setiap shift kerja. Kewajiban ini merupakan bentuk pemenuhan hak karyawan (*employee welfare*) — bukan transaksi jual beli — di mana perusahaan bertanggung jawab penuh atas pengadaan, penyimpanan, dan distribusi susu kepada seluruh tenaga kerja yang berhak.

Pemenuhan kewajiban ini dilaksanakan melalui sebuah vending machine yang ditempatkan di area karyawan. Setiap karyawan dapat mengambil jatah susu mereka secara mandiri pada waktu distribusi yang telah ditentukan. Operasional distribusi ini terbagi dalam tiga sesi harian yang disebut sebagai *shift*, yaitu Shift 1, Shift 2, dan Shift 3. Setiap pengambilan susu oleh karyawan tercatat secara otomatis oleh sistem vending machine ke dalam basis data perusahaan.

Pengelolaan stok vending machine selama ini dilakukan secara manual berdasarkan estimasi kasar operator. Pendekatan ini membawa konsekuensi ganda: di satu sisi terjadi kelebihan stok (*overstock*) yang mengakibatkan pemborosan biaya pengadaan dan risiko produk kedaluwarsa, di sisi lain terjadi kekurangan stok (*stockout*) yang berarti karyawan tidak dapat mengambil jatah susu yang menjadi hak mereka — suatu kondisi yang berpotensi melanggar kewajiban perusahaan. Kondisi ini diperparah oleh variabilitas pola konsumsi yang tinggi akibat beberapa faktor musiman, di antaranya:

- **Bulan Ramadan**: Penurunan konsumsi drastis (hampir nol) karena mayoritas karyawan berpuasa dan tidak mengambil jatah susu.
- **Hari libur nasional dan cuti bersama**: Jumlah karyawan yang hadir dan mengambil susu turun signifikan atau bahkan nol pada hari-hari tertentu seperti Hari Raya Idul Fitri, Natal, dan Tahun Baru ketika pabrik tidak beroperasi.
- **Pola hari dalam seminggu (Day-of-Week)**: Jumlah karyawan hadir pada hari Senin–Jumat berbeda nyata dengan Sabtu dan Minggu.
- **Pola antar shift**: Jumlah karyawan di Shift 1 secara historis lebih banyak dibandingkan Shift 2 dan Shift 3, sehingga konsumsi susu per shift berbeda.

Ketidakmampuan metode estimasi manual untuk memodelkan kompleksitas faktor-faktor di atas mendorong kebutuhan akan sistem peramalan yang bersifat kuantitatif, otomatis, dan dapat diandalkan dalam lingkungan produksi nyata (*production-ready*).

---

## 2. Rumusan Masalah

Berdasarkan latar belakang tersebut, penelitian ini merumuskan masalah sebagai berikut:

1. Bagaimana membangun model peramalan kebutuhan distribusi susu UHT bulanan pada vending machine karyawan yang mampu menangani anomali musiman akibat Ramadan dan hari libur nasional?
2. Bagaimana mendistribusikan prediksi bulanan tersebut ke dalam granularitas harian per shift secara akurat, dengan mempertimbangkan pola konsumsi karyawan yang berbeda-beda pada hari kerja, akhir pekan, hari libur, dan hari besar keagamaan?
3. Bagaimana mengintegrasikan model prediksi ke dalam sistem otomasi produksi yang dapat berjalan secara otonom setiap hari tanpa intervensi manual?

---

## 3. Tujuan Penelitian

Penelitian ini bertujuan untuk:

1. Merancang dan mengimplementasikan sistem peramalan konsumsi (*demand forecasting*) berbasis dua lapis (*two-layer cascaded prediction*) yang menggabungkan model *machine learning* XGBoost dengan sistem distribusi berbasis aturan (*rule-based*).
2. Mengembangkan mekanisme penanganan anomali Ramadan yang orisinal, yaitu **Ramadan Lag Skipper**, yang memastikan fitur lag temporal model tidak terkontaminasi oleh data konsumsi abnormal selama bulan Ramadan.
3. Membangun **Smart Event Classifier v2.2** sebagai komponen distribusi harian yang mampu mengklasifikasikan setiap hari dalam bulan ke dalam tujuh kategori bobot konsumsi berdasarkan karakteristik hari tersebut.
4. Mengintegrasikan seluruh komponen ke dalam pipeline produksi otomatis yang berjalan harian (*daily automated pipeline*) dengan mekanisme validasi data berlapis.

---

## 4. Objek Penelitian

### 4.1 Sistem Prediksi dan Sumber Data

Objek penelitian utama dalam studi ini adalah **sistem peramalan permintaan distribusi (demand forecasting system)** yang dibangun untuk mengotomasi pengadaan susu UHT karyawan di PT GS Battery. Sistem ini bukan penelitian di bidang Internet of Things (IoT) atau perangkat keras — vending machine yang beroperasi di area karyawan berfungsi sebagai **instrumen pencatat data pasif** yang menghasilkan log transaksi distribusi secara otomatis.

Dengan demikian, penelitian ini bersifat **data-centric**: titik masuknya adalah data historis yang sudah terakumulasi selama tiga tahun, dan kontribusinya terletak pada algoritma serta pipeline prediksi yang dibangun di atas data tersebut, bukan pada pengembangan sistem mesin atau IoT.

Produk yang didistribusikan melalui sistem ini adalah susu UHT dalam empat varian rasa:

| Kode Varian | Nama Produk |
|---|---|
| Coklat | Susu UHT rasa coklat |
| Moca | Susu UHT rasa moka |
| Original (Putih) | Susu UHT tawar (tanpa perasa) |
| Strawberry | Susu UHT rasa stroberi |

Setiap pengambilan susu oleh karyawan dicatat secara otomatis oleh sistem vending machine ke dalam basis data dengan kolom waktu (`update_time`), nomor slot produk (`slot_number`), nama shift saat pengambilan (`keterangan`), dan jumlah unit yang diambil (`qty`). Akumulasi data log inilah yang menjadi sumber utama (*single source of truth*) untuk seluruh proses pelatihan dan evaluasi model.

### 4.2 Periode Data

Data historis yang digunakan mencakup periode **April 2023 hingga Desember 2025**, yang merupakan periode di mana data distribusi tersedia dengan kualitas yang cukup untuk pelatihan model. Periode ini mencakup setidaknya dua siklus Ramadan lengkap (2023 dan 2024), memberikan cukup data bagi model untuk mempelajari pola anomali konsumsi selama bulan puasa.

### 4.3 Shift Operasional

Vending machine beroperasi dalam tiga shift dengan konvensi penamaan sesuai sistem internal PT GS Battery:

| ID Shift | Keterangan | Karakteristik |
|---|---|---|
| SHIFT1-AWAL, SHIFT1-AKHIR | Shift pertama (pagi/siang) | Jumlah karyawan terbanyak — volume konsumsi tertinggi |
| SHIFT2-AWAL, SHIFT2-AKHIR | Shift kedua (sore) | Volume konsumsi menengah |
| SHIFT3-AWAL, SHIFT3-AKHIR | Shift ketiga (malam/dini hari) | Volume konsumsi paling kecil |
| SHIFTPUTIH-AWAL, SHIFTPUTIH-AKHIR | Shift khusus (non-rotasi) | Volume sangat kecil (< 2% total konsumsi) |

---

## 5. Signifikansi dan Kontribusi Penelitian

### 5.1 Kontribusi Teknis

Penelitian ini memberikan beberapa kontribusi teknis yang belum banyak dibahas dalam literatur peramalan kebutuhan distribusi untuk konteks industri manufaktur di Asia Tenggara:

1. **Ramadan Lag Skipper**: Mekanisme penghitungan fitur lag temporal yang secara aktif melewatkan bulan-bulan Ramadan. Alih-alih menggunakan lag sederhana berdasarkan offset kalender (bulan ini − N bulan), sistem menghitung lag berdasarkan bulan normal terdekat. Hal ini mencegah kontaminasi fitur prediktif oleh data konsumsi ekstrem yang tidak representatif selama periode puasa.

2. **Arsitektur Dua Lapis Heterogen (ML + Rule-Based)**: Hasil eksperimen internal menunjukkan bahwa model *machine learning* murni (Prophet dari Meta) menghasilkan WAPE 27% untuk distribusi harian, sedangkan sistem distribusi berbasis aturan dengan Smart Event Classifier menghasilkan WAPE 3.99%. Temuan ini menunjukkan bahwa kombinasi heterogen antara ML untuk prediksi agregat bulanan dan *rule-based* untuk distribusi granular harian lebih unggul dibandingkan pendekatan ML murni untuk kasus ini.

3. **Step 9 Business Logic Fallback**: Pendekatan *graceful degradation* yang mendeteksi bulan dengan hari produktif sangat sedikit (≤ 10 hari, tipikal puncak Ramadan) dan secara otomatis mengganti prediksi XGBoost dengan kalkulasi heuristik berbasis rata-rata konsumsi harian historis. Ini mencegah prediksi yang tidak masuk akal pada kondisi ekstrem.

4. **Fractional Working Days**: Representasi hari kerja yang tidak biner. Alih-alih menghitung hari kerja sebagai bilangan bulat, sistem menghitung kontribusi fraksional berdasarkan shift yang aktif pada hari tersebut. Hari dengan hanya Shift 2 aktif dihitung sebagai 0.38 hari kerja (bukan 1.0), mencerminkan jumlah karyawan yang hadir dan berpotensi mengambil susu secara aktual.

### 5.2 Kontribusi Praktis

Dari sisi operasional bisnis, sistem yang dibangun memberikan:
- **Proyeksi efisiensi pengadaan**: berdasarkan akurasi prediksi sistem (MAPE ~3–5%) dibandingkan estimasi manual yang diasumsikan memiliki error ~20–30%, sistem berpotensi mengurangi volume pembelian susu berlebih yang tidak terpakai (*overstock*)
- Otomasi penuh pipeline prediksi yang sebelumnya dilakukan secara manual oleh staf
- Jaminan pemenuhan kewajiban distribusi susu kepada karyawan (*employee welfare compliance*)

> **Catatan metodologi**: Angka penghematan biaya spesifik yang pernah dikutip sebelumnya tidak dapat diverifikasi karena tidak ada dokumentasi metodologi perhitungannya. Sebagai gantinya, bagian 6 di dokumen evaluasi menyajikan **proyeksi berbasis asumsi transparan** — termasuk harga referensi pasar dan asumsi tingkat error manual — yang dapat direplikasi dan diverifikasi oleh pembaca.

---

## 6. Batasan Penelitian

Penelitian ini memiliki beberapa batasan yang perlu diakui:

1. **Skala**: Sistem ini dirancang dan diuji untuk satu unit vending machine. Skalabilitas ke sistem multi-mesin atau multi-lokasi belum dievaluasi.
2. **Variabilitas preferensi varian**: Prediksi per varian (Coklat, Moca, Original, Strawberry) secara individual masih memiliki error 15–18% karena pilihan varian karyawan setiap harinya bersifat tidak deterministik. Ini merupakan batas alam (*natural limit*) — tidak ada data yang dapat memprediksi secara pasti apakah karyawan tertentu hari ini akan memilih susu coklat atau stroberi.
3. **Shift volume kecil**: Shift dengan volume konsumsi < 2% dari total (SHIFT3-AWAL, SHIFTPUTIH-AWAL/AKHIR) memiliki error persentase yang secara inheren lebih tinggi karena denominatornya kecil. Ini bukan kesalahan sistem, melainkan konsekuensi matematis dari metrik berbasis persentase.
4. **Data Ramadan terbatas**: Pola konsumsi pada Minggu menjelang Ramadan hanya memiliki 3 titik data historis. Model akan terus membaik seiring bertambahnya data dari tahun ke tahun.
5. **Ketergantungan pada kalender SQL**: Sistem bergantung sepenuhnya pada keakuratan data di tabel `dbo.OperationalCalendar`. Kesalahan input kalender (misalnya tidak mencatat hari libur baru atau perubahan jadwal shift) akan langsung memengaruhi kualitas prediksi distribusi.
