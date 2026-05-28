# 📈 API Endpoint Specification — Menu ML Retrain Logs

Dokumen ini menjelaskan blueprint API untuk **ML Retrain Logs** yang akan dipanggil oleh aplikasi Android Studio. Semua logika query SQL dan perhitungan sekuensial kuartal dicuri dari ASP.NET MVC (`DashboardController.cs.Retrain()`) dan diadaptasi ke FastAPI.

---

## 1. Mekanisme Perhitungan Kuartal & Tahun Sekuensial (ML Lifecycle)

Di dalam database SQL Server, tabel `RetrainLog` tidak menyimpan data kuartal (`Q1`, `Q2`, dst.) atau tahun training secara eksplisit. Logika penentuan kuartal dan tahun dihitung secara dinamis dari urutan baris waktu maju (*Chronological Sequence Number*) dengan aturan bisnis legacy sebagai berikut:

- **Tahun Basis**: Mulai dari tahun **`2026`**.
- **Kuartal Berulang**: Setiap kali iterasi sekuens bertambah, nilai kuartal berputar dari `1, 2, 3, 4` kemudian kembali lagi ke `1, 2, 3, 4`.
- **Kenaikan Tahun**: Setiap **4 sekuens** retrain sukses terlampaui, tahun bertambah **`+1`** tahun.

FastAPI akan meniru logika pembagian modulo matematika ini secara presisi agar data yang tampil di Android 100% konsisten dengan versi web dashboard.

---

## 2. Endpoint: Fetch Retrain Logs (`GET /api/v1/retrain/logs`)

Mengambil seluruh daftar riwayat retrain model Machine Learning terurut dari yang terbaru (*descending* berdasarkan waktu eksekusi).

- **HTTP Method**: `GET`
- **Request Query Params** (Optional untuk standard mobile pagination):
  - `limit` (integer, default: `100` untuk mencegah overhead memory)
  - `offset` (integer, default: `0`)

### A. Pydantic Response Schema (JSON Contract)
```json
[
  {
    "id": 12,
    "quarter_label": "Q4",
    "calculated_quarter": 4,
    "calculated_year": 2028,
    "run_timestamp": "2028-11-15T02:00:00",
    "model_version": "XGBoost_v6",
    "mape": 6.82,
    "mae": 15.3,
    "rmse": 18.7,
    "training_rows": 12500,
    "training_period_end": "2028-10-31",
    "best_params": "{\"max_depth\": 6, \"n_estimators\": 150}",
    "status": "Success"
  },
  {
    "id": 11,
    "quarter_label": "Q3",
    "calculated_quarter": 3,
    "calculated_year": 2028,
    "run_timestamp": "2028-08-14T02:00:00",
    "model_version": "XGBoost_v5",
    "mape": 7.45,
    "mae": 16.1,
    "rmse": 19.8,
    "training_rows": 11200,
    "training_period_end": "2028-07-31",
    "best_params": "{\"max_depth\": 5, \"n_estimators\": 100}",
    "status": "Success"
  }
]
```

### B. Python SQL Query & Business Logic

FastAPI akan memanggil query CTE untuk mendapatkan `SequenceNum` kronologis terlebih dahulu, baru kemudian membungkusnya dalam kalkulasi matematika Python:

```python
# Di dalam services/dashboard_service.py:
def get_retrain_logs(conn, limit: int = 100, offset: int = 0):
    cursor = conn.cursor()
    
    # Query SQL CTE (Common Table Expression) untuk memberikan nomor urut dari yang paling lama
    # lalu mengurutkan hasilnya kembali dari yang terbaru (descending)
    sql_query = """
        WITH RankedLogs AS (
            SELECT 
                [Id],
                [RunTimestamp],
                [ModelVersion],
                [MAPE],
                [MAE],
                [RMSE],
                [TrainingRows],
                [TrainingPeriodEnd],
                [BestParams],
                [Status],
                ROW_NUMBER() OVER(ORDER BY RunTimestamp ASC) as SequenceNum 
            FROM [dbo].[RetrainLog]
        )
        SELECT * 
        FROM RankedLogs 
        ORDER BY RunTimestamp DESC
    """
    cursor.execute(sql_query)
    rows = cursor.fetchall()
    
    logs = []
    # Pemrosesan sekuensial modulo di Python
    for row in rows:
        seq_num = row.SequenceNum
        
        # Logika Quarter: ((seqNum - 1) % 4) + 1
        q_num = ((seq_num - 1) % 4) + 1
        quarter_label = f"Q{q_num}"
        
        # Logika Tahun: 2026 + ((seqNum - 1) // 4)
        calculated_year = 2026 + ((seq_num - 1) // 4)
        
        # Best Params JSON check (Cegah error parsers)
        best_params_raw = row.BestParams or "{}"
        
        logs.append({
            "id": row.Id,
            "quarter_label": quarter_label,
            "calculated_quarter": q_num,
            "calculated_year": calculated_year,
            "run_timestamp": row.RunTimestamp.isoformat() if row.RunTimestamp else None,
            "model_version": row.ModelVersion.strip() if row.ModelVersion else "",
            "mape": round(float(row.MAPE), 2) if row.MAPE is not None else 0.0,
            "mae": round(float(row.MAE), 2) if row.MAE is not None else 0.0,
            "rmse": round(float(row.RMSE), 2) if row.RMSE is not None else 0.0,
            "training_rows": int(row.TrainingRows) if row.TrainingRows is not None else 0,
            "training_period_end": row.TrainingPeriodEnd.strip() if row.TrainingPeriodEnd else "",
            "best_params": best_params_raw,
            "status": row.Status.strip() if row.Status else "Failed"
        })
        
    # Terapkan paging limit dan offset manual di Python
    return logs[offset:offset + limit]
```

---

## 3. Penanganan Data Kosong / NULL pada Metrik Evaluasi

Pada kasus tertentu di mana status pelatihan adalah `Failed`, kolom-kolom performa model seperti `MAPE`, `MAE`, dan `RMSE` akan bernilai **NULL** di SQL Server.
- **Standarisasi API**: FastAPI wajib mengonversi nilai `NULL/DBNull` tersebut ke **`0.0`** secara otomatis agar library parser JSON di Kotlin (seperti Gson atau Moshi) tidak membuang error *NullPointerException* atau crash saat deserialisasi objek numerik bertipe non-nullable `Double` di Android Studio.

---

## 💡 Tips untuk Developer Android Studio (Kotlin)

1. **Retrofit Data Class**:
   Definisikan model data Kotlin dengan struktur aman berikut:
   ```kotlin
   data class RetrainLogEntry(
       val id: Int,
       @SerializedName("quarter_label") val quarterLabel: String,
       @SerializedName("calculated_quarter") val calculatedQuarter: Int,
       @SerializedName("calculated_year") val calculatedYear: Int,
       @SerializedName("run_timestamp") val runTimestamp: String?,
       @SerializedName("model_version") val modelVersion: String,
       val mape: Double,
       val mae: Double,
       val rmse: Double,
       @SerializedName("training_rows") val trainingRows: Int,
       @SerializedName("training_period_end") val trainingPeriodEnd: String,
       @SerializedName("best_params") val bestParams: String,
       val status: String
   )
   ```
2. **Pemberian Warna Status Ringkas**:
   Tampilkan status `'Success'` dengan teks **Hijau Bold (Green)** dan status `'Failed'` dengan teks **Merah Bold (Red)** di item list view RecyclerView Kotlin demi kemudahan visibilitas administrator.
3. **Format Best Params JSON Viewer**:
   Kolom `best_params` dikembalikan berupa format JSON String mentah. Di Android Studio, Anda dapat memparsing JSON String tersebut menggunakan library `JSONObject(bestParams)` untuk menyajikannya dalam format dialog info yang cantik berisi pasangan kunci-nilai (key-value) parameter model ML.
