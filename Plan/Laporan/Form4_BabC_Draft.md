# PART C: FUNCTIONAL TESTING

This section presents the functional testing results conducted on the completed Capstone Design Project. It covers all test cases, including positive paths, negative validations, input boundary limits, and database state transitions for all system features across the native Android application and FastAPI backend.

All functional tests are categorized by module and formatted in individual testing tables following the project guidelines.

---

## 1. Authentication and Registration Modules

### 1.1. Log In Process
This process tests user authentication, session security, backend validations, role checks, and network exception handling during the login flow.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Successful Login (Superadmin) | `Username/Email`: "superadmin",<br>`Password`: "Super123",<br>Click `btnLogin` | - App sends HTTP POST to `/login` with credentials.<br>- Backend returns HTTP 200 with user JSON (level_user = 9).<br>- App saves session in `SessionManager`.<br>- Displays Toast: `"Welcome, superadmin!"`.<br>- Navigates to `SidebarMenuActivity` showing User Management. | PASS |
| 2 | Successful Login (Normal User) | `Username/Email`: "normaluser",<br>`Password`: "Normal123",<br>Click `btnLogin` | - App sends HTTP POST to `/login`.<br>- Backend returns HTTP 200 with user JSON (level_user = 1).<br>- App saves session in `SessionManager`.<br>- Displays Toast: `"Welcome, normaluser!"`.<br>- Navigates to `SidebarMenuActivity` hiding User Management. | PASS |
| 3 | Login with Incorrect Password | `Username/Email`: "superadmin",<br>`Password`: "WrongPassword",<br>Click `btnLogin` | - App sends HTTP POST to `/login`.<br>- Backend returns HTTP 401: `{"detail": "Incorrect password"}`.<br>- App displays Toast: `"Incorrect password"`. | PASS |
| 4 | Login with Unregistered User | `Username/Email`: "unknownuser",<br>`Password`: "SomePass123",<br>Click `btnLogin` | - App sends HTTP POST to `/login`.<br>- Backend returns HTTP 404: `{"detail": "User not found"}`.<br>- App displays Toast: `"User not found"`. | PASS |
| 5 | Empty Fields Validation | `Username/Email`: "",<br>`Password`: "",<br>Click `btnLogin` | - App intercepts request locally (no API call is made).<br>- Displays warning icons on input fields: `"Username/Email is required"` and `"Password is required"`. | PASS |
| 6 | Login by Approved User with Pending OTP | `Username/Email`: "pendinguser",<br>`Password`: "UserPass123",<br>Click `btnLogin` | - App sends HTTP POST to `/login`.<br>- Backend returns HTTP 400: `{"detail": "PENDING_OTP"}`.<br>- App detects code and displays Alert Dialog: *"Verifikasi Akun - Akun Anda telah disetujui tetapi belum diaktifkan..."*.<br>- User clicks "Verifikasi Sekarang" -> Redirects to OTP verification form. | PASS |
| 7 | Network Offline / Server Unreachable | `Username/Email`: "superadmin",<br>`Password`: "Super123",<br>Click `btnLogin` (FastAPI backend is offline) | - OkHttp tries to connect to `http://10.0.2.2:8000` and times out.<br>- App catches `IOException` via `onFailure()`.<br>- Progress dialog is dismissed.<br>- Displays Toast: `"Network Error: Failed to connect to /10.0.2.2:8000"`. | PASS |

---

### 1.2. User Registration Process
This process tests the registration forms, local input validation rules, and double-layered verification (Admin approval + email OTP token confirmation).

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Successful Registration Request | `Full Name`: "Ahmad Andi",<br>`Email`: "andi@company.com",<br>`Phone`: "08123456789",<br>`Password`: "AndiPass123",<br>Click `btnRegister` | - App sends HTTP POST to `/api/v1/auth/register`.<br>- Backend writes user to database with `status_active = 'P'` (Pending) and `level_user = 1`.<br>- Backend sends OTP code to registered email.<br>- App displays Toast: `"Akun Pending! Silakan tunggu verifikasi Superadmin."`.<br>- Registration form is hidden; OTP verification layout (`layoutOtpForm`) becomes visible. | PASS |
| 2 | Registration Fields Empty Validation | `Full Name`: "", `Email`: "",<br>`Phone`: "", `Password`: "",<br>Click `btnRegister` | - App intercepts request locally.<br>- Displays validation messages: `"Nama Lengkap wajib diisi"`, `"Email wajib diisi"`, `"Nomor HP wajib diisi"`, and `"Password wajib diisi"` on corresponding fields. | PASS |
| 3 | Invalid Email / Phone format | `Email`: "andi-at-company",<br>`Phone`: "abcd123",<br>Click `btnRegister` | - App validation regex flags invalid patterns.<br>- Displays local field errors: `"Format email tidak valid"` and `"Nomor HP hanya boleh berisi angka"`. | PASS |
| 4 | Successful OTP Token Verification | `etRegOtp`: "987654",<br>Click `btnVerifyOtp` (correct OTP token entered) | - App sends HTTP POST to `/api/v1/auth/verify-token` with the token.<br>- Backend marks user as `status_active = '1'` (Active) in `master_user` table.<br>- App displays Toast: `"Akun berhasil diaktifkan! Silakan login."`.<br>- Redirects user to `LoginPageActivity`. | PASS |
| 5 | Invalid OTP Token Entry | `etRegOtp`: "000000",<br>Click `btnVerifyOtp` (incorrect/expired OTP entered) | - App sends HTTP POST to `/api/v1/auth/verify-token`.<br>- Backend returns HTTP 400: `{"detail": "Token/OTP tidak valid atau kedaluwarsa"}`.<br>- App displays Toast: `"Token/OTP tidak valid atau kedaluwarsa"`. | PASS |

---

### 1.3. Password Recovery Process (Forgot Password)
This process tests the request of OTP tokens for password recovery, validation of identity, and final submission of the new password.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Successful Forgot Password OTP Request | `Username`: "ahmad",<br>`Email`: "andi@company.com",<br>Click `btnSendOtp` | - App sends HTTP POST to `/api/v1/auth/reset-password/request`.<br>- Backend verifies username matches email, generates reset token, and emails it.<br>- Displays Toast: `"Debug OTP: [otp_code]"` in debug mode, and transitions to OTP/New Password confirmation layout. | PASS |
| 2 | Mismatched Username and Email | `Username`: "ahmad",<br>`Email`: "wrong@company.com",<br>Click `btnSendOtp` | - App sends HTTP POST request.<br>- Backend returns HTTP 404: `{"detail": "User not found"}`.<br>- Displays Toast: `"User not found"`. | PASS |
| 3 | Successful Password Reset Confirmation | `etOtp`: "123456",<br>`etNewPassword`: "NewSecurePass99",<br>Click `btnResetConfirm` | - App sends HTTP POST to `/api/v1/auth/reset-password/confirm`.<br>- Backend updates password hash in database and clears OTP token.<br>- Displays Toast: `"Password successfully reset. Please log in."`.<br>- Redirects to Login screen. | PASS |
| 4 | Invalid OTP Token on Confirmation | `etOtp`: "999999",<br>`etNewPassword`: "NewSecurePass99",<br>Click `btnResetConfirm` | - App sends HTTP POST request.<br>- Backend returns HTTP 400: `{"detail": "Invalid or expired OTP token"}`.<br>- Displays Toast: `"Invalid or expired OTP token"`. | PASS |

---

## 2. Dashboard and Navigation Modules

### 2.1. Sidebar Navigation Menu & Role-Based Access Control (RBAC)
This process tests the sidebar navigation drawer transitions, highlight styles, role-based visibility restrictions, and session termination.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Superadmin Menu Visibility | Log in as Superadmin (User Level = 9),<br>Open Sidebar Menu | - `tvUserName` displays "Superadmin".<br>- `tvUserRole` displays "Superadmin (Level 9)".<br>- User Management option (`menuMasterData`) is set to `View.VISIBLE` and is selectable. | PASS |
| 2 | Normal User Menu Visibility | Log in as Normal User (User Level = 1),<br>Open Sidebar Menu | - `tvUserName` displays the employee's name.<br>- `tvUserRole` displays "User Biasa".<br>- User Management option (`menuMasterData`) is programmatically set to `View.GONE` (completely hidden). | PASS |
| 3 | Selection Highlight and Redirect | Click on "Inventory Dashboard" row in the sidebar | - App calls `clearAllSelections()` to reset previous menu backgrounds.<br>- Selected row is set to `v.setSelected(true)` to change background color.<br>- Opens `InventoryDashboardActivity` and closes sidebar. | PASS |
| 4 | Safe Logout Action | Click on "Logout" menu row, click Positive on confirmation dialog | - App calls `SessionManager.logout()`.<br>- Clears shared preferences session keys.<br>- Displays Toast: `"Logging out..."`.<br>- Launches `LoginPageActivity` with flags `FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_CLEAR_TASK` to destroy the Activity backstack. | PASS |

---

### 2.2. General Affairs Dashboard (Stock & Sales Monitoring)
This process tests real-time operations visualization, chart generation (line and pie charts), date filters, and empty state rendering.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Load Dashboard with Valid Data | Open `DashboardSummaryActivity` | - App sends GET request to `/api/v1/dashboard/metrics`.<br>- Displays active metrics (Orders, Revenue, Price, Products Sold) with correct indicators.<br>- Renders `flavorPieChart` with sales share percentages.<br>- Renders `salesTrendChart` with historical transaction trend curves. | PASS |
| 2 | Apply Date Range Filter | Click `btnDateFilter`, select date range (e.g. May 1 to May 15, 2026), click Confirm | - App triggers network request with parameters `?start_date=2026-05-01&end_date=2026-05-15`.<br>- Metric cards, Pie chart, and Line chart update dynamically to reflect chosen dates. | PASS |
| 3 | Filter by Specific Shift | Select "Shift 2" in the `autoCompleteFilter` dropdown spinner | - App filters current dataset locally or makes API request with `?shift=SHIFT2`.<br>- Charts and transaction feeds display data belonging only to Shift 2. | PASS |
| 4 | Load Dashboard with Zero Transactions (Empty State) | Select date range with no sales logs (e.g. January 1 to January 2, 2026) | - API returns HTTP 404: `{"detail": "No data found for the selected period"}`.<br>- App clears pie/line charts and overlays empty text: `"Tidak ada data untuk periode ini"`. | PASS |
| 5 | Line Chart Scalability (High Date Range) | Select date range > 14 days (e.g., full month of May 2026) | - App detects date range > 14 days.<br>- Disables data point dots (`dataSet.setDrawCircles(false)`) and activates smooth cubic bezier lines to prevent visual overcrowding. | PASS |

---

## 3. Machine Learning and Forecasting Modules

### 3.1. Demand Forecasting Engine (ML UI & API)
This process tests loading forecasting outputs, chart rendering logic, Local/API synchronization, and backend safety checks (SATPAM data guards).

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Load Prediction Dashboard | Open `PredictionDashboardActivity` | - App fetches data from `/api/v1/forecast/history`.<br>- Displays active prediction quarter (e.g., Q3 2026).<br>- Renders error metrics (MAPE = 7.8%, MAE = 1250).<br>- Renders `forecast_chart` (predicted vs actual line series). | PASS |
| 2 | Toggle Prediction Graph View Modes | Select "Per Variant" from chart view dropdown spinner | - App switches chart series from Total to 4 separate lines representing variant flavors (Coklat, Strawberry, Moca, Original).<br>- Layout height expands from `270dp` to `500dp` to properly display chart details and prevent legend overlap. | PASS |
| 3 | Paginating Daily Forecast Logs | Click `btnLogNextMonth` or `btnLogPrevMonth` on daily log recycler | - Recycler dynamically filters and displays prediction vs actual error logs for the specific month in the selected quarter. | PASS |
| 4 | Generate Forecast with Complete Data | Trigger POST `/api/v1/forecast/generate` with parameters `{"start_month": "2026-07", "end_month": "2026-09"}` (Data coverage for prior month June is 85%) | - Backend SATPAM check passes (>80% threshold).<br>- XGBoost Layer 1 and Layer 2 models run chain predictions.<br>- Writes output to `ForecastResults_Layer1` and `ForecastResults_Layer2` tables.<br>- Returns HTTP 200 with forecast summary and smart insights. | PASS |
| 5 | Block Forecast Due to Incomplete Data (SATPAM Block) | Trigger POST `/api/v1/forecast/generate` for Q3 2026 when June data coverage is only 30%, and `force_run = false` | - Backend SATPAM check flags data gap.<br>- Operation blocked; returns HTTP 400: `{"detail": "Data coverage for June 2026 is only 30%. Forecast blocked to prevent distortion."}`. | PASS |
| 6 | Force Run Forecast with Data Gap | Trigger POST `/api/v1/forecast/generate` with `force_run = true` | - Backend bypasses the data gap check.<br>- Executes forecast using available data and falls back to business logic for extreme gap periods.<br>- Writes prediction rows and sets `is_data_gap = 1` in database. | PASS |

---

### 3.2. ML Model Retraining Operations
This process tests model training execution, hyperparameter grid search, accuracy evaluation, training logs display, and rollback mechanisms.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Trigger Manual Model Retraining | Trigger POST `/api/v1/model/retrain` | - Backend starts background thread.<br>- Executes ETL pipeline, constructs training features, performs GridSearchCV, and trains XGBoost.<br>- Saves new `.joblib` model artifact, backing up the old model file.<br>- Inserts run metrics (MAPE, hyperparameters) into `dbo.RetrainLog`. | PASS |
| 2 | Load Model Retrain Logs in App | Open `RetrainLogsActivity` | - App fetches logs via GET `/api/v1/retrain/logs`.<br>- Renders recycler cards showing execution timestamp, status badge, model version, and MAPE.<br>- Stripe color indicator displays Green for SUCCESS and Red for FAILED runs. | PASS |
| 3 | Reload Historical Forecasts from Logs | Click on a success log card from Q1 2026 | - App gets log year/quarter, returns `RESULT_OK` with data to `PredictionDashboardActivity`, and finishes.<br>- Dashboard reloads metrics and charts corresponding to Q1 2026. | PASS |
| 4 | Handle Training Data Spikes (Share Smoother test) | Execute retraining where June 2026 demand is extremely distorted due to Ramadan shutdown (Strawberry has 90% share) | - ETL pipeline runs Share Smoother.<br>- Corrects Strawberry share from 90% to interpolated 25.4% based on May and July bounds.<br>- XGBoost training continues with cleaned share features, preventing target leakage. | PASS |

---

## 4. Operational Configuration and Administrative Modules

### 4.1. Factory Operational Calendar Management
This process tests calendar visual grids, month navigation, day status adjustments, year additions/deletions, and automatic Indonesian holiday generation.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Load and Navigate Calendar | Open `CalendarOperationalActivity`, swipe monthly viewpager to the left | - App loads monthly calendar fragments.<br>- Swiping monthly view transitions layout smoothly.<br>- Calendar title `tvMonthTitle` updates instantly (e.g. "Juni 2026" to "Juli 2026"). | PASS |
| 2 | Open and Modify Day Status | Click on "15 June 2026" day cell in calendar grid, toggle Working Day to OFF, click Save | - Opens `EditDayBottomSheet` displaying active toggles.<br>- Toggling Working Day OFF auto-sets Shutdown to ON and deactivates Shift 1, 2, and 3 switches.<br>- Clicking save calls POST `/api/v1/calendar/day`.<br>- Database updates `OperationalCalendar` row.<br>- Calendar grid refreshes showing red highlight (Shutdown) for June 15. | PASS |
| 3 | Add New Operational Year | Click `btnAddYear`, input "2027", click Confirm | - App sends POST `/api/v1/calendar/generate?year=2027`.<br>- Backend calls `holidays.Indonesia` to auto-populate public holidays, generates 365 calendar rows in database, and seeds them.<br>- Calendar year spinner adds "2027" and reloads. | PASS |
| 4 | Delete Operational Year | Click `btnDeleteYear`, select "2026", click Positive on warning dialog | - App prompts warning dialog: *"Tindakan ini akan MENGHAPUS SELURUH data operasional..."*.<br>- Confirming triggers DELETE `/api/v1/calendar/year/2026`.<br>- Database deletes all 2026 rows.<br>- App removes 2026 from year list and refreshes UI. | PASS |

---

### 4.2. Excel Transaction Data Upload (Manual Insert)
This process tests exporting templates based on API version, Excel file picking, server-side data validation, ETL parsing summaries, and database writes.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Download Excel Template (Android 10+) | Click `btnDownloadTemplate` on Android 11 emulator | - App runs MediaStore code block saving template to `Downloads/` directory.<br>- Displays Toast: `"Template saved to Downloads folder."` without prompting runtime write permissions. | PASS |
| 2 | Download Excel Template (Android 9-) | Click `btnDownloadTemplate` on Android 9 emulator | - App falls back to standard external storage paths, requests write permission, saves template, and uses `FileProvider` to share access safely. | PASS |
| 3 | Upload Valid Excel Transactions | Select valid Excel template with 150 transaction rows, click `btnProcessUpload` | - App uploads file to `/api/v1/manual-insert/upload` as multipart form data.<br>- Backend parses excel columns, removes duplicates, validates formatting, and writes rows to database with `is_manual_insert = 1`.<br>- Displays summary dialog: *"Total processed: 150, Inserted: 145, Duplicates: 5, Invalid: 0"*. | PASS |
| 4 | Upload Invalid / Corrupted Excel File | Select an arbitrary text file or corrupted excel file, click `btnProcessUpload` | - App uploads file.<br>- Backend fails to parse column headers, returns HTTP 400: `{"detail": "Invalid file format. Missing required transaction columns."}`.<br>- Displays Toast: `"Upload failed: Invalid file format."`. | PASS |

---

### 4.3. Admin User Management
This process tests account status lists, pull-to-refresh indicators, manual verification overrides, role adjustments, and account deactivation.

| No. | Scenario | Every Possible Input | Expected Output | Output Result |
|:---|:---|:---|:---|:---|
| 1 | Load User List and Refresh | Open `MasterDataUserActivity`, perform pull-to-refresh swipe | - App sends GET `/api/v1/admin/users`.<br>- Recycler loads user cards with correct status colors (Green for Active, Red for Pending, Orange for Verification).<br>- SwipeRefresh indicator stops spinning upon data load. | PASS |
| 2 | Approve Pending User Account | Click "Setujui" on a user card with PENDING status | - App sends POST `/api/v1/admin/approve-user` with target `userId`.<br>- Backend changes status to `status_active = 'T'` (verification phase) and generates OTP token.<br>- Displays popup: *"Berikut 6-digit OTP Aktivasi untuk pengujian: [otp_code]"* enabling testing team to verify token easily. | PASS |
| 3 | Edit User Role and Password | Click "Edit" on user card, change level from 1 (User Biasa) to 9 (Superadmin), enter new password, click Save | - App sends PUT `/api/v1/admin/users/{userId}` with JSON containing new level and password.<br>- Database updates `master_user` record.<br>- User list updates card role to "Superadmin". | PASS |
| 4 | Deactivate / Delete User Account | Click "Hapus" on user card, click Positive on confirmation popup | - App displays warning dialog: *"Apakah Anda yakin ingin menolak atau menonaktifkan akun... ?"*.<br>- Clicking positive sends DELETE `/api/v1/admin/users/{userId}`.<br>- Backend sets `status_active = '0'` or deletes the row.<br>- Displays Toast: `"User successfully deactivated"`. | PASS |
