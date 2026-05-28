from fastapi.testclient import TestClient
from main import app
import pprint
import datetime

client = TestClient(app)

print("\n=============================================")
print("TESTING ENDPOINTS: OPERATIONAL CALENDAR")
print("=============================================\n")

# 1. Fetch calendar data for year 2026
print("1. Testing GET /api/v1/calendar?year=2026...")
response = client.get("/api/v1/calendar?year=2026")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Year:", data["year"])
    print("Total Working Days in 2026:", data["total_working_days"])
    print("Available Years in DB:", data["available_years"])
    print("Number of Months returned:", len(data["months"]))
    print("Sample day from January (first day):")
    pprint.pprint(data["months"][0]["days"][0])
else:
    print(response.text)

# 2. Update calendar day 2026-05-25 (set to shutdown)
print("\n2. Testing POST /api/v1/calendar/day (Update day to shutdown)...")
req_update = {
    "date": "2026-05-25",
    "category": "Libur Nasional (Kustom)",
    "is_working_day": False,
    "is_ramadan": False,
    "is_shutdown": True
}
response = client.post("/api/v1/calendar/day", json=req_update)
print(f"Status Code: {response.status_code}")
print(response.json())

# Restore calendar day 2026-05-25 to original Working state
print("\nRestoring 2026-05-25 back to standard Working Day...")
req_restore = {
    "date": "2026-05-25",
    "category": "Kerja Normal",
    "is_working_day": True,
    "is_ramadan": False,
    "is_shutdown": False
}
response = client.post("/api/v1/calendar/day", json=req_restore)
print(f"Status Code: {response.status_code}")
print(response.json())

# 3. Clean up year 2027 if it exists from previous tests
print("\n3. Cleaning up year 2027 from DB...")
response = client.delete("/api/v1/calendar/year/2027")
print(f"Status Code: {response.status_code}")
print(response.json())

# 4. Generate new calendar for year 2027
print("\n4. Testing POST /api/v1/calendar/generate for year 2027...")
req_gen = {"year": 2027}
response = client.post("/api/v1/calendar/generate", json=req_gen)
print(f"Status Code: {response.status_code}")
print(response.json())

# 5. Fetch and verify generated 2027 calendar
print("\n5. Verifying generated 2027 calendar...")
response = client.get("/api/v1/calendar?year=2027")
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    data_2027 = response.json()
    print("Year:", data_2027["year"])
    print("Total Working Days in 2027:", data_2027["total_working_days"])
    
    # Check weekend: Jan 2, 2027 is a Saturday (is_weekend = True)
    jan_2 = data_2027["months"][0]["days"][1]
    print("Verification - Jan 2, 2027 (Saturday):")
    print(f"  Day category: {jan_2['day_category']}")
    print(f"  Is Weekend: {jan_2['is_weekend']}")
    print(f"  Is Working Day: {jan_2['is_working_day']}")
    
    # Check Ramadan 2027: March 20, 2027 is during Ramadan (is_ramadan = True)
    march_20 = data_2027["months"][2]["days"][19]
    print("Verification - March 20, 2027 (Ramadan):")
    print(f"  Date: {march_20['date']}")
    print(f"  Is Ramadan: {march_20['is_ramadan']}")
else:
    print(response.text)

# 6. Cleanup by deleting year 2027 to restore pristine DB state
print("\n6. Cleaning up: deleting generated 2027 calendar to restore DB state...")
response = client.delete("/api/v1/calendar/year/2027")
print(f"Status Code: {response.status_code}")
print(response.json())
