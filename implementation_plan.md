# Camera Pipeline Separation & Visitor Recognition Flow — Implementation Plan

## Problem
Litter detection and visitor face recognition are currently **mixed together** in the same camera processing loop (`camera_worker_loop` in `web_server.py`). Every camera runs both YOLO litter detection AND face recognition, causing conflicts and failures.

## Solution Architecture

### 1. Camera Purpose Field (Backend — `database/models.py` + `api/cameras.py`)
Add a `purpose` column to the `Camera` model:
- `"LITTER"` — camera only runs YOLO litter detection pipeline
- `"VISITOR"` — camera only runs face recognition for visitor monitoring
- Default: `"LITTER"` for backward compatibility

### 2. Separate Processing Pipelines (Backend — `web_server.py`)
- **Litter cameras**: Run YOLO detection → tracker → rule engine (existing pipeline)
- **Visitor cameras**: Run InsightFace face recognition → match against Supabase visitor embeddings → push notification to guard app via SSE/polling

### 3. Visitor Camera Worker (Backend — New `visitor_camera_worker`)
New background thread that:
- Processes only cameras with `purpose="VISITOR"`
- Periodically grabs frames → runs `face_service.recognize_face()`
- On match: stores a **pending match event** that the guard app polls
- Does NOT run YOLO litter detection

### 4. Guard App Integration (Backend API — `api/registration.py`)
New endpoint: `GET /api/v2/registration/camera-alerts`
- Guard app polls this every 3-5 seconds
- Returns any pending face recognition match events with visitor details
- Guard confirms entry/exit from the popup

### 5. Visitor Registration Flow (Existing + Fixes)
**First-time visit:**
1. Guard asks delivery partner for: name, phone, company, bike number
2. Guard takes photo in visitor app → photo sent to backend
3. Backend: photo → InsightFace → extract 512-d face embedding → store in Supabase
4. Photo file is **deleted** after embedding extraction (NOT stored in DB)
5. All details saved to Supabase `visitors` table

**Exit (auto-detected by visitor exit cam):**
1. Exit camera (purpose=VISITOR) captures frame → face recognition
2. Match found → creates EXIT event with timestamp
3. Guard app shows exit notification

**Subsequent visits (auto-detected by visitor entry cam):**
1. Entry camera (purpose=VISITOR) captures frame → face recognition
2. Match found → popup on guard app with full visitor details
3. Guard confirms → entry logged

---

## Files to Modify

### Backend (LIL project)
| File | Change |
|------|--------|
| [`database/models.py`](file:///d:/LIL/database/models.py) | Add `purpose` column to `Camera` model |
| [`api/cameras.py`](file:///d:/LIL/api/cameras.py) | Accept `purpose` in create/update camera |
| [`web_server.py`](file:///d:/LIL/web_server.py) | Filter cameras by purpose in `camera_worker_loop`; add `visitor_camera_worker` |
| [`api/registration.py`](file:///d:/LIL/api/registration.py) | Add `/camera-alerts` polling endpoint; delete photo after embedding |
| [`litter_guard_config.json`](file:///d:/LIL/litter_guard_config.json) | Add `purpose` field to camera configs |

### Visitor App (Flutter)
| File | Change |
|------|--------|
| [`lib/services/api_service.dart`](file:///d:/visitor%20app/lib/services/api_service.dart) | Poll `/camera-alerts` for real face matches |
| [`lib/screens/guard_dashboard_screen.dart`](file:///d:/visitor%20app/lib/screens/guard_dashboard_screen.dart) | Wire real camera alerts into popup |
| [`lib/widgets/camera_match_dialog.dart`](file:///d:/visitor%20app/lib/widgets/camera_match_dialog.dart) | Add Exit confirmation button for exit matches |

> [!IMPORTANT]
> The photo taken during registration is converted to a 512-d face embedding by InsightFace, stored in Supabase `visitor_embeddings`, and then the original photo file is **deleted from disk**. Only embeddings are persisted.
