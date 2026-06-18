from fastapi.testclient import TestClient
from main import app
import pprint

client = TestClient(app)

# Query dates in 2023 when there is known historical transaction data
start_date = "2023-01-01"
end_date = "2023-01-31"

print("\n=============================================")
print("TESTING ENDPOINTS: DASHBOARD SUMMARY")
print("=============================================\n")

# 1. Test /api/v1/dashboard/metrics
print("1. Testing GET /api/v1/dashboard/metrics...")
response = client.get(f"/api/v1/dashboard/metrics?start_date={start_date}&end_date={end_date}&shift_id=ALL")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)

# 2. Test /api/v1/dashboard/consumption-chart
print("\n2. Testing GET /api/v1/dashboard/consumption-chart...")
response = client.get(f"/api/v1/dashboard/consumption-chart?start_date={start_date}&end_date={end_date}&shift_id=ALL")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Labels (first 5):", data["labels"][:5])
    print("Data (first 5):", data["data"][:5])
    print("Most:", data["most"])
    print("Least:", data["least"])
else:
    print(response.text)

# 3. Test /api/v1/dashboard/sales-analytics
print("\n3. Testing GET /api/v1/dashboard/sales-analytics...")
response = client.get(f"/api/v1/dashboard/sales-analytics?start_date={start_date}&end_date={end_date}&shift_id=ALL")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)

# 4. Test /api/v1/dashboard/latest-transactions
print("\n4. Testing GET /api/v1/dashboard/latest-transactions...")
response = client.get(f"/api/v1/dashboard/latest-transactions?start_date={start_date}&end_date={end_date}&shift_id=ALL")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)

# 5. Test with specific shift_id (shift_id=1, SHIFT1)
print("\n5. Testing with specific shift_id=1...")
response = client.get(f"/api/v1/dashboard/metrics?start_date={start_date}&end_date={end_date}&shift_id=1")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    pprint.pprint(response.json())
else:
    print(response.text)
