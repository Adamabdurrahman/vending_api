from fastapi.testclient import TestClient
from main import app
import pandas as pd
import io
from sqlalchemy import text
from database import engine

client = TestClient(app)

print("\n=============================================")
print("TESTING ENDPOINTS: MANUAL INSERT EXCEL")
print("=============================================\n")

def cleanup_db():
    print("Cleaning up any existing test rows from database...")
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM dbo.Vending_Aggregrated WHERE is_manual_insert = 1 AND demand = 99")
        )
        print(f"Removed {deleted.rowcount} stale test rows.")

def main():
    # 0. Initial Clean up
    cleanup_db()
    
    # 1. Download Excel Template
    print("\n1. Testing GET /api/v1/manual-insert/template...")
    response_tpl = client.get("/api/v1/manual-insert/template")
    print(f"Status Code: {response_tpl.status_code}")
    assert response_tpl.status_code == 200, "Download template failed"
    
    # 2. Read downloaded file structure
    content = response_tpl.content
    df_tpl = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    print("Downloaded Excel template successfully.")
    print("Template Columns:", list(df_tpl.columns))
    print("Template Sample Rows:")
    print(df_tpl)
    
    # 3. Create a custom test DataFrame
    # 2026-06-01 is Monday (is_weekend=0)
    # 2026-06-06 is Saturday (is_weekend=1)
    # 2026-06-07 is Sunday (is_weekend=1)
    test_rows = [
        ['2026-06-01', 'SHIFT1 - AWAL', 'Coklat', 99, 0],
        ['2026-06-02', 'SHIFT2 - AWAL', 'Strawberry', 99, 0],
        ['2026-06-06', 'SHIFT3 - AWAL', 'Moca', 99, 0],
        ['2026-06-07', 'SHIFT1 - AKHIR', 'Original (Putih)', 99, 0]
    ]
    df_test = pd.DataFrame(test_rows, columns=list(df_tpl.columns))
    
    # Convert DataFrame to bytes stream for upload
    upload_buf = io.BytesIO()
    df_test.to_excel(upload_buf, index=False, engine='openpyxl')
    upload_buf.seek(0)
    
    # 4. Upload mock spreadsheet
    print("\n2. Testing POST /api/v1/manual-insert/upload (First Upload - New Rows)...")
    response_upload = client.post(
        "/api/v1/manual-insert/upload",
        files={"file": ("test_upload_insert.xlsx", upload_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    
    print(f"Status Code: {response_upload.status_code}")
    print("Response JSON:")
    res_data = response_upload.json()
    print(res_data)
    
    assert response_upload.status_code == 200, "Upload failed"
    assert res_data["success"] is True
    assert res_data["inserted_count"] == 4, f"Expected 4 inserts, got {res_data['inserted_count']}"
    assert res_data["duplicated_count"] == 0
    assert res_data["invalid_rows_skipped"] == 0
    
    # 5. Verify database records and dynamic fields
    print("\n3. Verifying dynamically generated attributes in database...")
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT tanggal, keterangan, nama_variant, demand, is_weekend, is_ramadan, is_manual_insert "
                 "FROM dbo.Vending_Aggregrated WHERE is_manual_insert = 1 AND demand = 99 "
                 "ORDER BY tanggal ASC")
        ).fetchall()
        
        for row in rows:
            print(f"Row: date={row[0]}, shift={row[1]}, variant={row[2]}, demand={row[3]}, is_weekend={row[4]}, is_ramadan={row[5]}, is_manual={row[6]}")
            
            # Assert weekend flags
            if str(row[0]) in ["2026-06-01", "2026-06-02"]:
                assert row[4] == 0, f"Expected is_weekend=0 for {row[0]}, got {row[4]}"
            elif str(row[0]) in ["2026-06-06", "2026-06-07"]:
                assert row[4] == 1, f"Expected is_weekend=1 for {row[0]}, got {row[4]}"
                
            # Assert manual insert flag
            assert row[6] == True or row[6] == 1, f"Expected is_manual_insert to be True, got {row[6]}"
            
    # 6. Re-upload the exact same spreadsheet to verify duplication prevention
    print("\n4. Testing POST /api/v1/manual-insert/upload (Second Upload - Duplicate Rows)...")
    # Reset bytes buffer pointer
    upload_buf.seek(0)
    response_dup = client.post(
        "/api/v1/manual-insert/upload",
        files={"file": ("test_upload_insert.xlsx", upload_buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    
    print(f"Status Code: {response_dup.status_code}")
    print("Response JSON:")
    res_dup_data = response_dup.json()
    print(res_dup_data)
    
    assert response_dup.status_code == 200, "Second upload failed"
    assert res_dup_data["success"] is True
    assert res_dup_data["inserted_count"] == 0, f"Expected 0 inserts on duplicate upload, got {res_dup_data['inserted_count']}"
    assert res_dup_data["duplicated_count"] == 4, f"Expected 4 duplicates skipped, got {res_dup_data['duplicated_count']}"
    assert res_dup_data["invalid_rows_skipped"] == 0
    
    # 7. Final Clean up
    print("\n5. Cleaning up database to keep staging pristine...")
    cleanup_db()
    print("Cleanup completed successfully.")
    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
