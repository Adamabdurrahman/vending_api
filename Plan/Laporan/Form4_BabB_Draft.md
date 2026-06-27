# PART B: PRODUCT DISPLAY

This section presents the visual exhibits of the completed Capstone Design Project. It showcases the user interfaces of the implemented software components (Android mobile application and FastAPI backend documentation). As described in Part A, this project is a software-based implementation and does not design or configure any custom hardware.

---

## 1. SOFTWARE PRODUCT DISPLAY

This chapter showcases the user interfaces of the native Android application developed in Java. For each screen, we provide a detailed explanation of its components, user inputs, layout behaviors, and all execution scenarios (such as success states, validation errors, dialog alerts, and loading overlays).

### 1.1. Authentication and Registration Screens

#### 1.1.1. Login Screen (`LoginPageActivity.java` & `activity_loginpage.xml`)
*   **Description**: The entry point of the mobile application. It handles secure user authentication against the FastAPI backend, fetches the user's role/level, and saves the session details locally in `SessionManager`.
*   **Key Components**:
    *   `TextInputEditText` for Username or Email input.
    *   `TextInputEditText` for Password input (with password visibility toggle).
    *   `MaterialButton` (`btnLogin`) to submit the authentication form.
    *   `TextView` (`tvForgotPassword`) to navigate to the password reset screen.
    *   `TextView` (`tvRegister`) with formatted, bolded text pointing to the register page.
    *   `ProgressBar` to indicate active background networking requests.
*   **Functional Scenarios & Error Handling**:
    *   **Success Scenario**: Submitting valid credentials triggers a `POST /login` request. The API returns an HTTP 200 containing user details (ID, email, user level). The app saves these keys in `SessionManager`, displays a welcome Toast (`"Welcome, [username]"`), and starts `SidebarMenuActivity`.
    *   **Empty Fields Scenario**: Clicking Login with empty inputs triggers local validation. Field errors are displayed: `"Username/Email is required"` on the email field, or `"Password is required"` on the password field.
    *   **Pending OTP Scenario**: If the user has been approved by the Superadmin but has not verified their email via OTP, the API returns a 400 error payload containing error code `"PENDING_OTP"`. The app parses this JSON detail and displays an Alert Dialog: *"Verifikasi Akun - Akun Anda telah disetujui oleh Superadmin tetapi belum diaktifkan. Apakah Anda ingin memasukkan OTP verifikasi sekarang?"*. Clicking positive redirects the user directly to the Register screen with the OTP input layout enabled.
    *   **Invalid Credentials Scenario**: Submitting incorrect passwords or unregistered usernames displays a Toast containing the error message returned from the backend (e.g., `"Incorrect password"` or `"User not found"`).
    *   **Network Failure Scenario**: If the backend server is unreachable or offline, the OkHttp client triggers `onFailure()` after a timeout threshold, displaying a Toast: `"Network Error: [Exception Message]"`.

```
[IMAGE: Screenshot of the Android Login Screen with empty credentials showing validation errors]
[IMAGE: Screenshot of the Login screen showing the verification dialog for pending OTP status]
```

#### 1.1.2. Registration Screen (`RegisterActivity.java` & `activity_register.xml`)
*   **Description**: Allows new employees or staff members to register for access. Accounts are created with `level_user = 1` (User Biasa) and `status_active = 'P'` (Pending Superadmin approval).
*   **Key Components**:
    *   `TextInputEditText` fields for Full Name (`username`), Primary Email (`email_primary`), Phone Number (`nohp`), and Password.
    *   `MaterialButton` (`btnRegister`) to submit the registration form.
    *   `LinearLayout` (`layoutRegisterForm`) containing the initial registration input fields.
    *   `LinearLayout` (`layoutOtpForm`) containing the OTP token verification field (`etRegOtp`) and verify button (`btnVerifyOtp`). This layout is hidden by default.
    *   `FrameLayout` (`progressOverlay`) containing a loading spinner to block screen interaction during network transactions.
*   **Functional Scenarios & Error Handling**:
    *   **Successful Request**: Submitting the registration form triggers `POST /api/v1/auth/register`. Upon HTTP 200, the app displays a Toast: `"Akun Pending! Silakan tunggu verifikasi Superadmin."`, hides `layoutRegisterForm`, and exhibits `layoutOtpForm` to prepare for OTP entry.
    *   **OTP Verification Success**: Entering the 6-digit OTP token received in the registered email triggers `POST /api/v1/auth/verify-token`. Upon success, the app shows a Toast: `"Akun berhasil diaktifkan! Silakan login."`, and redirects to `LoginPageActivity`.
    *   **Empty/Validation Failure**: Submitting with empty fields stops the request locally and displays: `"Nama Lengkap wajib diisi"`, `"Email wajib diisi"`, `"Nomor HP wajib diisi"`, or `"Password wajib diisi"` on the respective fields.
    *   **Incorrect OTP Token**: If the user submits an incorrect or expired 6-digit token, the backend returns an HTTP 400 error. The application parses the response error body and displays: `"Token/OTP tidak valid atau kedaluwarsa"` via a Toast.

```
[IMAGE: Screenshot of the Android Registration form screen showing input fields]
[IMAGE: Screenshot of the Register screen transitioned into the OTP verification input form]
```

#### 1.1.3. Forgot Password Screen (`ForgotPasswordActivity.java` & `activity_forgot_password.xml`)
*   **Description**: Enables users to recover their accounts by resetting their passwords using an OTP token generated by the server.
*   **Key Components**:
    *   `TextInputEditText` fields for Username and Email in the request phase.
    *   `TextInputEditText` fields for OTP token and New Password in the reset confirmation phase.
    *   `LinearLayout` (`layoutResetRequest`) and `LinearLayout` (`layoutResetConfirm`) to toggle between input forms.
    *   `MaterialButton` (`btnSendOtp` and `btnResetConfirm`) to trigger API operations.
*   **Functional Scenarios & Error Handling**:
    *   **Success OTP Request**: Submitting username and email calls `POST /api/v1/auth/reset-password/request`. Upon HTTP 200, it transitions to the confirm form. In development, a Toast is shown displaying: `"Debug OTP: [otp_code]"` for instant testing.
    *   **Success Reset**: Entering the correct OTP and new password calls `POST /api/v1/auth/reset-password/confirm`. Upon success, the user is redirected to the Login Screen.
    *   **Verification Errors**: Entering invalid formats or unmatched emails returns standard API error messages displayed via Toast (e.g. `"User not found"`).

```
[IMAGE: Screenshot of the Forgot Password requesting phase]
[IMAGE: Screenshot of the Forgot Password validation phase with OTP and new password inputs]
```

---

### 1.2. Core Navigation and Dashboard Screens

#### 1.2.1. Sidebar Navigation Menu (`SidebarMenuActivity.java` & `activity_sidebar_menu.xml`)
*   **Description**: The central navigation panel (drawer-style layout) containing links to all functional modules of the system.
*   **Key Components**:
    *   `TextView` (`tvUserName`) and `TextView` (`tvUserRole`) displaying the logged-in user's name and role retrieved from `SessionManager`.
    *   Navigation rows (`LinearLayout` widgets behaving as buttons) for Dashboard Summary, Inventory Dashboard, Prediction Dashboard, Employee Management, Operational Calendar, Insert Manual Excel, and Account settings.
    *   `LinearLayout` (`menuMasterData`) representing the User Management menu.
    *   Logout menu row (`menuLogout`) to clear shared preferences session data and exit.
*   **Functional Scenarios & Role-Based Access Control (RBAC)**:
    *   **Superadmin Access (Level 9)**: If the logged-in user level is `9`, `tvUserRole` displays `"Superadmin"`. The menu item `menuMasterData` (Master Data User) is programmatically set to `View.VISIBLE`, allowing full user administration control.
    *   **Normal User Access (Level 1)**: If the user level is `1`, `tvUserRole` displays `"User Biasa"`. The `menuMasterData` layout is set to `View.GONE`, restricting access to administrative menus.
    *   **Selection Highlight**: Selecting any menu row triggers `clearAllSelections()` to reset all backgrounds, highlights the selected layout (`v.setSelected(true)`), and starts the corresponding Activity.
    *   **Logout Confirmation**: Clicking logout calls `SessionManager.logout()` to clear all session cookies, shows a Toast: `"Logging out..."`, and launches `LoginPageActivity` with flags `FLAG_ACTIVITY_NEW_TASK | FLAG_ACTIVITY_CLEAR_TASK` to destroy the backstack.

```
[IMAGE: Screenshot of the Sidebar Menu layout as a Superadmin showing the active Master Data User row]
[IMAGE: Screenshot of the Sidebar Menu layout as a Normal User restricting the Master Data row]
```

#### 1.2.2. General Affairs Dashboard Summary (`DashboardSummaryActivity.java` & `activity_dashboard_summary.xml`)
*   **Description**: Provides General Affairs (GA) staff with real-time operations overview including VM transactions, daily sales charts, flavor preference pie charts, and recent transaction feeds.
*   **Key Components**:
    *   **Metric Cards**: Four rounded Material CardViews displaying total Orders, total Revenue, Average Price, and Products Sold. Each card includes indicator tags representing percentage changes compared to the prior period.
    *   **Date Range Filter Button (`btnDateFilter`)**: Opens `MaterialDatePicker` range picker to filter dashboard data.
    *   **Shift Dropdown (`autoCompleteFilter`)**: Spinner filtering data to Shift 1, Shift 2, Shift 3, or ALL.
    *   **Pie Chart (`flavorPieChart`)**: MPAndroidChart rendering variant sales shares.
    *   **Line Chart (`salesTrendChart`)**: MPAndroidChart rendering consumption trends over dates.
    *   **Legend Container (`legendContainer`)**: Linear layout for adding dynamic legend rows programmatically.
    *   **Transactions Recycler (`rvDashboardTransactions`)**: Lists the 10 latest VM transaction logs.
*   **Functional Scenarios & Visual Details**:
    *   **Dynamic Sales Legend**: The Pie Chart legend is not hardcoded. The activity reads the API arrays, calculates percentage shares, maps them to color tags (`PIE_COLORS`), and inserts custom labels into `legendContainer` dynamically.
    *   **No Data (HTTP 404)**: If a date range has no logs, the API returns HTTP 404. The app handles this gracefully, clearing charts and displaying `"Tidak ada data untuk periode ini"`.
    *   **Line Chart Auto-Scale**: The line chart renders dots if the range is $\le 14$ days to maintain visual clarity. If range $> 14$ days, dots are disabled (`dataSet.setDrawCircles(false)`) and smooth cubic bezier curves are drawn.

```
[IMAGE: Screenshot of the Dashboard Summary displaying active sales charts, cards, and transaction recyclers]
[IMAGE: Screenshot of the Dashboard Summary showing empty states with no data available warnings]
```

---

### 1.3. Machine Learning Forecasting and Operations

#### 1.3.1. Demand Prediction Dashboard (`PredictionDashboardActivity.java` & `activity_prediction_dashboard.xml`)
*   **Description**: Displays quarterly forecasting reports generated by the XGBoost Machine Learning model. It presents historical performance compared to forecasts, error tracking, and links to retrain logs.
*   **Key Components**:
    *   **Main Header Badge (`tvQuarterTitle`)**: Displays the currently loaded forecast period (e.g. *"Kuartal 3 2026"*).
    *   **Primary Metrics**: Main Accuracy card (`tvMainAccuracy` rendering `100% - MAPE`) and detailed MAPE sub-values.
    *   **Monthly Cards**: 3 sub-cards showing total demand and error indicators for Month 1, Month 2, Month 3.
    *   **Forecast Trend Chart (`forecast_chart`)**: Line chart showing predicted vs actual lines.
    *   **Flavor Distribution Recycler (`rvFlavorPredictions`)**: Shows horizontal error progress bars for each variant.
    *   **Shift Error Radar Chart (`shiftErrorChart`)**: MPAndroidChart Radar chart plotting absolute error mapping.
    *   **Daily Log Recycler (`rvDailyErrorLogs`)**: Shows exact daily logs comparing prediction vs actual values.
*   **Functional Scenarios & Details**:
    *   **Line Chart Modes**: Dropdown filter changes line chart series between *Total Demand*, *Total Per Variant* (Coklat, Strawberry, Moca, Original lines), and *Total Per Shift* (Shift 1, 2, 3, Putih lines).
    *   **Dynamic Chart Height**: The Line Chart layout adjusts its height dynamically depending on the series mode (e.g., expanding from `270dp` in Total mode to `500dp` in Shift mode to fit the legend and prevent overlap).
    *   **Radar Chart Singkat Shift**: Sumbu radar disingkat secara dinamis (misalnya `"SHIFT1 - AWAL"` disingkat menjadi `"S1-AWL"`) untuk menghindari penumpukan teks.
    *   **Daily Logs Pagination**: Buttons `btnLogPrevMonth` and `btnLogNextMonth` filter daily log items locally to Month 1, 2, or 3 of the selected quarter.

```
[IMAGE: Screenshot of the ML Prediction Dashboard displaying line charts comparing predictions vs actuals]
[IMAGE: Screenshot of the Prediction Dashboard displaying the Shift Error Radar Chart and Flavor error progress bars]
```

#### 1.3.2. Machine Learning Model Retrain Logs (`RetrainLogsActivity.java` & `activity_retrain_logs.xml`)
*   **Description**: Displays historical logs of the ML Model training pipeline from the API endpoint `GET /api/v1/retrain/logs`. It serves as a portal to reload the forecast dashboard for historical quarters.
*   **Key Components**:
    *   **Logs RecyclerView (`rvRetrainLogs`)**: Cards representing historical model runs.
    *   **Progress Loading Overlay (`loadingOverlay`)**: Displayed during API request.
*   **Functional Scenarios & Details**:
    *   **Log Card Details**: Displays Execution Timestamp, Status Badge (Success / Failed), Target Quarter, Model Version, accuracy metrics (MAPE, MAE, RMSE), training row counts, and data sync cutoffs.
    *   **Status Color Bar**: An accent stripe on the left edge of each card changes dynamically (Green for `"Success"`, Red for `"Failed"`).
    *   **Forecast Reload Trigger**: Clicking on any log card extracts its year and quarter, calls `setResult(RESULT_OK)` back to `PredictionDashboardActivity`, and finishes the activity. The prediction activity then executes a refresh to load that specific quarter's metrics.

```
[IMAGE: Screenshot of the Retrain Logs screen displaying historical training parameters and error metrics]
```

---

### 1.4. Operational Calendar and Configuration Screens

#### 1.4.1. Factory Operational Calendar (`CalendarOperationalActivity.java` & `activity_operational_calendar.xml`)
*   **Description**: Interface for managing working days, shutdowns, and shift overrides, which dynamically adjusts ML forecast features.
*   **Key Components**:
    *   **Year Spinner (`spinnerYear`)**: Dropdown displaying years present in the database.
    *   **ViewPager2 (`viewPagerCalendar`)**: Swipeable layout hosting 12 monthly calendar grid fragments.
    *   **Header Navigators (`btnPrevMonth` and `btnNextMonth`)**: Buttons to slide ViewPager2.
    *   **Actions Panel**: Add Year (`btnAddYear`) and Delete Year (`btnDeleteYear`) buttons.
    *   **Total Work Days Text (`tvTotalWorkingDays`)**: Summary total of active workdays.
*   **Functional Scenarios & Details**:
    *   **Monthly Swipe Navigation**: Swiping left/right transitions the month. The app automatically updates the header text (`tvMonthTitle`) to match the current index (e.g. *"Juli 2026"*).
    *   **Add Year Dialog**: Clicking Add Year prompts an AlertDialog with an input field suggesting the next sequential year (e.g., `2027`). Confirming triggers a `POST api/v1/calendar/generate` API call, which prompts the backend to auto-detect holidays and generate 365 calendar rows.
    *   **Delete Year Confirmation**: Clicking Delete Year opens a warning confirmation: *"Tindakan ini akan MENGHAPUS SELURUH data operasional untuk tahun [year] secara permanen."*. Confirming triggers a `DELETE` call to the server.

```
[IMAGE: Screenshot of the Operational Calendar swiped to a specific month layout displaying calendar grids]
[IMAGE: Screenshot of the confirmation prompt dialog for adding a new calendar year]
```

#### 1.4.2. Day Edit Dialog Sheet (`EditDayBottomSheet.java` & `bottom_sheet_edit_day.xml`)
*   **Description**: A Modal Bottom Sheet dialog opened by clicking any day in the operational calendar grid.
*   **Key Components**:
    *   `TextView` showing the target date.
    *   `Switch` for Working Day status (`switchWorkingDay`).
    *   `Switch` for Shutdown Day status (`switchShutdown`).
    *   `Switch` widgets for Shift 1 Active, Shift 2 Active, and Shift 3 Active.
    *   `EditText` (`etDescription`) to input holiday name or notes.
*   **Functional Scenarios & Verification**:
    *   **Auto-Toggles**: Turning Working Day *OFF* automatically toggles Shutdown *ON*, and sets all Shift switches to *OFF* to prevent conflicting states.
    *   **Save Action**: Clicking Save compiles the state into an `UpdateDayRequest` object and makes a `POST api/v1/calendar/day` API call. Upon HTTP 200, the dialog triggers `OnDayUpdatedListener` to refresh the parent calendar grid and dismisses itself.

```
[IMAGE: Screenshot of the Day Edit Bottom Sheet displaying working status toggles and description input]
```

---

### 1.5. Manual Data Insertion and User Administration

#### 1.5.1. Excel Transaction Manual Insert (`ManualInsertActivity.java` & `activity_manual_insert.xml`)
*   **Description**: Provides manual upload capabilities for transaction records. Users download an Excel template, fill in transactions, and upload the file to be processed by the ETL pipeline.
*   **Key Components**:
    *   **Download Button (`btnDownloadTemplate`)**: Triggers Excel template download from the backend.
    *   **Upload Drop Zone Card (`dropZone`)**: Clickable layout representing the Excel file picker.
    *   **File Status Row (`layoutFileSelected`)**: Displays selected file name (`tvSelectedFileName`) and clear button (`btnClearFile`).
    *   **Action Button (`btnProcessUpload`)**: Initiates the API upload process.
*   **Functional Scenarios & Storage Adaptations**:
    *   **Android 10+ (API 29+) MediaStore Downloader**: Uses `MediaStore.Downloads` API to save the template to the public `Downloads/` directory without requiring file write runtime permissions.
    *   **Android 9- FileProvider Downloader**: Saves files using legacy paths (`DIRECTORY_DOWNLOADS`) and opens them using `FileProvider` to share securely with spreadsheet applications.
    *   **Excel Upload Result Dialog**: Upon successful upload via `POST api/v1/manual-insert/upload`, the backend response is displayed in a detailed AlertDialog showing: total rows processed, inserted rows, duplicates skipped, and invalid records.

```
[IMAGE: Screenshot of the Manual Insert screen with drag-and-drop zone and selected Excel file]
[IMAGE: Screenshot of the Excel parsing summary popup dialog showing successful insertions]
```

#### 1.5.2. Admin User Management (`MasterDataUserActivity.java`, `UserAdapter.java` & `activity_master_data_user.xml`)
*   **Description**: Superadmin administration panel to review registrations, approve accounts, change roles, or delete users.
*   **Key Components**:
    *   `SwipeRefreshLayout` to pull-to-refresh the user list.
    *   `RecyclerView` (`rvUsers`) listing user cards.
    *   `LinearLayout` (`emptyStateLayout`) displayed if user lists are empty.
*   **Functional Scenarios & Actions**:
    *   **Status Indicators**: Each user card has a colored stripe and badge corresponding to their activation state: Green/`ACTIVE` (status 1), Red/`PENDING` (status P), Orange/`VERIFICATION` (status T).
    *   **Approve Dialog (Pending users)**: Clicking "Setujui" triggers `POST /api/v1/admin/approve-user`. The app displays a popup containing the activation OTP token generated for development: *"Berikut 6-digit OTP Aktivasi untuk pengujian: [otp_code]"*.
    *   **Edit User Dialog**: Allows the admin to change user role level (1 to 9) and enter a new password.
    *   **Reject/Deactivate Action**: Clicking delete opens a confirmation: *"Apakah Anda yakin ingin menolak atau menonaktifkan akun [username]?"*. Confirming calls `DELETE /api/v1/admin/users/{userId}` to deactivate the account.

```
[IMAGE: Screenshot of the User Management list layout displaying status badges and administrative action buttons]
[IMAGE: Screenshot of the Admin edit role and password dialog overlay]
```

---

### 1.6. API Reference Screen (FastAPI Swagger UI)
*   **Description**: Interactive API documentation generated by FastAPI, accessible locally via Web Browsers.
*   **Key Components**:
    *   Grouped endpoint router tabs: `/login`, `/account`, `/api/v1/dashboard`, `/api/v1/prediction`, `/api/v1/retrain`, `/api/v1/calendar`, and `/api/v1/manual-insert`.
    *   Expandable request bodies, parameters list, and schema details.
    *   Interactive "Try it out" feature allowing developers to test API responses from browser sandboxes.

```
[IMAGE: Screenshot of the FastAPI Swagger UI documentation page showing available endpoint groups]
```

---

## 2. HARDWARE PRODUCT DISPLAY

*Not Applicable*. As documented in Part A, this project is a purely software-based implementation focusing on the native Android mobile application, the Python REST API backend, the database tables, and the Machine Learning prediction modules. The system reads transaction records produced by existing vending machine nodes as data sources, but does not design, manufacture, or implement any custom hardware boards or circuit schematics.
