# EcoLifyBuddy

> **An AI-Based CCTV Intelligence System for Visitor Identification, Activity Tracking, and Safer, Cleaner Communities**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/database-Neon%20Postgres%20%2B%20pgvector-00e699.svg)](https://neon.tech/)
[![Computer Vision](https://img.shields.io/badge/CV-YOLO%20%2B%20ByteTrack-orange.svg)](https://github.com/ultralytics/ultralytics)
[![Re-ID](https://img.shields.io/badge/Re--ID-OSNet%20%2B%20pgvector-purple.svg)](https://github.com/KaiyangZhou/deep-person-reid)
[![Compliance](https://img.shields.io/badge/compliance-India%20DPDP%20Act%202023-brightgreen.svg)](PRIVACY.md)

---

## 1. Problem Statement

Delivery executives, technicians, vendors, domestic workers, and visitors repeatedly visit residential communities, commercial parks, and public facilities. Despite extensive CCTV infrastructure, there is no intelligent system to recognise recurring visitors and maintain a real-time, privacy-conscious history of their presence. 

During security incidents or audits, manually reviewing hours of footage across multiple disconnected cameras is slow, labour-intensive, and error-prone. **EcoLifyBuddy** solves this by detecting and tracking people in real time, recognising recurring individuals across cameras via appearance-based person re-identification (Re-ID), recording time-stamped entry/exit and zone dwell-time logs, flagging behavioral anomalies, and empowering authorised security officers to search visitor histories and auto-generate forensic incident timelines in seconds.

---

## 2. Key Capabilities

### Primary Module: Intelligent Visitor Identification & Activity Tracking

* **Multi-Camera Video Ingestion:** Simultaneous ingestion from RTSP/IP cameras, USB webcams, and local video demo files with virtual entry/exit tripwires and polygon zones.
* **Person & Object Detection (YOLO + ByteTrack):** High-throughput detection of persons alongside carried objects (backpack, handbag, suitcase, box/package, helmet, umbrella, bottle) mapped to COCO classes. Per-camera continuous tracking using Ultralytics ByteTrack.
* **Person Re-Identification (Cross-Camera & Cross-Day):** 512-dimensional appearance Re-ID feature embeddings generated via OSNet (ONNX / Torch) with a fallback to HSV colour-histogram matching. Embeddings are indexed using **pgvector** (HNSW index) on Neon Postgres.
* **Visitor Profiles & Categorisation:** Automatic visitor clustering into categories (*Delivery, Technician, Vendor, Domestic Worker, Guest, Unknown*) with human-in-the-loop manual merging, splitting, and labeling.
* **Time-Stamped Event Engine:** Continuous logging of events: `ENTRY`, `EXIT`, `ZONE_ENTER`, `ZONE_EXIT`, `OBJECT_CARRIED`, `OBJECT_LEFT_BEHIND`, `LOITERING`, `RESTRICTED_ZONE`, and `ODD_HOUR_VISIT`.
* **Anomaly Detection:** Rule-based heuristics combined with Isolation Forest machine learning on dwell time, zone permissions, unattended object duration, and visit frequency.
* **IoT & Sensor Fusion:** Ingestion of PIR motion triggers, RFID gate badges, and magnetic door sensors via HTTP webhooks / MQTT, correlated directly with camera timelines.
* **Search & Forensic Incident Timelines:** Filter by date, camera, visitor category, object, and natural language query (*"delivery person with a box near Gate 2 yesterday evening"*). One-click timeline reconstruction exported as PDF or JSON.
* **Privacy by Design:** Default face/body blurring for standard Viewer roles, optional consented face recognition (disabled by default), configurable retention auto-purge, and immutable audit logs compliant with India's **Digital Personal Data Protection (DPDP) Act 2023**.

### Legacy Module: Cleanliness & Waste Disposal Monitoring

The original public cleanliness and littering violation detection engine (`detector.py`, `rule_engine.py`, `tracker.py`, and `/api/violations`) is preserved in its entirety and accessible under the **"Legacy / Cleanliness Monitoring"** navigation tab.

---

## 3. System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Video & Sensor Ingestion"]
        RTSP["RTSP / IP Cameras"]
        Webcam["USB Webcams"]
        VideoFile["Recorded Video Files"]
        Sensors["IoT Sensors (RFID / PIR / Door)"]
    end

    subgraph CV["2. Computer Vision Pipeline (Python 3.12)"]
        YOLO["YOLOv8 / YOLO11 Detection\n(Person + Objects of Interest)"]
        Tracker["ByteTrack Tracker\n(Camera Track IDs & Tripwires)"]
        ReID["OSNet Feature Extractor\n(Appearance Re-ID 512-d)"]
        Fallback["Colour-Histogram Fallback"]
        ReID -.->|if model unavailable| Fallback
    end

    subgraph Storage["3. Persistence & Vector Indexing"]
        NeonDB[("Neon Postgres\n(Users, Roles, Cameras, Events)")]
        PgVector[("pgvector Extension\n(HNSW Cosine Vector Index)")]
        AuditStore[("Immutable Audit Log\n(Access, Exports, Un-blurs)")]
        ClipBuffer[("Ring Buffer\n(Event Clips & Thumbnails)")]
    end

    subgraph Backend["4. Application Services (Flask + SQLAlchemy)"]
        AuthService["JWT Auth & RBAC\n(Admin, Security Officer, Viewer, Auditor)"]
        EventEngine["Event & Anomaly Engine\n(Loitering, Restricted, Unattended)"]
        SearchEngine["Forensic Search & Timeline Generator\n(Filter / NL Parser -> PDF / JSON)"]
        LegacyRoutes["Legacy Cleanliness Engine\n(/api/violations, AlertSystem)"]
    end

    subgraph Frontend["5. Executive Web Dashboard (Tailwind Dark-Mode)"]
        Shell["index.html (Navigation Shell)"]
        VOverview["Overview & KPI Dashboard"]
        VLive["Live Multi-Camera Grid"]
        VVisitors["Visitor Directory & Profile"]
        VEvents["Time-Stamped Events Log"]
        VAlerts["Real-Time Alerts & Acknowledgment"]
        VTimeline["Search & Forensic Incident Timelines"]
        VCameras["Camera & Zone Tripwire Config"]
        VAnalytics["Analytics & Heatmaps"]
        VAudit["Compliance & Audit Log"]
        VLegacy["Legacy Cleanliness Monitoring Tab"]
    end

    Ingestion --> CV
    CV --> Backend
    Backend <--> Storage
    Backend <--> Frontend
```

---

## 4. Repository Structure

```text
c:\LIL\
├── api/                       # Modular Flask blueprints for new capabilities
│   ├── __init__.py           # Blueprint registry
│   └── ui.py                 # Shell routes: /login, /about, /partials/<name>, /api/v2/meta
├── services/                  # Business logic (ingestion, Re-ID, events, timeline, anomaly)
├── static/
│   └── js/
│       └── nav.js            # Dynamic partial view router (zero-build Tailwind client)
├── templates/
│   ├── index.html            # Unified executive shell with navigation
│   ├── login.html            # Dedicated branded login view
│   ├── about.html            # System overview, problem statement & compliance
│   └── partials/             # Component views loaded on-demand
│       ├── visitor_overview.html
│       ├── live_monitoring.html
│       ├── visitors.html
│       ├── events.html
│       ├── alerts.html
│       ├── search_timeline.html
│       ├── cameras_zones.html
│       ├── analytics.html
│       ├── settings.html
│       └── audit.html
├── .env.example              # Environment template with Neon & secret placeholders
├── .gitignore                # Excludes .env, model weights (*.pt, *.onnx), evidence clips
├── branding.py               # Single source of truth for product name, slogan & version
├── config.py                 # Configuration loader
├── pyproject.toml            # Project metadata (Python 3.12 pinned)
├── requirements.txt          # Python dependencies
├── PRIVACY.md                # Data protection & DPDP Act 2023 compliance specification
├── Start_ECOLIFEBUDDY.bat    # Windows launcher (runs in .venv312)
├── Stop_ECOLIFEBUDDY.bat     # Windows service stop script
└── web_server.py             # Main Flask server hosting API and legacy routes
```

---

## 5. Quickstart & Installation

### Prerequisites
* Windows 10/11 or Linux
* Python 3.12 (`py -3.12`)
* Neon Postgres account (with `pgvector` extension enabled)

### Step 1: Clone & Configure Environment
```powershell
# Clone the repository
git clone <repo-url> c:\LIL
cd c:\LIL

# Copy example environment configuration
copy .env.example .env
```

Configure `.env` with your Neon credentials and secrets:
```ini
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@ep-xxxx-pooler.REGION.aws.neon.tech/DBNAME?sslmode=require
DATABASE_URL_DIRECT=postgresql+psycopg://USER:PASSWORD@ep-xxxx.REGION.aws.neon.tech/DBNAME?sslmode=require
JWT_SECRET=generate-a-secure-random-secret
ADMIN_EMAIL=admin@organisation.org
ADMIN_PASSWORD=secure-admin-password
FACE_RECOGNITION_ENABLED=false
DETECTION_MODEL=yolo26n.pt
RETENTION_DAYS=30
```

### Step 2: Set Up Python 3.12 Virtual Environment
```powershell
# Create Python 3.12 virtualenv
py -3.12 -m venv .venv312

# Activate virtualenv
.venv312\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

### Step 3: Run the Application
You can run the application directly or use the automated desktop launcher:

* **Via Launcher:** Double-click `Start_ECOLIFEBUDDY.bat` or `LitterGuard_VMS.bat`
* **Via Command Line:**
  ```powershell
  .venv312\Scripts\python.exe web_server.py
  ```
* Open your browser at `http://127.0.0.1:5000`

---

## 6. Access Control & Role-Based Permissions (RBAC)

| Role | Permissions & Scope | Privacy Masking |
| :--- | :--- | :--- |
| **Admin** | Full system configuration, user provisioning, retention policy, camera/zone management | Optional unmasking with reason logged |
| **Security Officer** | Live monitoring, alerts acknowledgement, incident timeline generation, visitor labeling | Can request un-blur with mandatory audit note |
| **Viewer** | Live stream viewing and visitor directory lookup | **Faces & bodies blurred by default**; no export permissions |
| **Auditor** | Read-only access to immutable audit logs, consent records, and data retention status | Full audit visibility; no direct live feed access |

---

## 7. Privacy & DPDP Act 2023 Compliance

EcoLifyBuddy is built from the ground up to respect personal privacy and comply with India's **Digital Personal Data Protection Act (DPDP Act 2023)**:
* **Default Anonymisation:** Live video and recorded snapshots blur human faces and personal identifiers for non-administrative roles.
* **Strict Purpose Limitation:** Video surveillance is strictly utilized for physical premises safety, asset security, and authorized visitor tracking.
* **Feature-Flagged Face Recognition:** Facial recognition remains **OFF by default** and is only active for consented, registered individuals (e.g., enrolled security staff, trusted domestic workers).
* **Automated Retention Purge:** Embeddings, event clips, and thumbnails are purged automatically according to configurable retention windows (default: 30 days).
* **Immutable Audit Trail:** Every query, export, credential check, and un-blur event is cryptographically timestamped in the audit log.

For complete compliance details, data flow descriptions, and subject rights, refer to [PRIVACY.md](PRIVACY.md).

---

## 8. License & Acknowledgements

Developed for modern, secure, and clean communities. Built with [Flask](https://flask.palletsprojects.com/), [Ultralytics](https://github.com/ultralytics/ultralytics), [Neon](https://neon.tech/), and [Tailwind CSS](https://tailwindcss.com/).
