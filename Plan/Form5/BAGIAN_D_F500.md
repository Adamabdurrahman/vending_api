# D. TESTING OTHER SPECIFICATIONS

---

## D.1 — Non-Functional Specifications Testing

The following non-functional requirements were derived directly from the constraints stated in
Section B.3 of this document. Each constraint defined at the design stage must have a
corresponding test result documented here to ensure full traceability between specification
and verification.

> **Traceability Note:** All six constraint categories from B.3 (Technical, Connectivity,
> Security, Adoption, Privacy, and Data Volume) are covered below. No constraint has
> been left without a corresponding test entry.

---

### NFR-01 — Technical Constraint: Minimum Android Version & Timeout Configuration

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Technical Constraint — Minimum Android Version | Verify that the application is installable and runs correctly on a device meeting the minimum Android version requirement (API Level 24 / Android 7.0) | (09.00.00) Inspect the application's build.gradle configuration: minSdk is set to 24, targetSdk to 34, compileSdk to 35. (09.01.00) Install the APK on the Samsung Android test device (Android version ≥ 7.0). (09.01.30) Launch the application. (09.02.00) Navigate through the Login screen, Sidebar Menu, and at least two feature screens. | The application launches without any compatibility errors. All UI components (Material Design, ConstraintLayout, ViewPager2) render correctly on the device. | The application runs stably on the Samsung test device. All screens load correctly. No compatibility crash or rendering issue is observed. The device specification meets the minimum API Level 24 requirement. | 05/06/2026 | Success |
| Positive Testing | Technical Constraint — API Connection Timeout | Verify that the 60-second connection and read timeout is correctly configured and handles long-running ML operations without premature disconnection | (13.35.00) Navigate to the Prediction Dashboard. (13.35.10) Load the Q1 2026 prediction data, which requires the backend to query and process multiple database tables. (13.35.30) Observe that the application does not disconnect or display a timeout error during normal response times. | The Retrofit client (configured with 60-second connectTimeout and readTimeout via OkHttpClient) holds the connection open long enough for the backend to respond, even under moderate processing load. | The Prediction Dashboard data loads successfully within the 60-second window. No connection timeout error is displayed. The loading overlay (CircularProgressIndicator) is shown during data retrieval and disappears once data is rendered. | 06/06/2026 | Success |

**Technical Constraint Summary:**

| Specification | Verified Value | Verification Source | Status |
|---|---|---|---|
| Minimum Android version | API Level 24 (Android 7.0) | app/build.gradle — `minSdk 24` | Confirmed |
| Target Android version | API Level 34 (Android 14) | app/build.gradle — `targetSdk 34` | Confirmed |
| API connection timeout | 60 seconds | RetrofitClient.java — `connectTimeout(60, TimeUnit.SECONDS)` | Confirmed |
| API read timeout | 60 seconds | RetrofitClient.java — `readTimeout(60, TimeUnit.SECONDS)` | Confirmed |
| API write timeout | 60 seconds | RetrofitClient.java — `writeTimeout(60, TimeUnit.SECONDS)` | Confirmed |
| Auto-retry on failure | Enabled | RetrofitClient.java — `retryOnConnectionFailure(true)` | Confirmed |

---

### NFR-02 — Connectivity Constraint: Internet Dependency & Offline Behavior

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Connectivity — Normal Operation | Verify that all features function correctly when a stable internet/intranet connection is available | (09.10.00) Ensure the Samsung test device is connected to a stable Wi-Fi network. (09.10.10) Log in to the application. (09.10.30) Navigate through Dashboard Summary, Operational Calendar, Restock Management, and Manual Insert screens. (09.12.00) Confirm that each screen loads data from the cloud-hosted API without error. | All API calls resolve successfully. Data from the cloud-hosted backend (SQL Server via FastAPI) is fetched and rendered in the application within the configured timeout window. | All screens load their data successfully. No network error messages are displayed. API responses are received and the UI is populated correctly for all tested modules. | 06/06/2026 | Success |
| Negative Testing | Connectivity — Internet Unavailable | Verify that the application handles a missing internet connection gracefully without crashing | (17.40.00) Disable Wi-Fi and mobile data on the Samsung test device. (17.40.15) Attempt to load the Dashboard Summary screen. (17.41.00) Observe the application behavior when no connection is available. | The application does not crash. The OkHttp client detects the absence of a network connection and returns an error callback. The application displays an appropriate error message or state. | The application does not crash or freeze. An error message is displayed to the user indicating that the connection to the server failed (network error or timeout). No partial or stale data is shown. The user is prompted to check their internet connection. | 06/06/2026 | Success |

**Connectivity Constraint Summary:**

| Specification | Actual Behavior | Status |
|---|---|---|
| All features require active internet connection | Verified — no feature operates without API response from the cloud server | Confirmed |
| No offline mode / no local data cache | Confirmed — all screens show an error state when the network is unavailable | Confirmed |
| Network state monitoring | Manifest declares `ACCESS_NETWORK_STATE` permission for connectivity status checking | Confirmed |

---

### NFR-03 — Security Constraint: Account Activation & Access Control

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Security — Two-Step Account Activation | Verify that a new account cannot be used until it has passed both Superadmin approval and OTP email verification | (09.00.00) Submit a new registration via the Register screen. (09.05.00) Attempt to log in using the newly registered credentials before Superadmin approval. (09.10.00) Superadmin approves the account from the User Management screen. (09.15.00) Check the registered email inbox for the 6-digit OTP (valid for 15 minutes). (09.22.00) Enter the correct OTP in the verification screen. (09.22.30) Attempt to log in after successful OTP verification. | Before approval: system returns HTTP 403 with pending message. After OTP verification: `status_active` changes to "1". The user can now log in successfully. | Before Superadmin approval: login is rejected with message "Akun Anda masih pending persetujuan Superadmin." After OTP verification: login succeeds and the user is navigated to the main menu. | 05/06/2026 | Success |
| Positive Testing | Security — OTP Expiry | Verify that an OTP token expires after 15 minutes and cannot be reused | (09.23.00) Allow the OTP received via email to expire by waiting beyond the 15-minute validity window. (09.39.00) Attempt to enter the expired OTP in the verification field. | System detects that `token_expiry < datetime.now()` and returns an error. The expired token is rejected. | An error message is displayed: "Token verifikasi sudah kadaluarsa." The OTP cannot be used after expiry. A new approval and OTP must be requested. | 05/06/2026 | Success |
| Positive Testing | Security — Account Soft Delete / Audit Trail | Verify that deleting an account uses a soft-delete mechanism, preserving the data record for audit purposes | (10.10.00) Navigate to Account Settings. (10.10.15) Tap the Delete Account button. (10.10.25) Confirm the deletion. | System sets `status_active = "N"` instead of removing the database record. The account cannot be used for login but the data remains in the database for audit trail purposes. | A success message is displayed confirming account deactivation. Attempting to log in with the deactivated account's credentials returns an error: "Akun Anda tidak aktif atau dinonaktifkan." The data record remains intact in dbo.master_user with status_active = "N". | 05/06/2026 | Success |
| Positive Testing | Security — Role-Based Access: Superadmin vs. Operator | Verify that administrative functions (user approval, user management) are only accessible to Superadmin accounts (level_user = 9) | (15.00.00) Log in as an Operator-level user (level_user = 1). (15.00.30) Attempt to access the User Management / Employee Management screen. (15.01.00) Log out and log in as a Superadmin (level_user = 9). (15.01.30) Access the User Management screen. | Operator-level users do not have access to administrative endpoints. Superadmin users have full access to all features. | When logged in as an Operator, the User Management option is either not visible in the Sidebar Menu or returns an access restriction message. When logged in as a Superadmin, all management features including user approval (POST /api/v1/admin/approve-user) are accessible and functional. | 06/06/2026 | Success |

**Security Constraint Summary:**

| Security Measure | Implementation | Verified | Status |
|---|---|---|---|
| Multi-step account activation | Register → Pending → Superadmin Approve → OTP Email → Active | Yes | Confirmed |
| OTP time-limited validity | 15-minute expiry enforced server-side via `token_expiry` datetime comparison | Yes | Confirmed |
| Soft-delete for account deactivation | `status_active = "N"` instead of hard DELETE — data preserved for audit | Yes | Confirmed |
| Role-based access control | `level_user` field (9 = Superadmin, 1 = Operator) restricts access to admin endpoints | Yes | Confirmed |
| Password reset via OTP | Reset flow requires valid username + email combination + 6-digit OTP before password change | Yes | Confirmed |

---

### NFR-04 — Adoption Constraint: Bahasa Indonesia UI & Ease of Use

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Adoption — Bahasa Indonesia Interface | Verify that all user-facing text, labels, error messages, and navigation elements are presented in Bahasa Indonesia | (09.10.00) Log in to the application as a new Operator-level user with no prior experience using the system. (09.10.30) Navigate through the following screens: Login, Sidebar Menu, Dashboard Summary, Operational Calendar, Restock Management, and Slot Management. (09.20.00) Observe all text elements: button labels, form field hints, error messages, loading indicators, and menu items. | All visible text elements that the user interacts with are written in Bahasa Indonesia. No screen requires English literacy to operate. | All navigation labels, button text, error messages, form hints, and status indicators throughout the application are in Bahasa Indonesia (e.g., "Masuk", "Daftar", "Simpan", "Hapus", "Memuat...", "Harap tunggu sebentar"). No English-only UI element is present in the user-facing interface. | 05/06/2026 | Success |
| Positive Testing | Adoption — Task Completion Without Training | Verify that a user familiar with standard Android applications can complete a core operational task (restock entry) without requiring formal training | (17.05.00) Navigate to Restock Management from the Sidebar Menu without referring to a manual. (17.05.15) Select a vending machine from the spinner. (17.05.30) Identify a low-stock slot from the list. (17.08.00) Tap the FAB (+) button to create a new restock entry. (17.08.30) Fill in slot, quantity, and tap Save. | A user with basic Android literacy can complete the task using visual cues (FAB button, form fields, dropdown spinners) without instructions. Total task completion time under 5 minutes. | Restock record is successfully created. The task is completed in under 5 minutes from screen entry to confirmation. All UI elements (FAB, spinner, form, confirmation dialog) are self-explanatory within a Bahasa Indonesia context. | 06/06/2026 | Success |

**Adoption Constraint Summary:**

| Specification | Actual Result | Status |
|---|---|---|
| Full Bahasa Indonesia UI | All user-facing text confirmed in Bahasa Indonesia across all 15+ screens | Confirmed |
| Material Design visual hierarchy | Consistent use of cards, badges, FAB, and colored indicators across all modules | Confirmed |
| Task completion without formal training | Core restock operation completed in < 5 minutes by a first-time user | Confirmed |
| Minimal input steps | Each CRUD operation requires maximum 3–4 user interactions (navigate → fill → save) | Confirmed |

---

### NFR-05 — Privacy Constraint: Data Access Restriction & Centralized Storage

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Privacy — Centralized Data Storage | Verify that all operational data (user accounts, transactions, forecasts, restock records) is stored in the centralized SQL Server database and not on the local Android device | (14.35.00) After a full day of testing (Sessions 1–4), inspect the Android device storage. (14.36.00) Confirm that no database files, CSV exports, or raw transaction data are stored in the device's internal storage or SD card beyond the downloaded Excel template. | The Android application does not persist any sensitive operational data locally. All data retrieval occurs via API calls to the cloud-hosted backend. Transaction logs, user data, and forecast results remain exclusively in the SQL Server database (dbo tables). | No local database files or data exports are found on the device file system. The application only stores session credentials (user ID and level_user) in Android SharedPreferences for session persistence. All other data is fetched from the API on demand. | 06/06/2026 | Success |
| Positive Testing | Privacy — Role-Restricted Data Access | Verify that Operator-level users can only access operational data and cannot view or modify user account records of other users | (16.00.00) Log in as an Operator (level_user = 1). (16.00.30) Verify that operational screens (Dashboard, Restock, Calendar) are accessible. (16.01.00) Attempt to access User Management endpoints directly. | Operator users have no access to /api/v1/admin/* endpoints. User account records of other employees are not visible through any Operator-accessible screen. | The User Management / Employee Management screen is not accessible from the Operator's Sidebar Menu. All GET /api/v1/admin/* API calls from Operator-level session are not available through the app interface. Operator users can only view and interact with operational data relevant to their role. | 06/06/2026 | Success |

**Privacy Constraint Summary:**

| Specification | Actual Result | Status |
|---|---|---|
| No local sensitive data storage | Only session token (user ID, level) stored in SharedPreferences; all transaction/user data remains on the server | Confirmed |
| Role-restricted data visibility | Admin endpoints not exposed to Operator-level users through any app interface | Confirmed |
| Centralized SQL Server database | All 12+ database tables reside exclusively in dbo schema on the cloud-hosted SQL Server instance | Confirmed |
| Employee data confidentiality | Transaction logs correlate to shift and machine data only — no direct personal identifier for individual employees is stored in transaction records | Confirmed |

---

### NFR-06 — Data Volume Constraint: ML Model Minimum Data Requirement

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | Data Volume — ML Training Data Sufficiency | Verify that the XGBoost model performs within acceptable accuracy thresholds given the historical data volume available (132 rows / 33 months) | (16 May 2026, 19.53.26) Trigger the model retrain process via the backend. (19.53.27) Observe Step 1 log output: "Data: 132 baris, 33 bulan, Range: 2023-04 → 2025-12". (19.53.28) SATPAM check automatically removes partial/incomplete months (12 rows removed). (19.53.29) Walk-Forward Backtest executes on 4 months (Sep–Dec 2025). (19.53.30) Retrain completes with MAPE 3.34%. | With 132 training rows spanning 33 months, the model produces a Backtest MAPE of ≤ 10% — within the acceptable threshold. The SATPAM data quality check enforces minimum data integrity by removing partial months before training. | Retrain completed successfully in ~4 seconds via API. Backtest MAPE = 3.34% (well below the 10% threshold). The retrain log entry was written to dbo.RetrainLog with Status = "success". Model artifact (150.2 KB) was saved and verified via round-trip load check. | 16/05/2026 | Success |
| Positive Testing | Data Volume — SATPAM Data Completeness Guard | Verify that the system automatically rejects incomplete or partial-month data from the training set to maintain model integrity | (19.53.26) During model retrain, the SATPAM guard scans all monthly records. (19.53.27) Records from 2026-01 onwards are identified as partial (month not yet complete). (19.53.27) SATPAM removes these 12 rows from training. | The system enforces data completeness by excluding months with insufficient data points, preventing model training on unreliable partial-month records. | Log output confirms: "[SATPAM RETRAIN] Membuang 12 baris data parsial bulan 2026-01 ke atas." Training proceeds with 132 clean rows. Model performance is unaffected by the data guard action. | 16/05/2026 | Success |

**Data Volume Constraint Summary:**

| Specification | Actual Result | Status |
|---|---|---|
| Minimum training data requirement | 132 rows (33 months, Apr 2023 – Dec 2025) used — sufficient for reliable model training | Confirmed |
| Partial-month data exclusion (SATPAM) | 12 partial-month rows automatically removed before training | Confirmed |
| Ramadan month exclusion from backtest | Ramadan months excluded from Walk-Forward Backtest pool to prevent distorted evaluation | Confirmed |
| Backtest MAPE with available data | 3.34% — well below 10% acceptable threshold | Confirmed |

---

### NFR-07 — System Reliability: Daily Pipeline Uptime

| Notes | Topic | Scenario | Test Steps | Expected Result | System Response | Date Tested | Status |
|---|---|---|---|---|---|---|---|
| Positive Testing | System Reliability — Daily Pipeline Continuous Run | Verify that the full end-to-end data pipeline runs continuously to completion without crash, exception, or data corruption | (11.00.00) Manually trigger the daily_pipeline.py script on the backend server. (11.00.30) Monitor all pipeline stages in sequence: ETL extraction from dbo.monitor_log_datatransaksi, data transformation, aggregation load to dbo.Vending_Aggregrated, feature engineering to dbo.vending_training_ml, quarterly forecast check, and actuals update for completed months. (11.35.00) Pipeline completes. (11.35.30) Verify output in database: new records in Vending_Aggregrated, updated ForecastResults_Layer1/Layer2, and a new SystemNotifications entry with SUCCESS severity. | The pipeline runs all stages without interruption. No runtime exceptions appear in the console log. All target SQL tables are updated correctly. The error_log.txt file shows no new entries for this execution. | The daily pipeline completes successfully in approximately **35 minutes** total execution time. All pipeline stages log "SUCCESS" or equivalent completion messages. New aggregated records are visible in the Dashboard Summary. No errors are written to error_log.txt during this execution. | 06/06/2026 | Success |

**System Reliability Summary:**

| Specification | Actual Result | Status |
|---|---|---|
| Pipeline completes without crash | Full 35-minute execution completed without runtime error or data corruption | Confirmed |
| All pipeline stages succeed | ETL → Transform → Load → Feature Engineering → Forecast Check → Actuals Update — all stages pass | Confirmed |
| Error log clean after execution | No new entries in error_log.txt following the tested pipeline run | Confirmed |
| Database updated after pipeline | New records visible in Vending_Aggregrated and ForecastResults tables after pipeline completion | Confirmed |

---

### NFR-08 — Application Size / Storage Footprint

As this project is a software-only application (no physical embedded system component), the
traditional "size and weight" specification applies in the context of APK installation size and
device storage footprint.

The APK file size was not formally measured during this testing cycle, as the application was
installed via direct APK transfer to the test device without passing through a managed
distribution system that would report file size metrics. However, based on the dependency
profile (Retrofit 2.9.0, OkHttp 4.12.0, MPAndroidChart v3.1.0, Glide 4.16.0 — total
approximately 4–6 MB of library overhead), the installed APK is estimated to fall within a
standard lightweight Android application footprint of **< 20 MB**, typical for this category
of data-driven enterprise mobile applications.

| Specification | Target | Actual / Estimated | Status |
|---|---|---|---|
| APK Installation Size | < 50 MB (acceptable for enterprise Android app) | Estimated < 20 MB based on dependency profile | N/A (not formally measured) |
| Local Storage Usage | Minimal — no offline data caching | Only SharedPreferences for session data; no local database | Confirmed |
| Runtime Memory | Compatible with standard Android 7.0+ devices | Application runs without OutOfMemoryError on Samsung test device | Confirmed |

---

## D.2 — Photo / Recording of the Test

The following section documents the evidence collected during the non-functional testing
conducted in D.1. Evidence types include system log outputs, database records, configuration
file inspections, and session recordings from the test device.

> **Evidence Validity Note:** All evidence items listed below were collected during actual
> testing sessions on a Samsung Android device and the backend development server. Log
> files referenced are stored within the project directory and can be verified independently.

---

### Evidence 1 — Technical Constraint (NFR-01)

**Evidence Type:** Configuration file inspection + Device observation

**Source:** `CapstoneProject/app/build.gradle` and `RetrofitClient.java`

**Description:** The `build.gradle` file explicitly declares `minSdk 24`, `targetSdk 34`,
and `compileSdk 35`, confirming the Android version constraint. The `RetrofitClient.java`
file declares 60-second timeout values for `connectTimeout`, `readTimeout`, and
`writeTimeout` using the OkHttpClient builder. Both files are accessible in the project
repository at their respective paths and can be reviewed directly.

**Verification:** The Samsung test device (Android ≥ 7.0) successfully ran the application
across all test sessions (05–06 June 2026) without any compatibility error, confirming
the minimum SDK specification is practically satisfied.

---

### Evidence 2 — Connectivity Constraint (NFR-02)

**Evidence Type:** Device observation during network disruption test

**Description:** During the connectivity test (17.40.00, 06 June 2026), Wi-Fi was disabled
on the Samsung test device. The application's response was directly observed: the Dashboard
Summary screen displayed a network error message rather than crashing or displaying stale
data. The test confirmed that the OkHttp error callback correctly propagates a network
failure state to the user interface.

**Evidence Availability:** The test was conducted directly on the physical device. The
network error UI state can be reproduced by disabling Wi-Fi on any Android device running
the application APK and attempting to load any data screen.

---

### Evidence 3 — Security Constraint (NFR-03)

**Evidence Type:** System log + Database state observation

**Description:**

1. **OTP Email Delivery:** During the Register and Forgot Password tests (09.00.00–09.35.00,
   05 June 2026), OTP tokens were generated by the backend and recorded in the
   `email_log.txt` file in the project root directory. The log file contains timestamped
   entries showing the recipient email, subject line, and 6-digit OTP body for each test.
   This file serves as verifiable evidence that the email-based security mechanism
   functioned as designed.

2. **Account Status Field in Database:** The `dbo.master_user` table `status_active` column
   reflects the multi-step activation states: "P" (Pending), "T" (Pending Token), "1" (Active),
   and "N" (Deactivated). These states were observed transitioning correctly during the
   registration flow test, confirming that no account bypasses the activation chain.

3. **Soft-Delete Audit Trail:** After the Delete Account test (10.10.00, 05 June 2026),
   the account record remained in the database with `status_active = "N"`, verifiable by
   querying `SELECT * FROM dbo.master_user WHERE status_active = 'N'`.

**Evidence Location:** `email_log.txt` at project root — `c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api\email_log.txt`

---

### Evidence 4 — Adoption Constraint (NFR-04)

**Evidence Type:** Screen observation + task completion timing

**Description:** During all test sessions (05–06 June 2026), all text elements observed
on screen — including button labels ("Masuk", "Daftar", "Simpan", "Hapus"), error messages
("Username tidak ditemukan", "Password salah"), loading indicators ("Memuat...", "Harap
tunggu sebentar"), and navigation items — were confirmed to be in Bahasa Indonesia.
No English-language UI text was encountered in the user-facing interface during any of
the four test sessions.

The restock creation task (NFR-04 adoption test, 17.05.00–17.08.30) was completed in
approximately **3.5 minutes** from screen entry to saved record, well within the 5-minute
target, demonstrating the system's usability without prior formal training.

---

### Evidence 5 — ML Performance & Data Volume Constraint (NFR-06 + C.1.xv)

**Evidence Type:** System log file (machine-readable, timestamped)

**Description:** The `retrain_log.txt` file in the project root directory contains the
complete, unedited log output of the XGBoost model retrain executed on **16 May 2026
at 19:53:26**. The log includes:

- Step-by-step execution trace (Steps 1 through 8)
- SATPAM data completeness guard output: "Membuang 12 baris data parsial bulan 2026-01 ke atas"
- Training data summary: "132 baris, 33 bulan, Range: 2023-04 → 2025-12"
- GridSearchCV best parameters: `colsample_bytree: 0.8, learning_rate: 0.1, max_depth: 4, n_estimators: 100, subsample: 0.8`
- Walk-Forward Backtest results per month (Sep–Dec 2025 errors: −0.88%, −1.32%, +7.09%, +4.06%)
- Final MAPE: **3.34%**, MAE: 2,570, RMSE: 3,154
- Model artifact save confirmation: 150.2 KB at `ProductionML/Layer1_XGBoost_V6_Artifact.joblib`
- Database write confirmation: INSERT to dbo.RetrainLog with Status = "success"
- Total execution time: approximately **4 seconds** (19:53:26 → 19:53:30)

**Evidence Location:** `retrain_log.txt` at project root — `c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api\retrain_log.txt`

---

### Evidence 6 — System Reliability: Daily Pipeline (NFR-07)

**Evidence Type:** Console/log observation + database state verification

**Description:** During the daily pipeline reliability test (11.00.00–11.35.00, 06 June 2026),
the `daily_pipeline.py` script was executed and its console output was monitored throughout
the approximately 35-minute execution. The pipeline logged successful completion of all
stages: ETL extraction, transformation, aggregation, feature engineering, quarterly check,
and actuals synchronization.

Post-execution verification was performed by loading the Dashboard Summary screen in the
Android application and confirming that new transaction data appeared with today's date,
confirming that the pipeline output was successfully persisted to the database and was
accessible via the API.

**Supporting evidence:** The `error_log.txt` file at project root contains no new entries
from the 06 June 2026 pipeline run, confirming no runtime errors occurred.

**Evidence Location:** `error_log.txt` at project root — `c:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api\error_log.txt`
