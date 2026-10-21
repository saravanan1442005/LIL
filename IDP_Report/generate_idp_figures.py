"""
generate_idp_figures.py
Generates all UML, architectural, and evaluation figures required for the IDP-I Project Report:
- fig_logo.png (Eco Life Buddy Brand Logo)
- fig_4_1_2_data_flow.png (DFD Diagram)
- fig_4_1_3_frontend_flow.png (Front-end Camera Stream Data Flow)
- fig_4_1_4_use_case.png (UML Use Case Diagram)
- fig_4_1_5_class_diagram.png (UML Class Diagram)
- fig_4_1_6_activity_diagram.png (UML Activity Diagram)
- fig_4_1_7_structural_diagram.png (Structural System Boundary Diagram)
- fig_4_1_8_component_diagram.png (Component Diagram)
- fig_ai4_mvp_validation.png (MVP Validation Bar Chart)
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle, Wedge
import numpy as np

OUTPUT_DIR = r"c:\LIL\IDP_Report\figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

# -------------------------------------------------------------
# 1. LOGO GENERATION
# -------------------------------------------------------------
def generate_logo():
    fig, ax = plt.subplots(figsize=(6, 6), dpi=300)
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.axis('off')
    
    # Outer circle ring
    circle_outer = Circle((0, 0), 2.5, color='#059669', fill=False, lw=6)
    circle_inner = Circle((0, 0), 2.35, color='#10B981', fill=False, lw=2, ls='--')
    ax.add_patch(circle_outer)
    ax.add_patch(circle_inner)
    
    # Center green leaf / shield graphic
    shield = patches.RegularPolygon((0, 0.2), 3, radius=1.3, orientation=np.pi, 
                                    facecolor='#ECFDF5', edgecolor='#059669', lw=3)
    ax.add_patch(shield)
    
    # Eye / Camera aperture symbol in center
    eye_outer = Circle((0, 0.2), 0.55, facecolor='#065F46', edgecolor='white', lw=2)
    eye_pupil = Circle((0, 0.2), 0.25, facecolor='#34D399', edgecolor='white', lw=1.5)
    ax.add_patch(eye_outer)
    ax.add_patch(eye_pupil)
    
    # Text
    ax.text(0, -1.2, "ECO LIFE BUDDY", ha='center', va='center', 
            fontsize=16, fontweight='bold', color='#064E3B')
    ax.text(0, -1.6, "AI Cleanliness & Surveillance System", ha='center', va='center', 
            fontsize=9.5, fontweight='semibold', color='#047857')
    ax.text(0, -2.0, "Watch. Detect. Protect.", ha='center', va='center', 
            fontsize=8.5, fontstyle='italic', color='#6B7280')

    p = os.path.join(OUTPUT_DIR, "fig_logo.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved logo:", p)

# -------------------------------------------------------------
# 2. DATA FLOW DIAGRAM (DFD) - FIG 4.1.2
# -------------------------------------------------------------
def generate_data_flow():
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')
    
    ax.text(6, 7.6, "Figure 4.1.2: End-to-End System Data Flow Diagram (DFD)", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0F172A')

    # External Entities (Rectangles)
    # 1. CCTV Video Feed, 2. Violator/Pedestrian, 3. Security Guard, 4. Municipal Admin
    def draw_entity(x, y, text, color='#2563EB'):
        box = FancyBboxPatch((x-1.0, y-0.45), 2.0, 0.9, boxstyle="square,pad=0.05",
                             facecolor='#EFF6FF', edgecolor=color, lw=2.0)
        ax.add_patch(box)
        ax.text(x, y, text, ha='center', va='center', fontsize=8.5, fontweight='bold', color='#1E3A8A')

    # Processes (Circles/Ovals)
    def draw_process(x, y, p_num, p_name, color='#059669'):
        circle = Circle((x, y), 0.75, facecolor='#ECFDF5', edgecolor=color, lw=2.0)
        ax.add_patch(circle)
        ax.text(x, y+0.18, f"{p_num}", ha='center', va='center', fontsize=9.0, fontweight='bold', color=color)
        ax.text(x, y-0.15, p_name, ha='center', va='center', fontsize=7.2, fontweight='bold', color='#064E3B')

    # Data Stores (Open-ended parallel lines)
    def draw_datastore(x, y, d_id, d_name):
        ax.plot([x-1.1, x+1.1], [y+0.35, y+0.35], color='#D97706', lw=2)
        ax.plot([x-1.1, x+1.1], [y-0.35, y-0.35], color='#D97706', lw=2)
        ax.fill_between([x-1.1, x+1.1], [y-0.35, y-0.35], [y+0.35, y+0.35], color='#FEF3C7', alpha=0.7)
        ax.text(x, y, f"{d_id}: {d_name}", ha='center', va='center', fontsize=7.8, fontweight='bold', color='#92400E')

    # Placement
    draw_entity(1.5, 6.0, "CCTV RTSP /\nEntrance Camera", '#2563EB')
    draw_process(4.2, 6.0, "1.0", "Ingest &\nPreprocess", '#2563EB')
    draw_process(7.0, 6.0, "2.0", "Face Scan &\nID Tagging", '#7C3AED')
    draw_datastore(10.0, 6.0, "D1", "Visitor & Face\nEmbedding DB")

    draw_process(4.2, 3.8, "3.0", "YOLO26 Detect\n& ByteTrack", '#059669')
    draw_process(7.0, 3.8, "4.0", "Spatio-Temporal\nRule Engine", '#D97706')
    draw_datastore(10.0, 3.8, "D2", "Active Violation\nWatchlist DB")

    draw_process(7.0, 1.5, "5.0", "Exit Face Scan\n& Vector Match", '#DC2626')
    draw_entity(10.2, 1.5, "Security Guard\nTablet & Siren", '#DC2626')
    draw_entity(3.8, 1.5, "Municipal Admin\nGIS Dashboard", '#0284C7')

    # Arrows
    def arrow(x1, y1, x2, y2, label=""):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6, mutation_scale=12))
        if label:
            mx, my = (x1+x2)/2, (y1+y2)/2
            ax.text(mx, my+0.12, label, ha='center', va='center', fontsize=6.8, color='#334155', backgroundcolor='#FFFFFF')

    arrow(2.5, 6.0, 3.45, 6.0, "Raw RTSP Stream")
    arrow(4.95, 6.0, 6.25, 6.0, "Enhanced Frame")
    arrow(7.75, 6.0, 8.9, 6.0, "Vector + ID #1042")
    arrow(4.2, 5.25, 4.2, 4.55, "Campus Video")
    arrow(4.95, 3.8, 6.25, 3.8, "Tracks & BBoxes")
    arrow(7.75, 3.8, 8.9, 3.8, "Violation Snapshot")
    arrow(10.0, 3.4, 7.6, 1.9, "Active Watchlist")
    arrow(7.75, 1.5, 9.2, 1.5, "Interception Alert")
    arrow(7.0, 3.05, 7.0, 2.25, "Event Trigger")
    arrow(6.25, 1.5, 4.8, 1.5, "Telemetry / KDE")

    p = os.path.join(OUTPUT_DIR, "fig_4_1_2_data_flow.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved DFD:", p)

# -------------------------------------------------------------
# 3. FRONT-END CAMERA STREAM DATA FLOW - FIG 4.1.3
# -------------------------------------------------------------
def generate_frontend_flow():
    fig, ax = plt.subplots(figsize=(11, 6.5), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7)
    ax.axis('off')
    
    ax.text(5.5, 6.6, "Figure 4.1.3: Front-End Telemetry and Camera Stream Pipeline", 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0F172A')

    steps = [
        ("Edge CCTV Nodes", "RTSP Streams\n(1080p @ 30 FPS)\nEntrance, Campus, Exit", 0.5, 3.0, 2.0, 2.2, '#EFF6FF', '#2563EB'),
        ("Video Stream Worker", "OpenCV VideoCapture\nThread-Safe Deque Buffer\nMotion Bypass Gate", 3.0, 3.0, 2.2, 2.2, '#F0FDF4', '#059669'),
        ("Flask Web Server", "MJPEG Multi-Part Stream\nWebSocket Telemetry\nREST API Controllers", 5.7, 3.0, 2.2, 2.2, '#FEF3C7', '#D97706'),
        ("Client Dashboards", "1. Admin Web Console\n2. Guard Mobile Tablet\n3. Turnstile IoT Lock", 8.4, 3.0, 2.2, 2.2, '#FEE2E2', '#DC2626'),
    ]

    for title, desc, x, y, w, h, bg, border in steps:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.12",
                             facecolor=bg, edgecolor=border, lw=2.0)
        ax.add_patch(box)
        header = FancyBboxPatch((x, y+h-0.55), w, 0.55, boxstyle="round,pad=0.04,rounding_size=0.08",
                                facecolor=border, edgecolor=border)
        ax.add_patch(header)
        ax.text(x+w/2, y+h-0.27, title, ha='center', va='center', fontsize=8.5, fontweight='bold', color='white')
        ax.text(x+w/2, y+(h-0.55)/2, desc, ha='center', va='center', fontsize=7.8, color='#1E293B', linespacing=1.3)

    for i in range(3):
        x_start = steps[i][2] + steps[i][4]
        x_end = steps[i+1][2]
        ax.annotate('', xy=(x_end, 4.1), xytext=(x_start, 4.1),
                    arrowprops=dict(arrowstyle="-|>", color='#475569', lw=2.0, mutation_scale=14))

    # Bottom notes
    ax.text(5.5, 1.5, "Sub-100ms Latency | WebRTC / WebSocket Feed | Mobile-Responsive Dashboard", 
            ha='center', va='center', fontsize=9.0, fontweight='bold', color='#047857',
            bbox=dict(boxstyle="round,pad=0.4", facecolor='#ECFDF5', edgecolor='#059669', lw=1.2))

    p = os.path.join(OUTPUT_DIR, "fig_4_1_3_frontend_flow.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved frontend flow:", p)

# -------------------------------------------------------------
# 4. USE CASE DIAGRAM - FIG 4.1.4
# -------------------------------------------------------------
def generate_use_case():
    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis('off')

    ax.text(6, 8.6, "Figure 4.1.4: UML Use Case Diagram for Eco Life Buddy", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0F172A')

    # System boundary box
    sys_box = FancyBboxPatch((3.2, 0.4), 5.6, 7.8, boxstyle="round,pad=0.1,rounding_size=0.15",
                             facecolor='#F8FAFC', edgecolor='#475569', lw=2.0)
    ax.add_patch(sys_box)
    ax.text(6.0, 7.9, "Eco Life Buddy System Boundary", ha='center', va='center', 
            fontsize=10.5, fontweight='bold', color='#0F172A')

    # Actors
    def draw_actor(x, y, name):
        # Head
        ax.add_patch(Circle((x, y+0.45), 0.22, color='#1E293B'))
        # Body
        ax.plot([x, x], [y+0.23, y-0.2], color='#1E293B', lw=2.5)
        # Arms
        ax.plot([x-0.3, x+0.3], [y+0.05, y+0.05], color='#1E293B', lw=2.5)
        # Legs
        ax.plot([x, x-0.25], [y-0.2, y-0.65], color='#1E293B', lw=2.5)
        ax.plot([x, x+0.25], [y-0.2, y-0.65], color='#1E293B', lw=2.5)
        ax.text(x, y-0.9, name, ha='center', va='center', fontsize=8.2, fontweight='bold', color='#0F172A')

    draw_actor(1.2, 6.5, "Campus Visitor /\nStudent")
    draw_actor(1.2, 3.0, "Environmental\nViolator")
    draw_actor(10.6, 6.5, "Campus Security\nOfficer")
    draw_actor(10.6, 2.5, "Municipal /\nCampus Admin")

    # Use Cases (Ellipses)
    use_cases = [
        ("UC1: Register Face & Assign ID", 6.0, 7.2, '#EFF6FF', '#2563EB'),
        ("UC2: Track Movement Across CCTV", 6.0, 6.3, '#EFF6FF', '#2563EB'),
        ("UC3: Detect Littering Violation", 6.0, 5.3, '#FEF3C7', '#D97706'),
        ("UC4: Upload Evidence to Watchlist", 6.0, 4.4, '#FEF3C7', '#D97706'),
        ("UC5: Exit Face Scan & Watchlist Query", 6.0, 3.4, '#FEE2E2', '#DC2626'),
        ("UC6: Sound Siren & Lock Exit Turnstile", 6.0, 2.4, '#FEE2E2', '#DC2626'),
        ("UC7: Review Snapshot & Intercept", 6.0, 1.5, '#ECFDF5', '#059669'),
        ("UC8: Configure ROIs & View Heatmaps", 6.0, 0.7, '#E0F2FE', '#0284C7'),
    ]

    for text, x, y, bg, border in use_cases:
        ellipse = patches.Ellipse((x, y), 3.8, 0.65, facecolor=bg, edgecolor=border, lw=1.8)
        ax.add_patch(ellipse)
        ax.text(x, y, text, ha='center', va='center', fontsize=7.8, fontweight='semibold', color='#0F172A')

    # Association lines
    def assoc(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color='#64748B', lw=1.5, ls='--')

    assoc(1.6, 6.5, 4.1, 7.2)
    assoc(1.6, 6.5, 4.1, 6.3)
    assoc(1.6, 3.0, 4.1, 5.3)
    assoc(1.6, 3.0, 4.1, 3.4)

    assoc(9.8, 6.5, 7.9, 3.4)
    assoc(9.8, 6.5, 7.9, 2.4)
    assoc(9.8, 6.5, 7.9, 1.5)

    assoc(9.8, 2.5, 7.9, 4.4)
    assoc(9.8, 2.5, 7.9, 0.7)

    p = os.path.join(OUTPUT_DIR, "fig_4_1_4_use_case.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved use case:", p)

# -------------------------------------------------------------
# 5. CLASS DIAGRAM - FIG 4.1.5
# -------------------------------------------------------------
def generate_class_diagram():
    fig, ax = plt.subplots(figsize=(13, 8.5), dpi=300)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9)
    ax.axis('off')

    ax.text(6.5, 8.7, "Figure 4.1.5: UML Class Diagram of Eco Life Buddy Core System", 
            ha='center', va='center', fontsize=13, fontweight='bold', color='#0F172A')

    def draw_class(x, y, w, h, name, attrs, methods, color='#2563EB'):
        box = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.0",
                             facecolor='#FFFFFF', edgecolor=color, lw=1.8)
        ax.add_patch(box)
        header = FancyBboxPatch((x, y+h-0.55), w, 0.55, boxstyle="square,pad=0.0",
                                facecolor=color, edgecolor=color)
        ax.add_patch(header)
        ax.text(x+w/2, y+h-0.27, name, ha='center', va='center', fontsize=8.5, fontweight='bold', color='white')
        
        # Attributes
        ax.text(x+0.1, y+h-0.75, attrs, ha='left', va='top', fontsize=6.8, color='#1E293B', family='monospace')
        # Separator line
        h_split = y + h - 0.55 - (len(attrs.split('\n')) * 0.22 + 0.15)
        ax.plot([x, x+w], [h_split, h_split], color=color, lw=1.0)
        # Methods
        ax.text(x+0.1, h_split-0.1, methods, ha='left', va='top', fontsize=6.8, color='#0F172A', family='monospace')

    draw_class(0.5, 5.0, 3.4, 3.2, "CameraManager", 
               "- rtsp_urls: List[str]\n- active_streams: Dict\n- buffer_queue: Queue", 
               "+ start_capture()\n+ get_frame(cam_id)\n+ release_all()\n+ motion_gated(f1, f2)", '#2563EB')

    draw_class(4.5, 5.0, 3.6, 3.2, "YOLO26Detector", 
               "- model: YOLO26s_TRT\n- conf_threshold: float = 0.45\n- target_classes: List[str]", 
               "+ detect(frame: np.ndarray)\n+ extract_bboxes()\n+ get_nms_free_preds()", '#059669')

    draw_class(8.8, 5.0, 3.6, 3.2, "ByteTracker", 
               "- active_tracks: Dict\n- kalman_filters: Dict\n- tau_lost: int = 15", 
               "+ update(detections)\n+ get_trajectory(track_id)\n+ recover_low_conf_bbox()", '#7C3AED')

    draw_class(0.5, 0.8, 3.5, 3.4, "RuleEngine", 
               "- d_pw_thresh: float = 120\n- d_wb_thresh: float = 80\n- tau_min: int = 18", 
               "+ evaluate_separation(p, o)\n+ check_bin_proximity(o, b)\n+ filter_confusers(p, o)\n+ trigger_violation(p_id)", '#D97706')

    draw_class(4.6, 0.8, 3.6, 3.4, "WatchlistDB", 
               "- db_uri: sqlite:///alerts.db\n- active_violators: Dict\n- cipher: AES256", 
               "+ register_face(face_emb)\n+ log_violation(v_record)\n+ query_exit_match(face_emb)\n+ purge_old_records()", '#DC2626')

    draw_class(8.8, 0.8, 3.6, 3.4, "AlertDispatcher", 
               "- smtp_client: SMTP\n- twilio_sms: Client\n- guard_tablets: List[str]", 
               "+ dispatch_exit_alarm(p_id)\n+ lock_turnstile_gate()\n+ send_evidence_package()\n+ render_heatmap()", '#0284C7')

    # Association lines
    ax.plot([3.9, 4.5], [6.6, 6.6], color='#475569', lw=1.6)
    ax.plot([8.1, 8.8], [6.6, 6.6], color='#475569', lw=1.6)
    ax.plot([6.3, 6.3], [5.0, 4.2], color='#475569', lw=1.6)
    ax.plot([2.25, 2.25], [5.0, 4.2], color='#475569', lw=1.6)
    ax.plot([4.0, 4.6], [2.5, 2.5], color='#475569', lw=1.6)
    ax.plot([8.2, 8.8], [2.5, 2.5], color='#475569', lw=1.6)

    p = os.path.join(OUTPUT_DIR, "fig_4_1_5_class_diagram.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved class diagram:", p)

# -------------------------------------------------------------
# 6. ACTIVITY DIAGRAM - FIG 4.1.6
# -------------------------------------------------------------
def generate_activity_diagram():
    fig, ax = plt.subplots(figsize=(10, 11), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 12)
    ax.axis('off')

    ax.text(5.0, 11.6, "Figure 4.1.6: UML Activity Diagram - End-to-End System Logic", 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0F172A')

    # Start Node
    ax.add_patch(Circle((5.0, 11.0), 0.22, color='#0F172A'))

    def draw_action(y, text, color='#2563EB', h=0.65, w=4.4):
        box = FancyBboxPatch((5.0 - w/2, y - h/2), w, h, boxstyle="round,pad=0.06,rounding_size=0.15",
                             facecolor='#F8FAFC', edgecolor=color, lw=1.8)
        ax.add_patch(box)
        ax.text(5.0, y, text, ha='center', va='center', fontsize=7.6, fontweight='semibold', color='#0F172A')

    def draw_decision(y, text):
        diamond = patches.RegularPolygon((5.0, y), 4, radius=0.6, orientation=0,
                                         facecolor='#FEF3C7', edgecolor='#D97706', lw=1.8)
        ax.add_patch(diamond)
        ax.text(5.0, y, text, ha='center', va='center', fontsize=6.8, fontweight='bold', color='#92400E')

    draw_action(10.1, "1. Visitor Enters Campus Entrance Gate\nOverhead Camera Detects Face", '#2563EB')
    draw_action(9.1, "2. Compute Face Vector & Assign ID #1042\nRegister into Ingress DB", '#2563EB')
    draw_action(8.1, "3. Person Traverses Campus Pathways\nByteTrack Tracks Trajectory via CCTV", '#059669')
    draw_decision(6.9, "Waste Item\nDropped?")
    
    # Left branch for no violation
    ax.annotate('', xy=(5.0, 5.7), xytext=(5.0, 6.3),
                arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.text(5.25, 6.0, "Yes", fontsize=7.5, color='#DC2626', fontweight='bold')

    draw_action(5.2, "4. Calculate d_pw & d_wb Distances\nValidate tau_min Persistence Gate", '#D97706')
    draw_decision(4.0, "Outside\nBin ROI?")
    
    ax.annotate('', xy=(5.0, 2.9), xytext=(5.0, 3.4),
                arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.text(5.25, 3.15, "Yes", fontsize=7.5, color='#DC2626', fontweight='bold')

    draw_action(2.5, "5. Violation Confirmed: Log Snapshot & ID #1042\nto Active Violation Watchlist DB", '#DC2626')
    draw_action(1.5, "6. Person Approaches Exit Turnstiles\nExit Camera Performs Sub-100ms Query", '#7C3AED')
    draw_action(0.5, "7. MATCH FOUND: Warning Siren + LED Alert\nLock Turnstile & Security Interception", '#DC2626')

    # End Node
    ax.add_patch(Circle((9.0, 0.5), 0.22, color='#0F172A'))
    ax.add_patch(Circle((9.0, 0.5), 0.28, fill=False, edgecolor='#0F172A', lw=1.8))
    ax.text(9.0, 0.05, "Interception\nCompleted", ha='center', va='center', fontsize=6.8, fontweight='bold')

    # Arrows
    ax.annotate('', xy=(5.0, 10.45), xytext=(5.0, 10.78), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(5.0, 9.45), xytext=(5.0, 9.75), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(5.0, 8.45), xytext=(5.0, 8.75), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(5.0, 7.5), xytext=(5.0, 7.75), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(5.0, 4.6), xytext=(5.0, 4.85), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(5.0, 1.85), xytext=(5.0, 2.15), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(5.0, 0.85), xytext=(5.0, 1.15), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))
    ax.annotate('', xy=(8.7, 0.5), xytext=(7.2, 0.5), arrowprops=dict(arrowstyle="-|>", color='#475569', lw=1.6))

    # Loop back arrows for No
    ax.plot([5.6, 8.2, 8.2, 5.0], [6.9, 6.9, 7.8, 7.8], color='#059669', lw=1.5, ls='--')
    ax.text(6.8, 7.05, "No (Compliant)", fontsize=7.2, color='#059669', fontweight='bold')

    p = os.path.join(OUTPUT_DIR, "fig_4_1_6_activity_diagram.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved activity diagram:", p)

# -------------------------------------------------------------
# 7. STRUCTURAL SYSTEM BOUNDARY DIAGRAM - FIG 4.1.7
# -------------------------------------------------------------
def generate_structural_diagram():
    fig, ax = plt.subplots(figsize=(11, 7.5), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 8)
    ax.axis('off')

    ax.text(5.5, 7.6, "Figure 4.1.7: Structural System Boundary Diagram of Eco Life Buddy", 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0F172A')

    # Main boundary
    boundary = FancyBboxPatch((0.5, 0.5), 10.0, 6.7, boxstyle="round,pad=0.1,rounding_size=0.15",
                              facecolor='#F8FAFC', edgecolor='#334155', lw=2.2)
    ax.add_patch(boundary)
    ax.text(5.5, 7.0, "Eco Life Buddy System Architecture & Subsystem Boundaries", 
            ha='center', va='center', fontsize=10.0, fontweight='bold', color='#1E293B')

    tiers = [
        ("Client & Edge Ingestion Tier", 
         "• Multi-Camera RTSP Streams\n• Ingress Turnstile Face Cam\n• Egress Scanner Node", 
         0.8, 3.8, 2.8, 2.7, '#EFF6FF', '#2563EB'),
        ("AI Vision & Inference Tier", 
         "• CLAHE Luminance Enhancer\n• YOLO26 Dual-Head Detector\n• ByteTrack Trajectory Tracker", 
         4.1, 3.8, 2.8, 2.7, '#F0FDF4', '#059669'),
        ("Rule & Reasoning Tier", 
         "• Proximity Normalizer (d_pw)\n• Persistence Gate (tau_min)\n• Confuser & Sweeper Filter", 
         7.4, 3.8, 2.8, 2.7, '#FEF3C7', '#D97706'),
        ("Secure Storage Tier", 
         "• Ingress Session Face DB\n• Active Violation Watchlist\n• AES-256 Encrypted Dossiers", 
         2.0, 0.8, 3.2, 2.4, '#F3E8FF', '#7C3AED'),
        ("Enforcement & Dispatch Tier", 
         "• Exit Siren & Warning Board\n• Turnstile Hardware Lockout\n• Security Guard Web Tablet", 
         5.8, 0.8, 3.2, 2.4, '#FEE2E2', '#DC2626'),
    ]

    for title, desc, x, y, w, h, bg, border in tiers:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06,rounding_size=0.1",
                             facecolor=bg, edgecolor=border, lw=1.8)
        ax.add_patch(box)
        header = FancyBboxPatch((x, y+h-0.5), w, 0.5, boxstyle="round,pad=0.04,rounding_size=0.08",
                                facecolor=border, edgecolor=border)
        ax.add_patch(header)
        ax.text(x+w/2, y+h-0.25, title, ha='center', va='center', fontsize=8.2, fontweight='bold', color='white')
        ax.text(x+0.15, y+(h-0.5)/2, desc, ha='left', va='center', fontsize=7.5, color='#1E293B', linespacing=1.35)

    p = os.path.join(OUTPUT_DIR, "fig_4_1_7_structural_diagram.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved structural diagram:", p)

# -------------------------------------------------------------
# 8. COMPONENT DIAGRAM - FIG 4.1.8
# -------------------------------------------------------------
def generate_component_diagram():
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')

    ax.text(6.0, 7.6, "Figure 4.1.8: UML Component Diagram with Defined Interfaces", 
            ha='center', va='center', fontsize=12.5, fontweight='bold', color='#0F172A')

    def draw_component(x, y, w, h, name, color='#2563EB'):
        box = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0.05",
                             facecolor='#F8FAFC', edgecolor=color, lw=2.0)
        ax.add_patch(box)
        # Component tabs on left
        tab1 = FancyBboxPatch((x-0.25, y+h-0.55), 0.5, 0.35, boxstyle="square,pad=0.0",
                              facecolor=color, edgecolor=color)
        tab2 = FancyBboxPatch((x-0.25, y+0.2), 0.5, 0.35, boxstyle="square,pad=0.0",
                              facecolor=color, edgecolor=color)
        ax.add_patch(tab1)
        ax.add_patch(tab2)
        ax.text(x+w/2, y+h/2, name, ha='center', va='center', fontsize=8.2, fontweight='bold', color='#0F172A')

    draw_component(0.8, 4.5, 2.5, 1.8, "Video Ingestion\nComponent", '#2563EB')
    draw_component(4.5, 4.5, 2.8, 1.8, "AI Vision &\nTracking Engine", '#059669')
    draw_component(8.5, 4.5, 2.7, 1.8, "Spatial-Temporal\nRule Component", '#D97706')

    draw_component(1.5, 1.2, 2.8, 1.8, "Watchlist &\nEvidence DB", '#7C3AED')
    draw_component(5.5, 1.2, 2.8, 1.8, "Exit Interception\nController", '#DC2626')
    draw_component(9.2, 1.2, 2.2, 1.8, "Web & GIS\nDashboard", '#0284C7')

    # Interface sockets and lollipop connections
    ax.plot([3.3, 4.25], [5.4, 5.4], color='#475569', lw=1.8)
    ax.plot([7.3, 8.25], [5.4, 5.4], color='#475569', lw=1.8)
    ax.plot([8.5, 7.0], [4.5, 3.0], color='#475569', lw=1.8)
    ax.plot([4.3, 5.5], [2.1, 2.1], color='#475569', lw=1.8)
    ax.plot([8.3, 9.2], [2.1, 2.1], color='#475569', lw=1.8)

    p = os.path.join(OUTPUT_DIR, "fig_4_1_8_component_diagram.png")
    fig.savefig(p, dpi=300, bbox_inches='tight')
    plt.close()
    print("Saved component diagram:", p)

# -------------------------------------------------------------
# 9. MVP VALIDATION BAR CHART - FIG A.I.4
# -------------------------------------------------------------
def generate_mvp_validation():
    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=300)
    fig.patch.set_facecolor('#FFFFFF')
    ax.set_facecolor('#F8FAFC')

    questions = [
        "Prefers Automated AI\nSurveillance over Manual",
        "Exit Warning & Turnstile\nLock Deterrence Impact",
        "Photo Evidence Makes\nViolations Undisputed",
        "GIS Heatmaps Helpful for\nSanitation Planning",
        "Clear Compliance with\nDPDP Act Privacy Norms"
    ]
    scores = [94.2, 91.8, 96.5, 89.4, 92.0]
    colors = ['#2563EB', '#059669', '#D97706', '#7C3AED', '#0284C7']
    edge_colors = ['#1D4ED8', '#047857', '#B45309', '#6D28D9', '#0369A1']

    # Draw subtle background grid
    ax.grid(axis='y', linestyle='--', linewidth=0.8, color='#CBD5E1', alpha=0.7, zorder=0)
    ax.set_axisbelow(True)

    # Plot bars with generous width and spacing
    x_indices = range(len(questions))
    bars = ax.bar(x_indices, scores, color=colors, width=0.52, edgecolor=edge_colors, linewidth=1.5, zorder=3)

    # Y-axis bounds and styling
    ax.set_ylim(0, 120)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'], fontsize=10, fontweight='bold', color='#334155')
    ax.set_ylabel("Stakeholder Approval Rate (%)", fontsize=11.5, fontweight='bold', color='#0F172A', labelpad=14)

    # X-axis ticks and labels with generous padding so text never overlaps
    ax.set_xticks(x_indices)
    ax.set_xticklabels(questions, fontsize=9.5, fontweight='bold', color='#1E293B', linespacing=1.2)
    ax.tick_params(axis='x', pad=10, bottom=False)
    ax.tick_params(axis='y', left=True, color='#94A3B8')

    # Spines styling
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)
    for spine in ['left', 'bottom']:
        ax.spines[spine].set_color('#94A3B8')
        ax.spines[spine].set_linewidth(1.2)

    # Target threshold reference line (e.g., 85% Target Acceptance)
    bench_line = ax.axhline(85, color='#DC2626', linestyle='--', linewidth=1.5, alpha=0.85, zorder=2, label='Target Acceptance Benchmark (85%)')

    # Value tags above bars
    for bar, score, color in zip(bars, scores, colors):
        h = bar.get_height()
        ax.annotate(f"{score:.1f}%",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 8),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=10.5, fontweight='bold', color='#0F172A',
                    bbox=dict(boxstyle='round,pad=0.35', facecolor='#FFFFFF', edgecolor='#CBD5E1', lw=1.2, alpha=0.98),
                    zorder=4)

    # Main Title and Subtitle
    ax.set_title("Figure A.I.4: Stakeholder MVP Validation Survey Results (N=120)\n"
                 "Evaluated across Campus Administration, Security Officers, Facility Management, and Student Body",
                 fontsize=12, fontweight='bold', pad=18, color='#0F172A', linespacing=1.35)

    # Clean legend for the benchmark line
    ax.legend(loc='upper right', frameon=True, facecolor='#FFFFFF', edgecolor='#CBD5E1', 
              fontsize=9.2, fancybox=True, framealpha=0.95, borderpad=0.6)

    plt.tight_layout()
    p = os.path.join(OUTPUT_DIR, "fig_ai4_mvp_validation.png")
    fig.savefig(p, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print("Saved MVP validation chart:", p)

if __name__ == "__main__":
    generate_logo()
    generate_data_flow()
    generate_frontend_flow()
    generate_use_case()
    generate_class_diagram()
    generate_activity_diagram()
    generate_structural_diagram()
    generate_component_diagram()
    generate_mvp_validation()
    print("All IDP figures generated successfully!")
