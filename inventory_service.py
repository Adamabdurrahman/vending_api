"""
Inventory Service Module
Menangani Inventory Dashboard + DSS logic sesuai dokumen InventoryDashboard.
"""

from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, func
import schemas
import models
from fastapi import HTTPException, status

VARIANTS = [
    "Coklat",
    "Strawberry",
    "Moca",
    "Original (Putih)"
]


def get_latest_balance(db: Session, variant_name: str) -> int:
    row = db.execute(
        text(
            "SELECT TOP 1 balance_after FROM dbo.warehouse_stock "
            "WHERE variant_name = :variant_name "
            "ORDER BY id DESC"
        ),
        {"variant_name": variant_name},
    ).fetchone()

    return row[0] if row else 0


def get_all_balances(db: Session) -> dict:
    balances = {}
    for variant in VARIANTS:
        balances[variant] = get_latest_balance(db, variant)
    return balances


def get_vm_stock_by_variant(db: Session) -> dict:
    sql = """
        SELECT v.nama_variant, SUM(r.stok_qty) as total_qty
        FROM dbo.manage_restok r
        LEFT JOIN dbo.manage_map_slot_number map 
            ON r.id_recnum_mav = map.id_recnum_mav
            AND SUBSTRING(r.slot_number, 1, 1) = map.slot_name
        LEFT JOIN dbo.master_variant v
            ON map.id_recnum_variant = v.id_recnum_variant
        WHERE r.status_restok = 1
        GROUP BY v.nama_variant
    """
    rows = db.execute(text(sql)).fetchall()
    result = {variant: 0 for variant in VARIANTS}
    for row in rows:
        if row[0] in result:
            result[row[0]] = int(row[1] or 0)
    return result


def get_auto_sync_watermark(db: Session):
    row = db.execute(
        text(
            "SELECT MAX(created_at) FROM dbo.warehouse_stock "
            "WHERE movement_type = 'OUT' AND created_by = 'auto-sync'"
        )
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def sync_warehouse_out(db: Session):
    watermark = get_auto_sync_watermark(db)
    if watermark:
        query = text(
            "SELECT t.id_recnum_mld, t.id_recnum_mav, t.slot_number, t.qty, t.update_time, v.nama_variant "
            "FROM dbo.monitor_log_datatransaksi t "
            "LEFT JOIN dbo.manage_map_slot_number map "
            "  ON t.id_recnum_mav = map.id_recnum_mav "
            "  AND SUBSTRING(t.slot_number, 1, 1) = map.slot_name "
            "LEFT JOIN dbo.master_variant v "
            "  ON map.id_recnum_variant = v.id_recnum_variant "
            "WHERE t.kategori_transaksi = 'stocking' "
            "  AND t.status_transaksi = '1' "
            "  AND t.update_time > :watermark "
            "ORDER BY t.update_time ASC"
        )
        rows = db.execute(query, {"watermark": watermark}).fetchall()
    else:
        query = text(
            "SELECT t.id_recnum_mld, t.id_recnum_mav, t.slot_number, t.qty, t.update_time, v.nama_variant "
            "FROM dbo.monitor_log_datatransaksi t "
            "LEFT JOIN dbo.manage_map_slot_number map "
            "  ON t.id_recnum_mav = map.id_recnum_mav "
            "  AND SUBSTRING(t.slot_number, 1, 1) = map.slot_name "
            "LEFT JOIN dbo.master_variant v "
            "  ON map.id_recnum_variant = v.id_recnum_variant "
            "WHERE t.kategori_transaksi = 'stocking' "
            "  AND t.status_transaksi = '1' "
            "ORDER BY t.update_time ASC"
        )
        rows = db.execute(query).fetchall()

    aggregated = {}
    events_processed = 0
    for row in rows:
        variant = row[5]
        if not variant:
            continue
        qty = int(row[3] or 0)
        if qty <= 0:
            continue
        aggregated[variant] = aggregated.get(variant, 0) + qty
        events_processed += 1

    total_out_qty = 0
    for variant, qty in aggregated.items():
        prev_balance = get_latest_balance(db, variant)
        new_balance = prev_balance - qty
        db.execute(
            text(
                "INSERT INTO dbo.warehouse_stock (variant_name, movement_type, qty, balance_after, note, created_by, created_at) "
                "VALUES (:variant_name, 'OUT', :qty, :balance_after, :note, 'auto-sync', :created_at)"
            ),
            {
                "variant_name": variant,
                "qty": qty,
                "balance_after": new_balance,
                "note": f"Auto-sync: {events_processed} event stocking",
                "created_at": datetime.now(),
            }
        )
        total_out_qty += qty
    if aggregated:
        db.commit()

    note = "Auto-sync running" if aggregated else "No new stocking events to sync"
    return {
        "processed_variants": len(aggregated),
        "total_out_qty": total_out_qty,
        "note": note,
        "watermark": watermark,
        "events_processed": events_processed,
    }


def get_inventory_forecast(db: Session, year: int, quarter: int) -> tuple[bool, dict, dict]:
    months = [
        f"{year}-{(quarter - 1) * 3 + 1:02d}",
        f"{year}-{(quarter - 1) * 3 + 2:02d}",
        f"{year}-{(quarter - 1) * 3 + 3:02d}",
    ]

    sql = text(
        "SELECT PredictedMonth, DemandCoklat, DemandStrawberry, DemandMoca, DemandOriginal, TotalDemand, ActualDemand, ErrorPercent "
        "FROM dbo.ForecastResults_Layer1 "
        "WHERE PredictedMonth IN (:m1, :m2, :m3)"
    )
    rows = db.execute(
        sql,
        {"m1": months[0], "m2": months[1], "m3": months[2]}
    ).fetchall()

    if not rows:
        return False, {}, {}

    forecast = {variant: 0 for variant in VARIANTS}
    monthly = {variant: [] for variant in VARIANTS}
    total_predicted = 0
    actual_demand = 0
    error_percent = None

    for row in rows:
        pred_month = row[0]
        demand = {
            "Coklat": int(row[1] or 0),
            "Strawberry": int(row[2] or 0),
            "Moca": int(row[3] or 0),
            "Original (Putih)": int(row[4] or 0),
        }
        total_predicted += int(row[5] or 0)
        actual_demand = int(row[6] or 0)
        error_percent = float(row[7]) if row[7] is not None else None

        month_num = int(pred_month.split("-")[1])
        month_name = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"][month_num - 1]

        for variant, qty in demand.items():
            forecast[variant] += qty
            monthly[variant].append({
                "month_name": month_name,
                "month_number": month_num,
                "predicted": qty,
            })

    return True, forecast, monthly


def calculate_to_purchase(forecast: dict, warehouse: dict, vm_stock: dict) -> tuple[list[dict], dict]:
    variants = []
    total_to_purchase = 0

    for variant in VARIANTS:
        predicted = forecast.get(variant, 0)
        warehouse_qty = warehouse.get(variant, 0)
        vm_qty = vm_stock.get(variant, 0)
        available = warehouse_qty + vm_qty
        to_purchase = max(0, predicted - available)
        variants.append({
            "variant_name": variant,
            "predicted_demand": predicted,
            "warehouse_stock": warehouse_qty,
            "vm_stock": vm_qty,
            "total_available": available,
            "to_purchase": to_purchase,
            "purchase_percentage": 0.0,
            "monthly": []
        })
        total_to_purchase += to_purchase

    for item in variants:
        item["purchase_percentage"] = round((item["to_purchase"] / total_to_purchase * 100), 1) if total_to_purchase > 0 else 0.0
    return variants, {"total_to_purchase": total_to_purchase}


def build_available_quarters(year: int, quarter: int) -> list[dict]:
    current_year = date.today().year
    quarters = []
    for y in range(current_year - 1, current_year + 1):
        for q in range(1, 5):
            if y == year and q == quarter:
                label = f"Q{q} {y} (Dipilih)"
            else:
                label = f"Q{q} {y}"
            quarters.append({"year": y, "quarter": q, "label": label})
    return sorted(quarters, key=lambda x: (x["year"], x["quarter"]), reverse=True)


def get_quarter_label(year: int, quarter: int) -> str:
    month_names = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    months = [month_names[(quarter - 1) * 3], month_names[(quarter - 1) * 3 + 1], month_names[(quarter - 1) * 3 + 2]]
    return f"Q{quarter} {year} ({months[0]} - {months[1]} - {months[2]})"


def get_inventory_dashboard(
    db: Session,
    year: int | None = None,
    quarter: int | None = None,
    page: int = 1,
    per_page: int = 10,
    variant: str | None = None,
    movement_type: str | None = None,
    request: schemas.StockInRequest | None = None,
):
    today = date.today()
    if year is None:
        year = today.year
    if quarter is None:
        quarter = (today.month - 1) // 3 + 2
        if quarter > 4:
            quarter = 1
            year += 1

    if request is not None:
        stock_in_result = add_stock_in(db, request)
    else:
        stock_in_result = None

    available_quarters = build_available_quarters(year, quarter)
    movements = get_movements(db, page, per_page, variant, movement_type)
    has_data, forecast, monthly = get_inventory_forecast(db, year, quarter)

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
            "decision_support": None,
            "auto_sync_info": None,
            "movements": movements,
            "stock_in_result": None,
        }

    warehouse = get_all_balances(db)
    vm_stock = get_vm_stock_by_variant(db)
    variants, totals = calculate_to_purchase(forecast, warehouse, vm_stock)

    for item in variants:
        item["monthly"] = monthly[item["variant_name"]]

    summary = {
        "total_predicted_demand": sum(forecast.values()),
        "total_warehouse_stock": sum(warehouse.values()),
        "total_vm_stock": sum(vm_stock.values()),
        "total_available": sum(warehouse.values()) + sum(vm_stock.values()),
        "total_to_purchase": totals["total_to_purchase"],
    }

    decision_support = {
        "recommended_purchase_total": totals["total_to_purchase"],
        "top_variant": "",
        "top_variant_qty": 0,
        "notes": []
    }
    sorted_variants = sorted(variants, key=lambda x: x["to_purchase"], reverse=True)
    if sorted_variants and sorted_variants[0]["to_purchase"] > 0:
        decision_support["top_variant"] = sorted_variants[0]["variant_name"]
        decision_support["top_variant_qty"] = sorted_variants[0]["to_purchase"]
        decision_support["notes"].append(
            f"Rekomendasi pembelian utama: {sorted_variants[0]['variant_name']} sebanyak {sorted_variants[0]['to_purchase']} unit."
        )

    if totals["total_to_purchase"] == 0:
        decision_support["notes"].append("Tidak perlu pembelian tambahan, stok gudang dan VM mencukupi untuk kuartal ini.")
    else:
        decision_support["notes"].append(
            "Hitung ulang rekomendasi jika forecast atau sisa stok gudang berubah."
        )

    history_summary = None
    if date(year, (quarter - 1) * 3 + 3, 1) < today.replace(day=1):
        history_summary = get_history_summary(db, year, quarter)

    auto_sync_result = sync_warehouse_out(db)
    auto_sync_info = {
        "processed_variants": auto_sync_result["processed_variants"],
        "total_out_qty": auto_sync_result["total_out_qty"],
        "note": auto_sync_result["note"],
    }

    if auto_sync_info["processed_variants"] > 0:
        decision_support["notes"].append(
            f"Auto-sync berhasil memproses {auto_sync_info['processed_variants']} variant dan menyesuaikan stok gudang."
        )

    return {
        "year": year,
        "quarter": quarter,
        "quarter_label": get_quarter_label(year, quarter),
        "has_prediction_data": True,
        "available_quarters": available_quarters,
        "summary": summary,
        "variants": variants,
        "history_summary": history_summary,
        "decision_support": decision_support,
        "auto_sync_info": auto_sync_info,
        "movements": movements,
        "stock_in_result": stock_in_result,
    }


def get_history_summary(db: Session, year: int, quarter: int):
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    start_date = date(year, start_month, 1)
    if end_month == 12:
        end_date = date(year, 12, 31)
    else:
        end_date = date(year, end_month + 1, 1) - timedelta(days=1)

    sql_in = text(
        "SELECT SUM(qty) FROM dbo.warehouse_stock "
        "WHERE movement_type = 'IN' "
        "AND created_at >= :start_date AND created_at <= :end_date"
    )
    sql_out = text(
        "SELECT SUM(qty) FROM dbo.warehouse_stock "
        "WHERE movement_type = 'OUT' "
        "AND created_at >= :start_date AND created_at <= :end_date"
    )
    sql_cons = text(
        "SELECT COUNT(*) FROM dbo.monitor_log_datatransaksi "
        "WHERE kategori_transaksi = 'ambil' "
        "AND update_time >= :start_date AND update_time <= :end_date"
    )
    sql_forecast = text(
        "SELECT SUM(TotalDemand), SUM(ActualDemand), AVG(MAPE_Total) "
        "FROM dbo.ForecastResults_Layer1 "
        "WHERE PredictedMonth IN (:m1, :m2, :m3)"
    )
    months = [
        f"{year}-{start_month:02d}",
        f"{year}-{start_month+1:02d}",
        f"{year}-{start_month+2:02d}",
    ]

    total_in = db.execute(sql_in, {"start_date": start_date, "end_date": end_date}).scalar() or 0
    total_out = db.execute(sql_out, {"start_date": start_date, "end_date": end_date}).scalar() or 0
    total_consumed = db.execute(sql_cons, {"start_date": start_date, "end_date": end_date}).scalar() or 0
    forecast_row = db.execute(sql_forecast, {"m1": months[0], "m2": months[1], "m3": months[2]}).fetchone()

    return {
        "total_stock_in": int(total_in),
        "total_stock_out": int(total_out),
        "total_consumed": int(total_consumed),
        "predicted_demand": int(forecast_row[0] or 0),
        "actual_demand": int(forecast_row[1] or 0),
        "prediction_accuracy": round(100.0 - float(forecast_row[2] or 0), 1) if forecast_row[2] is not None else 0.0,
        "per_variant": []
    }


def get_movements(db: Session, page: int = 1, per_page: int = 10, variant: str | None = None, type: str | None = None):
    per_page = min(per_page, 50)
    params = {"offset": (page - 1) * per_page, "limit": per_page}
    where = []

    base_sql = "FROM dbo.warehouse_stock WHERE 1=1"
    if variant:
        base_sql += " AND variant_name = :variant"
        params["variant"] = variant
    if type:
        base_sql += " AND movement_type = :movement_type"
        params["movement_type"] = type.upper()

    total_sql = f"SELECT COUNT(*) {base_sql}"
    data_sql = f"SELECT id, variant_name, movement_type, qty, balance_after, note, created_by, created_at {base_sql} ORDER BY created_at DESC OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"

    total_items = db.execute(text(total_sql), params).scalar() or 0
    rows = db.execute(text(data_sql), params).fetchall()

    items = []
    for row in rows:
        created_at = row[7]
        items.append({
            "id": row[0],
            "date": created_at.strftime("%Y-%m-%d"),
            "date_string": created_at.strftime("%d %b %Y"),
            "time_string": created_at.strftime("%H:%M"),
            "variant_name": row[1],
            "movement_type": row[2],
            "qty": int(row[3]),
            "balance_after": int(row[4]),
            "note": row[5],
            "created_by": row[6],
        })

    total_pages = (total_items + per_page - 1) // per_page
    return {
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "items": items,
    }


def add_stock_in(db: Session, request: schemas.StockInRequest):
    valid_items = []
    errors = []
    for item in request.items:
        if item.qty < 0:
            errors.append("Semua qty harus >= 0.")
        elif item.variant_name not in VARIANTS:
            errors.append(f"Varian '{item.variant_name}' tidak dikenali.")
        elif item.qty > 0:
            valid_items.append(item)

    if errors:
        return {
            "success": False,
            "message": "Validasi gagal.",
            "errors": list(dict.fromkeys(errors)),
        }

    if not valid_items:
        return {"success": False, "message": "Tidak ada varian dengan qty > 0. Isi minimal satu varian.", "errors": []}

    results = []
    total_added = 0
    for item in valid_items:
        previous_balance = get_latest_balance(db, item.variant_name)
        new_balance = previous_balance + item.qty

        db.execute(
            text(
                "INSERT INTO dbo.warehouse_stock (variant_name, movement_type, qty, balance_after, note, created_by, created_at) "
                "VALUES (:variant_name, 'IN', :qty, :balance_after, :note, :created_by, :created_at)"
            ),
            {
                "variant_name": item.variant_name,
                "qty": item.qty,
                "balance_after": new_balance,
                "note": request.note,
                "created_by": "admin",
                "created_at": datetime.now(),
            }
        )
        total_added += item.qty
        results.append({
            "variant_name": item.variant_name,
            "qty_added": item.qty,
            "previous_balance": previous_balance,
            "new_balance": new_balance,
        })

    db.commit()
    return {
        "success": True,
        "message": f"{len(results)} varian berhasil ditambahkan ke gudang.",
        "total_added": total_added,
        "results": results,
    }
