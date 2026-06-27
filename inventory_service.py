"""
inventory_service.py
================================================================================
Business logic untuk Inventory Dashboard + DSS (Decision Support System).
Dibangun berdasarkan Plan/InventoryDashboard/01–04.

Tiga alur utama:
  A. Stok Masuk   : Manual oleh admin → POST /api/v1/inventory/stock-in
  B. Stok Keluar  : Auto-sync dari event stocking VM → dijalankan tiap GET dashboard
  C. Kalkulasi DSS: Prediksi − Gudang − VM = Rekomendasi Beli

Tabel yang digunakan:
  - dbo.warehouse_stock          (BARU — ledger gudang)
  - dbo.manage_restok            (snapshot stok VM per slot)
  - dbo.manage_map_slot_number   (mapping slot → variant)
  - dbo.master_variant           (nama variant)
  - dbo.ForecastResults_Layer1   (prediksi per bulan per variant)
  - dbo.monitor_log_datatransaksi(log event ambil / stocking)
================================================================================
"""

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

import schemas

# ── Konstanta ─────────────────────────────────────────────────────────────────

VARIANTS = ["Coklat", "Strawberry", "Moca", "Original (Putih)"]

_MONTH_ABBR = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Agu",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Des",
}

_MONTH_FULL = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember",
}


# ── Helper: utilitas kuartal ───────────────────────────────────────────────────


def _quarter_months(year: int, quarter: int) -> tuple[str, str, str]:
    """Kembalikan 3 string PredictedMonth untuk satu kuartal."""
    base = (quarter - 1) * 3 + 1
    return (
        f"{year}-{base:02d}",
        f"{year}-{base + 1:02d}",
        f"{year}-{base + 2:02d}",
    )


def _quarter_date_range(year: int, quarter: int) -> tuple[dt.datetime, dt.datetime]:
    """Kembalikan (start_dt, end_dt) untuk satu kuartal (inklusif)."""
    base = (quarter - 1) * 3 + 1
    start = dt.datetime(year, base, 1, 0, 0, 0)
    end_month = base + 2
    # Hari terakhir bulan ke-3 kuartal
    if end_month == 12:
        end = dt.datetime(year, 12, 31, 23, 59, 59)
    else:
        end = dt.datetime(year, end_month + 1, 1) - dt.timedelta(seconds=1)
    return start, end


def get_quarter_label(year: int, quarter: int) -> str:
    """Contoh: 'Q3 2026 (Jul - Agu - Sep)'"""
    base = (quarter - 1) * 3 + 1
    return (
        f"Q{quarter} {year} "
        f"({_MONTH_ABBR[base]} - {_MONTH_ABBR[base + 1]} - {_MONTH_ABBR[base + 2]})"
    )


def is_past_quarter(year: int, quarter: int) -> bool:
    today = dt.date.today()
    current_quarter = (today.month - 1) // 3 + 1
    if year < today.year:
        return True
    if year == today.year and quarter < current_quarter:
        return True
    return False


def _default_year_quarter() -> tuple[int, int]:
    """Default: kuartal berikutnya dari sekarang."""
    today = dt.date.today()
    current_quarter = (today.month - 1) // 3 + 1
    if current_quarter < 4:
        return today.year, current_quarter + 1
    return today.year + 1, 1


# ── Modul: Gudang (warehouse_stock) ───────────────────────────────────────────


def get_latest_balance(db: Session, variant_name: str) -> int:
    """
    Ambil saldo gudang terakhir untuk satu variant.
    Menggunakan MAX(id) sebagai proxy untuk baris terbaru.
    Mengembalikan 0 jika belum ada riwayat.
    """
    row = db.execute(
        text(
            "SELECT TOP 1 balance_after FROM dbo.warehouse_stock "
            "WHERE variant_name = :v ORDER BY id DESC"
        ),
        {"v": variant_name},
    ).fetchone()
    return int(row[0]) if row else 0


def get_all_balances(db: Session) -> dict:
    """Saldo gudang semua 4 variant sekarang."""
    return {v: get_latest_balance(db, v) for v in VARIANTS}


# ── Modul: Stok VM ─────────────────────────────────────────────────────────────


def get_vm_stock_by_variant(db: Session) -> dict:
    """
    Hitung total stok di semua VM per variant.
    Join: manage_restok → manage_map_slot_number → master_variant
    Catatan: status_restok di DB adalah VARCHAR ('1' = aktif).
    """
    sql = text("""
        SELECT
            v.nama_variant,
            ISNULL(SUM(r.stok_qty), 0) AS total_qty
        FROM dbo.manage_restok r
        JOIN dbo.manage_map_slot_number m
            ON r.id_recnum_mav = m.id_recnum_mav
            AND SUBSTRING(r.slot_number, 1, 1) = m.slot_name
        JOIN dbo.master_variant v
            ON m.id_recnum_variant = v.id_recnum_variant
        WHERE r.status_restok = '1'
        GROUP BY v.nama_variant
    """)
    rows = db.execute(sql).fetchall()

    result = {v: 0 for v in VARIANTS}
    for row in rows:
        if row[0] in result:
            result[row[0]] = int(row[1])
    return result


# ── Modul: Auto-Sync OUT (Alur B) ─────────────────────────────────────────────


def _get_sync_watermark(db: Session):
    """
    Ambil timestamp OUT terakhir yang diproses auto-sync.
    None = belum pernah sync sama sekali → proses semua stocking events.
    """
    row = db.execute(
        text(
            "SELECT MAX(created_at) FROM dbo.warehouse_stock "
            "WHERE movement_type = 'OUT' AND created_by = 'auto-sync'"
        )
    ).fetchone()
    return row[0] if (row and row[0] is not None) else None


def sync_warehouse_out(db: Session) -> dict:
    """
    Alur B: Deteksi event stocking baru → aggregasi per variant →
    insert OUT entries ke warehouse_stock.

    Menggunakan watermark agar tidak ada data dobel.
    """
    watermark = _get_sync_watermark(db)

    # Query stocking events dari monitor_log_datatransaksi
    if watermark:
        sql = text("""
            SELECT
                t.id_recnum_mav,
                t.slot_number,
                t.qty,
                t.update_time,
                v.nama_variant
            FROM dbo.monitor_log_datatransaksi t
            LEFT JOIN dbo.manage_map_slot_number m
                ON t.id_recnum_mav = m.id_recnum_mav
                AND SUBSTRING(t.slot_number, 1, 1) = m.slot_name
            LEFT JOIN dbo.master_variant v
                ON m.id_recnum_variant = v.id_recnum_variant
            WHERE t.kategori_transaksi = 'stocking'
              AND t.status_transaksi = '1'
              AND t.update_time > :watermark
            ORDER BY t.update_time ASC
        """)
        rows = db.execute(sql, {"watermark": watermark}).fetchall()
    else:
        sql = text("""
            SELECT
                t.id_recnum_mav,
                t.slot_number,
                t.qty,
                t.update_time,
                v.nama_variant
            FROM dbo.monitor_log_datatransaksi t
            LEFT JOIN dbo.manage_map_slot_number m
                ON t.id_recnum_mav = m.id_recnum_mav
                AND SUBSTRING(t.slot_number, 1, 1) = m.slot_name
            LEFT JOIN dbo.master_variant v
                ON m.id_recnum_variant = v.id_recnum_variant
            WHERE t.kategori_transaksi = 'stocking'
              AND t.status_transaksi = '1'
            ORDER BY t.update_time ASC
        """)
        rows = db.execute(sql).fetchall()

    # Aggregasi qty per variant (skip jika mapping tidak ketemu)
    aggregated: dict[str, int] = {}
    events_processed = 0
    # index: [0]=id_recnum_mav, [1]=slot_number, [2]=qty, [3]=update_time, [4]=nama_variant
    for row in rows:
        variant = row[4]  # nama_variant (bisa None jika mapping tidak ditemukan)
        if not variant:
            continue  # Skip — slot tidak terpetakan ke variant manapun
        qty = int(row[2] or 0)
        if qty <= 0:
            continue
        aggregated[variant] = aggregated.get(variant, 0) + qty
        events_processed += 1

    if not aggregated:
        return {
            "processed_variants": 0,
            "total_out_qty": 0,
            "note": "Tidak ada event stocking baru yang perlu disinkronisasi.",
            "watermark": str(watermark) if watermark else None,
        }

    # Insert OUT entries
    total_out = 0
    sync_time = dt.datetime.now()
    for variant, qty in aggregated.items():
        prev_balance = get_latest_balance(db, variant)
        new_balance = prev_balance - qty  # Bisa negatif jika belum ada stok awal

        db.execute(
            text("""
                INSERT INTO dbo.warehouse_stock
                    (variant_name, movement_type, qty, balance_after, note, created_by, created_at)
                VALUES
                    (:v, 'OUT', :qty, :bal, :note, 'auto-sync', :ts)
            """),
            {
                "v": variant,
                "qty": qty,
                "bal": new_balance,
                "note": f"Auto-sync: {events_processed} event stocking",
                "ts": sync_time,
            },
        )
        total_out += qty

    db.commit()

    return {
        "processed_variants": len(aggregated),
        "total_out_qty": total_out,
        "note": f"Auto-sync berhasil: {events_processed} event stocking → {len(aggregated)} variant.",
        "watermark": str(watermark) if watermark else None,
    }


# ── Modul: Prediksi (ForecastResults_Layer1) ──────────────────────────────────


def _get_forecast_data(db: Session, year: int, quarter: int) -> tuple[bool, dict, dict]:
    """
    Ambil prediksi dari ForecastResults_Layer1 untuk 3 bulan dalam kuartal.

    Returns:
        (has_data, forecast_per_variant, monthly_per_variant)
        forecast_per_variant = {"Coklat": 850, ...}  (total 3 bulan)
        monthly_per_variant  = {"Coklat": [{month_name, month_number, predicted}, ...]}
    """
    m1, m2, m3 = _quarter_months(year, quarter)

    rows = db.execute(
        text("""
            SELECT
                PredictedMonth,
                ISNULL(DemandCoklat,        0) AS DemandCoklat,
                ISNULL(DemandStrawberry,    0) AS DemandStrawberry,
                ISNULL(DemandMoca,          0) AS DemandMoca,
                ISNULL(DemandOriginal,      0) AS DemandOriginal,
                ISNULL(TotalDemand,         0) AS TotalDemand
            FROM dbo.ForecastResults_Layer1
            WHERE PredictedMonth IN (:m1, :m2, :m3)
            ORDER BY PredictedMonth ASC
        """),
        {"m1": m1, "m2": m2, "m3": m3},
    ).fetchall()

    if not rows:
        return False, {}, {}

    # Map kolom DB → nama variant
    _col_map = {
        "Coklat": 1,
        "Strawberry": 2,
        "Moca": 3,
        "Original (Putih)": 4,
    }

    forecast = {v: 0 for v in VARIANTS}
    monthly = {v: [] for v in VARIANTS}

    for row in rows:
        month_str = row[0]
        month_num = int(month_str.split("-")[1])
        month_name = _MONTH_FULL.get(month_num, month_str)

        for variant, col_idx in _col_map.items():
            qty = int(row[col_idx] or 0)
            forecast[variant] += qty
            monthly[variant].append(
                {
                    "month_name": month_name,
                    "month_number": month_num,
                    "predicted": qty,
                }
            )

    return True, forecast, monthly


# ── Modul: DSS Calculation ──────────────────────────────────────────────────────


def _calculate_purchase(
    forecast: dict, warehouse: dict, vm_stock: dict
) -> tuple[list, int]:
    """
    Hitung rekomendasi pembelian per variant.
    Rumus: to_purchase = MAX(0, predicted - warehouse - vm_stock)

    Returns:
        (variants_list, total_to_purchase)
    """
    total_to_purchase = 0
    items = []

    for v in VARIANTS:
        predicted = forecast.get(v, 0)
        wh_stock = warehouse.get(v, 0)
        vm_qty = vm_stock.get(v, 0)
        available = wh_stock + vm_qty
        to_buy = max(0, predicted - available)

        items.append(
            {
                "variant_name": v,
                "predicted_demand": predicted,
                "warehouse_stock": wh_stock,
                "vm_stock": vm_qty,
                "total_available": available,
                "to_purchase": to_buy,
                "purchase_percentage": 0.0,  # dihitung setelah total diketahui
                "monthly": [],  # diisi setelah ini
            }
        )
        total_to_purchase += to_buy

    # Hitung persentase pembelian
    for item in items:
        if total_to_purchase > 0:
            item["purchase_percentage"] = round(
                item["to_purchase"] / total_to_purchase * 100, 1
            )

    return items, total_to_purchase


# ── Modul: Available Quarters ───────────────────────────────────────────────────


def get_available_quarters(db: Session) -> list:
    """
    Query kuartal yang tersedia secara dinamis dari ForecastResults_Layer1.
    """
    rows = db.execute(
        text("""
            SELECT DISTINCT
                CAST(LEFT(PredictedMonth, 4) AS INT) AS yr,
                CEILING(CAST(RIGHT(PredictedMonth, 2) AS INT) / 3.0) AS qtr
            FROM dbo.ForecastResults_Layer1
            ORDER BY 1 DESC, 2 DESC
        """)
    ).fetchall()

    result = []
    for row in rows:
        y, q = int(row[0]), int(row[1])
        result.append(
            {
                "year": y,
                "quarter": q,
                "label": f"Q{q} {y}",
            }
        )
    return result


# ── Modul: History Summary (kuartal lalu) ──────────────────────────────────────


def get_history_summary(db: Session, year: int, quarter: int) -> dict:
    """
    Hitung ringkasan historis untuk kuartal yang sudah lewat.
    Mengembalikan total IN/OUT gudang, konsumsi aktual, dan breakdown per variant.
    """
    start_dt, end_dt = _quarter_date_range(year, quarter)
    m1, m2, m3 = _quarter_months(year, quarter)

    # Total IN gudang dalam kuartal
    total_in = (
        db.execute(
            text(
                "SELECT ISNULL(SUM(qty), 0) FROM dbo.warehouse_stock "
                "WHERE movement_type = 'IN' AND created_at >= :s AND created_at <= :e"
            ),
            {"s": start_dt, "e": end_dt},
        ).scalar()
        or 0
    )

    # Total OUT gudang dalam kuartal
    total_out = (
        db.execute(
            text(
                "SELECT ISNULL(SUM(qty), 0) FROM dbo.warehouse_stock "
                "WHERE movement_type = 'OUT' AND created_at >= :s AND created_at <= :e"
            ),
            {"s": start_dt, "e": end_dt},
        ).scalar()
        or 0
    )

    # Total konsumsi (event ambil) dalam kuartal
    total_consumed = (
        db.execute(
            text(
                "SELECT COUNT(*) FROM dbo.monitor_log_datatransaksi "
                "WHERE kategori_transaksi = 'ambil' "
                "AND update_time >= :s AND update_time <= :e"
            ),
            {"s": start_dt, "e": end_dt},
        ).scalar()
        or 0
    )

    # Prediksi vs aktual dari Layer1
    forecast_row = db.execute(
        text("""
            SELECT
                ISNULL(SUM(TotalDemand),  0) AS pred,
                ISNULL(SUM(ActualDemand), 0) AS act,
                AVG(MAPE_Total)              AS mape
            FROM dbo.ForecastResults_Layer1
            WHERE PredictedMonth IN (:m1, :m2, :m3)
        """),
        {"m1": m1, "m2": m2, "m3": m3},
    ).fetchone()

    predicted_demand = int(forecast_row[0] or 0)
    actual_demand = int(forecast_row[1] or 0)
    mape = float(forecast_row[2] or 0)
    accuracy = round(100.0 - mape, 1) if mape else 0.0

    # ── Per-variant breakdown ──────────────────────────────────────────────────

    # Prediksi per variant (dari Layer1)
    pred_rows = db.execute(
        text("""
            SELECT
                ISNULL(SUM(DemandCoklat),        0),
                ISNULL(SUM(DemandStrawberry),    0),
                ISNULL(SUM(DemandMoca),          0),
                ISNULL(SUM(DemandOriginal),      0)
            FROM dbo.ForecastResults_Layer1
            WHERE PredictedMonth IN (:m1, :m2, :m3)
        """),
        {"m1": m1, "m2": m2, "m3": m3},
    ).fetchone()
    pred_per_variant = {
        "Coklat": int(pred_rows[0] or 0) if pred_rows else 0,
        "Strawberry": int(pred_rows[1] or 0) if pred_rows else 0,
        "Moca": int(pred_rows[2] or 0) if pred_rows else 0,
        "Original (Putih)": int(pred_rows[3] or 0) if pred_rows else 0,
    }

    # IN per variant dari warehouse_stock
    in_rows = db.execute(
        text("""
            SELECT variant_name, ISNULL(SUM(qty), 0)
            FROM dbo.warehouse_stock
            WHERE movement_type = 'IN'
              AND created_at >= :s AND created_at <= :e
            GROUP BY variant_name
        """),
        {"s": start_dt, "e": end_dt},
    ).fetchall()
    in_per_variant = {v: 0 for v in VARIANTS}
    for row in in_rows:
        if row[0] in in_per_variant:
            in_per_variant[row[0]] = int(row[1])

    # OUT per variant dari warehouse_stock
    out_rows = db.execute(
        text("""
            SELECT variant_name, ISNULL(SUM(qty), 0)
            FROM dbo.warehouse_stock
            WHERE movement_type = 'OUT'
              AND created_at >= :s AND created_at <= :e
            GROUP BY variant_name
        """),
        {"s": start_dt, "e": end_dt},
    ).fetchall()
    out_per_variant = {v: 0 for v in VARIANTS}
    for row in out_rows:
        if row[0] in out_per_variant:
            out_per_variant[row[0]] = int(row[1])

    # Konsumsi (ambil) per variant — butuh JOIN ke mapping slot
    consumed_rows = db.execute(
        text("""
            SELECT
                v.nama_variant,
                COUNT(*) AS consumed
            FROM dbo.monitor_log_datatransaksi t
            LEFT JOIN dbo.manage_map_slot_number m
                ON t.id_recnum_mav = m.id_recnum_mav
                AND SUBSTRING(t.slot_number, 1, 1) = m.slot_name
            LEFT JOIN dbo.master_variant v
                ON m.id_recnum_variant = v.id_recnum_variant
            WHERE t.kategori_transaksi = 'ambil'
              AND t.update_time >= :s AND t.update_time <= :e
              AND v.nama_variant IS NOT NULL
            GROUP BY v.nama_variant
        """),
        {"s": start_dt, "e": end_dt},
    ).fetchall()
    consumed_per_variant = {v: 0 for v in VARIANTS}
    for row in consumed_rows:
        if row[0] in consumed_per_variant:
            consumed_per_variant[row[0]] = int(row[1])

    per_variant = [
        {
            "variant_name": v,
            "stock_in": in_per_variant[v],
            "stock_out": out_per_variant[v],
            "consumed": consumed_per_variant[v],
            "predicted": pred_per_variant[v],
            "actual": consumed_per_variant[v],  # aktual = apa yang benar-benar diambil
        }
        for v in VARIANTS
    ]

    return {
        "total_stock_in": int(total_in),
        "total_stock_out": int(total_out),
        "total_consumed": int(total_consumed),
        "predicted_demand": predicted_demand,
        "actual_demand": actual_demand,
        "prediction_accuracy": accuracy,
        "per_variant": per_variant,
    }


# ── ENDPOINT 1: GET /api/v1/inventory/dashboard ────────────────────────────────


def get_inventory_dashboard(db: Session, year: int = None, quarter: int = None) -> dict:
    """
    Main orchestrator untuk Inventory Dashboard.
    Urutan eksekusi: Alur B (sync) → Alur C (DSS calc) → build response.
    """
    # Default: kuartal berikutnya
    if year is None or quarter is None:
        _y, _q = _default_year_quarter()
        year = year if year is not None else _y
        quarter = quarter if quarter is not None else _q

    # Validasi quarter range
    if quarter < 1 or quarter > 4:
        raise HTTPException(status_code=400, detail="quarter harus antara 1 dan 4")

    # STEP 0 — Alur B: Auto-sync stocking events → warehouse OUT
    sync_result = sync_warehouse_out(db)

    # STEP 1 — Available quarters (dinamis dari Layer1)
    available_quarters = get_available_quarters(db)

    # STEP 2 — Cek apakah ada data prediksi
    has_data, forecast, monthly = _get_forecast_data(db, year, quarter)

    if not has_data:
        return {
            "year": year,
            "quarter": quarter,
            "quarter_label": get_quarter_label(year, quarter),
            "has_prediction_data": False,
            "available_quarters": available_quarters,
            "summary": None,
            "variants": [],
            "history_summary": None,
            "auto_sync_info": sync_result,
        }

    # STEP 3 — Ambil stok gudang & VM
    warehouse = get_all_balances(db)
    vm_stock = get_vm_stock_by_variant(db)

    # STEP 4 — Kalkulasi DSS
    variant_items, total_to_purchase = _calculate_purchase(
        forecast, warehouse, vm_stock
    )

    # Attach monthly breakdown ke setiap variant
    for item in variant_items:
        item["monthly"] = monthly.get(item["variant_name"], [])

    # STEP 5 — Summary
    summary = {
        "total_predicted_demand": sum(forecast.values()),
        "total_warehouse_stock": sum(warehouse.values()),
        "total_vm_stock": sum(vm_stock.values()),
        "total_available": sum(warehouse.values()) + sum(vm_stock.values()),
        "total_to_purchase": total_to_purchase,
    }

    # STEP 6 — History (hanya jika kuartal sudah lewat)
    history_summary = None
    if is_past_quarter(year, quarter):
        history_summary = get_history_summary(db, year, quarter)

    # STEP 7 — Decision support notes
    sorted_by_buy = sorted(variant_items, key=lambda x: x["to_purchase"], reverse=True)
    notes = []
    if total_to_purchase == 0:
        notes.append(
            "Stok gudang dan VM mencukupi untuk kuartal ini. Tidak perlu pembelian tambahan."
        )
    else:
        top = sorted_by_buy[0]
        notes.append(
            f"Rekomendasi pembelian utama: {top['variant_name']} sebanyak {top['to_purchase']:,} unit "
            f"({top['purchase_percentage']}% dari total)."
        )
        if any(warehouse[v] < 0 for v in VARIANTS):
            notes.append(
                "⚠️ Saldo gudang negatif terdeteksi. "
                "Silakan input stok awal gudang agar kalkulasi DSS akurat."
            )
        if sync_result["processed_variants"] > 0:
            notes.append(
                f"Auto-sync memproses {sync_result['processed_variants']} variant "
                f"({sync_result['total_out_qty']:,} unit keluar ke VM)."
            )

    decision_support = {
        "recommended_purchase_total": total_to_purchase,
        "top_variant": sorted_by_buy[0]["variant_name"]
        if total_to_purchase > 0
        else "",
        "top_variant_qty": sorted_by_buy[0]["to_purchase"]
        if total_to_purchase > 0
        else 0,
        "notes": notes,
    }

    return {
        "year": year,
        "quarter": quarter,
        "quarter_label": get_quarter_label(year, quarter),
        "has_prediction_data": True,
        "available_quarters": available_quarters,
        "summary": summary,
        "variants": variant_items,
        "history_summary": history_summary,
        "decision_support": decision_support,
        "auto_sync_info": sync_result,
    }


# ── ENDPOINT 2: GET /api/v1/inventory/movements ───────────────────────────────


def get_stock_movements(
    db: Session,
    page: int = 1,
    per_page: int = 10,
    variant: str = None,
    movement_type: str = None,
) -> dict:
    """
    Riwayat pergerakan stok gudang dengan paginasi.
    Diurutkan terbaru dulu (created_at DESC).
    """
    per_page = min(max(1, per_page), 50)  # clamp 1–50
    offset = (page - 1) * per_page

    where_parts = ["1=1"]
    params: dict = {"offset": offset, "limit": per_page}

    if variant:
        where_parts.append("variant_name = :variant")
        params["variant"] = variant

    if movement_type:
        mt = movement_type.upper()
        if mt not in ("IN", "OUT"):
            raise HTTPException(status_code=400, detail="type harus 'IN' atau 'OUT'")
        where_parts.append("movement_type = :mt")
        params["mt"] = mt

    where_clause = " AND ".join(where_parts)

    total_items = (
        db.execute(
            text(f"SELECT COUNT(*) FROM dbo.warehouse_stock WHERE {where_clause}"),
            params,
        ).scalar()
        or 0
    )

    rows = db.execute(
        text(f"""
            SELECT
                id, variant_name, movement_type,
                qty, balance_after, note, created_by, created_at
            FROM dbo.warehouse_stock
            WHERE {where_clause}
            ORDER BY created_at DESC
            OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
        """),
        params,
    ).fetchall()

    total_pages = max(1, (total_items + per_page - 1) // per_page)

    items = []
    for r in rows:
        created_at = r[7]
        items.append(
            {
                "id": r[0],
                "date": created_at.strftime("%Y-%m-%d") if created_at else "",
                "date_string": created_at.strftime("%d %b %Y") if created_at else "",
                "time_string": created_at.strftime("%H:%M") if created_at else "",
                "variant_name": r[1],
                "movement_type": r[2],
                "qty": int(r[3]),
                "balance_after": int(r[4]),
                "note": r[5],
                "created_by": r[6],
            }
        )

    return {
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "items": items,
    }


# ── ENDPOINT 3: POST /api/v1/inventory/stock-in ───────────────────────────────


def add_stock_in(db: Session, request: schemas.InventoryStockInRequest) -> dict:
    """
    Alur A: Catat stok masuk dari supplier ke gudang.
    Batch insert — item dengan qty = 0 diskip (bukan error).
    Minimal 1 item harus qty > 0.

    Parameter `date` opsional (format YYYY-MM-DD):
    - Tidak diisi → pakai tanggal hari ini (default, stok baru)
    - Diisi       → pakai tanggal tersebut (untuk input data historis / penyesuaian)
    """
    # Validasi
    errors = []
    for item in request.items:
        if item.variant_name not in VARIANTS:
            errors.append(f"Varian '{item.variant_name}' tidak dikenali.")
        if item.qty < 0:
            errors.append("Semua qty harus >= 0.")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"success": False, "message": "Validasi gagal.", "errors": errors},
        )

    valid_items = [i for i in request.items if i.qty > 0]
    if not valid_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "Tidak ada varian dengan qty > 0. Isi minimal satu varian.",
            },
        )

    # Tentukan timestamp: pakai request.date jika ada, fallback ke sekarang
    if request.date:
        try:
            entry_ts = dt.datetime.strptime(request.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Format date tidak valid: '{request.date}'. Gunakan YYYY-MM-DD.",
            )
    else:
        entry_ts = dt.datetime.now()

    results = []
    total_added = 0
    note = (request.note or "")[:200]

    for item in valid_items:
        prev_balance = get_latest_balance(db, item.variant_name)
        new_balance = prev_balance + item.qty

        db.execute(
            text("""
                INSERT INTO dbo.warehouse_stock
                    (variant_name, movement_type, qty, balance_after, note, created_by, created_at)
                VALUES
                    (:v, 'IN', :qty, :bal, :note, 'admin', :ts)
            """),
            {
                "v": item.variant_name,
                "qty": item.qty,
                "bal": new_balance,
                "note": note if note else None,
                "ts": entry_ts,
            },
        )
        results.append(
            {
                "variant_name": item.variant_name,
                "qty_added": item.qty,
                "previous_balance": prev_balance,
                "new_balance": new_balance,
            }
        )
        total_added += item.qty

    db.commit()

    is_adjustment = request.date is not None
    return {
        "success": True,
        "message": f"{len(results)} varian berhasil ditambahkan ke gudang.",
        "entry_date": entry_ts.strftime("%Y-%m-%d"),
        "is_adjustment": is_adjustment,
        "total_added": total_added,
        "results": results,
        "errors": None,
    }
