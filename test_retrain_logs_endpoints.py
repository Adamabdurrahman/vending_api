from fastapi.testclient import TestClient
from main import app
from sqlalchemy import text
from database import engine

client = TestClient(app)

print("\n=============================================")
print("TESTING ENDPOINTS: ML RETRAIN LOGS")
print("=============================================\n")

def cleanup_db():
    print("Cleaning up any existing test logs from database...")
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM dbo.RetrainLog WHERE ModelVersion LIKE 'TEST_%'")
        )
        print(f"Removed {deleted.rowcount} stale test logs.")

def insert_test_logs():
    print("Inserting mock chronological retrain logs for sequence testing...")
    test_data = [
        # Chronological order of runs
        ('2026-01-01 02:00:00', 'TEST_v1', 5.5, 10.0, 12.0, 1000, '2025-12', '{"p":1}', 'Success'),
        ('2026-02-01 02:00:00', 'TEST_v2', 5.2, 9.8, 11.5, 1100, '2026-01', '{"p":2}', 'Success'),
        ('2026-03-01 02:00:00', 'TEST_v3', 5.0, 9.5, 11.0, 1200, '2026-02', '{"p":3}', 'Success'),
        ('2026-04-01 02:00:00', 'TEST_v4', 4.8, 9.0, 10.5, 1300, '2026-03', '{"p":4}', 'Success'),
        ('2026-05-01 02:00:00', 'TEST_v5', 4.5, 8.5, 10.0, 1400, '2026-04', '{"p":5}', 'Success'),
        # 1 Failed log to test NULL conversion
        ('2026-06-01 02:00:00', 'TEST_failed', None, None, None, None, None, None, 'Failed')
    ]
    
    with engine.begin() as conn:
        for run_ts, model_ver, mape, mae, rmse, rows, period_end, params, status in test_data:
            conn.execute(
                text("""
                    INSERT INTO dbo.RetrainLog 
                    (RunTimestamp, ModelVersion, MAPE, MAE, RMSE, TrainingRows, TrainingPeriodEnd, BestParams, Status)
                    VALUES 
                    (:run_ts, :model_ver, :mape, :mae, :rmse, :rows, :period_end, :params, :status)
                """),
                {
                    "run_ts": run_ts,
                    "model_ver": model_ver,
                    "mape": mape,
                    "mae": mae,
                    "rmse": rmse,
                    "rows": rows,
                    "period_end": period_end,
                    "params": params,
                    "status": status
                }
            )
    print("Mock retrain logs inserted successfully.")

def main():
    # 0. Initial Cleanup
    cleanup_db()
    
    try:
        # 1. Insert test logs
        insert_test_logs()
        
        # 2. Call GET endpoint
        print("\n1. Testing GET /api/v1/retrain/logs...")
        response = client.get("/api/v1/retrain/logs?limit=50")
        print(f"Status Code: {response.status_code}")
        assert response.status_code == 200, "Fetch retrain logs failed"
        
        data = response.json()
        print(f"Retrieved {len(data)} log entries.")
        
        # Filter only our test logs (sorted descending by timestamp inside the service)
        test_logs = [item for item in data if item["model_version"].startswith("TEST_")]
        # Sort them ascending by timestamp to verify chronological sequence calculations
        test_logs.sort(key=lambda x: x["run_timestamp"])
        
        print("\nVerifying chronological sequence calculations (Sequence 1 to 5):")
        expected_seqs = [
            # model_version, expected_quarter_label, expected_quarter, expected_year
            ("TEST_v1", "Q1", 1, 2026),
            ("TEST_v2", "Q2", 2, 2026),
            ("TEST_v3", "Q3", 3, 2026),
            ("TEST_v4", "Q4", 4, 2026),
            ("TEST_v5", "Q1", 1, 2027)  # Loops back to Q1, year incremented by +1!
        ]
        
        for idx, (ver, exp_q_lbl, exp_q, exp_yr) in enumerate(expected_seqs):
            log_item = test_logs[idx]
            print(f"Log: model={log_item['model_version']}, ts={log_item['run_timestamp']}, calculated={log_item['quarter_label']} ({log_item['calculated_year']})")
            
            assert log_item["model_version"] == ver
            assert log_item["quarter_label"] == exp_q_lbl, f"Expected {exp_q_lbl}, got {log_item['quarter_label']}"
            assert log_item["calculated_quarter"] == exp_q, f"Expected {exp_q}, got {log_item['calculated_quarter']}"
            assert log_item["calculated_year"] == exp_yr, f"Expected {exp_yr}, got {log_item['calculated_year']}"
            
        print("Sequence mapping logic verified successfully [OK].")
        
        # 3. Verify Null Safety
        print("\n2. Testing null safety metric conversion for failed training runs...")
        failed_log = [item for item in test_logs if item["model_version"] == "TEST_failed"][0]
        print("Failed Log entry parsed from API:")
        print(f"  model_version       : {failed_log['model_version']}")
        print(f"  status              : {failed_log['status']}")
        print(f"  mape                : {failed_log['mape']} (type: {type(failed_log['mape']).__name__})")
        print(f"  mae                 : {failed_log['mae']} (type: {type(failed_log['mae']).__name__})")
        print(f"  rmse                : {failed_log['rmse']} (type: {type(failed_log['rmse']).__name__})")
        print(f"  training_rows       : {failed_log['training_rows']}")
        print(f"  training_period_end : '{failed_log['training_period_end']}'")
        print(f"  best_params         : '{failed_log['best_params']}'")
        
        assert failed_log["mape"] == 0.0, "Expected NULL MAPE to coalesce to 0.0"
        assert failed_log["mae"] == 0.0, "Expected NULL MAE to coalesce to 0.0"
        assert failed_log["rmse"] == 0.0, "Expected NULL RMSE to coalesce to 0.0"
        assert failed_log["training_rows"] == 0, "Expected NULL rows to coalesce to 0"
        assert failed_log["training_period_end"] == "", "Expected NULL period to coalesce to empty string"
        assert failed_log["best_params"] == "{}", "Expected NULL params to coalesce to '{}'"
        print("Null safety mapping verified successfully [OK].")
        
        # 4. Verify Pagination
        print("\n3. Testing pagination limits and offsets...")
        # Get offset 1, limit 2
        response_pag = client.get("/api/v1/retrain/logs?limit=2&offset=1")
        print(f"Status Code: {response_pag.status_code}")
        assert response_pag.status_code == 200
        
        pag_data = response_pag.json()
        print(f"Retrieved {len(pag_data)} entries under pagination limits.")
        assert len(pag_data) == 2, f"Expected 2 entries, got {len(pag_data)}"
        
        # Assert offsets match sequence slicing
        all_ids = [item["id"] for item in data]
        pag_ids = [item["id"] for item in pag_data]
        print("All IDs:", all_ids[:5])
        print("Paginated IDs:", pag_ids)
        assert pag_ids == all_ids[1:3], "Pagination offset or order mismatch"
        print("Pagination logic verified successfully [OK].")

    finally:
        # 5. Final Cleanup
        print("\n4. Cleaning up test database data...")
        cleanup_db()
        print("Cleanup completed successfully.")
        
    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
