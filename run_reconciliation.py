"""
run_reconciliation.py
=====================
Eksekusi satu kali rekonsiliasi opening balance gudang.

Konsep:
  Semua susu yang pernah masuk ke VM (stocking 2023-2026 Q1)
  pasti pernah ada di gudang terlebih dahulu.

  Maka: IN gudang = total stocking ke VM sepanjang history.
  Balance setelah rekonsiliasi = 0.
  Ini adalah titik awal sistem Q1 2026.

Tanggal entry: 2022-12-31 (sebelum semua data, tidak masuk kuartal manapun)
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

# Nilai dari query check_stocking.py (sudah terverifikasi):
RECONCILIATION = {
    "Coklat": 2_310_118,
    "Strawberry": 1_415_789,
    "Moca": 883_492,
    "Original (Putih)": 920_149,
}

print("=" * 60)
print("REKONSILIASI OPENING BALANCE GUDANG")
print("Tanggal: 2022-12-31 (sebelum data pertama)")
print("=" * 60)
print()

# Cek saldo sekarang sebelum rekonsiliasi
print("Saldo SEBELUM rekonsiliasi:")
for variant, total_out in RECONCILIATION.items():
    r = client.get(f"/api/v1/inventory/movements?variant={variant}&type=OUT&per_page=1")
    d = r.json()
    # ambil balance terakhir dari GET dashboard
    pass

r = client.get("/api/v1/inventory/dashboard?year=2026&quarter=1")
d = r.json()
if d.get("variants"):
    for v in d["variants"]:
        print(f"  {v['variant_name']:22} wh = {v['warehouse_stock']:>12,}")

print()
print("Mengirim rekonsiliasi...")

payload = {
    "items": [{"variant_name": k, "qty": v} for k, v in RECONCILIATION.items()],
    "note": "Opening balance rekonsiliasi - total stocking ke VM 2023-2026 Q1",
    "date": "2022-12-31",
}

resp = client.post("/api/v1/inventory/stock-in", json=payload)
print(f"Status: {resp.status_code}")

if resp.status_code == 201:
    result = resp.json()
    print(f"entry_date    : {result['entry_date']}")
    print(f"is_adjustment : {result['is_adjustment']}")
    print(f"total_added   : {result['total_added']:,}")
    print()
    print("Detail per variant:")
    for r2 in result["results"]:
        print(
            f"  {r2['variant_name']:22} +{r2['qty_added']:>10,}  "
            f"prev={r2['previous_balance']:>12,}  new={r2['new_balance']:>12,}"
        )
else:
    print(f"ERROR: {resp.text}")

print()
print("Saldo SETELAH rekonsiliasi:")
r3 = client.get("/api/v1/inventory/dashboard?year=2026&quarter=1")
d3 = r3.json()
if d3.get("variants"):
    for v in d3["variants"]:
        status = "OK" if v["warehouse_stock"] >= 0 else "MASIH NEGATIF"
        print(f"  {v['variant_name']:22} wh = {v['warehouse_stock']:>12,}  [{status}]")

print()
print("=" * 60)
print("Rekonsiliasi selesai.")
print("Sistem sekarang dimulai dari Q1 2026 dengan balance = 0.")
print("=" * 60)
