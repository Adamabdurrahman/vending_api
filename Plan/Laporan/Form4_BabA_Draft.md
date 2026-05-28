# PART A: DESIGNS IMPLEMENTATION

---

## 1. Functions / Procedure / Class Implementation

This section presents the actual code implementation of the system's core logic,
mapped directly from the hierarchical design (Use Case → Activity → Sequence Diagrams)
described in Form 3, Part B.

The system is implemented in Python using FastAPI as the web framework, with the
Machine Learning engine built on top of XGBoost, scikit-learn, and Pandas. The backend
is structured as a modular service-oriented architecture, where each major function is
isolated into its own service file for maintainability and separation of concerns.

### 1.1. Core Application Entry Point (`main.py`)

The central application module registers all REST API endpoints using FastAPI.
It serves as the single entry point that routes incoming HTTP requests to the
appropriate service functions, directly reflecting the "API Communication Layer"
defined in Form 3's Sequence Diagram (Figure 2.5).

```python
from fastapi import FastAPI, BackgroundTasks, Depends
from sqlalchemy.orm import Session

import forecast_service
import retrain_service
import etl_service
import notif_service

app = FastAPI(
    title="Vending Machine API",
    description="API untuk jembatan aplikasi Android Vending ke SQL Server",
    version="1.0.0",
)
```

The application exposes endpoints grouped into five functional categories:

| Category         | Endpoints                                  | Maps to Form 3           |
|------------------|--------------------------------------------|--------------------------|
| Authentication   | `POST /login`                              | Use Case: Login          |
| Account Management | `GET/PUT/DELETE /account/{id}`           | Use Case: Manage Account |
| Forecasting      | `POST /api/v1/forecast/generate`           | Activity: ML Forecasting |
| ML Operations    | `POST /api/v1/model/retrain`               | Activity: Model Training |
| Notifications    | `GET /api/v1/notifications`                | Sequence: System Events  |

---

### 1.2. Machine Learning Model Class (`ProductionML/Layer1_Core.py`)

The most critical class in the system is `Layer1Model`, a self-contained model wrapper
that encapsulates the entire XGBoost prediction pipeline. This class directly implements
the "Machine Learning Forecasting Layer" described in Form 3, Section D.1.d.

```python
class Layer1Model:
    def __init__(self, model, scaler, imputer, feature_cols, historical_df, metadata):
        self.model = model           # Trained XGBRegressor
        self.scaler = scaler         # StandardScaler for normalization
        self.imputer = imputer       # SimpleImputer for missing values
        self.feature_cols = feature_cols  # 22 feature names
        self.historical_df = historical_df  # Historical data for lag calculation
        self.metadata = metadata     # Version, metrics, configuration
```

**Key Methods:**

| Method             | Purpose                                                      |
|--------------------|--------------------------------------------------------------|
| `build_features()` | Constructs the 22-dimensional feature vector for a given month, including lag values, growth rates, share percentages, and calendar features. Implements the "Lag Skipper" mechanism that bypasses Ramadan months when computing lag references. |
| `predict()`        | Runs the XGBoost model inference. If productive days ≤ 10 (extreme Ramadan), it automatically falls back to a Business Logic formula instead of relying on the ML model. |
| `save_model()`     | Serializes the entire model (including scaler, imputer, and historical data) into a single `.joblib` artifact file. |
| `load_model()`     | Class method that deserializes and validates the artifact file. |

**Feature Engineering — The 22-Feature Vector:**

The model uses 22 engineered features for each prediction, categorized as follows:

| Category              | Features                                           |
|-----------------------|----------------------------------------------------|
| Calendar Features     | `working_days`, `ramadan_pct`, `holiday_pct`       |
| Temporal Encoding     | `month_sin`, `month_cos`, `month_idx`              |
| Variant One-Hot       | `var_Coklat`, `var_Moca`, `var_Original`, `var_Strawberry` |
| Lag Features          | `lag_1m`, `lag_2m`, `lag_12m`, `rolling_avg_3m`    |
| Trend Features        | `growth_rate`, `trend_slope_3m`, `yoy_change`, `demand_acceleration` |
| Share Features        | `share_lag_1m`, `total_demand_lag_1m`, `share_change`, `share_trend_3m` |

**Lag Skipper Implementation:**

A distinctive feature of the system is the Ramadan-aware lag calculation.
Standard time-series models use direct lag references (e.g., lag_1m = previous month).
However, since Ramadan months exhibit extreme demand suppression (up to 90% drop),
using them as lag references would severely distort predictions for subsequent months.

```python
def _get_normal_lag_month(self, yr, mn, lag_n):
    """Skip Ramadan months when computing lag references."""
    curr_yr, curr_mn = yr, mn
    count = 0
    while count < lag_n:
        curr_mn -= 1
        if curr_mn == 0:
            curr_mn = 12
            curr_yr -= 1
        ps = f"{curr_yr}-{curr_mn:02d}"
        if not self._is_ramadan(ps):  # Skip if Ramadan
            count += 1
    return f"{curr_yr}-{curr_mn:02d}"
```

For example, when predicting April 2026 demand, instead of using March 2026
(a Ramadan month with ~5,500 units) as `lag_1m`, the system automatically
skips backward to January 2026 (~52,000 units), providing a more representative
reference point.

---

### 1.3. Forecast Orchestrator (`forecast_service.py`)

This module implements the complete prediction pipeline described in
Form 3's Activity Diagram (Figure 2.3 — ML Forecasting Activity).
It orchestrates the two-layer prediction architecture:

**Layer 1 (Monthly Budget):** Uses the `Layer1Model` XGBoost to predict total
monthly demand per flavor variant.

**Layer 2 (Daily Distribution):** Distributes the monthly budget into daily x shift
x variant granularity using calendar-aware weighting algorithms.

```python
def generate_forecast(start_year, start_month, end_year, end_month,
                      is_data_gap=False, is_retrained=False):
    """
    Chain Prediction: predicts multiple months sequentially,
    where each month's prediction becomes the lag input for the next.
    """
```

**Key Procedures within the Forecast Pipeline:**

| Step | Procedure                     | Description                                   |
|------|-------------------------------|-----------------------------------------------|
| 1    | Data Completeness Check       | Validates that the previous month has >=80% data coverage before allowing prediction |
| 2    | Load Artifact                 | Loads the pre-trained `Layer1Model` from the `.joblib` file |
| 3    | Load Historical Data          | Reads `Vending_Aggregrated` from SQL Server |
| 4    | Time Machine Simulation       | Cuts historical data to exactly before `start_month` to ensure temporal consistency |
| 5    | Build Profiles                | Constructs Shift Profile and Day-of-Week Profile from historical data |
| 6    | Chain Prediction Loop         | For each target month: Layer 1 predict, Layer 2 distribute, Save to SQL |
| 7    | Smart Insight Generation      | Analyzes results and generates contextual notification messages |

**Smart Insight Engine:**

After prediction, the system automatically generates human-readable insights
by detecting patterns such as:

- Business Logic activation (extreme Ramadan months)
- Partial Ramadan impact on demand
- Post-Ramadan demand recovery (>250% increase vs. previous month)
- Significant demand drops (>20% vs. previous month)
- Recurring seasonal patterns across multiple years

---

### 1.4. ETL Pipeline (`etl_service.py`)

This module implements the "Data Preprocessing and Validation Layer" and
"Data Aggregation and Feature Engineering Layer" described in Form 3, Section D.1.b-c.

```python
def run_etl_pipeline():
    """
    5-step pipeline:
    1. EXTRACT  - Pull raw transactions from monitor_log_datatransaksi
    2. TRANSFORM - Map slots to flavors, aggregate daily, add calendar flags
    3. LOAD     - Write clean data to Vending_Aggregrated (preserving manual inserts)
    4. FEATURE ENGINEERING - Build ML-ready features via Databuilder
    5. LOAD ML  - Write features to vending_training_ml
    """
```

**Data Flow Implementation:**

```
[monitor_log_datatransaksi] --Extract--> Raw DataFrame
        |
        v Transform
   Map slot_number -> variant name (via manage_map_new_slot + manage_map_slot_number)
   Aggregate: group by (tanggal, shift, variant) -> count as demand
   Fill gaps: create template for all date x shift x variant combinations
   Add flags: is_holiday (via holidays.Indonesia), is_weekend, is_ramadan
        |
        v Load
   [Vending_Aggregrated] <- DELETE WHERE is_manual_insert = 0, then INSERT
        |
        v Feature Engineering
   build_v3_exact_features() -> lag, rolling avg, share, growth rate, etc.
        |
        v Load ML
   [vending_training_ml] <- TRUNCATE, then INSERT
```

A critical design decision in the ETL process is the **selective deletion strategy**:
rather than truncating the entire `Vending_Aggregrated` table, the pipeline only
deletes rows where `is_manual_insert = 0` (system-generated data), preserving any
manually entered data by administrators. This ensures data integrity while allowing
complete pipeline re-execution.

---

### 1.5. Retrain Service (`retrain_service.py`)

This module implements the model retraining pipeline, which is triggered either
automatically by the quarterly scheduler or manually via the API endpoint.

```python
def run_retrain(exclude_month_and_beyond=None):
    """
    8-step retraining pipeline:
    Step 1: Load training data from SQL
    Step 2: Additional feature engineering (trend_slope_3m, yoy_change, etc.)
    Step 2B: Share Smoother (interpolate distorted Ramadan shares)
    Step 3: GridSearchCV for hyperparameter optimization
    Step 4: Walk-Forward Backtest (4 most recent non-Ramadan months)
    Step 5: Final model training on all data
    Step 6: Backup previous artifact
    Step 7: Export new artifact (.joblib)
    Step 8: Round-trip verification (load -> predict -> validate)
    """
```

**Share Smoother — Data Quality Mechanism:**

During Ramadan months, extremely low demand distorts flavor share percentages
(e.g., Strawberry appearing as 90% market share due to only a handful of transactions).
The Share Smoother detects and corrects these distortions:

```python
# Detection criteria for distorted data:
is_distorted = (
    (total_monthly_demand < 500) or      # Anomalously low total
    (share_pct > 85.0) or                # One variant dominates
    (share_pct < 2.0 and median > 5.0)   # Variant nearly disappears
)
# Correction: interpolate using neighboring months
share_new = (share_previous_month + share_next_month) / 2.0
```

**Hyperparameter Optimization:**

The system uses `GridSearchCV` with 5-fold cross-validation to find the optimal
XGBoost parameters:

```python
param_grid = {
    "n_estimators": [50, 100],
    "learning_rate": [0.05, 0.1],
    "max_depth": [3, 4],
    "subsample": [0.8, 1.0],
    "colsample_bytree": [0.6, 0.8],
}
```

---

### 1.6. Scheduler Service (`scheduler_service.py`)

This module implements the automated quarterly scheduling logic described
in Form 3's Connection and Data Flow section, where a "System Scheduler
automatically triggers the Machine Learning Engine on a predefined schedule."

```python
def check_and_run_quarterly():
    """
    Smart Backfill algorithm:
    1. Scan from Q1 2026 forward to find the oldest unpredicted quarter
    2. Verify data completeness of the previous quarter (>=80% threshold)
    3. Decision matrix:
       - >=80% complete -> NORMAL RUN (retrain + predict)
       - <80% but >=45 days elapsed -> FORCE RUN (predict without retrain)
       - <80% and <45 days -> WAITING (retry tomorrow)
    """
```

---

### 1.7. Daily Pipeline Orchestrator (`daily_pipeline.py`)

This is the top-level automation script designed to be executed once daily
(e.g., via Windows Task Scheduler or cron job):

```python
def job():
    # Step 1: ETL - refresh transaction data
    run_etl_pipeline()

    # Step 2: Update Actuals - sync prediction vs. actual for evaluation
    # Dynamically finds months with predictions but no actuals yet
    for month in pending_months:
        update_actuals(month)

    # Step 3: Quarterly Check - trigger new predictions if needed
    check_and_run_quarterly()
```

---

### 1.8. Notification Service (`notif_service.py`)

A lightweight notification system that logs system events to the database
for consumption by the dashboard interface:

```python
def push(notif_type, severity, title, message=None,
         related_month=None, related_quarter=None):
    """
    Severity levels: SUCCESS, INFO, WARNING, ERROR
    NotifType: ETL, UPDATE_ACTUALS, QUARTERLY, RETRAIN, SYSTEM
    """
```

Shortcut functions (`success()`, `info()`, `warning()`, `error()`,
`error_from_exception()`) provide a clean API for other services to
emit notifications without boilerplate SQL code.

---

## 2. Database Implementation

The database architecture is implemented in Microsoft SQL Server, directly
fulfilling the "Data Storage Tier" described in Form 3's System Architecture
(Section A.1) and the Entity Relationship Diagram (Figure 3.1).

The implementation extends the original ERD design with additional tables
specifically created to support the Machine Learning pipeline and system
monitoring capabilities that were not fully detailed in the design phase.

### 2.1. Database Connection Configuration

```python
# database.py
server = r'ADAM123\SQLEXPRESS'
database = 'db_vending_machine'
engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
```

The system connects via SQLAlchemy ORM with PyODBC driver, enabling both
ORM-based queries (for user management) and raw SQL execution (for ML
pipeline operations that require optimized bulk operations).

### 2.2. Table Implementation

The database consists of 10+ tables organized into three functional groups:

**Group A: Master Data and Transactions (from Form 3 ERD)**

| Table                          | Purpose                                          |
|--------------------------------|--------------------------------------------------|
| `dbo.master_user`              | User accounts with role-based access control     |
| `dbo.master_variant`           | Milk flavor master data (Coklat, Moca, Original, Strawberry) |
| `dbo.master_alat_vm`           | Vending machine registry and sync status         |
| `dbo.monitor_log_datatransaksi`| Raw IoT transaction logs from vending machines   |
| `dbo.manage_map_new_slot`      | Slot number mapping reference                    |
| `dbo.manage_map_slot_number`   | Slot-to-flavor variant mapping                   |

**Group B: Processed Data (ETL Output)**

| Table                        | Purpose                                            |
|------------------------------|----------------------------------------------------|
| `dbo.Vending_Aggregrated`    | Daily aggregated demand per shift x variant. This is the ETL pipeline's primary output and serves as the ground truth for actual demand data. |
| `dbo.vending_training_ml`    | Feature-engineered ML training dataset with 20+ computed columns (lags, rolling averages, growth rates, share percentages). |

**Group C: ML and System Operations (New — beyond Form 3 design)**

| Table                         | Purpose                                           |
|-------------------------------|---------------------------------------------------|
| `dbo.OperationalCalendar`     | Factory calendar: working days, shift schedules, Ramadan flags, shutdown dates. Acts as the single source of truth for all calendar-related computations. |
| `dbo.ForecastResults_Layer1`  | Monthly prediction results (total and per-variant demand, model metrics, actual vs. predicted comparison). |
| `dbo.ForecastResults_Layer2`  | Daily granular predictions per date x shift x variant, with actual comparison columns. |
| `dbo.RetrainLog`              | Model retraining history (timestamp, MAPE, MAE, RMSE, hyperparameters, training data scope). |
| `dbo.SystemNotifications`     | System event log for dashboard notifications (ETL status, forecast completion, retrain results). |

**Key Table: `dbo.ForecastResults_Layer1`**

```sql
CREATE TABLE [dbo].[ForecastResults_Layer1] (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    PredictedMonth      VARCHAR(7) NOT NULL,       -- e.g., "2026-04"
    RunTimestamp        DATETIME NOT NULL,
    ModelVersion        VARCHAR(20),
    TotalDemand         INT NOT NULL,               -- Layer 1 prediction
    DemandCoklat        INT,                        -- Per-variant breakdown
    DemandMoca          INT,
    DemandOriginal      INT,
    DemandStrawberry    INT,
    IsBusinessLogic     BIT DEFAULT 0,              -- 1 = fallback formula used
    ProductiveDays      FLOAT,
    MAPE_Total          FLOAT,                      -- Model accuracy metrics
    MAE_Total           FLOAT,
    RMSE_Total          FLOAT,
    ActualDemand        INT NULL,                   -- Filled by Update Actuals
    ErrorPercent        FLOAT NULL,                 -- Prediction vs. Actual
    ActualUpdatedAt     DATETIME NULL,
    is_data_gap         BIT DEFAULT 0,              -- Forced run due to timeout
    is_retrained        BIT DEFAULT 0               -- Retrained before prediction
);
```

**Key Table: `dbo.ForecastResults_Layer2`**

```sql
CREATE TABLE [dbo].[ForecastResults_Layer2] (
    Id                  INT IDENTITY(1,1) PRIMARY KEY,
    RunTimestamp        DATETIME NOT NULL,
    PredictedMonth      VARCHAR(7) NOT NULL,
    [Date]              DATE NOT NULL,
    DayName             VARCHAR(10),
    Shift               VARCHAR(30) NOT NULL,
    Variant             VARCHAR(30) NOT NULL,
    PredictedDemand     INT NOT NULL,
    IsHoliday           BIT DEFAULT 0,
    IsRamadan           BIT DEFAULT 0,
    IsWeekend           BIT DEFAULT 0,
    ActualDemand        INT NULL,
    ErrorPercent        FLOAT NULL
);
-- Performance index for common query patterns
CREATE NONCLUSTERED INDEX IX_Layer2_DateShiftVariant
    ON [dbo].[ForecastResults_Layer2] ([Date], Shift, Variant);
```

### 2.3. Database Schema Setup Script

All database tables are created and verified through a dedicated setup script
(`setup_forecast_tables.py`) that implements idempotent operations — checking
whether each table already exists before attempting creation, and safely adding
new columns to existing tables using `ALTER TABLE` when schema evolution is needed.

[IMAGE: Screenshot of SQL Server Management Studio showing the table list]

---

## 3. User Interface Implementation

The user interface is implemented as a native Android application developed in Java,
directly fulfilling the "Presentation Layer" described in Form 3, Section D.1.f.
The application communicates exclusively with the Python backend via REST API calls,
consuming JSON responses to render interactive dashboards and forecast visualizations.

### 3.1. Login Screen

The login screen implements the authentication flow defined in Form 3's Testing
Scenario A (Table: Authentication and Access Control). It sends a `POST /login`
request with username and password credentials, receiving a JSON response containing
the user profile and access level.

[IMAGE: Screenshot of Android Login Screen]

### 3.2. Main Dashboard

The dashboard provides real-time visualization of consumption data, implementing
the functionality described in Form 3's Testing Scenario B (Dashboard Monitoring).
Key elements include:

- Daily consumption trend charts (using MPAndroidChart library)
- Shift-based usage breakdown
- Current stock level indicators

[IMAGE: Screenshot of Android Dashboard]

### 3.3. Forecast Module

The forecast module displays the 3-month demand predictions generated by the
Machine Learning engine. This screen directly implements Form 3's Figure 1.4
(Forecast Module mockup) and Testing Scenario D (Forecasting Module).

Features include:
- Total demand prediction with per-flavor breakdown
- Visual chart comparing predicted vs. actual demand
- Model accuracy metrics (MAPE, MAE) displayed prominently
- Warning indicators when prediction confidence is low

The data is retrieved via `GET /api/v1/forecast/history` and rendered using
MPAndroidChart bar/line charts.

[IMAGE: Screenshot of Android Forecast Module]

### 3.4. Notification Center

The notification center displays system events (ETL completion, forecast results,
retrain status) retrieved from `GET /api/v1/notifications`. Users can mark
individual notifications as read or clear all notifications at once.

[IMAGE: Screenshot of Notification Screen]

> **Note:** The Procurement Planning module (Form 3, Figure 1.5) represents
> the decision-support layer where GA Staff can review, modify, and confirm
> procurement plans based on forecast results. [Describe current status:
> implemented / in progress / planned for next phase]

---

## 4. Hardware Implementation

This project is primarily a **software-based system**. No custom hardware was
designed or manufactured as part of this capstone. However, the system operates
on top of existing physical infrastructure that serves as its data source.
This section documents that infrastructure and the deployment environment.

### 4.1. Existing Infrastructure: Milk Vending Machines (IoT Data Source)

The facility has pre-existing milk vending machines that were already deployed
and operational before this project began. These machines function as IoT data
generators — every dispensing event is automatically recorded as a raw transaction
log and stored in the SQL Server database.

The data points captured by the existing vending machines include:

| Data Point          | Description                                      |
|---------------------|--------------------------------------------------|
| `update_time`       | Timestamp of the transaction                     |
| `id_recnum_mav`     | Unique identifier of the vending machine         |
| `slot_number`       | Physical slot from which the product was dispensed|
| `keterangan`        | Shift designation (SHIFT1, SHIFT2, SHIFT3)       |
| `qty`               | Quantity dispensed                                |
| `status_transaksi`  | Transaction validity flag ('1' = successful)     |

This project **does not modify the vending machine hardware or firmware** in any way.
Instead, it leverages the transaction data already being collected by these machines
as the foundational input for the ETL pipeline and Machine Learning engine.
The `dbo.monitor_log_datatransaksi` table serves as the bridge between the
physical hardware layer and the software system developed in this project.

### 4.2. Deployment Environment

The software system is deployed on the following infrastructure:

| Component          | Specification                                |
|--------------------|----------------------------------------------|
| Operating System   | Windows (local server)                       |
| Database Server    | Microsoft SQL Server (ADAM123\SQLEXPRESS)     |
| Backend Runtime    | Python 3.12 with FastAPI + Uvicorn           |
| ML Libraries       | XGBoost, scikit-learn, Pandas, NumPy         |
| Network Access     | Local network (HTTP, accessible via IP)      |
| Scheduling         | Windows Task Scheduler (daily pipeline)      |

---

## 5. Integration Among Every Module

This section describes how all modules (Code, Database, UI, and Hardware) are
integrated into a cohesive end-to-end system, directly validating the system
architecture and data flow described in Form 3, Section A.

### 5.1. End-to-End Integration Architecture

```
+--------------+     Raw Logs      +------------------------------+
| Vending      | ----------------> | SQL Server                   |
| Machines     |                   | (monitor_log_datatransaksi)  |
| (Hardware)   |                   +--------------+---------------+
+--------------+                                  |
                                                  | ETL Pipeline
                                                  | (daily_pipeline.py)
                                                  v
                                   +------------------------------+
                                   | Vending_Aggregrated          |
                                   | (clean daily data)           |
                                   +--------------+---------------+
                                                  |
                              +-------------------+-------------------+
                              |                   |                   |
                              v                   v                   v
                    +-------------+    +--------------+    +--------------+
                    | Feature Eng.|    | Update       |    | Quarterly    |
                    | -> training |    | Actuals      |    | Check        |
                    |   _ml table |    | (evaluate)   |    | (predict)    |
                    +------+------+    +--------------+    +------+-------+
                           |                                      |
                           |          +---------------+           |
                           +--------->| Retrain Model |<----------+
                                      | (if needed)   |
                                      +-------+-------+
                                              |
                                              v
                                   +------------------------------+
                                   | ForecastResults (Layer1 + 2) |
                                   | + RetrainLog                 |
                                   | + SystemNotifications        |
                                   +--------------+---------------+
                                                  |
                                    +-------------+-------------+
                                    |             |             |
                                    v             v             v
                            +------------+ +----------+ +------------+
                            | Android    | | Website  | | Dashboard  |
                            | App (Java) | | (.NET)   | | (Direct    |
                            | via REST   | | via SQL  | |  SQL Query)|
                            | API (JSON) | | Server   | |            |
                            +------------+ +----------+ +------------+
```

### 5.2. Integration Flow: Daily Automated Pipeline

The daily pipeline (`daily_pipeline.py`) serves as the primary integration point,
orchestrating the interaction between all system modules in a single automated run:

| Step | Module                  | Input                          | Output                        | Integration Point        |
|------|-------------------------|--------------------------------|-------------------------------|--------------------------|
| 1    | ETL Service             | Raw IoT logs from SQL          | Clean daily data + ML features| Hardware to Database     |
| 2    | Update Actuals          | Vending_Aggregrated + ForecastResults | Updated error metrics   | Database to Database     |
| 3    | Quarterly Check         | Calendar + ForecastResults     | Decision: wait / retrain+predict | Database to ML Engine |
| 3a   | Retrain Service         | vending_training_ml            | New model artifact (.joblib)  | Database to ML to File   |
| 3b   | Forecast Service        | Model artifact + Calendar      | ForecastResults_Layer1 and Layer2 | ML to Database        |
| 3c   | Notification Service    | Pipeline results               | SystemNotifications           | All to Database to UI    |

### 5.3. Integration Flow: User Request (Android to API to Database)

A key architectural principle of this system is the **separation between data
production and data consumption**. All heavy computation (ETL, retrain, prediction)
is performed automatically by the daily pipeline (Section 5.2) and stored in
SQL Server tables. The Android application **never triggers ML computation directly**
— it only reads the pre-computed results through lightweight GET endpoints.

When a user accesses the forecast module on the Android application, the following
integration sequence occurs:

```
1. [Background — already completed by daily_pipeline.py]
   ETL -> Retrain -> Forecast -> Results stored in SQL Server tables

2. [User opens Android App]
   Android App sends HTTP GET to /api/v1/forecast/history

3. FastAPI endpoint receives the request

4. Python backend executes a simple SELECT query on ForecastResults_Layer1
   (no ML computation — data is already pre-computed)

5. Results are serialized to JSON format

6. JSON response is transmitted back to the Android App

7. MPAndroidChart library renders the data as interactive charts
```

This design ensures that the mobile application remains fast and responsive,
as it never waits for ML model execution. The API layer acts purely as a
**data-serving bridge** between the SQL Server database and the Android client,
following the same principle used by the website (.NET) which reads directly
from SQL Server.

This flow implements the Sequence Diagram interaction described in Form 3,
Figure 2.5, validating the "separation of heavy computational load from
application response time" principle.

### 5.4. Integration Flow: Manual Forecast Trigger (API to ML to Database)

When an authorized user triggers a new forecast via `POST /api/v1/forecast/generate`:

```
1. FastAPI receives the request with parameters (start/end month)
2. forecast_service.py validates data completeness ("SATPAM" guard)
3. Layer1Model artifact is loaded from disk
4. Historical data is loaded from SQL Server
5. Chain Prediction executes: Layer 1 then Layer 2 for each month
6. Results are written to ForecastResults_Layer1 and Layer2 tables
7. Smart Insight is generated and returned in the API response
8. SystemNotifications table is updated for dashboard visibility
```

### 5.5. Safety Net Integration

A critical aspect of the system integration is the layered safety net that
prevents cascading errors across modules:

| Safety Mechanism        | Protects Integration Between             |
|-------------------------|------------------------------------------|
| SATPAM Data Check       | ETL to Forecast (prevents prediction with incomplete data) |
| SATPAM VM Status        | Hardware to Update Actuals (warns about offline machines) |
| Target Leakage Guard    | Database to Retrain (prevents future data from leaking into training) |
| Time Machine Simulation | Database to Forecast (ensures temporal consistency regardless of execution date) |
| Smart Backfill          | Scheduler to Forecast (automatically recovers from missed quarters) |

These mechanisms ensure that even if individual components experience delays or
partial failures, the overall system remains consistent and produces reliable outputs.

---

> **[NOTES FOR AUTHOR — REMOVE BEFORE SUBMISSION]**
>
> Items to add before finalizing:
> - [ ] Screenshot Android App (Login, Dashboard, Forecast, Notification)
> - [ ] Screenshot SQL Server Management Studio (showing table list)
> - [ ] Screenshot Swagger UI (/docs) showing API endpoints
> - [ ] More formal architecture diagram (draw.io / Visio)
> - [ ] Clarify status of Procurement Planning module
> - [ ] Photo/specifications of vending machine hardware if required
> - [ ] Screenshot of .NET website if being included
> - [ ] Add figure numbers consistent with Form 3 numbering
