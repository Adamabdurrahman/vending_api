# B. RESTATE THE SPECIFICATIONS STATED IN THE F-200 DOCUMENT

---

## 1. Main Functionality

This system is a **Machine Learning-Based Smart Vending Machine Management System** designed to monitor
and manage employee milk benefit distribution in a manufacturing company environment.
Under the company's welfare policy, every employee is entitled to receive **2 bottles of
milk per working shift** — one upon entering and one upon leaving the production floor.
The vending machines serve as the physical medium for this benefit distribution, and
this system is built to ensure the process is measurable, monitored, and data-driven.

The main functionalities of the system are:

- **User Authentication & Account Management**: Provides a secure multi-step user
  onboarding flow including self-registration, Superadmin approval, OTP-based email
  verification, and token-based password reset. Authenticated users can update their
  profile information, change passwords, and upload a profile photo.

- **Operational Calendar Management**: Enables administrators to configure the factory's
  operational schedule on a per-day basis, including working days, shift activation
  (Shift 1 / Shift 2 / Shift 3), national holidays, Ramadan periods, and total shutdown
  days. The calendar serves as the authoritative source of truth for the XGBoost prediction
  engine and daily distribution planning.

- **Master Data Management**: Provides full CRUD (Create, Read, Update, Delete)
  management for four core reference entities:
  - **Product Variants** — milk flavors available in the vending machines (e.g., Coklat,
    Moca, Original/Putih, Strawberry)
  - **Vending Machine Units** — registration and configuration of each physical vending
    machine deployed on the production floor
  - **Shift Schedules** — definition of shift names, department assignments, start and
    end times
  - **Slot Configurations** — mapping of physical slots in each machine to a product
    variant, including maximum slot capacity

- **Restock Management**: Allows operators to monitor current milk stock levels per slot
  per machine, receive low-stock alerts (threshold-based), create and update restocking
  records, and track who performed each restock operation and when.

- **Manual Transaction Data Input**: Provides a mechanism for administrators to upload
  historical or corrective transaction data via a standardized Excel template. The system
  validates the uploaded file, checks for duplicate records, and inserts the data into the
  main transaction table with a manual-insert flag for traceability.

- **Transaction Monitoring Dashboard**: Displays a real-time operational overview of
  daily benefit distribution, including key metrics (total transactions taken, failed
  dispensations, restock count, and today's transactions), a daily consumption trend
  chart, variant distribution analytics, and the latest transaction log — all filterable
  by date range and shift.

- **Machine Learning-Based Demand Prediction (Forecasting)**: The core forecasting feature of the
  system. Uses a two-layer XGBoost machine learning pipeline to forecast milk demand:
  - **Layer 1** predicts total monthly demand per variant using 22 engineered features
    (lag values, seasonality encoding, Ramadan flags, trend slopes, etc.)
  - **Layer 2** distributes the monthly budget to a granular daily x shift x variant level
    using the operational calendar and historical shift profiles.
  The model is automatically retrained on a quarterly schedule using a Walk-Forward
  Backtest evaluation and GridSearchCV hyperparameter optimization.

- **Inventory Dashboard & Decision Support System (DSS)**: Provides a higher-level
  view of inventory health across the entire operation, including stock movement history
  (paginated, filterable by variant and movement type), per-variant stock levels, and
  a structured stock-in input form for recording incoming milk deliveries from the supplier.

- **ML Retrain Logs Monitoring**: Displays a historical log of all model retraining events,
  including performance metrics (MAPE, MAE, RMSE), the best hyperparameters found, number
  of training rows used, and the final retraining status (success or error).

---

## 2. User Characteristics

The system serves **2 types of users**, differentiated by the `level_user` field in the
user database:

| Users | Responsibility | Access Rights | Education Level | Skill Level | Experience | Type of Training |
|---|---|---|---|---|---|---|
| **Superadmin** (level_user = 9) | Full system oversight: approves new user registrations, manages all master data, triggers forecasting and retraining, monitors all dashboards and logs | Full access to all features and administrative endpoints | Minimum S1 (Bachelor's Degree) in a relevant field (IT, Industrial Engineering, or Management) | Advanced — comfortable using web-based management tools and interpreting data charts | Experienced with internal factory data systems | On-the-job training provided during system handover |
| **Operator** (level_user = 1) | Daily operational monitoring: manages restock activities, monitors transaction dashboards, configures operational calendar, uploads manual transaction data | Access to operational features (dashboard, restock, calendar, manual insert, inventory); no access to user approval or system administration | Minimum SMA/SMK or Diploma, particularly administrative or production staff | Basic to moderate digital literacy — familiar with Android-based applications | No prior experience required; system designed for ease of use | Brief in-app walkthrough; no extensive formal training needed |

**Note on Account Activation Flow:**
A new user registers via the Android application. The account is placed in **Pending**
status until a Superadmin reviews and approves it. Upon approval, the user receives a
**6-digit OTP token** via their registered email (valid for 15 minutes). The account is
fully activated only after successful OTP verification.

---

## 3. Constraints

The following constraints apply to the system based on its design decisions and
implementation context:

- **Technical Constraints**: The Android client application requires a minimum of
  Android 7.0 (API Level 24) to run. The application uses ViewBinding and Material
  Design components, which require modern Android runtime support. The backend API
  connection timeout is configured at 60 seconds to accommodate ML inference operations
  (forecasting and retraining) that may take extended processing time.

- **Connectivity Constraints**: All features of the Android application require an active
  internet connection to communicate with the cloud-hosted backend API. There is no
  offline mode; all data retrieval, dashboard rendering, and data submission depend on
  a live connection to the server. The system is intended to be used within the company's
  operational environment where network access is consistently available.

- **Security Constraints**: User accounts require a two-step activation process
  (Superadmin approval followed by OTP email verification) before they can be used.
  Password reset also requires OTP verification via registered email. Account deactivation
  is handled as a soft delete (status flag change) to preserve audit trails.

- **Adoption Constraints**: The system's user interface is developed entirely in
  Bahasa Indonesia to ensure accessibility for factory floor operators who may not
  be proficient in English. The UI design follows Material Design principles with clear
  visual hierarchy, color-coded status badges, and minimal user input steps to reduce
  the learning curve for non-technical users.

- **Privacy Constraints**: The system processes and stores employee-related operational
  data including transaction logs (which can be correlated to shift and machine records),
  user account information, and stocking records. All data is maintained within a
  centralized SQL Server database hosted on the company's cloud infrastructure. Access
  to data is role-restricted — Operators can view dashboards and perform operational
  inputs, while only Superadmins can manage user accounts and system-level configurations.

- **Data Volume Constraints**: The XGBoost model's forecasting accuracy relies on a sufficient
  volume of historical transaction data. The retrain service enforces a minimum training
  data requirement and excludes anomalous months (e.g., months with 10 or fewer
  productive days, such as full-Ramadan periods) from the training set to preserve
  model integrity.

---

## 4. Product Development Environment

### a. Hardware

- **Developer Workstation**: Lenovo ThinkPad laptop (company-issued device) used for
  both backend Python development and Android Studio development.
- **Android Testing Device**: Samsung Android smartphone (company-owned device) used
  for physical device testing of the APK during development and debugging cycles.
- **Local Database Server**: Microsoft SQL Server Express instance installed on the
  developer workstation, used during local development and testing of backend API
  endpoints.

### b. Software

**Backend (vending_api — Python):**

| Component | Technology | Version |
|---|---|---|
| API Framework | FastAPI | Latest stable |
| ASGI Server | Uvicorn | Latest stable |
| ORM | SQLAlchemy | Latest stable |
| DB Driver | PyODBC | Latest stable |
| Schema Validation | Pydantic + pydantic-settings | Latest stable |
| Database (Dev) | Microsoft SQL Server Express | 2019 / 2022 |
| ML Model | XGBoost (via scikit-learn wrapper) | Latest stable |
| Data Processing | Pandas + NumPy | Latest stable |
| Model Serialization | Joblib | Latest stable |
| Calendar / Holiday | holidays (Python library, Indonesia locale) | Latest stable |
| Email Notification | Python smtplib via Gmail SMTP | Standard library |

**Android Client (CapstoneProject — Java):**

| Component | Technology | Version |
|---|---|---|
| IDE | Android Studio | Latest stable |
| Language | Java | 17 |
| Min SDK | Android 7.0 (API Level 24) | — |
| Target SDK | Android 14 (API Level 34) | — |
| Compile SDK | API Level 35 | — |
| Networking | Retrofit | 2.9.0 |
| HTTP Client | OkHttp + Logging Interceptor | 4.12.0 |
| JSON Parser | Gson | 2.10.1 |
| Image Loading | Glide | 4.16.0 |
| Charting Library | MPAndroidChart | 3.1.0 |
| UI Components | Material Design (AppCompat) | Latest stable |
| Layout | ViewPager2, SwipeRefreshLayout, ConstraintLayout | Latest stable |
| Data Binding | ViewBinding | Built-in |

### c. Connection

- The backend API was tested locally during development using FastAPI's built-in Swagger
  UI (http://localhost:8000/docs) and via Python-based automated test scripts.
- The Android client during development used the Android Emulator loopback address
  (10.0.2.2:8000) to connect to the locally running FastAPI server.
- Physical device testing used the developer workstation's local IP address over a shared
  Wi-Fi network.

---

## 5. Product Operational Environment

### a. Hardware

- **Cloud Server**: The vending_api FastAPI backend is deployed to a cloud hosting
  platform, making the API accessible over the internet. The SQL Server database is
  hosted on the same or a linked cloud environment.
- **Android Devices (Client)**: Samsung Android smartphones (minimum Android 7.0 /
  API Level 24) used by Superadmin and Operator personnel within the company facility.
  Devices must have internet or intranet access to communicate with the cloud-hosted API.

### b. Software

- **Backend Deployment**: The FastAPI application is run via Uvicorn on the cloud server.
  The SQL Server database stores all operational data including user accounts, transaction
  logs, forecast results, operational calendar, restock records, and ML model retrain logs.
- **Android Distribution**: The application is packaged as an APK file and distributed
  directly to authorized devices via manual installation (sideloading). There is no
  Play Store distribution; installation is managed internally by the system administrator.
- **ML Artifacts**: Trained XGBoost model artifacts (.joblib files) are stored on the
  server within the ProductionML/ directory and loaded by the backend at inference time.
  Artifact versioning and backup are handled automatically by the retrain service.

### c. Connection

- Android devices connect to the cloud-hosted backend via the internet or the company's
  internal network, depending on deployment configuration.
- All API calls use Retrofit with a 60-second timeout for both connection and read
  operations, accommodating ML inference response times.
- The system requires a stable internet or intranet connection at all times during
  operation, as there is no local caching or offline fallback mechanism implemented.
- The operational calendar and shift configuration stored in the cloud database serve
  as the shared source of truth for both the Android client (display) and the backend
  ML pipeline (computation).
