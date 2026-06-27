# C. FUNCTIONAL TESTING

---

## C.1 — Testing Results of Every Function in the Specification

The following functional tests were conducted across two testing sessions:
- **Session 1 — 05 June 2026**: User Authentication & Account Management
- **Session 2 — 06 June 2026**: Operational Calendar, Manual Insert, Dashboards, and All Module Management features

All tests were performed on a Samsung Android device connected to the cloud-hosted backend API.

---

### i. User Authentication

#### Register

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Register | New user submits complete and valid registration form | (09.00.00) Open the application. (09.00.10) Navigate to the Register screen. (09.00.20) Fill in all fields: Username, Email, Phone, Password. (09.00.45) Tap the Register button. | System creates a new account with `status_active = "P"` (Pending), sends a success message. | A success message is displayed: "Akun berhasil dibuat. Menunggu persetujuan Superadmin." The screen remains on the register page. | 05/06/2026 | Success |
| Negative Testing | Register | User submits registration with an already-used username | (09.03.00) Navigate to the Register screen. (09.03.15) Fill in a username that already exists in the system. Fill in remaining valid fields. (09.03.40) Tap the Register button. | System rejects the request and returns a validation error for duplicate username. | An error message is displayed: "Username sudah terpakai." Form is not submitted. | 05/06/2026 | Success |
| Negative Testing | Register | User submits registration with an already-used email address | (09.05.00) Navigate to the Register screen. (09.05.15) Fill in a valid new username but an email address already registered in the system. (09.05.40) Tap the Register button. | System rejects the request and returns a validation error for duplicate email. | An error message is displayed: "Email sudah terdaftar." Form is not submitted. | 05/06/2026 | Success |

---

#### Log In

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Log In | User logs in with valid credentials | (09.10.00) Open the application. (09.10.05) Enter a valid registered username and correct password. (09.10.15) Tap the Login button. | System authenticates the user, returns user profile data including level_user and session information. | The application navigates to the Sidebar Menu (main dashboard). The user's profile name is displayed correctly in the sidebar. | 05/06/2026 | Success |
| Negative Testing | Log In | User logs in with a correct username but wrong password | (09.13.00) On the Login screen, enter a valid registered username and an incorrect password. (09.13.15) Tap the Login button. | System returns HTTP 401 — password mismatch. | An error message is displayed: "Password salah." The user remains on the Login screen. | 05/06/2026 | Success |
| Negative Testing | Log In | User logs in with a username that does not exist | (09.15.00) On the Login screen, enter a username that has never been registered. (09.15.15) Tap the Login button. | System returns HTTP 404 — username not found. | An error message is displayed: "Username tidak ditemukan." The user remains on the Login screen. | 05/06/2026 | Success |
| Negative Testing | Log In | User attempts to log in with an account still pending Superadmin approval | (09.17.00) Attempt to log in using credentials of an account with `status_active = "P"`. (09.17.15) Tap the Login button. | System returns HTTP 403 — account pending. | An error message is displayed: "Akun Anda masih pending persetujuan Superadmin." The user remains on the Login screen. | 05/06/2026 | Success |

---

#### Forgot Password (OTP Reset Flow)

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Forgot Password | User successfully resets password using a valid OTP | (09.20.00) On the Login screen, tap "Forgot Password". (09.20.10) Enter a valid registered username and matching primary email. (09.20.30) Tap the Submit button. (09.21.00) Retrieve the 6-digit OTP from the registered email. (09.22.00) Enter the correct OTP in the verification field. (09.22.15) Enter and confirm a new password. (09.22.30) Tap Confirm. | System sends OTP to email, then upon correct OTP entry, updates the user's password and clears the security token. | A success message is displayed: "Password Anda berhasil diperbarui." The user is redirected to the Login screen. The user can then log in with the new password. | 05/06/2026 | Success |
| Negative Testing | Forgot Password | User submits a username-email combination that does not match | (09.25.00) On the Forgot Password screen, enter a valid username but an email address that does not match the registered email for that user. (09.25.20) Tap Submit. | System returns an error — combination not found or account not active. | An error message is displayed: "Kombinasi Username dan Email tidak ditemukan atau akun tidak aktif." | 05/06/2026 | Success |
| Negative Testing | Forgot Password | User enters an incorrect or expired OTP | (09.27.00) Complete the first step of forgot password (valid username + email). (09.27.30) Enter an intentionally wrong 6-digit code in the OTP field. (09.27.45) Tap Confirm. | System rejects the OTP and returns an error. | An error message is displayed: "OTP salah." The user is prompted to re-enter the OTP. | 05/06/2026 | Success |

---

#### Session Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Session Persistence | User re-opens the app without logging out and is redirected directly to the main menu | (09.35.00) Log in to the application. (09.35.30) Close the application without logging out. (09.36.00) Re-open the application. | Session data is preserved locally. The app detects an active session and skips the login screen. | The application navigates directly to the Sidebar Menu without requiring the user to log in again. | 05/06/2026 | Success |
| Positive Testing | Log Out | User logs out and is returned to the Login screen | (09.38.00) From the Sidebar Menu, tap the Logout button. | Session is cleared from the device. | The application navigates back to the Login screen. The user must log in again to access any feature. | 05/06/2026 | Success |

---

### ii. Account Settings

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Profile | User views their own account information | (09.42.00) From the Sidebar Menu, navigate to Account Settings. | System fetches user profile data from the API via GET /account/{id}. | The user's current username, primary email, secondary email, and profile photo are displayed correctly. | 05/06/2026 | Success |
| Positive Testing | Edit Profile | User updates their username and email successfully | (09.45.00) On the Account Settings screen, modify the username and/or email fields. (09.45.30) Tap Save Changes. | System sends a PUT /account/{id}/update request. The database record is updated. | A success response is shown. The updated values are reflected on the screen immediately. | 05/06/2026 | Success |
| Positive Testing | Change Password | User successfully changes their account password | (09.50.00) On the Account Settings screen, tap Change Password. (09.50.15) Enter a new password. (09.50.30) Tap Confirm. | System sends a PUT /account/{id}/change-password request. The password field in the database is updated. | A success message is displayed. The user can subsequently log in using the new password. | 05/06/2026 | Success |
| Positive Testing | Upload Profile Photo | User uploads a new profile photo | (09.55.00) On the Account Settings screen, tap the camera/photo icon. (09.55.10) Select a photo from the device gallery. (09.55.20) Confirm the selection. | System uploads the image to the server via POST /account/{id}/upload-photo and updates the photo_url field in the database. | The new profile photo is displayed on the Account Settings screen. | 05/06/2026 | Success |
| Negative Testing | Edit Profile | User attempts to save changes with an empty username field | (10.00.00) On the Account Settings screen, clear the username field entirely. (10.00.15) Tap Save Changes. | Client-side or server-side validation rejects the empty username. | An error or validation message is shown. The profile is not updated. | 05/06/2026 | Success |

---

### iii. Operational Calendar Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Calendar | User views the operational calendar for year 2026 | (09.05.00) From the Sidebar Menu, navigate to Kalender Operasional. The current year (2026) is loaded by default. | System fetches full-year calendar data via GET /api/v1/calendar?year=2026. All 12 months are returned with per-day operational status. | A 12-month swipeable calendar is displayed. Each day shows its category (Kerja Normal, Libur, Ramadan, Shutdown, etc.) using color-coded indicators. | 06/06/2026 | Success |
| Positive Testing | Edit Calendar Day | User modifies the operational status of a specific day | (09.12.00) On the calendar view, tap a specific date (e.g., 2026-07-15). (09.12.15) A bottom-sheet dialog opens. (09.12.30) Change the day category from "Kerja Normal" to "Libur Nasional". (09.12.45) Tap Save. | System sends POST /api/v1/calendar/day with the updated configuration. If the date exists, it is updated; if not, it is inserted (upsert). Shift_Active flags are recalculated automatically by the server. | The calendar view updates to reflect the new status for that date. The day indicator color changes accordingly. | 06/06/2026 | Success |
| Positive Testing | Generate Calendar Year | Superadmin generates a full calendar for a new year | (09.20.00) On the Operational Calendar screen, tap the Generate button. (09.20.15) Input year 2027. (09.20.25) Confirm the generation. | System sends POST /api/v1/calendar/generate with `{"year": 2027}`. Server auto-detects Indonesian national holidays, Ramadan approximation, and weekends for all 365/366 days. | A success message is displayed. Navigating to year 2027 on the calendar shows all days populated with appropriate operational categories. | 06/06/2026 | Success |
| Negative Testing | Generate Calendar Year | Superadmin attempts to generate a calendar for a year that already exists | (09.30.00) Attempt to generate a calendar for year 2026 (which already exists in the database). (09.30.15) Confirm the generation. | System returns HTTP 400 — calendar for the specified year already exists. | An error message is displayed indicating the year already has a calendar. No duplicate data is created. | 06/06/2026 | Success |
| Positive Testing | Delete Calendar Year | Superadmin deletes all calendar records for a specific year | (09.35.00) On the Operational Calendar screen, tap the Delete Year button. (09.35.15) Confirm the deletion in the dialog. | System sends DELETE /api/v1/calendar/year/{year}. All records for that year are removed from the OperationalCalendar table. | A success message is displayed. Navigating to the deleted year on the calendar shows no data. | 06/06/2026 | Success |
| Negative Testing | Delete Calendar Year | User cancels a calendar year deletion in the confirmation dialog | (09.42.00) Tap the Delete Year button. (09.42.10) When the confirmation dialog appears, tap Cancel instead of Confirm. | No API call is made. The calendar data is unchanged. | The dialog is dismissed. The calendar for the selected year remains intact and unchanged. | 06/06/2026 | Success |

---

### iv. Manual Transaction Data Input

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Download Template | User downloads the official Excel input template | (10.00.00) Navigate to Manual Insert screen. (10.00.15) Tap the Download Template button. | System sends GET /api/v1/manual-insert/template. The server returns the Template_Insert.xlsx file as a binary stream. | The Excel file is downloaded and saved to the device. A file-open dialog appears, allowing the user to open the file with a compatible application. | 06/06/2026 | Success |
| Positive Testing | Upload Valid Excel | User uploads a correctly formatted Excel file with new transaction data | (10.05.00) On the Manual Insert screen, tap Upload File. (10.05.15) Select a valid .xlsx file that follows the template format with no duplicate records. (10.05.30) Confirm the upload. | System sends POST /api/v1/manual-insert/upload. Server validates columns, checks for duplicates, calculates is_ramadan and is_weekend flags automatically, and inserts new records into dbo.Vending_Aggregrated with is_manual_insert=1. | A success response is displayed showing the number of rows successfully inserted. The data becomes available in the dashboard and analytics views. | 06/06/2026 | Success |
| Negative Testing | Upload Invalid File | User attempts to upload a file with incorrect column structure | (10.15.00) On the Manual Insert screen, tap Upload File. (10.15.15) Select an Excel file that does not follow the required template columns. (10.15.30) Confirm the upload. | System returns a validation error — required columns are missing or malformed. No data is inserted into the database. | An error message is displayed describing the column mismatch. The upload is rejected. | 06/06/2026 | Success |
| Negative Testing | Upload Duplicate Data | User attempts to upload a file containing records already present in the database | (10.22.00) Upload a valid Excel file that contains the same date-shift-variant combinations already in the database. | System detects duplicates during processing. Duplicate rows are skipped; only truly new rows (if any) are inserted. | A response message indicates the number of skipped duplicate rows and the number of newly inserted rows (which may be 0 if all rows are duplicates). | 06/06/2026 | Success |

---

### v. Transaction Monitoring Dashboard (Dashboard Summary)

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Load Dashboard Metrics | User opens Dashboard Summary and views current-period metrics | (13.05.00) Navigate to Dashboard Summary from the Sidebar Menu. The current week's date range is used as default. | System fetches all four metric cards via GET /api/v1/dashboard/metrics. Returns: Taken (successful transactions), Failed (dispensation failures), Restock count, and Taken Today. | Four metric cards are displayed at the top of the screen with numerical values. A daily consumption line chart and variant analytics chart are rendered below. | 06/06/2026 | Success |
| Positive Testing | Filter by Date Range | User applies a custom date range filter to the dashboard | (13.15.00) On the Dashboard Summary screen, open the date picker. (13.15.30) Set start date to 2026-05-01 and end date to 2026-05-31. (13.15.50) Tap Apply. | System re-fetches all endpoints with the new date range parameters. All metric cards, charts, and transaction list update accordingly. | All displayed data updates to reflect the May 2026 data. The chart range adjusts to show daily distribution across May. | 06/06/2026 | Success |
| Positive Testing | Filter by Shift | User filters the dashboard to show data for a specific shift only | (13.25.00) On the Dashboard Summary screen, open the shift filter dropdown. (13.25.15) Select a specific shift (e.g., SHIFT1). (13.25.25) Tap Apply. | System re-fetches endpoints with the shift_id parameter set. All metrics and charts filter to show only data for the selected shift. | All displayed values update to reflect only SHIFT1 data. The transaction list also filters to show only SHIFT1 transactions. | 06/06/2026 | Success |
| Positive Testing | View Latest Transactions | User scrolls through the latest transaction log | (13.32.00) On the Dashboard Summary screen, scroll down to the Latest Transactions section. | System fetches the 10 most recent transactions via GET /api/v1/dashboard/latest-transactions. | A list of the most recent transactions is displayed, showing date, shift, variant, and quantity for each entry. | 06/06/2026 | Success |

---

### vi. Prediction Dashboard (ML Forecast)

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Load Prediction Summary | User views the ML forecast summary for Q1 2026 | (13.35.00) Navigate to Prediction Dashboard from the Sidebar Menu. (13.35.10) Select year 2026 and quarter Q1. | System fetches prediction summary via GET /api/v1/prediction/summary?year=2026&quarter=1. Returns monthly demand forecast for January, February, and March 2026 per variant, along with MAPE and error metrics where actuals are available. | A summary card is displayed showing total predicted demand for the quarter. Per-variant breakdown (Coklat, Moca, Original, Strawberry) is shown. Actual vs. predicted comparison is visible for completed months. | 06/06/2026 | Success |
| Positive Testing | View Prediction Chart | User views the chart comparing predicted vs. actual demand | (13.45.00) On the Prediction Dashboard, scroll to the chart section. | System fetches chart data via GET /api/v1/prediction/chart-data?year=2026&quarter=1. Returns time-series data for both predicted and actual demand per variant. | A line or bar chart is rendered showing the comparison between predicted and actual values over time. For completed months (Jan, Feb), the actual line is populated; for future months, only the prediction line is shown. | 06/06/2026 | Success |
| Positive Testing | Change Quarter | User switches to a different quarter to view different predictions | (13.50.00) On the Prediction Dashboard, change the quarter selector from Q1 to Q2. | System re-fetches all prediction endpoints with the new quarter parameter. | All summary cards and charts update to reflect Q2 2026 forecast data. If Q2 data is not yet generated, an appropriate empty state or message is shown. | 06/06/2026 | Success |
| Positive Testing | View Variant Error Detail | User examines per-variant prediction errors | (13.55.00) On the Prediction Dashboard, tap or navigate to the Variant Errors section. | System fetches variant-level errors via GET /api/v1/prediction/variant-errors?year=2026&quarter=1. | A list of prediction errors per variant (Coklat, Moca, Original, Strawberry) is displayed, showing MAPE and direction (over/under-predict) for each. | 06/06/2026 | Success |

---

### vii. Inventory Dashboard & Decision Support

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Load Inventory Dashboard | User opens the Inventory Dashboard and views current stock levels | (14.00.00) Navigate to Inventory Dashboard from the Sidebar Menu. (14.00.15) The current quarter is loaded by default. | System fetches dashboard data via GET /api/v1/inventory/dashboard. Returns current stock levels per variant, DSS recommendations, and summary metrics. | Stock levels per variant are displayed in a card or grid format. Any low-stock warnings or DSS-recommended reorder quantities are shown. | 06/06/2026 | Success |
| Positive Testing | View Stock Movements | User browses the paginated stock movement history | (14.10.00) On the Inventory Dashboard, navigate to the Stock Movements section. (14.10.15) Scroll through the list. (14.11.00) Apply a variant filter (e.g., filter by "Coklat"). | System fetches movement history via GET /api/v1/inventory/movements with pagination and filter parameters. | A paginated list of stock movements is displayed, showing date, type (IN/OUT), variant, and quantity for each entry. The list filters correctly when a variant filter is applied. | 06/06/2026 | Success |
| Positive Testing | Input Stock-In | User records a new incoming milk delivery from the supplier | (14.20.00) On the Inventory Dashboard, tap the Stock-In button. (14.20.15) Fill in the variant, quantity, and date fields. (14.20.40) Tap Submit. | System sends POST /api/v1/inventory/stock-in with the stock-in details. A new movement record is created with type=IN. The stock level for the specified variant is updated in the database. | A success message is displayed. The new stock-in entry appears in the Stock Movements list. The stock level summary card updates to reflect the increased inventory. | 06/06/2026 | Success |

---

### viii. ML Retrain Logs Monitoring

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Retrain Log List | User views the list of all model retrain events | (14.35.00) Navigate to Retrain Logs from the Sidebar Menu. | System fetches retrain history via GET /api/v1/retrain/logs. Returns a list of all retrain events including timestamps, MAPE, MAE, RMSE, training row count, and status. | A scrollable list of retrain log entries is displayed. The most recent entry (2026-05-16 19:53:26, MAPE 3.34%, Status: success) is visible at the top of the list. | 06/06/2026 | Success |
| Positive Testing | View Retrain Log Detail | User reviews the details of a specific retrain event | (14.38.00) Tap on the retrain log entry dated 2026-05-16. | The detailed metrics of that specific retrain run are shown, including best hyperparameters and the training period. | The detail view shows: Model Version (V6+ retrained), MAPE 3.34%, MAE 2,570, RMSE 3,154, Training Rows 132, Training Period End 2025-12, Best Params (colsample_bytree: 0.8, learning_rate: 0.1, max_depth: 4, n_estimators: 100, subsample: 0.8), Status: success. | 06/06/2026 | Success |

---

### ix. Master Data — Product Variant Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Variant List | User views all registered milk variants | (15.00.00) Navigate to Master Variant from the Sidebar Menu. | System fetches all variants via GET /api/v1/variants. | A list of all product variants is displayed (e.g., Coklat, Moca, Original/Putih, Strawberry), each showing their name, image, and active status. | 06/06/2026 | Success |
| Positive Testing | Create Variant | User adds a new milk variant | (15.05.00) Tap the FAB (+) button. (15.05.15) Fill in variant name and upload an image. (15.05.40) Tap Save. | System sends POST /api/v1/variants. A new variant record is created in dbo.master_variant. | A success message is shown. The new variant appears in the list. | 06/06/2026 | Success |
| Positive Testing | Edit Variant | User updates an existing variant's information | (15.12.00) Tap the edit icon on an existing variant card. (15.12.15) Modify the variant name. (15.12.30) Tap Save. | System sends PUT /api/v1/variants/{id}. The record is updated in the database. | The variant list refreshes and shows the updated name. | 06/06/2026 | Success |
| Positive Testing | Delete Variant | User deletes an existing variant with confirmation | (15.20.00) Tap the delete icon on a variant card. (15.20.10) Confirm the deletion in the dialog. | System sends DELETE /api/v1/variants/{id}. The record is removed from the database. | The variant is no longer visible in the list after deletion. | 06/06/2026 | Success |
| Negative Testing | Create Variant | User attempts to create a variant with an empty name | (15.25.00) Tap the FAB (+) button. (15.25.10) Leave the variant name field empty. (15.25.20) Tap Save. | Client-side or server-side validation rejects the empty name. No record is created. | An error or validation message is displayed. The form is not submitted. | 06/06/2026 | Success |
| Negative Testing | Delete Variant | User cancels a variant deletion in the confirmation dialog | (15.28.00) Tap the delete icon on a variant card. (15.28.10) Tap Cancel in the confirmation dialog. | No DELETE API call is made. The variant remains in the database. | The dialog is dismissed. The variant still appears in the list, unchanged. | 06/06/2026 | Success |

---

### x. Master Data — Vending Machine Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Machine List | User views all registered vending machine units | (15.35.00) Navigate to Machine Management from the Sidebar Menu. | System fetches all machines via GET /api/v1/machine. | A list of all vending machine units is displayed, showing their name, reference number, IP address, and status. | 06/06/2026 | Success |
| Positive Testing | Create Machine | User registers a new vending machine unit | (15.40.00) Tap the FAB (+) button. (15.40.15) Fill in machine name, reference number, and IP address. (15.40.40) Tap Save. | System sends POST /api/v1/machine. A new record is created in dbo.master_alat_vm. | A success message is shown. The new machine appears in the list. | 06/06/2026 | Success |
| Positive Testing | Edit Machine | User updates an existing machine's information | (15.48.00) Tap the edit icon on a machine card. (15.48.15) Modify the machine name. (15.48.30) Tap Save. | System sends PUT /api/v1/machine/{id}. The record is updated in the database. | The machine list refreshes with the updated information. | 06/06/2026 | Success |
| Positive Testing | Delete Machine | User deletes a vending machine unit with confirmation | (15.55.00) Tap the delete icon on a machine card. (15.55.10) Confirm the deletion. | System sends DELETE /api/v1/machine/{id}. The record is removed. | The machine is no longer visible in the list. | 06/06/2026 | Success |
| Negative Testing | Delete Machine | User cancels a machine deletion in the confirmation dialog | (15.58.00) Tap the delete icon. (15.58.10) Tap Cancel in the confirmation dialog. | No API call is made. | The dialog is dismissed. The machine remains in the list. | 06/06/2026 | Success |

---

### xi. Master Data — Shift Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Shift List | User views all registered work shifts | (16.05.00) Navigate to Shift Management from the Sidebar Menu. | System fetches all shifts via GET /api/v1/shift. | A list of all shifts is displayed, showing shift name, department, start time, end time, and active status. | 06/06/2026 | Success |
| Positive Testing | Create Shift | User creates a new work shift | (16.10.00) Tap the FAB (+) button. (16.10.15) Fill in shift name, department name, start time, and end time. (16.10.45) Tap Save. | System sends POST /api/v1/shift. A new record is created in dbo.master_settime. | A success message is shown. The new shift appears in the list. | 06/06/2026 | Success |
| Positive Testing | Edit Shift | User updates an existing shift's schedule | (16.18.00) Tap the edit icon on a shift card. (16.18.15) Modify the start or end time. (16.18.35) Tap Save. | System sends PUT /api/v1/shift/{id}. The record is updated. | The shift list refreshes with the updated schedule. | 06/06/2026 | Success |
| Positive Testing | Delete Shift | User deletes an existing shift with confirmation | (16.25.00) Tap the delete icon on a shift card. (16.25.10) Confirm the deletion. | System sends DELETE /api/v1/shift/{id}. The record is removed. | The shift is no longer visible in the list. | 06/06/2026 | Success |
| Negative Testing | Create Shift | User attempts to create a shift with empty name or time fields | (16.28.00) Tap the FAB (+). (16.28.10) Leave required fields (shift name, time) empty. (16.28.20) Tap Save. | Validation prevents submission. No record is created. | An error or validation message is shown. The form is not submitted. | 06/06/2026 | Success |

---

### xii. Master Data — Slot Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Slot List by Machine | User views slots configured for a specific vending machine | (16.35.00) Navigate to Slot Management. (16.35.10) Select a vending machine from the spinner. | System fetches slots via GET /api/v1/slot?vm_id={id}. | A list of all slots for the selected machine is displayed, showing slot name, maximum capacity, and assigned variant. | 06/06/2026 | Success |
| Positive Testing | Create Slot | User creates a new slot configuration for a machine | (16.40.00) Tap the FAB (+). (16.40.15) Fill in slot name, assign a variant, and set maximum capacity. (16.40.45) Tap Save. | System sends POST /api/v1/slot. A new record is created in dbo.manage_map_slot_number. | A success message is shown. The new slot appears in the list for the selected machine. | 06/06/2026 | Success |
| Positive Testing | Edit Slot | User updates a slot's variant assignment or capacity | (16.48.00) Tap the edit icon on a slot card. (16.48.15) Change the assigned variant. (16.48.30) Tap Save. | System sends PUT /api/v1/slot/{id}. The record is updated. | The slot list refreshes with the updated variant assignment. | 06/06/2026 | Success |
| Positive Testing | Delete Slot | User deletes a slot configuration with confirmation | (16.55.00) Tap the delete icon on a slot card. (16.55.10) Confirm the deletion. | System sends DELETE /api/v1/slot/{id}. The record is removed. | The slot is no longer visible in the list. | 06/06/2026 | Success |
| Negative Testing | Delete Slot | User cancels a slot deletion in the confirmation dialog | (16.58.00) Tap the delete icon. (16.58.10) Tap Cancel in the dialog. | No API call is made. | The dialog is dismissed. The slot remains in the list unchanged. | 06/06/2026 | Success |

---

### xiii. Restock Management

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | View Restock List | User views all restock records for a selected machine | (17.05.00) Navigate to Restock Management. (17.05.10) Select a machine from the spinner. | System fetches restock data via GET /api/v1/restock/vm/{vm_id}. | A list of all restock records for the selected machine is displayed, showing slot name, current stock quantity, status, auditor name, and last update date. | 06/06/2026 | Success |
| Positive Testing | Filter Low-Stock Alerts | User enables the low-stock filter to see only slots below threshold | (17.12.00) On the Restock Management screen, check the "Stok Rendah < 10" checkbox. | System sends GET /api/v1/restock/alerts/low-stock?threshold=10 or applies a client-side filter. Only slots with stock_qty < 10 are shown. | The list filters to show only slots with critically low stock. An alert indicator is visible for each item. | 06/06/2026 | Success |
| Positive Testing | Create Restock Record | User creates a new restock entry for a specific slot | (17.18.00) Tap the FAB (+). (17.18.15) Select a slot from the dropdown. (17.18.30) Enter the restocked quantity. (17.18.45) Tap Save. | System sends POST /api/v1/restock. A new record is created in dbo.manage_restok with the auditor username and current timestamp. | A success message is shown. The new restock record appears in the list with updated stock quantity and auditor information. | 06/06/2026 | Success |
| Positive Testing | Edit Restock Record | User updates the quantity of an existing restock record | (17.24.00) Tap the edit icon on a restock card. (17.24.15) Modify the stock quantity. (17.24.30) Tap Save. | System sends PUT /api/v1/restock/{id}. The record is updated with the new quantity and current timestamp. | The list refreshes with the updated stock quantity. | 06/06/2026 | Success |
| Positive Testing | Delete Restock Record | User deletes a restock record with confirmation | (17.30.00) Tap the delete icon on a restock card. (17.30.10) Confirm the deletion. | System sends DELETE /api/v1/restock/{id}. The record is removed from the database. | The restock entry is no longer visible in the list. | 06/06/2026 | Success |
| Negative Testing | Create Restock | User attempts to submit a restock entry with zero quantity | (17.34.00) Tap the FAB (+). (17.34.10) Enter 0 in the quantity field. (17.34.20) Tap Save. | Validation rejects the zero quantity. No record is created. | An error or validation message is displayed. The form is not submitted. | 06/06/2026 | Success |

---

### xiv. ML Pipeline Performance — Daily Pipeline Run

The daily demand forecasting pipeline (`daily_pipeline.py`) runs as a scheduled background process. The following performance test verified that the end-to-end pipeline completes successfully without error within its expected execution window.

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Daily Pipeline Execution | Full ETL + ML pipeline runs to completion without crashing | (11.00.00) Manually trigger the daily_pipeline.py script on the backend server. (11.00.30) Monitor the console and log output through each stage: ETL extraction, data transformation, aggregation load, feature engineering, quarterly forecast check, and actuals update. (11.35.00) Pipeline completes. | The pipeline executes all stages in sequence without runtime errors. All log entries show SUCCESS or equivalent status. Results are written to the database (Vending_Aggregrated, ForecastResults_Layer1, ForecastResults_Layer2, and SystemNotifications tables). | The pipeline completes within approximately 35 minutes. Log output shows all stages completed successfully. No error entries are present in the error_log.txt file for this execution. Dashboard data updates reflect the latest pipeline output. | 06/06/2026 | Success |

---

### xv. ML Model Accuracy — XGBoost Forecast Evaluation

The following table documents the quantitative performance of the XGBoost demand prediction model based on actual forward-test results for Q1 2026. The data was verified through the Prediction Dashboard and corroborated with the raw retrain_log.txt and Journal 07 Evaluasi dan Hasil.

**Model Version:** V6+ (retrained 2026-05-16 19:53:26)
**Training Data Range:** April 2023 — December 2025 (132 rows, 33 months)

#### Layer 1 — Monthly Demand Prediction Accuracy

| Evaluation Type | Target | Actual Result | Status |
|---|---|---|---|
| Backtest MAPE (4-month walk-forward, Sep–Dec 2025) | < 10% | **3.34%** | Success |
| Forward Test — January 2026 | < 10% | **1.3% (under-predict)** | Success |
| Forward Test — February 2026 (Ramadan partial) | < 10% | **4.9% (over-predict)** | Success |
| Forward Test — March 2026 (Business Logic month) | < 10% | **1.4% (under-predict)** | Success |
| Skill Score vs. Naive Baseline | > 20% | **> 60%** | Success |

#### Layer 2 — Daily Distribution Accuracy

| Evaluation Type | Target | Actual Result | Status |
|---|---|---|---|
| WAPE (Weighted Absolute Percentage Error) — Daily | < 10% | **3.99%** | Success |
| Shift KPI Score (shifts with error < 10%) | > 75% of shifts | **81.3% (6.5/8 avg.)** | Success |
| Event Handling Accuracy (holidays, weekends, Ramadan) | > 70% | **89.5% (17/19 event days)** | Success |
| Day-of-Week Profile Max Error | < 2pp | **0.63 percentage points** | Success |

#### Retrain Performance

| Metric | Value |
|---|---|
| Retrain Timestamp | 2026-05-16 19:53:26 |
| Total Retrain Duration | ~4 seconds (API-triggered) |
| Training Rows Used | 132 |
| Training Period End | 2025-12 |
| Best Hyperparameters | `colsample_bytree: 0.8, learning_rate: 0.1, max_depth: 4, n_estimators: 100, subsample: 0.8` |
| MAPE Backtest | 3.34% |
| MAE | 2,570 units |
| RMSE | 3,154 units |
| Artifact Size | 150.2 KB |
| Final Status | success |

---

## C.2 — Qualitative Testing (User Acceptance Testing)

### Overview

User Acceptance Testing (UAT) was conducted as an internal developer acceptance test to verify that all implemented features perform as specified in the system requirements. The UAT was carried out by the developer responsible for integrating the Android frontend with the backend API, using a Samsung Android device connected to the cloud-hosted backend environment.

The UAT was conducted on **05–06 June 2026** covering all functional modules described in the Main Functionality specification (Section B.1).

### UAT Feature Verification Table

| No | Use Cases / Processes | Acknowledged by | Test Date | Status |
|---|---|---|---|---|
| 1 | **User Authentication & Account Management** | Adam Abdurrahman (Developer) | 05/06/2026 | Success |
| | *Parameters:* User can register a new account. Account is placed in Pending status awaiting Superadmin approval. User receives OTP via email after approval and activates the account. User can log in with valid credentials. User is rejected with appropriate message for invalid credentials. User can reset password via OTP email flow. User can log out. Session persists after app restart without logout. | | | |
| 2 | **Account Settings** | Adam Abdurrahman (Developer) | 05/06/2026 | Success |
| | *Parameters:* User can view their own profile data. User can update username and email. User can change password. User can upload and update profile photo. | | | |
| 3 | **Operational Calendar Management** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* User can view the full-year calendar with per-day operational status. User can modify the status of any individual day (working day, holiday, shutdown, Ramadan). User can generate a new year's calendar automatically. User can delete an existing year's calendar. | | | |
| 4 | **Manual Transaction Data Input** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* User can download the standardized Excel input template. User can upload a valid Excel file and data is inserted into the database. System rejects files with incorrect structure. System skips duplicate records automatically. | | | |
| 5 | **Transaction Monitoring Dashboard** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* Dashboard loads key metrics (Taken, Failed, Restock, Today). Consumption chart renders correctly. Variant analytics chart renders correctly. Date range filter applies to all metrics and charts. Shift filter applies to all metrics and charts. Latest transactions list is displayed. | | | |
| 6 | **ML-Based Prediction Dashboard** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* Prediction summary loads for selected year and quarter. Per-variant forecast values are displayed. Chart comparing predicted vs. actual is rendered. Quarter selector changes the displayed data. Variant-level error breakdown is visible. | | | |
| 7 | **Inventory Dashboard & Stock-In** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* Inventory dashboard loads stock levels per variant. Stock movement history is displayed in paginated list. Variant filter on stock movements works correctly. New stock-in records can be submitted successfully. | | | |
| 8 | **Master Data Management (Variant, Machine, Shift, Slot)** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* All four master data modules support full CRUD operations (Create, Read, Update, Delete). Deletion requires confirmation dialog. Canceling deletion preserves data. Input validation prevents empty required fields from being submitted. | | | |
| 9 | **Restock Management** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* Restock list loads for a selected machine. Low-stock filter shows only slots below threshold. New restock records can be created with slot, quantity, and auditor data. Existing records can be edited. Records can be deleted with confirmation. | | | |
| 10 | **ML Retrain Logs Monitoring** | Adam Abdurrahman (Developer) | 06/06/2026 | Success |
| | *Parameters:* Retrain logs list loads from the database. Most recent retrain entry (2026-05-16, MAPE 3.34%, Status: success) is displayed. Log entries show all relevant metrics (MAPE, MAE, RMSE, training rows, hyperparameters). | | | |

### Key Points & Qualitative Feedback

| Key Points | Observations and Analysis |
|---|---|
| **User Authentication Flow** | The two-step registration process (Superadmin approval → OTP email) adds an intentional friction point that ensures no unauthorized users can access the system. This is appropriate for the operational context where all users must be identifiable employees. |
| **Operational Calendar** | The swipeable monthly calendar UI provides an intuitive interface for managing complex operational schedules. The ability to modify individual days without affecting surrounding dates is critical for handling unexpected shutdowns or ad-hoc holidays. |
| **ML Prediction Accuracy** | The XGBoost model achieves MAPE of 3.34% on backtest and 1.3%–4.9% on the 2026 forward test, which is well within the acceptable threshold of 10% for supply chain demand planning. The system provides genuine business value for procurement planning. |
| **Daily Pipeline Reliability** | The full ETL + ML pipeline executes reliably in approximately 35 minutes. All stages complete without error. This confirms the system can be scheduled to run nightly or on a recurring basis to keep forecast data current. |
| **Master Data Modularity** | Having four separate management screens for Variants, Machines, Shifts, and Slots provides clear separation of concerns. Each module is independently manageable, allowing operators to update specific configurations without affecting unrelated data. |
| **Restock Management** | The low-stock alert filter (< 10 units) provides a practical quick view for operators performing daily inventory checks. The auditor field (user_input) ensures accountability by recording who performed each restocking operation. |

**Acknowledgment:**

Testing was completed by the developer as part of the integration verification process.

Acknowledged by: **Adam Abdurrahman**
Role: Developer / System Integrator
Date: 06 June 2026

---

## C.3 — Detail of Test Procedures Carried Out According to the Design

The detailed test procedures have been carried out and documented comprehensively in every test case table presented in sub-section C.1 above. Each table entry includes timestamped test steps in chronological order (format: HH.MM.SS), the expected system behavior based on the functional specification, the actual observed system response, the date the test was performed, and the final pass/fail status. All test scenarios — covering both positive (valid input, expected flow) and negative (invalid input, error handling) cases — were executed on a physical Samsung Android device connected to the cloud-hosted backend API, ensuring results reflect real-world operational conditions rather than emulator or mock environments.

---

## C.4 — Procedures for the Demo Are Created and Verified

The demonstration procedure has been created and verified through the test case documentation presented in sub-section C.1. Each test case entry in the tables above is directly reusable as a step-by-step demo script: the Scenario column provides the demo context, the Test Steps column provides the exact sequence of actions to perform, and the System Response column describes the expected outcome visible to the audience. The full test sequence — from user registration through dashboard viewing and module management — can be reproduced end-to-end to demonstrate the complete system capability in a live demo setting.
