# Poin 3 — Bentuk Data / Response (Inventory Dashboard DSS)

## 3.1 Endpoint 1: Dashboard Utama

### Request

```
GET /api/v1/inventory/dashboard?year=2026&quarter=3
```

| Param | Tipe | Wajib | Default | Keterangan |
|-------|------|-------|---------|------------|
| `year` | int | Tidak | Tahun saat ini | Tahun target |
| `quarter` | int | Tidak | Kuartal berikutnya | 1–4 |

### Response (Kuartal Aktif / Mendatang)

```json
{
  "year": 2026,
  "quarter": 3,
  "quarter_label": "Q3 2026 (Jul - Aug - Sep)",
  "has_prediction_data": true,
  "available_quarters": [
    {"year": 2026, "quarter": 3, "label": "Q3 2026"},
    {"year": 2026, "quarter": 2, "label": "Q2 2026"},
    {"year": 2026, "quarter": 1, "label": "Q1 2026"},
    {"year": 2025, "quarter": 4, "label": "Q4 2025"}
  ],

  "summary": {
    "total_predicted_demand": 2600,
    "total_warehouse_stock": 480,
    "total_vm_stock": 110,
    "total_available": 590,
    "total_to_purchase": 2010
  },

  "variants": [
    {
      "variant_name": "Coklat",
      "predicted_demand": 850,
      "warehouse_stock": 200,
      "vm_stock": 45,
      "total_available": 245,
      "to_purchase": 605,
      "purchase_percentage": 30.1,
      "monthly": [
        {"month_name": "Juli",      "month_number": 7, "predicted": 280},
        {"month_name": "Agustus",   "month_number": 8, "predicted": 290},
        {"month_name": "September", "month_number": 9, "predicted": 280}
      ]
    },
    {
      "variant_name": "Strawberry",
      "predicted_demand": 720,
      "warehouse_stock": 150,
      "vm_stock": 30,
      "total_available": 180,
      "to_purchase": 540,
      "purchase_percentage": 26.9,
      "monthly": [
        {"month_name": "Juli",      "month_number": 7, "predicted": 240},
        {"month_name": "Agustus",   "month_number": 8, "predicted": 250},
        {"month_name": "September", "month_number": 9, "predicted": 230}
      ]
    },
    {
      "variant_name": "Moca",
      "predicted_demand": 600,
      "warehouse_stock": 80,
      "vm_stock": 20,
      "total_available": 100,
      "to_purchase": 500,
      "purchase_percentage": 24.9,
      "monthly": [
        {"month_name": "Juli",      "month_number": 7, "predicted": 200},
        {"month_name": "Agustus",   "month_number": 8, "predicted": 210},
        {"month_name": "September", "month_number": 9, "predicted": 190}
      ]
    },
    {
      "variant_name": "Original (Putih)",
      "predicted_demand": 430,
      "warehouse_stock": 50,
      "vm_stock": 15,
      "total_available": 65,
      "to_purchase": 365,
      "purchase_percentage": 18.2,
      "monthly": [
        {"month_name": "Juli",      "month_number": 7, "predicted": 145},
        {"month_name": "Agustus",   "month_number": 8, "predicted": 150},
        {"month_name": "September", "month_number": 9, "predicted": 135}
      ]
    }
  ],

  "history_summary": null
}
```

### Response (Kuartal Lalu — `history_summary` terisi)

Saat user melihat kuartal yang sudah lewat, field `history_summary` tidak null:

```json
{
  "year": 2026,
  "quarter": 1,
  "quarter_label": "Q1 2026 (Jan - Feb - Mar)",
  "has_prediction_data": true,
  "available_quarters": [ ... ],

  "summary": {
    "total_predicted_demand": 2400,
    "total_warehouse_stock": 300,
    "total_vm_stock": 85,
    "total_available": 385,
    "total_to_purchase": 2015
  },

  "variants": [ ... ],

  "history_summary": {
    "total_stock_in": 800,
    "total_stock_out": 620,
    "total_consumed": 580,
    "predicted_demand": 600,
    "actual_demand": 580,
    "prediction_accuracy": 96.7,
    "per_variant": [
      {
        "variant_name": "Coklat",
        "stock_in": 250,
        "stock_out": 190,
        "consumed": 175,
        "predicted": 200,
        "actual": 175
      },
      {
        "variant_name": "Strawberry",
        "stock_in": 200,
        "stock_out": 160,
        "consumed": 155,
        "predicted": 160,
        "actual": 155
      },
      {
        "variant_name": "Moca",
        "stock_in": 180,
        "stock_out": 145,
        "consumed": 135,
        "predicted": 130,
        "actual": 135
      },
      {
        "variant_name": "Original (Putih)",
        "stock_in": 170,
        "stock_out": 125,
        "consumed": 115,
        "predicted": 110,
        "actual": 115
      }
    ]
  }
}
```

### Response (Prediksi Belum Tersedia)

```json
{
  "year": 2026,
  "quarter": 4,
  "quarter_label": "Q4 2026 (Okt - Nov - Des)",
  "has_prediction_data": false,
  "available_quarters": [ ... ],
  "summary": null,
  "variants": [],
  "history_summary": null
}
```

---

## 3.2 Endpoint 2: Log Pergerakan Stok (Paginasi)

### Request

```
GET /api/v1/inventory/movements?page=1&per_page=10&variant=Coklat&type=IN
```

| Param | Tipe | Wajib | Default | Keterangan |
|-------|------|-------|---------|------------|
| `page` | int | Tidak | 1 | Halaman ke-n |
| `per_page` | int | Tidak | 10 | Item per halaman (max 50) |
| `variant` | string | Tidak | null (semua) | Filter varian tertentu |
| `type` | string | Tidak | null (semua) | Filter: `IN` atau `OUT` |

### Response

```json
{
  "page": 1,
  "per_page": 10,
  "total_items": 47,
  "total_pages": 5,
  "items": [
    {
      "id": 47,
      "date": "2026-05-28",
      "date_string": "28 Mei 2026",
      "time_string": "08:15",
      "movement_type": "IN",
      "variant_name": "Coklat",
      "qty": 200,
      "balance_after": 680,
      "created_by": "admin",
      "note": "PO-2026-007"
    },
    {
      "id": 46,
      "date": "2026-05-27",
      "date_string": "27 Mei 2026",
      "time_string": "14:30",
      "movement_type": "OUT",
      "variant_name": "Strawberry",
      "qty": 15,
      "balance_after": 245,
      "created_by": "auto-sync",
      "note": "Auto-sync: 3 event stocking"
    },
    {
      "id": 45,
      "date": "2026-05-27",
      "date_string": "27 Mei 2026",
      "time_string": "14:30",
      "movement_type": "OUT",
      "variant_name": "Coklat",
      "qty": 20,
      "balance_after": 480,
      "created_by": "auto-sync",
      "note": "Auto-sync: 4 event stocking"
    }
  ]
}
```

---

## 3.3 Endpoint 3: Input Stok Masuk (Batch)

### Request

```
POST /api/v1/inventory/stock-in
Content-Type: application/json
```

```json
{
  "items": [
    {"variant_name": "Coklat",            "qty": 605},
    {"variant_name": "Strawberry",        "qty": 540},
    {"variant_name": "Moca",              "qty": 0},
    {"variant_name": "Original (Putih)",  "qty": 365}
  ],
  "note": "PO-2026-007"
}
```

> **Catatan:** `Moca` qty=0 akan diskip — tidak di-insert ke ledger.

### Response (Sukses)

```json
{
  "success": true,
  "message": "3 varian berhasil ditambahkan ke gudang.",
  "total_added": 1510,
  "results": [
    {
      "variant_name": "Coklat",
      "qty_added": 605,
      "previous_balance": 200,
      "new_balance": 805
    },
    {
      "variant_name": "Strawberry",
      "qty_added": 540,
      "previous_balance": 150,
      "new_balance": 690
    },
    {
      "variant_name": "Original (Putih)",
      "qty_added": 365,
      "previous_balance": 50,
      "new_balance": 415
    }
  ]
}
```

### Response (Error — Validasi)

```json
{
  "success": false,
  "message": "Validasi gagal.",
  "errors": [
    "Varian 'Vanila' tidak dikenali.",
    "Semua qty harus >= 0."
  ]
}
```

### Response (Error — Tidak ada item valid)

```json
{
  "success": false,
  "message": "Tidak ada varian dengan qty > 0. Isi minimal satu varian."
}
```

---

## 3.4 Penjelasan Field per Section

### Summary

| Field | Tipe | Sumber | Keterangan |
|-------|------|--------|------------|
| `total_predicted_demand` | int | SUM(Layer1.DemandX) across 3 months | Total prediksi kuartal |
| `total_warehouse_stock` | int | SUM(warehouse_stock latest per variant) | Saldo gudang semua varian |
| `total_vm_stock` | int | SUM(manage_restok mapped to variant) | Stok di semua VM |
| `total_available` | int | warehouse + vm | Total tersedia |
| `total_to_purchase` | int | SUM(to_purchase per variant) | Total rekomendasi beli |

### Variant Item

| Field | Tipe | Sumber | Keterangan |
|-------|------|--------|------------|
| `variant_name` | string | Hardcoded 4 varian | Nama varian susu |
| `predicted_demand` | int | SUM(Layer1.DemandX) for 3 months | Prediksi kuartal untuk varian ini |
| `warehouse_stock` | int | warehouse_stock latest balance | Saldo gudang varian ini |
| `vm_stock` | int | manage_restok mapped | Stok VM varian ini |
| `total_available` | int | warehouse + vm | Total tersedia varian ini |
| `to_purchase` | int | MAX(0, predicted - available) | Rekomendasi beli |
| `purchase_percentage` | float | to_purchase / total_to_purchase * 100 | Proporsi pembelian |
| `monthly[]` | array | Layer1 per PredictedMonth | Breakdown 3 bulan |

### History Summary (hanya untuk kuartal lalu)

| Field | Tipe | Sumber | Keterangan |
|-------|------|--------|------------|
| `total_stock_in` | int | warehouse_stock IN in quarter | Total masuk dari supplier |
| `total_stock_out` | int | warehouse_stock OUT in quarter | Total keluar ke VM |
| `total_consumed` | int | monitor_log_datatransaksi (ambil) in quarter | Total diambil karyawan |
| `predicted_demand` | int | Layer1 TotalDemand | Prediksi saat itu |
| `actual_demand` | int | Layer1 ActualDemand | Konsumsi aktual |
| `prediction_accuracy` | float | 100 - MAPE | Akurasi prediksi |
| `per_variant[]` | array | Breakdown per varian | Detail per varian |
