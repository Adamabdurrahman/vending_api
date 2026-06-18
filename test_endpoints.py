import sys
import os

from forecast_service import generate_forecast, update_actuals

print("--- TEST 4A: GENERATE PREDIKSI APRIL 2026 ---")
try:
    res1 = generate_forecast(2026, 1, 2026, 4)
    print("Result Generate:")
    import pprint
    pprint.pprint(res1)
except Exception as e:
    print(f"Error: {e}")

print("\n--- TEST 4B: UPDATE ACTUALS APRIL 2026 ---")
try:
    res2 = update_actuals("2026-04")
    print("Result Update Actuals:")
    import pprint
    pprint.pprint(res2)
except Exception as e:
    print(f"Error: {e}")
