from fastapi.testclient import TestClient
from main import app
import pprint

client = TestClient(app)

year = 2026
quarter = 1

print("\n=============================================")
print("TESTING ENDPOINTS: PREDICTION DASHBOARD")
print("=============================================\n")

# 1. Test /api/v1/prediction/summary
print("1. Testing GET /api/v1/prediction/summary...")
response = client.get(f"/api/v1/prediction/summary?year={year}&quarter={quarter}")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)

# 2. Test /api/v1/prediction/variant-errors
print("\n2. Testing GET /api/v1/prediction/variant-errors...")
response = client.get(f"/api/v1/prediction/variant-errors?year={year}&quarter={quarter}")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)

# 3. Test /api/v1/prediction/shift-errors
print("\n3. Testing GET /api/v1/prediction/shift-errors...")
response = client.get(f"/api/v1/prediction/shift-errors?year={year}&quarter={quarter}")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)

# 4. Test /api/v1/prediction/daily-logs
print("\n4. Testing GET /api/v1/prediction/daily-logs...")
response = client.get(f"/api/v1/prediction/daily-logs?year={year}&quarter={quarter}")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    logs = response.json()
    print(f"Total log rows returned: {len(logs)}")
    if logs:
        print("Sample daily log (first row):")
        pprint.pprint(logs[0])
else:
    print(response.text)

# 5. Test /api/v1/prediction/chart-data
print("\n5. Testing GET /api/v1/prediction/chart-data...")
response = client.get(f"/api/v1/prediction/chart-data?year={year}&quarter={quarter}")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Labels (first 5 dates):", data["labels"][:5])
    print("Total Predicted (first 5):", data["total"]["predicted"][:5])
    print("Total Actual (first 5):", data["total"]["actual"][:5])
    print("Coklat Predicted (first 5):", data["variants"]["coklat"]["predicted"][:5])
    print("Shift 1 Awal Predicted (first 5):", data["shifts"]["s1_awal"]["predicted"][:5])
else:
    print(response.text)
