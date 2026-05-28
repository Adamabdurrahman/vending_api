# 🔮 API Endpoint Specification — Menu Prediction Dashboard

Dokumen ini menjelaskan blueprint API untuk **Prediction Dashboard** yang akan dipanggil oleh aplikasi Android Studio. Semua logika query SQL dicuri dari ASP.NET MVC (`DashboardController.cs` & `prediction.js`) dan diadaptasi ke FastAPI.

---

## 1. Filter Parameter Global (Android to API)

Semua endpoint Prediction Dashboard di Android wajib mendukung parameter query opsional berikut agar perilakunya sama dengan web:

- `year` (integer, default: `2026`)
- `quarter` (integer, default: `1`, rentang nilai `1` - `4`)

Untuk mempermudah pemrosesan di FastAPI, berikut mapping bulan per kuartal:
- **Q1**: Bulan 1 (Januari), 2 (Februari), 3 (Maret) -> Label `'YYYY-01'`, `'YYYY-02'`, `'YYYY-03'`
- **Q2**: Bulan 4 (April), 5 (Mei), 6 (Juni) -> Label `'YYYY-04'`, `'YYYY-05'`, `'YYYY-06'`
- **Q3**: Bulan 7 (Juli), 8 (Agustus), 9 (September) -> Label `'YYYY-07'`, `'YYYY-08'`, `'YYYY-09'`
- **Q4**: Bulan 10 (Oktober), 11 (November), 12 (Desember) -> Label `'YYYY-10'`, `'YYYY-11'`, `'YYYY-12'`

---

## 2. Endpoint 1: Prediction Summary & Insights (`/api/v1/prediction/summary`)

Menyediakan data ringkasan performa model ML di Android: **Tingkat Akurasi (100 - MAPE)**, **Prediksi Demand per Bulan** (tiga bulan dalam kuartal terpilih), perbandingan dengan kuartal sebelumnya (*jika Q > 1*), serta pesan **Insight Evaluasi Model** dari `SystemNotifications`.

- **HTTP Method**: `GET`
- **Request Query Params**: `year`, `quarter`

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "accuracy": 92.5,
  "current_year": 2026,
  "current_quarter": 1,
  "show_comparison": true,
  "months": {
    "month_1": {
      "month_name": "Januari",
      "total_demand": "12,450",
      "error_percent": 6.8,
      "diff": {
        "show_diff": true,
        "diff_percentage": 12.3,
        "diff_is_positive": true,
        "diff_demand_text": "1,360"
      }
    },
    "month_2": {
      "month_name": "Februari",
      "total_demand": "11,800",
      "error_percent": 7.5,
      "diff": {
        "show_diff": true,
        "diff_percentage": 2.1,
        "diff_is_positive": false,
        "diff_demand_text": "250"
      }
    },
    "month_3": {
      "month_name": "Maret",
      "total_demand": "13,100",
      "error_percent": 8.2,
      "diff": {
        "show_diff": true,
        "diff_percentage": 5.4,
        "diff_is_positive": true,
        "diff_demand_text": "670"
      }
    }
  },
  "insights": {
    "accuracy_notif": "Akurasi model XGBoost kuartal ini stabil di 92.5%.",
    "model_text": "XGBoost_v3 optimal dengan parameter max_depth=6.",
    "total_prediction": "37,350"
  }
}
```

### B. Python SQL Query & Logika Bisnis (Curi dari C#)

FastAPI akan menjalankan query Layer 1 untuk mengambil MAPE dan Total Demand, lalu menghitung perubahan persentase dan mengambil pesan notifikasi:

```python
# Di dalam services/dashboard_service.py:
def get_prediction_summary(conn, year: int, quarter: int):
    # Hitung string bulan (PredictedMonth format YYYY-MM)
    m1 = f"{year}-{(quarter - 1) * 3 + 1:02d}"
    m2 = f"{year}-{(quarter - 1) * 3 + 2:02d}"
    m3 = f"{year}-{(quarter - 1) * 3 + 3:02d}"
    
    prev_m1, prev_m2, prev_m3 = "", "", ""
    show_comparison = quarter > 1
    if show_comparison:
        prev_m1 = f"{year}-{(quarter - 2) * 3 + 1:02d}"
        prev_m2 = f"{year}-{(quarter - 2) * 3 + 2:02d}"
        prev_m3 = f"{year}-{(quarter - 2) * 3 + 3:02d}"

    # 1. Query Layer 1
    sql_layer1 = """
        SELECT [PredictedMonth], [MAPE_Total], [TotalDemand], [ErrorPercent]
        FROM [dbo].[ForecastResults_Layer1]
        WHERE [PredictedMonth] IN (?, ?, ?) 
           OR [PredictedMonth] IN (?, ?, ?)
    """
    
    # Jalankan query SQL Server menggunakan pyodbc
    cursor = conn.cursor()
    cursor.execute(sql_layer1, (m1, m2, m3, prev_m1 or "XXXX", prev_m2 or "XXXX", prev_m3 or "XXXX"))
    rows = cursor.fetchall()
    
    # 2. Query SystemNotifications untuk insight
    q_label = f"Q{quarter}"
    sql_notif = """
        SELECT TOP 2 [NotifType], [Message]
        FROM [dbo].[SystemNotifications]
        WHERE Title LIKE ?
        ORDER BY CreatedAt ASC
    """
    cursor.execute(sql_notif, (f"%{q_label}%",))
    notif_rows = cursor.fetchall()
    
    # Proses data sesuai logika C# di DashboardController.cs (CalculateDiff dll.)
    # ...
```

---

## 3. Endpoint 2: Variant Error Distribution (`/api/v1/prediction/variant-errors`)

Menyediakan persentase error model prediksi untuk setiap varian susu per bulan dalam kuartal terpilih untuk disajikan dalam bentuk **Bar Chart** atau **Tabel Perbandingan** di Android.

- **HTTP Method**: `GET`
- **Request Query Params**: `year`, `quarter`

### A. Pydantic Response Schema (JSON Contract)
```json
[
  {
    "variant_name": "Coklat",
    "month_1_error": 5.4,
    "month_1_abs_error": 5.4,
    "month_2_error": -2.3,
    "month_2_abs_error": 2.3,
    "month_3_error": 1.1,
    "month_3_abs_error": 1.1
  },
  {
    "variant_name": "Strawberry",
    "month_1_error": 12.1,
    "month_1_abs_error": 12.1,
    "month_2_error": 8.7,
    "month_2_abs_error": 8.7,
    "month_3_error": -4.2,
    "month_3_abs_error": 4.2
  }
]
```

### B. SQL Query yang Dicuri (Layer 2 Variant)
```sql
SELECT 
    [Variant],
    [PredictedMonth],
    ISNULL(SUM(PredictedDemand), 0) AS TotalPred,
    ISNULL(SUM(ActualDemand), 0) AS TotalAct,
    ((ISNULL(SUM(PredictedDemand), 0) * 1.0) - ISNULL(SUM(ActualDemand), 0)) / NULLIF(SUM(ActualDemand), 0) * 100.0 AS Error_Pct,
    ABS(((ISNULL(SUM(PredictedDemand), 0) * 1.0) - ISNULL(SUM(ActualDemand), 0)) / NULLIF(SUM(ActualDemand), 0) * 100.0) AS Abs_Error_Pct
FROM [dbo].[ForecastResults_Layer2]
WHERE PredictedMonth IN (?, ?, ?)
GROUP BY [Variant], [PredictedMonth]
ORDER BY [Variant], [PredictedMonth]
```

---

## 4. Endpoint 3: Shift Error Distribution (`/api/v1/prediction/shift-errors`)

Menyediakan persentase error mutlak (*Absolute Error*) per shift kerja per bulan dalam kuartal terpilih.

- **HTTP Method**: `GET`
- **Request Query Params**: `year`, `quarter`

### A. Pydantic Response Schema (JSON Contract)
```json
[
  {
    "shift_name": "SHIFT1 - AWAL",
    "month_1_abs_error": 8.4,
    "month_2_abs_error": 6.2,
    "month_3_abs_error": 9.1
  },
  {
    "shift_name": "SHIFT1 - AKHIR",
    "month_1_abs_error": 11.5,
    "month_2_abs_error": 7.9,
    "month_3_abs_error": 12.4
  }
]
```

### B. SQL Query yang Dicuri (Layer 2 Shift)
```sql
SELECT 
    [Shift],
    [PredictedMonth],
    ABS(((ISNULL(SUM(PredictedDemand),0) * 1.0) - ISNULL(SUM(ActualDemand), 0)) / NULLIF(SUM(ActualDemand), 0) * 100.0) AS Abs_Error_Pct
FROM [dbo].[ForecastResults_Layer2]
WHERE PredictedMonth IN (?, ?, ?)
GROUP BY [Shift], [PredictedMonth]
ORDER BY [Shift], [PredictedMonth]
```

---

## 5. Endpoint 4: Daily Log Entries (`/api/v1/prediction/daily-logs`)

Menyediakan daftar transaksi harian aktual vs prediksi untuk varian dan shift tertentu, dibatasi maksimum **TOP 30 data per bulan** dalam kuartal (Total 90 baris). Dilengkapi parameter kecocokan `is_close` (toleransi error < 20% atau selisih <= 8 unit).

- **HTTP Method**: `GET`
- **Request Query Params**: `year`, `quarter`

### A. Pydantic Response Schema (JSON Contract)
```json
[
  {
    "predicted_month": "2026-01",
    "date": "2026-01-01",
    "date_string": "01 Jan 2026",
    "shift_name": "SHIFT1 - AWAL",
    "variant_name": "Coklat",
    "actual_demand": 42,
    "predicted_demand": 45,
    "is_close": true
  },
  {
    "predicted_month": "2026-01",
    "date": "2026-01-01",
    "date_string": "01 Jan 2026",
    "shift_name": "SHIFT1 - AKHIR",
    "variant_name": "Strawberry",
    "actual_demand": 15,
    "predicted_demand": 30,
    "is_close": false
  }
]
```

### B. SQL Query yang Dicuri (Partitioned Ranked CTE)
```sql
WITH RankedLogs AS (
    SELECT 
        [PredictedMonth],
        [Date],
        [Shift],
        [Variant],
        ISNULL([ActualDemand], 0) AS ActualDemand,
        ISNULL([PredictedDemand], 0) AS PredictedDemand,
        ROW_NUMBER() OVER(PARTITION BY [PredictedMonth] ORDER BY [Date] ASC, [Shift] ASC) as rn
    FROM [dbo].[ForecastResults_Layer2]
    WHERE PredictedMonth IN (?, ?, ?)
)
SELECT 
    [PredictedMonth],
    [Date],
    [Shift],
    [Variant],
    [ActualDemand],
    [PredictedDemand]
FROM RankedLogs
WHERE rn <= 30
ORDER BY [PredictedMonth] ASC, [Date] ASC
```

---

## 6. Endpoint 5: Prediction Chart Data (`/api/v1/prediction/chart-data`)

Menyediakan dataset line chart raksasa yang mengembalikan **27 deret data** untuk digambar secara interaktif pada satu chart terpadu di Android. Client dapat melakukan switching filter view (Total, Varian, Shift) langsung di sisi aplikasi mobile tanpa melakukan request ulang ke server.

- **HTTP Method**: `GET`
- **Request Query Params**: `year`, `quarter`

### A. Pydantic Response Schema (JSON Contract)
```json
{
  "labels": ["2026-01-01", "2026-01-02", "2026-01-03"],
  "total": {
    "predicted": [150, 162, 148],
    "actual": [140, 158, 150]
  },
  "variants": {
    "coklat": {
      "predicted": [40, 45, 41],
      "actual": [38, 42, 43]
    },
    "strawberry": {
      "predicted": [30, 32, 29],
      "actual": [25, 34, 30]
    },
    "moca": {
      "predicted": [20, 25, 23],
      "actual": [22, 24, 21]
    },
    "original": {
      "predicted": [60, 60, 55],
      "actual": [55, 58, 56]
    }
  },
  "shifts": {
    "s1_awal": { "predicted": [20, 22, 19], "actual": [18, 20, 21] },
    "s1_akhir": { "predicted": [15, 17, 16], "actual": [14, 15, 15] },
    "s2_awal": { "predicted": [25, 27, 24], "actual": [22, 28, 22] },
    "s2_akhir": { "predicted": [18, 20, 19], "actual": [16, 18, 17] },
    "s3_awal": { "predicted": [30, 32, 31], "actual": [28, 30, 29] },
    "s3_akhir": { "predicted": [22, 24, 21], "actual": [20, 25, 22] },
    "s_putih_awal": { "predicted": [12, 11, 10], "actual": [10, 12, 9] },
    "s_putih_akhir": { "predicted": [8, 9, 8], "actual": [12, 10, 5] }
  }
}
```

### B. SQL Query yang Dicuri (Aggregated Pivot)

Aplikasi FastAPI disarankan menggunakan **Named Column Binding** untuk memetakan hasil query berikut agar aman dari bug perubahan urutan kolom:

```sql
SELECT 
    [Date],
    ISNULL(SUM(PredictedDemand), 0) AS TotalPred,
    ISNULL(SUM(ActualDemand), 0) AS TotalAct,
    
    ISNULL(SUM(CASE WHEN Variant = 'Coklat' THEN PredictedDemand ELSE 0 END), 0) AS PredCoklat,
    ISNULL(SUM(CASE WHEN Variant = 'Coklat' THEN ActualDemand ELSE 0 END), 0) AS ActCoklat,
    ISNULL(SUM(CASE WHEN Variant = 'Strawberry' THEN PredictedDemand ELSE 0 END), 0) AS PredStrawberry,
    ISNULL(SUM(CASE WHEN Variant = 'Strawberry' THEN ActualDemand ELSE 0 END), 0) AS ActStrawberry,
    ISNULL(SUM(CASE WHEN Variant = 'Moca' THEN PredictedDemand ELSE 0 END), 0) AS PredMoca,
    ISNULL(SUM(CASE WHEN Variant = 'Moca' THEN ActualDemand ELSE 0 END), 0) AS ActMoca,
    ISNULL(SUM(CASE WHEN Variant = 'Original (Putih)' THEN PredictedDemand ELSE 0 END), 0) AS PredOriginal,
    ISNULL(SUM(CASE WHEN Variant = 'Original (Putih)' THEN ActualDemand ELSE 0 END), 0) AS ActOriginal,

    ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredS1Awal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActS1Awal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredS1Akhir,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT1 - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActS1Akhir,

    ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredS2Awal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActS2Awal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredS2Akhir,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT2 - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActS2Akhir,

    ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredS3Awal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActS3Awal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredS3Akhir,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFT3 - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActS3Akhir,

    ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AWAL' THEN PredictedDemand ELSE 0 END), 0) AS PredSPutihAwal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AWAL' THEN ActualDemand ELSE 0 END), 0) AS ActSPutihAwal,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AKHIR' THEN PredictedDemand ELSE 0 END), 0) AS PredSPutihAkhir,
    ISNULL(SUM(CASE WHEN Shift = 'SHIFTPUTIH - AKHIR' THEN ActualDemand ELSE 0 END), 0) AS ActSPutihAkhir
FROM [dbo].[ForecastResults_Layer2]
WHERE PredictedMonth IN (?, ?, ?)
GROUP BY [Date]
ORDER BY [Date] ASC
```

---

## 💡 Tips untuk Developer Android Studio (Kotlin)

1. **Efisiensi Memory Chart**: Request payload chart-data berukuran cukup besar (karena mencakup data harian 3 bulan penuh). Pastikan Anda hanya memanggil `/chart-data` sekali saat halaman di-load, simpan dalam variabel cache ViewModel lokal, dan lakukan pemfilteran data di memori aplikasi Android untuk beralih mode visualisasi (Total, Varian, Shift).
2. **Custom Legend di MPAndroidChart**: Gunakan `LineDataSet` secara dinamis di Android. Ketika user memilih mode "Variant", masukkan 8 `LineDataSet` ke dalam `LineData` objek. Nonaktifkan render legend jika grafik terasa padat dan gunakan legend kustom di XML layout Kotlin.
3. **Format Tanggal**: Gunakan `LocalDate.parse(dateStr)` di Kotlin SDK 26+ untuk memformat label sumbu X (Axis-X) line chart agar lebih enak dibaca (misal dari `"2026-01-01"` menjadi `"01 Jan"`).
