# 📊 API Endpoint Specification — Menu Dashboard Summary

Dokumen ini menjelaskan blueprint API untuk **Dashboard Summary** yang akan dipanggil oleh aplikasi Android Studio. Semua logika query SQL dicuri dari ASP.NET MVC (`DashboardController.cs` & `dashboard.js`) dan diadaptasi ke FastAPI.

---

## 1. Filter Parameter Global (Android to API)

Semua endpoint Dashboard Summary di Android wajib mendukung parameter query opsional berikut agar perilakunya sama dengan web:

- `start_date` (string, ISO-8601 format `YYYY-MM-DD`, default: *Hari ini*)
- `end_date` (string, ISO-8601 format `YYYY-MM-DD`, default: *Hari ini*)
- `shift_id` (integer/string, default: `"ALL"`, id_recnum_mst dari database)

---

## 2. Endpoint 1: Metric Cards (`/api/v1/dashboard/metrics`)

Menyediakan data untuk 4 kartu metrik utama di Android: **Taken (Susu Berhasil Diambil)**, **Failed (Transaksi Gagal)**, **Restock (Stok Susu Masuk)**, dan **Taken Today (Pengambilan Hari Ini)**.

- **HTTP Method**: `GET`
- **Request Query Params**: `start_date`, `end_date`, `shift_id`

### A. Pydantic Response Schema (JSON Contract)
Aplikasi Android akan menerima format data ini secara terstruktur:

```json
{
  "orders": {
    "title": "TAKEN (SUSU DIAMBIL)",
    "value": "1,234",
    "change": "+12.5%",
    "is_positive": true,
    "icon": "fa-cart-shopping"
  },
  "revenue": {
    "title": "TRANSAKSI GAGAL",
    "value": "56",
    "change": "-3.2%",
    "is_positive": false,
    "icon": "fa-xmark"
  },
  "averagePrice": {
    "title": "RESTOCK",
    "value": "789",
    "change": "+8.1%",
    "is_positive": true,
    "icon": "fa-rotate-right"
  },
  "productSold": {
    "title": "TAKEN TODAY",
    "value": "45",
    "change": "+5.2%",
    "is_positive": true,
    "icon": "fa-bag-shopping"
  }
}
```

### B. Python SQL Query & Logika Bisnis (Curi dari C#)

FastAPI akan menjalankan query SQL multi-result set menggunakan Temporary Table `#GroupedDates` untuk menghitung perbandingan periode saat ini vs periode sebelumnya (*mirror period*):

```python
# Di dalam dashboard_service.py:
def get_metrics_data(conn, start_date: str, end_date: str, shift_id: str):
    # 1. Hitung durasi hari untuk mirror period
    # delta_days = (end_date - start_date)
    # prev_start_date = start_date - delta_days
    # prev_end_date = start_date - 1 day
    
    # 2. Shift Filter Generator (Hasil terjemahan C# GetShiftFilterSql)
    shift_filter = ""
    if shift_id != "ALL":
        # Ambil jam_mulai dan jam_akhir dari master_settime
        # Jika normal: AND CAST(update_time AS TIME) >= start AND CAST(update_time AS TIME) <= end
        # Jika overnight: AND (CAST(update_time AS TIME) >= start OR CAST(update_time AS TIME) <= end)
        pass

    sql_query = f"""
    -- Buat Temp Table untuk agregasi data
    SELECT 
        CAST(update_time AS DATE) as tgl,
        kategori_transaksi,
        COUNT(*) as cnt,
        SUM(CASE WHEN kategori_transaksi = 'stocking' THEN ISNULL(qty, 0) ELSE 0 END) as qty_sum
    INTO #GroupedDates
    FROM monitor_log_datatransaksi
    WHERE update_time >= ? AND update_time <= ? {shift_filter}
    GROUP BY CAST(update_time AS DATE), kategori_transaksi;

    -- RESULT 1: TAKEN (ambil) periode saat ini vs periode kemarin
    SELECT 
        (SELECT ISNULL(SUM(cnt), 0) FROM #GroupedDates WHERE kategori_transaksi = 'ambil' AND tgl BETWEEN ? AND ?) as CurrentVal,
        (SELECT ISNULL(SUM(cnt), 0) FROM #GroupedDates WHERE kategori_transaksi = 'ambil' AND tgl BETWEEN ? AND ?) as PrevVal;

    -- RESULT 2: FAILED (transaksigagal) periode saat ini vs periode kemarin
    SELECT 
        (SELECT ISNULL(SUM(cnt), 0) FROM #GroupedDates WHERE kategori_transaksi = 'transaksigagal' AND tgl BETWEEN ? AND ?) as CurrentVal,
        (SELECT ISNULL(SUM(cnt), 0) FROM #GroupedDates WHERE kategori_transaksi = 'transaksigagal' AND tgl BETWEEN ? AND ?) as PrevVal;

    -- RESULT 3: RESTOCK (stocking qty) periode saat ini vs periode kemarin
    SELECT 
        (SELECT ISNULL(SUM(qty_sum), 0) FROM #GroupedDates WHERE kategori_transaksi = 'stocking' AND tgl BETWEEN ? AND ?) as CurrentVal,
        (SELECT ISNULL(SUM(qty_sum), 0) FROM #GroupedDates WHERE kategori_transaksi = 'stocking' AND tgl BETWEEN ? AND ?) as PrevVal;

    -- RESULT 4: TAKEN TODAY (hari ini vs kemarin jam yang sama)
    -- Lakukan query terpisah untuk real-time data hari ini vs kemarin
    """
    
    # Jalankan dengan pyodbc cursor
    cursor = conn.cursor()
    cursor.execute(sql_query, params)
    
    # Membaca multiple result set di pyodbc:
    # row1 = cursor.fetchone()
    # cursor.nextset()
    # row2 = cursor.fetchone()
    # ...
```

---

## 3. Endpoint 2: Consumption Chart (`/api/v1/dashboard/consumption-chart`)

Menyediakan data untuk menggambarkan **Line Chart** trend konsumsi harian (Taken) di Android.

- **HTTP Method**: `GET`
- **Request Query Params**: `start_date`, `end_date`, `shift_id`

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "labels": ["01 May", "02 May", "03 May", "04 May"],
  "data": [120, 150, 80, 200],
  "most": {
    "date": "04 May 2026",
    "count": 200
  },
  "least": {
    "date": "03 May 2026",
    "count": 80
  }
}
```

### B. SQL Query yang Dicuri
```sql
SELECT 
    FORMAT(update_time, 'dd MMM') as Hari,
    COUNT(*) as Jumlah
FROM monitor_log_datatransaksi
WHERE kategori_transaksi = 'ambil' 
  AND update_time >= ? 
  AND update_time <= ?
  {shift_filter}
GROUP BY FORMAT(update_time, 'dd MMM'), CAST(update_time AS DATE)
ORDER BY CAST(update_time AS DATE) ASC;
```

---

## 4. Endpoint 3: Sales Analytics per Variant (`/api/v1/dashboard/sales-analytics`)

Menyediakan data proporsi konsumsi per varian susu untuk **Doughnut/Pie Chart** di Android.

- **HTTP Method**: `GET`
- **Request Query Params**: `start_date`, `end_date`, `shift_id`

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "labels": ["Coklat", "Strawberry", "Moca", "Original (Putih)"],
  "data": [450, 250, 150, 384]
}
```

### B. SQL Query yang Dicuri (JOIN Mapping)
```sql
SELECT 
    ISNULL(v.nama_variant, 'Unknown') as nama_variant,
    COUNT(m.id_recnum_mav) as jumlah
FROM monitor_log_datatransaksi m
LEFT JOIN manage_map_slot_number map ON SUBSTRING(m.slot_number, 1, 1) = map.slot_name
LEFT JOIN master_variant v ON map.id_recnum_variant = v.id_recnum_variant
WHERE m.kategori_transaksi = 'ambil'
  AND m.update_time >= ? 
  AND m.update_time <= ?
  {shift_filter}
GROUP BY v.nama_variant;
```

---

## 5. Endpoint 4: Latest Transactions (`/api/v1/dashboard/latest-transactions`)

Menyediakan daftar 10 transaksi terbaru untuk ditampilkan dalam format **List View** atau **Table** di Android.

- **HTTP Method**: `GET`
- **Request Query Params**: `start_date`, `end_date`, `shift_id`

### A. Pydantic Response Schema (JSON Contract)
```json
[
  {
    "rfid": "ABC123XYZ",
    "timestamp": "25/05/2026 14:30:15",
    "status": "Berhasil",
    "kategori": "ambil"
  },
  {
    "rfid": "999888777",
    "timestamp": "25/05/2026 14:25:01",
    "status": "Gagal",
    "kategori": "transaksigagal"
  }
]
```

### B. SQL Query yang Dicuri (TOP 10)
```sql
SELECT TOP 10 
    rfid,
    update_time,
    kategori_transaksi
FROM monitor_log_datatransaksi
WHERE kategori_transaksi IN ('ambil', 'transaksigagal')
  AND update_time >= ? 
  AND update_time <= ?
  {shift_filter}
ORDER BY update_time DESC;
```

---

## 💡 Tips untuk Developer Android Studio (Kotlin)

1. **Retrofit Library**: Gunakan library `Retrofit` + `GsonConverterFactory` di Kotlin untuk menembak endpoint-endpoint di atas dengan sangat mudah.
2. **MPAndroidChart**: Untuk menggambar Line Chart dan Doughnut Chart secara interaktif di Android, sangat disarankan menggunakan library open-source populer `MPAndroidChart`. Data JSON di atas sudah dirancang agar langsung bisa dipetakan ke objek `Entry` dan `PieEntry` library tersebut.
