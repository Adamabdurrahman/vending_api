"""
run_clean_reconciliation.py
===========================
Hapus semua data warehouse_stock lama, lalu rekonsiliasi bersih.

Logika:
  1. Hapus semua entry di warehouse_stock
  2. Insert IN per variant = total stocking ke VM 2023-2026 Q1
     (dated 2022-12-31, sebelum semua data)
  3. Panggil dashboard → auto-sync jalan → insert OUT = jumlah sama
  4. Hasil: balance = IN - OUT = 0  ← ini yang diinginkan
"""

from fastapi.testclient import TestClient
from sqlalchemy import text

from database import engine
from main import app

client = TestClient(app)

# Nilai terverifikasi dari check_stocking.py
OPENING = {
    "Coklat": 2_310_118,
    "Strawberry": 1_415_789,
    "Moca": 883_492,
    "Original (Putih)": 920_149,
}

# ── STEP 1: Hapus semua entry ─────────────────────────────────────────────────
print("STEP 1 — Hapus semua entry warehouse_stock...")
with engine.begin() as conn:
    result = conn.execute(text("DELETE FROM dbo.warehouse_stock"))
    print(f"  {result.rowcount} entry dihapus.")

# ── STEP 2: Insert IN opening balance ────────────────────────────────────────
print("\nSTEP 2 — Insert opening balance IN per variant (2022-12-31)...")
with engine.begin() as conn:
    for variant, qty in OPENING.items():
        conn.execute(
            text("""
                INSERT INTO dbo.warehouse_stock
                    (variant_name, movement_type, qty, balance_after, note, created_by, created_at)
                VALUES
                    (:v, 'IN', :qty, :bal, :note, 'system', '2022-12-31')
            """),
            {
                "v": variant,
                "qty": qty,
                "bal": qty,  # balance setelah entry ini = qty (mulai dari 0)
                "note": "Opening balance rekonsiliasi - total stocking ke VM 2023-2026 Q1",
            },
        )
        print(f"  IN {variant:22} = {qty:>10,}  balance_after = {qty:>10,}")

# ── STEP 3: Trigger auto-sync via dashboard ───────────────────────────────────
print("\nSTEP 3 — Trigger auto-sync (panggil dashboard)...")
r = client.get("/api/v1/inventory/dashboard?year=2026&quarter=1")
d = r.json()

sync = d.get("auto_sync_info", {})
print(f"  Auto-sync: {sync.get('note')}")
print(f"  Processed variants : {sync.get('processed_variants')}")
print(
    f"  Total OUT qty      : {sync.get('total_out_qty'):,}"
    if sync.get("total_out_qty")
    else "  Total OUT qty      : 0"
)

# ── STEP 4: Verifikasi balance ────────────────────────────────────────────────
print("\nSTEP 4 — Verifikasi balance akhir...")
if d.get("variants"):
    semua_ok = True
    for v in d["variants"]:
        wh = v["warehouse_stock"]
        status = "OK (nol)" if wh == 0 else ("POSITIF" if wh > 0 else "NEGATIF")
        print(f"  {v['variant_name']:22} balance = {wh:>10,}  [{status}]")
        if wh != 0:
            semua_ok = False
    print()
    if semua_ok:
        print("  Semua balance = 0. Rekonsiliasi berhasil sempurna.")
    else:
        print(
            "  Catatan: balance tidak tepat 0, ada selisih kecil dari entry test sebelumnya."
        )
        print("  Untuk memperbaiki, jalankan script ini sekali lagi.")

# ── STEP 5: Cek history summary Q1 ───────────────────────────────────────────
print("\nSTEP 5 — Cek history summary Q1 2026...")
if d.get("history_summary"):
    h = d["history_summary"]
    print(f"  stock_in  : {h['total_stock_in']:,}")
    print(f"  stock_out : {h['total_stock_out']:,}")
    print(f"  consumed  : {h['total_consumed']:,}")
    print(f"  accuracy  : {h['prediction_accuracy']}%")
else:
    print("  (history summary tidak tersedia)")

print("\n" + "=" * 60)
print("Rekonsiliasi selesai.")
print("Warehouse stock dimulai dari balance = 0 per Q1 2026.")
print("=" * 60)
