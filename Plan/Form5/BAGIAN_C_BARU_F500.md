# C. VIDEO DEMONSTRATION

---

## Overview

This section provides the video demonstration of the **Smart Vending Machine Management
System** — an ML-based employee milk benefit monitoring and management system developed
for PT GS Battery. The video covers three required components: how to build the system
(backend setup), how to install the system (Android APK installation), and how to use
the system (end-to-end feature walkthrough).

---

## Video URL

> **Google Drive Link:**
>
> `[PASTE GOOGLE DRIVE VIDEO LINK HERE]`
>
> *(Ensure the link sharing is set to "Anyone with the link can view" before submission.)*

---

## Video Content Outline

The demonstration video is structured into three main parts as required:

---

### Part 1 — How to Build the System

**Estimated Duration:** ~10–15 minutes

This part demonstrates the complete setup process for the backend (`vending_api`) from
a fresh environment.

**Content covered:**

1. **System Requirements**
   - Python 3.x installed
   - Microsoft SQL Server (Express or full) available
   - Required ODBC Driver (17 or 18) for SQL Server installed
   - Git or direct download of the project folder

2. **Backend Setup (`vending_api`)**
   - Navigate to the project root directory
   - Create and activate a Python virtual environment:
     ```
     python -m venv venv
     venv\Scripts\activate
     ```
   - Install all Python dependencies:
     ```
     pip install -r requirements.txt
     ```
   - Configure the database connection string in the `.env` file:
     - `DB_SERVER` — SQL Server instance name (e.g., `YOURPC\SQLEXPRESS`)
     - `DB_NAME` — target database name
     - `EMAIL_SENDER` — Gmail address for OTP email sending
     - `EMAIL_PASSWORD` — Gmail App Password

3. **Database Initialization**
   - Confirm that the required SQL Server tables exist:
     `dbo.master_user`, `dbo.master_variant`, `dbo.master_alat_vm`, `dbo.master_settime`,
     `dbo.manage_map_slot_number`, `dbo.manage_restok`, `dbo.OperationalCalendar`,
     `dbo.ForecastResults_Layer1`, `dbo.ForecastResults_Layer2`, `dbo.RetrainLog`,
     `dbo.SystemNotifications`, `dbo.Vending_Aggregrated`, `dbo.vending_training_ml`
   - Verify that the ML model artifact exists at:
     `ProductionML/Layer1_XGBoost_V6_Artifact.joblib`

4. **Running the Backend Server**
   - Start the FastAPI backend with Uvicorn:
     ```
     uvicorn main:app --host 0.0.0.0 --port 8000
     ```
   - Verify the API is running by opening the Swagger documentation in a browser:
     `http://localhost:8000/docs`
   - Confirm all 18 API tag groups are visible and accessible in the Swagger UI

---

### Part 2 — How to Install the System

**Estimated Duration:** ~3–5 minutes

This part demonstrates how to install the Android client application on a Samsung device.

**Content covered:**

1. **APK Transfer**
   - Transfer the `CapstoneProject.apk` file to the target Android device
     (via USB file transfer, Google Drive, or any file sharing method)

2. **Enable Installation from Unknown Sources**
   - On the Android device, go to **Settings → Security (or Apps)** and enable
     **"Install Unknown Apps"** or **"Allow from this source"** for the file manager
     or browser being used to open the APK

3. **APK Installation**
   - Open the `.apk` file on the Android device
   - Tap **Install** when prompted
   - Wait for the installation to complete (typically under 30 seconds)
   - Tap **Open** to launch the application

4. **First-Time Configuration**
   - The app will open on the Login screen
   - The backend server URL is preconfigured in the app
     (`RetrofitClient.java` — base URL points to the cloud-hosted API)
   - Ensure the Android device has an active internet connection before use

---

### Part 3 — How to Use the System

**Estimated Duration:** ~20–30 minutes

This part provides a complete end-to-end feature demonstration of the system,
performed on a Samsung Android device connected to the live backend.

**Content covered (in order):**

| Sequence | Feature Demonstrated | Key Actions Shown |
|---|---|---|
| 1 | **User Registration** | Fill registration form, submit, observe Pending status |
| 2 | **Superadmin Approval** | Superadmin approves new user from the User Management screen |
| 3 | **OTP Email Verification** | Retrieve OTP from email, enter in app, account activated |
| 4 | **Login** | Enter credentials, navigate to Sidebar Menu |
| 5 | **Account Settings** | View profile, edit username, upload profile photo |
| 6 | **Operational Calendar** | View 2026 calendar, edit a day, generate 2027 calendar |
| 7 | **Manual Insert** | Download Excel template, upload valid file, confirm insertion |
| 8 | **Dashboard Summary** | View metric cards, apply date filter, apply shift filter |
| 9 | **Prediction Dashboard** | View Q1 2026 forecast, per-variant breakdown, predicted vs. actual chart |
| 10 | **Inventory Dashboard** | View stock levels, browse movement history, input stock-in |
| 11 | **Master Variant Management** | View list, create new variant, edit, delete |
| 12 | **Machine Management** | View list, register new machine, edit, delete |
| 13 | **Shift Management** | View list, create new shift with schedule, edit, delete |
| 14 | **Slot Management** | Select machine, view slots, configure new slot, edit |
| 15 | **Restock Management** | View by machine, filter low-stock, create restock entry, edit |
| 16 | **ML Retrain Logs** | View retrain history, inspect MAPE and hyperparameters of latest run |
| 17 | **Logout** | Tap logout, confirm session is cleared, return to Login screen |

---

## Video Quality Checklist

The following requirements must be met before submitting the video:

| Requirement | Description | Status |
|---|---|---|
| **Video Clarity** | Screen recording is clear, not blurred, not dark, and not pixelated. All text on screen is legible. | ☐ Verified |
| **Audio Clarity** | Voice narration is clear and close to the microphone. Minimum background noise. No echo or distortion. | ☐ Verified |
| **Screen Resolution** | Minimum 720p (1280×720) recording; 1080p preferred | ☐ Verified |
| **Language** | Narration and/or on-screen labels are consistent (Bahasa Indonesia or English throughout) | ☐ Verified |
| **Google Drive Access** | Video link is set to "Anyone with the link can view" — not restricted to specific accounts | ☐ Verified |
| **Complete Coverage** | All three parts (Build, Install, Use) are present and clearly segmented | ☐ Verified |
| **Duration** | Total video length is sufficient to demonstrate all features clearly (estimated 35–50 minutes) | ☐ Verified |

---

## Recording Tools (Recommended)

| Tool | Purpose |
|---|---|
| **Android screen recorder** (built-in or AZ Screen Recorder) | Record the Android app feature demonstration for Part 3 |
| **Windows screen recorder** (Xbox Game Bar `Win+G` or OBS Studio) | Record the backend setup and API documentation for Part 1 |
| **Any screen recording tool with audio** | For narration during Part 2 (APK installation) |

---

> **Note for submission:** After recording and uploading the video to Google Drive,
> replace the placeholder text `[PASTE GOOGLE DRIVE VIDEO LINK HERE]` in the
> **Video URL** section above with the actual shareable link.
