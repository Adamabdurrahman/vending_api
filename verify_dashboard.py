from database import SessionLocal
from sqlalchemy import text
import datetime
import sys
sys.path.insert(0, ".")
import dashboard_service

db = SessionLocal()

print("=== Test get_consumption_chart (SHIFT1) ===")
result = dashboard_service.get_consumption_chart(db, "2026-01-01", "2026-02-02", "SHIFT1")
print(f"  Labels ({len(result['labels'])} items): {result['labels'][:5]}...")
print(f"  Data ({len(result['data'])} items): {result['data'][:5]}...")
print(f"  Most: {result['most']}")
print(f"  Least: {result['least']}")
print()

print("=== Test get_sales_analytics (SHIFT1) ===")
result2 = dashboard_service.get_sales_analytics(db, "2026-01-01", "2026-02-02", "SHIFT1")
print(f"  Labels: {result2['labels']}")
print(f"  Data:   {result2['data']}")
print()

print("=== Test get_latest_transactions (SHIFT1) ===")
result3 = dashboard_service.get_latest_transactions(db, "2026-01-01", "2026-02-02", "SHIFT1")
print(f"  Jumlah baris: {len(result3)}")
for r in result3:
    print(f"  -> {r}")
print()

print("=== SHIFT_SQL debug untuk SHIFT1 ===")
sql_debug, params_debug = dashboard_service.get_shift_filter_sql(db, "SHIFT1")
print(f"  shift_sql   : {repr(sql_debug)}")
print(f"  shift_params: {params_debug}")

db.close()
