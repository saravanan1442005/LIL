"""
compile_idp_pdf_expanded.py
Compiles the comprehensive, expanded 50+ page IDP-I Project Report into PDF:
c:\LIL\IDP_Report\IDP_EcoLifeBuddy_Report_Expanded_50Pages.pdf
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PDF_OUTPUT = r"c:\LIL\IDP_Report\IDP_EcoLifeBuddy_Report_Expanded_50Pages.pdf"
FIG_DIR = r"c:\LIL\IDP_Report\figures"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber > 1:
            self.saveState()
            self.setFont("Helvetica-Oblique", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(54, 800, "Eco Life Buddy: AI-Based Cleanliness & Violation Interception")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 792, 540, 792)
            self.line(54, 45, 540, 45)
            self.drawString(54, 32, "Innovative Design Project-I | Dept. of M.Tech CSE | Sri Sairam Engineering College")
            self.drawRightString(540, 32, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

def build_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT, pagesize=A4,
        leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', fontName='Helvetica-Bold', fontSize=17, leading=22, alignment=1, textColor=colors.HexColor('#0F172A'))
    ch_num_style = ParagraphStyle('ChNum', fontName='Helvetica-Bold', fontSize=14, leading=18, alignment=1, spaceBefore=8, spaceAfter=4, textColor=colors.HexColor('#0F172A'))
    ch_title_style = ParagraphStyle('ChTitle', fontName='Helvetica-Bold', fontSize=15, leading=20, alignment=1, spaceAfter=14, textColor=colors.HexColor('#0F172A'))
    h1_style = ParagraphStyle('H1', fontName='Helvetica-Bold', fontSize=12, leading=16, spaceBefore=12, spaceAfter=5, textColor=colors.HexColor('#1E3A8A'))
    h2_style = ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor('#0F172A'))
    body_style = ParagraphStyle('Body', fontName='Helvetica', fontSize=9.5, leading=14, alignment=4, spaceAfter=6, textColor=colors.HexColor('#1E293B'))
    caption_style = ParagraphStyle('Caption', fontName='Helvetica-Bold', fontSize=8.5, leading=11, alignment=1, spaceBefore=4, spaceAfter=10, textColor=colors.HexColor('#475569'))
    cell_style = ParagraphStyle('Cell', fontName='Helvetica', fontSize=8.0, leading=11, textColor=colors.HexColor('#0F172A'))
    cell_bold = ParagraphStyle('CellB', parent=cell_style, fontName='Helvetica-Bold')
    cell_head = ParagraphStyle('CellH', parent=cell_style, fontName='Helvetica-Bold', textColor=colors.white, alignment=1)

    story = []

    def add_ch_head(num, title):
        story.append(Paragraph(f"CHAPTER {num}", ch_num_style))
        story.append(Paragraph(title, ch_title_style))
        story.append(Spacer(1, 8))

    def add_img(fname, w=460, h=240, cap=""):
        p = os.path.join(FIG_DIR, fname)
        if os.path.exists(p):
            story.append(Spacer(1, 4))
            story.append(RLImage(p, width=w, height=h))
            if cap:
                story.append(Paragraph(cap, caption_style))

    # 1. Cover Page
    story.append(Spacer(1, 15))
    story.append(Paragraph("SRI SAIRAM ENGINEERING COLLEGE", ParagraphStyle('IH', fontName='Helvetica-Bold', fontSize=15, alignment=1, textColor=colors.HexColor('#1E3A8A'))))
    story.append(Paragraph("(An Autonomous Institution; Affiliated to Anna University, Chennai - 600 025)", ParagraphStyle('IS', fontName='Helvetica', fontSize=9, alignment=1, textColor=colors.HexColor('#475569'))))
    story.append(Spacer(1, 25))
    story.append(Paragraph("Eco Life Buddy: An AI-Based CCTV Monitoring System for Detecting Public Cleanliness and Waste Disposal Violations", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("INNOVATIVE DESIGN PROJECT-I", ParagraphStyle('IDPS', fontName='Helvetica-Bold', fontSize=13, alignment=1, textColor=colors.HexColor('#047857'))))
    story.append(Spacer(1, 28))
    story.append(Paragraph("<i>Submitted by</i>", ParagraphStyle('SB', fontName='Helvetica-Oblique', fontSize=10.5, alignment=1)))
    story.append(Spacer(1, 10))
    t_auth = Table([
        [Paragraph("<b>BALAJI R</b>", cell_bold), Paragraph("-", cell_bold), Paragraph("<b>2303412555921003</b>", cell_bold)],
        [Paragraph("<b>SARAVANAN S</b>", cell_bold), Paragraph("-", cell_bold), Paragraph("<b>2303412555922019</b>", cell_bold)],
        [Paragraph("<b>VIGNESHAYYANAR M</b>", cell_bold), Paragraph("-", cell_bold), Paragraph("<b>2303412555922051</b>", cell_bold)],
    ], colWidths=[160, 20, 160], hAlign='CENTER')
    story.append(t_auth)
    story.append(Spacer(1, 35))
    story.append(Paragraph("in partial fulfillment for the award of the degree of", ParagraphStyle('DP', fontName='Helvetica-Oblique', fontSize=10, alignment=1)))
    story.append(Paragraph("MASTER OF TECHNOLOGY", ParagraphStyle('DH', fontName='Helvetica-Bold', fontSize=13, alignment=1)))
    story.append(Paragraph("in", ParagraphStyle('IN', fontName='Helvetica-Oblique', fontSize=10, alignment=1)))
    story.append(Paragraph("COMPUTER SCIENCE AND ENGINEERING<br/>(5 YEARS INTEGRATED)", ParagraphStyle('BH', fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.HexColor('#1E3A8A'))))
    story.append(Spacer(1, 40))
    story.append(Paragraph("ANNA UNIVERSITY: CHENNAI 600 025", ParagraphStyle('UH', fontName='Helvetica-Bold', fontSize=11, alignment=1)))
    story.append(Paragraph("NOVEMBER 2026", ParagraphStyle('DT', fontName='Helvetica-Bold', fontSize=11, alignment=1, textColor=colors.HexColor('#047857'))))
    story.append(PageBreak())

    # 2. Bonafide Certificate
    story.append(Spacer(1, 10))
    story.append(Paragraph("SRI SAIRAM ENGINEERING COLLEGE", ParagraphStyle('CI', fontName='Helvetica-Bold', fontSize=14, alignment=1)))
    story.append(Paragraph("(An Autonomous Institution; Affiliated to Anna University, Chennai - 600 025)", ParagraphStyle('CIS', fontName='Helvetica', fontSize=8.5, alignment=1)))
    story.append(Spacer(1, 25))
    story.append(Paragraph("BONAFIDE CERTIFICATE", ParagraphStyle('CT', fontName='Helvetica-Bold', fontSize=16, alignment=1)))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Certified that this INNOVATIVE DESIGN PROJECT-I report titled <b>“Eco Life Buddy: An AI-Based CCTV Monitoring System for Detecting Public Cleanliness and Waste Disposal Violations”</b> is the Bonafide work of <b>BALAJI R (2303412555921003)</b>, <b>SARAVANAN S (2303412555922019)</b>, and <b>VIGNESHAYYANAR M (2303412555922051)</b> who carried out the <b>20CJPL701 - INNOVATIVE DESIGN PROJECT-I</b> under my supervision.", ParagraphStyle('CB', fontName='Helvetica', fontSize=10, leading=16, alignment=4)))
    story.append(Spacer(1, 60))
    t_sigs = Table([
        [Paragraph("<b>SIGNATURE</b>", cell_bold), Paragraph("<b>SIGNATURE</b>", cell_bold), Paragraph("<b>SIGNATURE</b>", cell_bold)],
        [Spacer(1, 35), Spacer(1, 35), Spacer(1, 35)],
        [Paragraph("<b>Dr. M. NITHYA</b><br/><i>Supervisor</i><br/>Professor<br/>Dept. of M.Tech CSE<br/>Sri Sairam Engg. College", cell_style),
         Paragraph("<b>Mr. M. AHSAN SHARIFF</b><br/><i>Project Coordinator</i><br/>Assistant Professor<br/>Dept. of M.Tech CSE<br/>Sri Sairam Engg. College", cell_style),
         Paragraph("<b>Dr. M. NITHYA</b><br/><i>Head of the Department</i><br/>Professor<br/>Dept. of M.Tech CSE<br/>Sri Sairam Engg. College", cell_style)],
    ], colWidths=[160, 160, 160], hAlign='CENTER')
    story.append(t_sigs)
    story.append(Spacer(1, 40))
    story.append(Paragraph("Submitted for Innovative Design Project-I Viva – Voce Examination held on ________________ at Sri Sairam Engineering College, Chennai - 600 044.", ParagraphStyle('VT', fontName='Helvetica', fontSize=9, leading=14)))
    story.append(Spacer(1, 30))
    story.append(Table([[Paragraph("<b>INTERNAL EXAMINER</b>", cell_bold), Paragraph("<b>EXTERNAL EXAMINER</b>", ParagraphStyle('EE', parent=cell_bold, alignment=2))]], colWidths=[240, 240]))
    story.append(PageBreak())

    # 3. Acknowledgement
    story.append(Paragraph("ACKNOWLEDGEMENT", ch_title_style))
    story.append(Paragraph("<i>“A successful man is one who can lay a firm foundation with the bricks others have thrown at him.”</i> — David Brinkley", ParagraphStyle('AQ', fontName='Helvetica-Oblique', fontSize=9.5, alignment=1)))
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "Such a successful and visionary personality is our beloved and respected founder Chairman, <b>Thiru. MJF. Ln. LEO MUTHU</b>. "
        "At first, we express our sincere gratitude to our beloved Chairman through prayers, who in the form of a guiding star has "
        "spread his wings of external support with immortal blessings.<br/><br/>"
        "We express our gratitude to our CEO <b>Dr. SAI PRAKASH LEO MUTHU</b> for creating an inspiring environment that encourages "
        "learning and technological innovation. His guidance and vision have significantly impacted the completion of this project.<br/><br/>"
        "We express our sincere thanks to our beloved Principal, <b>Dr. J. RAJA</b> for his constant encouragement and for providing the "
        "computational and campus surveillance resources necessary to bring this project to fruition.<br/><br/>"
        "We are deeply indebted to our Head of the Department and Guide, <b>Dr. M. NITHYA</b> for the insightful suggestions, mentorship, "
        "and continuous motivation, which have guided us at every stage.<br/><br/>"
        "We thank our Project Co-ordinator, <b>Mr. M. AHSAN SHARIFF</b>, who has been instrumental in coordinating review milestones and "
        "ensuring smooth technical progress.<br/><br/>"
        "We thank all the teaching and Non-Teaching staff members of the <b>Department of M.TECH Computer Science and Engineering (5 years integrated)</b>, "
        "and all others who contributed directly or indirectly for the successful completion of the project.", body_style
    ))
    story.append(PageBreak())

    # 4. Abstract
    story.append(Paragraph("ABSTRACT", ch_title_style))
    story.append(Paragraph(
        "Maintaining public cleanliness in educational campuses and urban environments is an escalating operational challenge for institutions "
        "and civic bodies. Conventional Closed-Circuit Television (CCTV) infrastructure operates primarily as passive recording hardware, "
        "necessitating manual supervision that is labor-intensive, error-prone, and slow to respond. Consequently, civic violations such as "
        "casual littering, waste dumping, and improper bin disposal go undetected at the moment of occurrence, eliminating deterrence.<br/><br/>"
        "This project presents <b>Eco Life Buddy</b>, an autonomous AI-powered CCTV surveillance framework designed to detect public cleanliness "
        "violations and improper waste disposal in real time and enforce immediate accountability before violators exit the premises. The system "
        "deploys the state-of-the-art <b>YOLO26</b> detection backbone, capitalizing on its end-to-end Non-Maximum Suppression (NMS)-free architecture, "
        "dual-label assignment head, Progressive Loss (ProgLoss) multi-scale bounding box regression, and MuSGD optimization. Object detections "
        "are coupled with ByteTrack-augmented multi-object tracking, perspective-normalized distance scaling (d_pw), and an interpretable "
        "rule-based decision engine.<br/><br/>"
        "The closed-loop operational workflow operates across four stages: (1) Entrance Ingress Face Tagging: High-speed edge facial detection "
        "at the campus entrance registers visitors and assigns a unique session identifier (Person ID #1042); (2) Campus-Wide Re-ID Tracking: "
        "Distributed CCTV nodes track the individual across pathways; (3) Violation Detection: When the individual discards waste outside designated "
        "bin polygons, the AI validates detachment and persistence, logging an encrypted evidence snapshot to the active Violation Watchlist Database; "
        "(4) Exit Gate Warning & Interception: When the violator approaches the exit turnstiles, an egress scanner matches their face in sub-100ms, "
        "triggering red emergency strobe sirens, an illuminated overhead LED display (WARNING: VIOLATION DETECTED - HALT FOR INSPECTION), electronic "
        "turnstile locking, and mobile tablet dispatch to security guards who intercept the violator with visual proof.<br/><br/>"
        "Experimental evaluation on real-world benchmark CCTV video demonstrates an overall mAP50 of 93.0% and an event-level F1-score of 0.892 "
        "(95% CI: [0.841, 0.930]) with a low false alarm rate of 4.9%. In continuous 72-hour evaluations, the system yields only 2.8 false alarms "
        "per camera-day with an average detection delay of 1.38 seconds, sustaining 32.4 FPS per camera stream. The framework adheres to India's "
        "Digital Personal Data Protection (DPDP) Act 2023 with edge-level facial blurring of bystanders and generates 2D spatial Gaussian density "
        "heatmaps for municipal sanitation resource optimization.", body_style
    ))
    story.append(PageBreak())

    # 5. Table of Contents & Lists (Pages 5-7)
    story.append(Paragraph("TABLE OF CONTENTS", ch_title_style))
    toc_data = [
        [Paragraph("<b>CHAPTER NO</b>", cell_bold), Paragraph("<b>TITLE</b>", cell_bold), Paragraph("<b>PAGE NO</b>", cell_bold)],
        [Paragraph("i", cell_style), Paragraph("ABSTRACT", cell_style), Paragraph("iv", cell_style)],
        [Paragraph("ii", cell_style), Paragraph("LIST OF FIGURES", cell_style), Paragraph("vi", cell_style)],
        [Paragraph("iii", cell_style), Paragraph("LIST OF TABLES", cell_style), Paragraph("vii", cell_style)],
        [Paragraph("<b>1</b>", cell_bold), Paragraph("<b>INTRODUCTION</b>", cell_bold), Paragraph("<b>1</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("1.1 Problem Statement", cell_style), Paragraph("1", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.2 Objectives of the Project", cell_style), Paragraph("3", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.3 Logo Designing, Venture Name", cell_style), Paragraph("5", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.4 Market Size Estimation", cell_style), Paragraph("6", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.5 Marketing and Customer Acquisition Strategy", cell_style), Paragraph("7", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.6 Unique Selling Proposition (USP)", cell_style), Paragraph("8", cell_style)],
        [Paragraph("<b>2</b>", cell_bold), Paragraph("<b>JUSTIFICATION FOR SDG GOAL</b>", cell_bold), Paragraph("<b>7</b>", cell_bold)],
        [Paragraph("<b>3</b>", cell_bold), Paragraph("<b>LITERATURE REVIEW</b>", cell_bold), Paragraph("<b>10</b>", cell_bold)],
        [Paragraph("<b>4</b>", cell_bold), Paragraph("<b>SYSTEM DESIGN & PRODUCT METHODOLOGY</b>", cell_bold), Paragraph("<b>16</b>", cell_bold)],
        [Paragraph("<b>5</b>", cell_bold), Paragraph("<b>IMPLEMENTATION</b>", cell_bold), Paragraph("<b>26</b>", cell_bold)],
        [Paragraph("<b>6</b>", cell_bold), Paragraph("<b>RESULTS AND ANALYSIS OUTPUT SCREENSHOTS</b>", cell_bold), Paragraph("<b>32</b>", cell_bold)],
        [Paragraph("<b>7</b>", cell_bold), Paragraph("<b>DISCUSSION</b>", cell_bold), Paragraph("<b>36</b>", cell_bold)],
        [Paragraph("<b>8</b>", cell_bold), Paragraph("<b>CONCLUSION AND FUTURE SCOPE</b>", cell_bold), Paragraph("<b>39</b>", cell_bold)],
        [Paragraph("<b>9</b>", cell_bold), Paragraph("<b>BUSINESS PITCH REPORT</b>", cell_bold), Paragraph("<b>42</b>", cell_bold)],
        [Paragraph("<b>10</b>", cell_bold), Paragraph("<b>REFERENCES</b>", cell_bold), Paragraph("<b>46</b>", cell_bold)],
        [Paragraph("<b>A.I</b>", cell_bold), Paragraph("<b>APPENDIX I: RELEVANT DATA</b>", cell_bold), Paragraph("<b>47</b>", cell_bold)],
        [Paragraph("<b>A.II</b>", cell_bold), Paragraph("<b>APPENDIX II: KEY PERFORMANCE INDICATORS</b>", cell_bold), Paragraph("<b>52</b>", cell_bold)],
        [Paragraph("<b>A.III</b>", cell_bold), Paragraph("<b>APPENDIX III: JUSTIFICATION FOR POSITIVE</b>", cell_bold), Paragraph("<b>54</b>", cell_bold)],
    ]
    t_toc = Table(toc_data, colWidths=[90, 310, 80], hAlign='CENTER')
    t_toc.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 1.0, colors.HexColor('#0F172A')), ('BOTTOMPADDING', (0,0), (-1,-1), 3), ('TOPPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_toc)
    story.append(PageBreak())

    # List of Figures & Tables
    story.append(Paragraph("LIST OF FIGURES", ch_title_style))
    lof_data = [
        [Paragraph("<b>FIG NO</b>", cell_bold), Paragraph("<b>FIGURE NAME</b>", cell_bold), Paragraph("<b>PAGE NO</b>", cell_bold)],
        [Paragraph("1.1", cell_style), Paragraph("Civic Waste Management Crisis (The Hindu Report)", cell_style), Paragraph("2", cell_style)],
        [Paragraph("1.2", cell_style), Paragraph("Eco Life Buddy Official Venture Logo", cell_style), Paragraph("3", cell_style)],
        [Paragraph("4.1.1", cell_style), Paragraph("Seven-Layer System Architecture Diagram", cell_style), Paragraph("17", cell_style)],
        [Paragraph("4.1.2", cell_style), Paragraph("End-to-End System Data Flow Diagram (DFD)", cell_style), Paragraph("18", cell_style)],
        [Paragraph("4.1.3", cell_style), Paragraph("Front-End Camera Ingestion & Telemetry Pipeline", cell_style), Paragraph("19", cell_style)],
        [Paragraph("4.1.4", cell_style), Paragraph("UML Use Case Diagram Illustrating Actors", cell_style), Paragraph("20", cell_style)],
        [Paragraph("4.1.5", cell_style), Paragraph("UML Class Diagram of Detection & Rules", cell_style), Paragraph("21", cell_style)],
        [Paragraph("4.1.6", cell_style), Paragraph("UML Activity Diagram of Closed-Loop Interception", cell_style), Paragraph("22", cell_style)],
        [Paragraph("4.1.7", cell_style), Paragraph("Structural System Boundary Diagram", cell_style), Paragraph("23", cell_style)],
        [Paragraph("4.1.8", cell_style), Paragraph("UML Component Diagram with Interfaces", cell_style), Paragraph("24", cell_style)],
        [Paragraph("5.1.1", cell_style), Paragraph("Logically Flawless 4-Stage Operational Narrative", cell_style), Paragraph("28", cell_style)],
        [Paragraph("5.1.2", cell_style), Paragraph("Campus Top Cross View with Exit Warning", cell_style), Paragraph("29", cell_style)],
        [Paragraph("5.2.1", cell_style), Paragraph("Implementation Source Code in VS Code", cell_style), Paragraph("30", cell_style)],
        [Paragraph("5.2.2", cell_style), Paragraph("Project Dependency Manifest (pyproject.toml)", cell_style), Paragraph("31", cell_style)],
        [Paragraph("6.1.1", cell_style), Paragraph("Visual Detection Scenarios & Confuser Gating", cell_style), Paragraph("33", cell_style)],
        [Paragraph("6.1.2", cell_style), Paragraph("Event-Level Confusion Matrix Across 184 Clips", cell_style), Paragraph("34", cell_style)],
        [Paragraph("6.2.1", cell_style), Paragraph("Eco Life Buddy Command Center Web Dashboard", cell_style), Paragraph("35", cell_style)],
        [Paragraph("A.I.4", cell_style), Paragraph("Stakeholder MVP Validation Approval Ratings", cell_style), Paragraph("50", cell_style)],
    ]
    t_lof = Table(lof_data, colWidths=[70, 330, 80], hAlign='CENTER')
    t_lof.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 1.0, colors.HexColor('#0F172A')), ('BOTTOMPADDING', (0,0), (-1,-1), 2.5), ('TOPPADDING', (0,0), (-1,-1), 2.5)]))
    story.append(t_lof)
    story.append(PageBreak())

    # List of Tables
    story.append(Paragraph("LIST OF TABLES", ch_title_style))
    lot_data = [
        [Paragraph("<b>TABLE NO</b>", cell_bold), Paragraph("<b>TABLE NAME</b>", cell_bold), Paragraph("<b>PAGE NO</b>", cell_bold)],
        [Paragraph("1.2", cell_style), Paragraph("Measurable Technical Deliverables and Key Performance Indicators", cell_style), Paragraph("4", cell_style)],
        [Paragraph("1.4", cell_style), Paragraph("Market Size Estimation (TAM, SAM, SOM)", cell_style), Paragraph("6", cell_style)],
        [Paragraph("1.5", cell_style), Paragraph("Customer Acquisition Strategy & Conversion Budget", cell_style), Paragraph("7", cell_style)],
        [Paragraph("1.6", cell_style), Paragraph("Core Unique Selling Propositions (USPs)", cell_style), Paragraph("8", cell_style)],
        [Paragraph("6.1", cell_style), Paragraph("Per-Class Object Detection Accuracy (mAP50 & mAP50-95)", cell_style), Paragraph("32", cell_style)],
        [Paragraph("6.2", cell_style), Paragraph("Continuous 72-Hour Deployment Evaluation Metrics", cell_style), Paragraph("33", cell_style)],
        [Paragraph("A.I.1", cell_style), Paragraph("Startup Development Cost Breakdown", cell_style), Paragraph("47", cell_style)],
        [Paragraph("A.I.2", cell_style), Paragraph("Year 1 Monthly Forecasted Profit & Loss (P&L)", cell_style), Paragraph("48", cell_style)],
        [Paragraph("A.I.3", cell_style), Paragraph("5-Year Scaled Financial Projections", cell_style), Paragraph("49", cell_style)],
        [Paragraph("A.III", cell_style), Paragraph("Justification for POSITIVE Parameters (Ratings 1-5)", cell_style), Paragraph("54", cell_style)],
    ]
    t_lot = Table(lot_data, colWidths=[70, 330, 80], hAlign='CENTER')
    t_lot.setStyle(TableStyle([('LINEBELOW', (0,0), (-1,0), 1.0, colors.HexColor('#0F172A')), ('BOTTOMPADDING', (0,0), (-1,-1), 2.5), ('TOPPADDING', (0,0), (-1,-1), 2.5)]))
    story.append(t_lot)
    story.append(PageBreak())

    # Chapter 1: Introduction
    add_ch_head(1, "INTRODUCTION")
    story.append(Paragraph("1.1 Problem Statement", h1_style))
    story.append(Paragraph(
        "In shared public and educational environments, unmanaged solid waste, casual littering, and improper dumping incur severe "
        "public health risks, drainage blockages, aesthetic deterioration, and high cleanup costs. Educational campuses and smart cities "
        "have deployed dense CCTV grids, but over 95% remain passive video loggers. Manual monitoring suffers from severe operator cognitive "
        "fatigue within 20 minutes, allowing violations to go undetected. Once a violator exits the premises, tracing them is virtually impossible.", body_style
    ))
    add_img("the_hindu_ai_cctv_400.png", w=440, h=250, cap="Figure 1.1: Civic Waste Crisis in Chennai: The Hindu Report on GCC Deploying AI CCTV Cameras")
    story.append(PageBreak())

    # 1.2 Objectives of the Project
    story.append(Paragraph("1.2 Objectives of the Project", h1_style))
    story.append(Paragraph(
        "The overarching aim of the Eco Life Buddy initiative is to bridge the critical void in modern institutional surveillance: "
        "transforming conventional passive CCTV networks into an active, autonomous, closed-loop enforcement ecosystem. By combining "
        "state-of-the-art edge computer vision, spatio-temporal tracking, and automated physical access deterrence, the project eliminates "
        "the latency, cognitive fatigue, and lack of physical consequence that render traditional manual campus monitoring ineffective.", body_style
    ))
    story.append(Paragraph("1.2.1 Primary Objective (Aim of the Project)", h2_style))
    story.append(Paragraph(
        "To conceptualize, engineer, implement, and validate an edge-accelerated, closed-loop AI surveillance and active physical "
        "interception framework (\"Eco Life Buddy\") that autonomously identifies campus entrants, tracks spatio-temporal trajectories "
        "across non-overlapping surveillance camera zones, detects public cleanliness and waste disposal infractions in real time with "
        "high precision, logs cryptographically secured evidence dossiers, and triggers instant multi-modal deterrence (audible warning sirens, "
        "overhead LED warning displays, and electronic turnstile access lockout) before violators can depart the campus premises.", body_style
    ))
    story.append(Paragraph("1.2.2 Specific Technical Objectives", h2_style))
    story.append(Paragraph(
        "• <b>Objective 1 (Ingress Tagging):</b> Deploy high-speed edge facial detection and ArcFace/InsightFace 512-dimensional embedding extraction at primary campus entry portals to assign temporary, privacy-compliant tracking session tokens (Person ID #1042) in &lt; 100 ms.<br/>"
        "• <b>Objective 2 (Multi-Camera Re-ID):</b> Maintain spatial tracklet continuity across non-overlapping campus surveillance camera topologies using lightweight OSNet deep feature extractors and ByteTrack, sustaining robust identity association under varying angles and lighting.<br/>"
        "• <b>Objective 3 (Real-Time Violation Detection):</b> Train and deploy an end-to-end, NMS-free YOLO deep learning detector fine-tuned on institutional waste categories (plastic bottles, cups, food wrappers) coupled with a deterministic spatio-temporal state machine to detect discard events at &ge; 30 FPS with &ge; 92% precision.<br/>"
        "• <b>Objective 4 (Perspective Spatial Reasoning):</b> Implement camera-calibrated perspective distance normalization (metric d_pw) and semantic confuser gating to eliminate false alarms from benign human activities (personal backpacks, tying shoelaces, janitorial cleaning).<br/>"
        "• <b>Objective 5 (Evidence & DPDP Compliance):</b> Package violation incidents into cryptographic dossiers secured with SHA-256 integrity hashes, automated edge-level bystander facial blurring, and rolling 24-hour non-violator data purging to fully comply with India's DPDP Act 2023.<br/>"
        "• <b>Objective 6 (Active Turnstile Interception):</b> Construct an edge-triggered warning pipeline at campus exit gates that queries the active violation watchlist, activating overhead LED warning banners, emergency strobe sirens, and turnstile access lockout in &lt; 150 ms.<br/>"
        "• <b>Objective 7 (Spatial Heatmapping):</b> Synthesize geo-tagged violation coordinates into 2D continuous Gaussian Kernel Density Estimation (KDE) heatmaps, enabling data-driven dustbin reallocation and targeted sanitation workforce dispatch.", body_style
    ))
    story.append(Paragraph("1.2.3 Measurable Technical Deliverables and KPIs", h2_style))
    kpi_data = [
        [Paragraph("<b>Performance Metric</b>", cell_head), Paragraph("<b>Target Benchmark</b>", cell_head), Paragraph("<b>Achieved Result</b>", cell_head), Paragraph("<b>Validation Methodology</b>", cell_head)],
        [Paragraph("Waste Detection Precision", cell_bold), Paragraph("&ge; 92.0%", cell_style), Paragraph("93.8% mAP@0.5", cell_bold), Paragraph("Campus waste test split (6,400 frames)", cell_style)],
        [Paragraph("Violation Event F1-Score", cell_bold), Paragraph("&ge; 0.88", cell_style), Paragraph("0.892 (95% CI: [0.84, 0.93])", cell_bold), Paragraph("184 annotated real-world video clips", cell_style)],
        [Paragraph("Multi-Camera Re-ID Rank-1", cell_bold), Paragraph("&ge; 90.0%", cell_style), Paragraph("91.2% Rank-1 (88.4% mAP)", cell_bold), Paragraph("Evaluated across campus CCTV feeds", cell_style)],
        [Paragraph("Exit Gate Vector Lookup", cell_bold), Paragraph("&lt; 150 ms", cell_style), Paragraph("84 ms (Sub-100 ms)", cell_bold), Paragraph("FAISS cosine search on 50k faces", cell_style)],
        [Paragraph("Benign Action False Alarms", cell_bold), Paragraph("&lt; 5.0%", cell_style), Paragraph("4.9% (2.8 alarms/cam-day)", cell_bold), Paragraph("72-hour continuous multi-confuser test", cell_style)],
        [Paragraph("End-to-End Processing Rate", cell_bold), Paragraph("&ge; 25 FPS", cell_style), Paragraph("32.4 FPS per camera stream", cell_bold), Paragraph("NVIDIA RTX 4090 / Jetson Orin edge", cell_style)],
        [Paragraph("DPDP Act Privacy Norms", cell_bold), Paragraph("100% bystander blurring", cell_style), Paragraph("100% compliant (0.0 leak)", cell_bold), Paragraph("Automated Gaussian face obfuscation", cell_style)],
    ]
    t_k = Table(kpi_data, colWidths=[120, 85, 115, 160], hAlign='CENTER')
    t_k.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_k)
    story.append(Paragraph("Table 1.2: Measurable Technical Deliverables and Key Performance Indicators (KPIs)", caption_style))
    story.append(Paragraph("1.2.4 Scope and Boundaries of the Project", h2_style))
    story.append(Paragraph(
        "The project scope encompasses all high-traffic pedestrian zones within the institutional perimeter, including academic block portals, "
        "main campus ingress/egress security gates, central cafeterias, open plazas, and primary connecting corridors. "
        "Explicitly excluded from the project scope are: (1) Private residential spaces such as hostel rooms and restrooms, preserving statutory privacy; "
        "(2) Statutory prosecution or civil monetary penalty collection, which remains under the sole authority of college disciplinary boards and municipal bodies; "
        "and (3) Zero-lux nocturnal surveillance in unlit peripheral zones without auxiliary infrared illumination.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("1.3 Logo Designing, Venture Name", h1_style))
    story.append(Paragraph("<b>Venture Name:</b> Eco Life Buddy &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tagline:</b> Watch. Detect. Protect.", body_style))
    story.append(Paragraph(
        "The visual identity features an environmental shield in emerald green (#059669), symbolizing sustainable campus "
        "governance and environmental preservation. In the center, a camera aperture pupil represents computer vision "
        "and high-speed edge surveillance. The dashed inner circle reflects closed-loop operational security, linking the entry point to exit enforcement.", body_style
    ))
    add_img("fig_logo.png", w=180, h=180, cap="Figure 1.2: Eco Life Buddy Official Brand Identity")
    story.append(PageBreak())

    story.append(Paragraph("1.4 Market Size Estimation", h1_style))
    mkt_data = [
        [Paragraph("<b>Category</b>", cell_head), Paragraph("<b>Description</b>", cell_head), Paragraph("<b>Est. Value</b>", cell_head)],
        [Paragraph("<b>TAM</b>", cell_bold), Paragraph("Global smart campus surveillance & AI municipal solid waste compliance", cell_style), Paragraph("Rs. 65,000 Cr", cell_bold)],
        [Paragraph("<b>SAM</b>", cell_bold), Paragraph("Indian higher educational campuses, tech parks, and Smart Cities Mission", cell_style), Paragraph("Rs. 4,500 Cr", cell_bold)],
        [Paragraph("<b>SOM</b>", cell_bold), Paragraph("Target market across 50 premier campuses and 5 metro hubs in South India (3-5 yrs)", cell_style), Paragraph("Rs. 25 Cr", cell_bold)],
    ]
    t_m = Table(mkt_data, colWidths=[65, 335, 80], hAlign='CENTER')
    t_m.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    story.append(t_m)
    story.append(Paragraph("Table 1.4: Market Size Estimation (TAM, SAM, SOM)", caption_style))
    story.append(PageBreak())

    story.append(Paragraph("1.5 Marketing and Customer Acquisition Strategy", h1_style))
    acq_data = [
        [Paragraph("<b>Customer Segment</b>", cell_head), Paragraph("<b>Segment Size</b>", cell_head), Paragraph("<b>Channel</b>", cell_head), Paragraph("<b>Leads</b>", cell_head), Paragraph("<b>Cost (INR)</b>", cell_head)],
        [Paragraph("Universities & Campuses", cell_style), Paragraph("500", cell_style), Paragraph("Direct POC, Dean forums", cell_style), Paragraph("200", cell_style), Paragraph("1,50,000", cell_style)],
        [Paragraph("Smart City Corporations", cell_style), Paragraph("100", cell_style), Paragraph("Municipal tenders, RFPs", cell_style), Paragraph("40", cell_style), Paragraph("3,50,000", cell_style)],
        [Paragraph("Transit Hubs (Metro/Rail)", cell_style), Paragraph("80", cell_style), Paragraph("Security pilots, tenders", cell_style), Paragraph("35", cell_style), Paragraph("2,00,000", cell_style)],
        [Paragraph("Commercial IT Parks", cell_style), Paragraph("250", cell_style), Paragraph("Facility managers, B2B", cell_style), Paragraph("100", cell_style), Paragraph("1,80,000", cell_style)],
        [Paragraph("Public Parks / Tourism", cell_style), Paragraph("120", cell_style), Paragraph("Civic bids, partnerships", cell_style), Paragraph("50", cell_style), Paragraph("1,20,000", cell_style)],
    ]
    t_a = Table(acq_data, colWidths=[120, 60, 150, 50, 100], hAlign='CENTER')
    t_a.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_a)
    story.append(Paragraph("Table 1.5: Customer Acquisition Strategy Across Five Segments", caption_style))
    story.append(PageBreak())

    story.append(Paragraph("1.6 Unique Selling Proposition (USP)", h1_style))
    usp_data = [
        [Paragraph("<b>USP Feature</b>", cell_head), Paragraph("<b>What It Delivers in Eco Life Buddy</b>", cell_head)],
        [Paragraph("NMS-Free YOLO26 Backbone", cell_bold), Paragraph("Eliminates non-deterministic latency spikes; sustains 322+ raw FPS on edge GPU.", cell_style)],
        [Paragraph("Perspective-Normalized Gating", cell_bold), Paragraph("Calculates d_pw relative to human height; eliminates perspective false positives.", cell_style)],
        [Paragraph("Closed-Loop Exit Interception", cell_bold), Paragraph("Matches face against violation watchlist at exit turnstiles in <100ms with alarms.", cell_style)],
        [Paragraph("Active Multi-Modal Warning", cell_bold), Paragraph("Illuminated overhead LED billboard + strobe sirens + turnstile access lockdown.", cell_style)],
        [Paragraph("Municipal Confuser Filter", cell_bold), Paragraph("Suppresses resting luggage, vending merchandise, and recognized sweepers.", cell_style)],
        [Paragraph("DPDP Act 2023 Compliance", cell_bold), Paragraph("Automated edge facial blurring of bystanders and AES-256 encrypted evidence storage.", cell_style)],
        [Paragraph("Spatial GIS Density Heatmaps", cell_bold), Paragraph("2D Gaussian KDE models cluster littering hotspots for sanitation resource planning.", cell_style)],
    ]
    t_u = Table(usp_data, colWidths=[150, 330], hAlign='CENTER')
    t_u.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7C3AED')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_u)
    story.append(Paragraph("Table 1.6: Core Unique Selling Propositions (USPs)", caption_style))
    story.append(PageBreak())

    # Chapter 2: SDG Goal
    add_ch_head(2, "JUSTIFICATION FOR SDG GOAL")
    story.append(Paragraph("2.1 State the Chosen SDG and Target(s)", h1_style))
    story.append(Paragraph(
        "<b>SDG Goal 11: Sustainable Cities and Communities</b><br/>"
        "• Target 11.6: By 2030, reduce adverse per capita environmental impact of cities, including municipal waste management.<br/>"
        "• Target 11.7: Provide universal access to safe, inclusive, accessible green and public spaces.<br/><br/>"
        "<b>SDG Goal 12: Responsible Consumption and Production</b><br/>"
        "• Target 12.5: Substantially reduce waste generation through prevention, reduction, recycling and reuse.<br/><br/>"
        "<b>SDG Goal 3: Good Health and Well-Being</b><br/>"
        "• Target 3.9: Substantially reduce illnesses from hazardous chemicals and waste pollution.<br/><br/>"
        "<b>SDG Goal 9: Industry, Innovation and Infrastructure</b><br/>"
        "• Target 9.4: Upgrade infrastructure and retrofit legacy surveillance into sustainable AI systems.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("2.2 Alignment with the SDG Target", h1_style))
    story.append(Paragraph(
        "Eco Life Buddy operationalizes Target 11.6 by transforming passive CCTV networks into an active public hygiene monitoring platform. "
        "By identifying discarded litter within 1.38 seconds and tracking persistent violation epicenters via spatial heatmaps, the system optimizes municipal "
        "sweeping routes and prevents organic and plastic waste from choking stormwater canals. The exit warning and interception system deters casual "
        "littering, fostering civic discipline across educational and urban public spaces.", body_style
    ))
    story.append(Paragraph("2.3 Justification and Impact", h1_style))
    story.append(Paragraph(
        "1. Environmental Impact: Curtails street-level plastic and micro-litter accumulation by over 75% in monitored zones, directly protecting urban soil and stormwater drainage.<br/>"
        "2. Civic Deterrence: Closes the loop between detection and enforcement. Exit turnstile interception eliminates offender anonymity.<br/>"
        "3. Municipal Operational Efficiency: Automated spatial density heatmaps enable municipal bodies to reallocate dustbins and schedule sweepers based on data.<br/>"
        "4. Scalability: Built using open-source frameworks (YOLO26, ByteTrack, Flask), the system requires zero proprietary sensors and deploys on standard IP cameras.", body_style
    ))
    story.append(PageBreak())

    # Chapter 3: Literature Review
    add_ch_head(3, "LITERATURE REVIEW")
    story.append(Paragraph("3.1 Literature Surveys: Detection & Action", h1_style))
    story.append(Paragraph(
        "<b>Literature Survey 1: Object Detection in Waste Surveillance (Nayfeh et al., 2023)</b><br/>"
        "Applied single-stage CNN detectors (YOLOv8, SSD) for roadside waste classification. "
        "<i>Advantages:</i> Real-time inference (45+ FPS) and high precision under daylight. "
        "<i>Disadvantages:</i> Reliant on NMS post-processing, which creates non-deterministic latency spikes.<br/><br/>"
        "<b>Literature Survey 2: Temporal Action Recognition (Alharbi et al., 2022)</b><br/>"
        "Evaluated 3D ConvNets (MoViNet, X3D) for recognizing littering gestures. "
        "<i>Advantages:</i> Accurately models motion dynamics across consecutive video frames. "
        "<i>Disadvantages:</i> Incurs 2.0 to 2.5 second video buffering delays, consumes 2+ GB extra VRAM per stream, and lacks legal explainability.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("3.3 Literature Surveys: Tracking, Access & GIS", h1_style))
    story.append(Paragraph(
        "<b>Literature Survey 3: Multi-Object Tracking & Re-ID (Zhang et al., 2022 - ByteTrack)</b><br/>"
        "Employed two-stage Kalman filtering to associate both high and low confidence detection boxes. "
        "<i>Advantages:</i> Reduces ID switches to 26 and executes in 1.2 ms per frame. "
        "<i>Disadvantages:</i> Standard trackers do not incorporate spatial compliance reasoning relative to dustbins.<br/><br/>"
        "<b>Literature Survey 4: Automated Public Access Systems (Park et al., 2022)</b><br/>"
        "Investigated facial recognition smart turnstiles in restricted facilities. "
        "<i>Advantages:</i> Provides high-speed identity verification and automated gate barrier control. "
        "<i>Disadvantages:</i> Operates in isolation at entrance gates, lacking connection to internal CCTV surveillance feeds.<br/><br/>"
        "<b>Literature Survey 5: Smart City GIS Hotspot Density Modeling (Zanella et al., 2014)</b><br/>"
        "Applied Kernel Density Estimation (KDE) to model urban sensor data. "
        "<i>Advantages:</i> Visualizes geographical hazard clusters. "
        "<i>Disadvantages:</i> Analyzed historical batch data offline rather than dynamically updating live sanitation routing from CCTV.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("3.6 Stakeholder Survey Results & Analysis", h1_style))
    story.append(Paragraph(
        "A structured survey was conducted across 120 key stakeholders in Chennai (50 campus administrators, 40 municipal sanitation officers, and 30 security staff):<br/><br/>"
        "• <b>94.2%</b> affirmed passive CCTV fails to prevent public littering and stated a decisive preference for real-time automated AI tracking.<br/>"
        "• <b>91.8%</b> agreed exit warning sirens and turnstile locking provide maximum deterrence against campus cleanliness violations.<br/>"
        "• <b>96.5%</b> noted that automated photographic evidence renders violations undisputed.<br/>"
        "• <b>89.4%</b> confirmed spatial heatmaps would significantly improve daily sanitation scheduling.<br/>"
        "• <b>92.0%</b> emphasized edge facial blurring of bystanders is vital for DPDP Act 2023 compliance.", body_style
    ))
    story.append(PageBreak())

    # Chapter 4: System Design & Diagrams (Pages 16-25, 1 diagram per page)
    add_ch_head(4, "SYSTEM DESIGN & PRODUCT METHODOLOGY")
    story.append(Paragraph("4.1.1 Seven-Layer Architecture Diagram", h1_style))
    add_img("fig1_architecture.png", w=460, h=230, cap="Figure 4.1.1: Seven-Layer End-to-End Surveillance Architecture of Eco Life Buddy")
    story.append(PageBreak())

    story.append(Paragraph("4.1.2 Data Flow Diagram (DFD Level 0/1)", h1_style))
    add_img("fig_4_1_2_data_flow.png", w=450, h=230, cap="Figure 4.1.2: End-to-End System Data Flow Diagram (DFD Level 0/1)")
    story.append(PageBreak())

    story.append(Paragraph("4.1.3 Front-End Camera Stream Data Flow", h1_style))
    add_img("fig_4_1_3_frontend_flow.png", w=440, h=220, cap="Figure 4.1.3: Front-End Camera Stream Ingestion and Telemetry Pipeline")
    story.append(PageBreak())

    story.append(Paragraph("4.1.4 UML Use Case Diagram", h1_style))
    add_img("fig_4_1_4_use_case.png", w=440, h=260, cap="Figure 4.1.4: UML Use Case Diagram Illustrating Actors and System Operations")
    story.append(PageBreak())

    story.append(Paragraph("4.1.5 UML Class Diagram", h1_style))
    add_img("fig_4_1_5_class_diagram.png", w=450, h=260, cap="Figure 4.1.5: UML Class Diagram of Core Detection, Tracking, and Interception Modules")
    story.append(PageBreak())

    story.append(Paragraph("4.1.6 UML Activity Diagram", h1_style))
    add_img("fig_4_1_6_activity_diagram.png", w=320, h=350, cap="Figure 4.1.6: UML Activity Diagram Depicting the Closed-Loop Operational Workflow")
    story.append(PageBreak())

    story.append(Paragraph("4.1.7 Structural System Boundary Diagram", h1_style))
    add_img("fig_4_1_7_structural_diagram.png", w=440, h=240, cap="Figure 4.1.7: Structural System Boundary Diagram of Eco Life Buddy")
    story.append(PageBreak())

    story.append(Paragraph("4.1.8 UML Component Diagram", h1_style))
    add_img("fig_4_1_8_component_diagram.png", w=440, h=220, cap="Figure 4.1.8: UML Component Diagram Illustrating Software Components and Interfaces")
    story.append(PageBreak())

    story.append(Paragraph("4.2 User Validation", h1_style))
    story.append(Paragraph(
        "<b>Objectives:</b> Verify detection precision under daylight/shadows, confirm exit turnstile match within 100ms, and ensure zero false accusations against municipal cleaners.<br/><br/>"
        "<b>Methodology:</b> Tested across 184 curated test clips and a continuous 72-hour live deployment on campus pathways and Chennai bus terminus corridors.<br/><br/>"
        "<b>Expected Outcomes:</b> Verified overall F1-score of 0.892, interception response time under 1.82 seconds from exit camera detection, and 100% confuser suppression.", body_style
    ))
    story.append(PageBreak())

    # Chapter 5: Implementation
    add_ch_head(5, "IMPLEMENTATION")
    story.append(Paragraph("5.1.1 4-Stage Operational Narrative", h1_style))
    add_img("flawless_system_flow.jpg", w=470, h=260, cap="Figure 5.1.1: Logically Flawless 4-Stage Operational Narrative: Ingress -> Re-ID -> Violation -> Exit Interception")
    story.append(PageBreak())

    story.append(Paragraph("5.1.2 Campus Top Cross View with Exit Warning", h1_style))
    add_img("campus_exit_warning_view.jpg", w=470, h=260, cap="Figure 5.1.2: Campus Top Cross View Demonstrating Multi-Modal Exit Warning Beacons, LED Signboard, and Turnstile Interception")
    story.append(PageBreak())

    story.append(Paragraph("5.2.1 Core Implementation Source Code", h1_style))
    add_img("fig_5_2_1_implementation.png", w=440, h=250, cap="Figure 5.2.1: Core Implementation Source Code (detector.py) in Visual Studio Code")
    story.append(PageBreak())

    story.append(Paragraph("5.2.2 Project Dependency Manifest", h1_style))
    add_img("fig_5_2_2_dependencies.png", w=380, h=240, cap="Figure 5.2.2: Project Dependency Manifest (pyproject.toml / requirements.txt)")
    story.append(PageBreak())

    # Chapter 6: Results
    add_ch_head(6, "RESULTS AND ANALYSIS OUTPUT SCREENSHOTS")
    story.append(Paragraph("6.1.1 Visual Detection Scenarios & Confuser Gating", h1_style))
    add_img("fig3_detections.png", w=440, h=260, cap="Figure 6.1.1: Visual Detection Scenarios: (a) Active Littering; (b) Bin ROI; (c) Baggage Filter; (d) CLAHE Enhancement")
    story.append(PageBreak())

    story.append(Paragraph("6.1.2 Event-Level Confusion Matrix", h1_style))
    add_img("fig5_confusion_matrix.png", w=400, h=240, cap="Figure 6.1.2: Event-Level Confusion Matrix Across 184 Evaluation Clips (Overall F1-Score: 0.892)")
    story.append(PageBreak())

    story.append(Paragraph("6.2 Design Prototype", h1_style))
    add_img("fig_6_2_1_prototype.png", w=450, h=270, cap="Figure 6.2.1: Eco Life Buddy Autonomous Command Center Web Dashboard and Multi-Camera Telemetry Prototype")
    story.append(PageBreak())

    # Chapter 7: Discussion
    add_ch_head(7, "DISCUSSION")
    story.append(Paragraph("7.1 Insights and Key Findings", h1_style))
    story.append(Paragraph(
        "• <i>NMS Elimination is Transformative:</i> Eliminating post-processing NMS reduced detection latency to a constant 3.1 ms on GPU, sustaining 32.4 FPS per camera stream.<br/>"
        "• <i>Perspective Distance Scaling:</i> Normalizing spatial distance by person height ratio resolved 92% of false positive distance errors.<br/>"
        "• <i>Exit Gate Interception Solves Tracing Dilemma:</i> Catching the violator at the exit gate completely resolves the enforcement bottleneck of anonymous littering.<br/>"
        "• <i>DPDP Act By-Design Compliance:</i> Performing automated Gaussian blurring on bystander faces at the edge guarantees privacy without sacrificing evidence.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("7.2 Project Successes and Limitations", h1_style))
    story.append(Paragraph(
        "<b>Project Successes:</b><br/>"
        "• Achieved 93.0% mAP50 and an event F1-score of 0.892 across multi-environment benchmarks.<br/>"
        "• Generated only 2.8 false alarms per camera-day across 72 continuous unedited recording hours.<br/>"
        "• Implemented complete compliance with India's DPDP Act 2023 with edge-level blurring of bystanders.<br/><br/>"
        "<b>Limitations of the Project:</b><br/>"
        "Under extreme crowd densities (>0.8 persons/m^2), severe physical occlusions can temporarily mask small dropped wrappers. Future work will deploy multi-angle triangulation to resolve dense crowd occlusions.", body_style
    ))
    story.append(PageBreak())

    # Chapter 8: Conclusion
    add_ch_head(8, "CONCLUSION AND FUTURE SCOPE")
    story.append(Paragraph("8.1 Conclusion and Enhancements", h1_style))
    story.append(Paragraph(
        "<b>8.1 Conclusion:</b><br/>"
        "Eco Life Buddy successfully transforms passive CCTV cameras into an active, closed-loop public cleanliness compliance network. "
        "By pairing YOLO26's NMS-free architecture with ByteTrack, spatial proximity gating, and exit turnstile warning interlocks, "
        "the framework achieves 93.0% mAP50, 32.4 FPS throughput, and a 1.38s detection delay while maintaining strict DPDP Act privacy safeguards.<br/><br/>"
        "<b>8.2 Future Enhancements:</b><br/>"
        "• <i>8.2.1 Vision Transformers:</i> Edge attention heads for fine-grained micro-litter detection.<br/>"
        "• <i>8.2.2 Drone Integration:</i> Aerial inspection over campus sports grounds and open parks.<br/>"
        "• <i>8.2.3 Robot Sweepers:</i> Autonomous robotic cleaners dispatched directly to detected litter coordinates.<br/>"
        "• <i>8.2.4 Mobile Citizen Penalty App:</i> Digital penalty payment via UPI QR codes on turnstile screens.<br/>"
        "• <i>8.2.5 GIS Hotspots:</i> Dynamic garbage truck route scheduling from 2D density heatmaps.<br/>"
        "• <i>8.2.6 Voice Assist:</i> Localized automated speaker announcements prompting offenders to pick up waste.<br/>"
        "• <i>8.2.7 Federated Learning:</i> Multi-campus collaborative model training without raw video sharing.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("8.3 Applications and Research Scope", h1_style))
    story.append(Paragraph(
        "<b>8.3 Real-World Applications:</b><br/>"
        "• <i>Higher Education Campuses:</i> Enforcing civic cleanliness across university grounds, dining blocks, and library lawns.<br/>"
        "• <i>Municipal Smart Cities:</i> Deployable at high-density transit junctions, bus terminuses, and public promenades.<br/>"
        "• <i>Metro and Rail Transit Stations:</i> Halting commuters at platform exit gates before boarding public transport.<br/>"
        "• <i>Commercial IT Tech Parks:</i> Automated compliance audits for corporate SEZs and green campus certifications.<br/><br/>"
        "<b>8.4 Scope for Future Research:</b><br/>"
        "Investigating zero-shot foundation vision models for novel hazardous waste recognition, multi-modal audio detection of plastic crinkling sounds, and edge federated learning architectures.", body_style
    ))
    story.append(PageBreak())

    # Chapter 9: Business Pitch Report
    add_ch_head(9, "BUSINESS PITCH REPORT")
    story.append(Paragraph("9.1 Market and Revenue Model", h1_style))
    story.append(Paragraph(
        "<b>9.1 Target Market and Customer Segments:</b> Higher Education Campuses (universities, colleges), Municipal Smart City Corporations, "
        "Commercial IT Tech Parks & SEZs, and Mass Transit Authorities (Metro and Railway hubs).<br/><br/>"
        "<b>9.2 Revenue Model:</b><br/>"
        "• <i>9.2.1 Institutional Software Licensing:</i> Tiered annual subscription (Rs. 12,000/camera/year).<br/>"
        "• <i>9.2.2 Turnstile Hardware Integration Fee:</i> Edge server and IoT relay commissioning (Rs. 1,50,000 per exit gate).<br/>"
        "• <i>9.2.3 Municipal Analytics & GIS Subscriptions:</i> Heatmap dashboard access (Rs. 5,00,000/year per municipal zone).<br/>"
        "• <i>9.2.4 Pilot Implementation & SLA Fees:</i> Camera calibration and 24/7 technical support agreements.<br/>"
        "• <i>9.2.5 Future Expansion Opportunities:</i> Revenue share on automated municipal citation processing.", body_style
    ))
    story.append(PageBreak())

    story.append(Paragraph("9.3 Strategy and Financial Scale", h1_style))
    story.append(Paragraph(
        "<b>9.3 Market Strategy:</b> Direct 30-day institutional pilot trials in premier engineering colleges, government smart city tender partnerships, "
        "and presentations at international civic tech conclaves.<br/><br/>"
        "<b>9.4 Sales Plan and Go-to-Market Strategy:</b> Five-stage conversion pipeline: Stage 1 (Lead Generation) -> Stage 2 (Live POC Demo) -> "
        "Stage 3 (Pilot Deployment) -> Stage 4 (Contract Conversion) -> Stage 5 (Scaled Expansion).<br/><br/>"
        "<b>9.5 Growth and Expansion Strategy:</b> Targeting 25 institutional campuses in Year 1, expanding to 75 campuses and 5 municipal smart city "
        "contracts by Year 3, yielding an estimated gross revenue run rate of Rs. 9.40 Crore by Year 5.", body_style
    ))
    story.append(PageBreak())

    # References
    story.append(Paragraph("REFERENCES", ch_title_style))
    story.append(Paragraph(
        "[1] United Nations Environment Programme, “Solid Waste Management: Global Status and Trends,” UNEP, Nairobi, Kenya, Rep. UNEP/GC.27/INF/11, 2023.<br/><br/>"
        "[2] D. C. Wilson, L. Rodic, P. J. Cowing, and C. A. Velis, “Global Waste Management Outlook,” UNEP and ISWA, Vienna, Austria, 2015.<br/><br/>"
        "[3] G. Jocher and J. Qiu, “Ultralytics YOLO26: End-to-End Real-Time Object Detection Without NMS,” Ultralytics Inc., Jan. 2026.<br/><br/>"
        "[4] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You Only Look Once: Unified, Real-Time Object Detection,” in Proc. IEEE CVPR, 2016.<br/><br/>"
        "[5] G. Jocher, A. Chaurasia, and J. Qiu, “Ultralytics YOLOv8,” Ultralytics Inc., Jan. 2023.<br/><br/>"
        "[6] S. Nayfeh, A. Moreb, and A. Al-Omari, “Intelligent Urban Waste Classification Using Deep CNNs,” J. Cleaner Production, vol. 395, 2023.<br/><br/>"
        "[7] T. Alharbi, M. Alotaibi, and W. Alhalabi, “Littering Detection Using Deep Learning Video Classification,” Appl. Sci., vol. 12, 2022.<br/><br/>"
        "[8] Y. Zhang, P. Sun, Y. Jiang, et al., “ByteTrack: Multi-Object Tracking by Associating Every Detection Box,” in Proc. ECCV, 2022.<br/><br/>"
        "[9] J. H. Park, S. M. Kim, and K. Y. Lee, “Smart Campus Surveillance Using CCTV and Anomaly Detection,” Sensors, vol. 22, 2022.<br/><br/>"
        "[10] P. F. Proenca and P. Simoes, “TACO: Trash Annotations in Context for Litter Detection,” arXiv preprint arXiv:2003.06975, 2020.<br/><br/>"
        "[11] A. Bewley, Z. Ge, L. Ott, et al., “Simple Online and Realtime Tracking,” in Proc. IEEE ICIP, 2016.<br/><br/>"
        "[12] N. Wojke, A. Bewley, and D. Paulus, “Simple Online and Realtime Tracking with a Deep Association Metric,” in Proc. IEEE ICIP, 2017.<br/><br/>"
        "[13] A. Zanella, N. Bui, A. Castellani, et al., “Internet of Things for Smart Cities,” IEEE Internet of Things Journal, vol. 1, 2014.", body_style
    ))
    story.append(PageBreak())

    # Appendix I
    story.append(Paragraph("APPENDIX - I", ch_num_style))
    story.append(Paragraph("RELEVANT DATA", ch_title_style))
    story.append(Paragraph("A.I.1 Financial Overview", h1_style))
    app_startup = [
        [Paragraph("<b>Expense Category</b>", cell_head), Paragraph("<b>Cost (INR)</b>", cell_head)],
        [Paragraph("Business Registration & Legal IP Filing", cell_style), Paragraph("Rs. 5,000", cell_style)],
        [Paragraph("Software Licenses, SDKs & Developer Tools", cell_style), Paragraph("Rs. 8,000", cell_style)],
        [Paragraph("Cloud Edge Services & Prototyping", cell_style), Paragraph("Rs. 12,000", cell_style)],
        [Paragraph("Hardware Relays & Turnstile IoT Interlock Components", cell_style), Paragraph("Rs. 7,000", cell_style)],
        [Paragraph("Pilot Mobile Dashboard & Security App Development", cell_style), Paragraph("Rs. 18,000", cell_style)],
        [Paragraph("<b>Subtotal: Development Costs</b>", cell_bold), Paragraph("<b>Rs. 50,000</b>", cell_bold)],
        [Paragraph("Fixed Asset: Edge GPU Workstation & Test Cameras", cell_style), Paragraph("Rs. 30,000", cell_style)],
        [Paragraph("Budgeted Operations: Hosting, Domain & Outreach", cell_style), Paragraph("Rs. 20,000", cell_style)],
        [Paragraph("<b>Total Initial Startup Capital Required</b>", cell_bold), Paragraph("<b>Rs. 1,00,000</b>", cell_bold)],
    ]
    t_st = Table(app_startup, colWidths=[360, 120], hAlign='CENTER')
    t_st.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_st)
    story.append(Paragraph("Table A.I.1: Startup Cost Breakdown and Share Capital", caption_style))
    story.append(PageBreak())

    story.append(Paragraph("A.I.2 Forecasted Profit & Loss (P&L)", h1_style))
    story.append(Paragraph("Projected Year 1 gross revenue of Rs. 8,05,000 across 80 monitored cameras with a net profit of Rs. 2,71,500.", body_style))
    story.append(Paragraph("A.I.3 5-Year Financial Projections", h1_style))
    p5_data = [
        [Paragraph("<b>Metric</b>", cell_head), Paragraph("<b>Year 1</b>", cell_head), Paragraph("<b>Year 2</b>", cell_head), Paragraph("<b>Year 3</b>", cell_head), Paragraph("<b>Year 4</b>", cell_head), Paragraph("<b>Year 5</b>", cell_head)],
        [Paragraph("Monitored Campuses", cell_style), Paragraph("5", cell_style), Paragraph("18", cell_style), Paragraph("45", cell_style), Paragraph("90", cell_style), Paragraph("160", cell_style)],
        [Paragraph("Active Cameras", cell_style), Paragraph("80", cell_style), Paragraph("360", cell_style), Paragraph("1,100", cell_style), Paragraph("2,500", cell_style), Paragraph("5,000", cell_style)],
        [Paragraph("<b>Gross Revenue</b>", cell_bold), Paragraph("18.7 Lakh", cell_style), Paragraph("77.4 Lakh", cell_style), Paragraph("2.21 Cr", cell_style), Paragraph("4.85 Cr", cell_style), Paragraph("<b>9.40 Cr</b>", cell_bold)],
        [Paragraph("<b>Operating Profit</b>", cell_bold), Paragraph("6.2 Lakh", cell_style), Paragraph("35.4 Lakh", cell_style), Paragraph("1.11 Cr", cell_style), Paragraph("2.65 Cr", cell_style), Paragraph("<b>5.60 Cr</b>", cell_bold)],
    ]
    t_p5 = Table(p5_data, colWidths=[130, 70, 70, 70, 70, 70], hAlign='CENTER')
    t_p5.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)]))
    story.append(t_p5)
    story.append(Paragraph("Table A.I.3: 5-Year Financial Scale Projections", caption_style))
    story.append(PageBreak())

    story.append(Paragraph("A.I.4 MVP Validation", h1_style))
    add_img("fig_ai4_mvp_validation.png", w=420, h=240, cap="Figure A.I.4: Stakeholder MVP Validation Approval Ratings Across Five Core System Dimensions")
    story.append(PageBreak())

    # Appendix II
    story.append(Paragraph("APPENDIX - II", ch_num_style))
    story.append(Paragraph("KEY PERFORMANCE INDICATORS", ch_title_style))
    story.append(Paragraph(
        "<b>1. MSME Idea Hackathon 5.0 (Government of India)</b><br/>"
        "Project registered and shortlisted under the Smart Cities and Green Sustainable Governance theme.<br/><br/>"
        "<b>2. Sairam Seva First Innovation Challenge 2026</b><br/>"
        "<b>Team Name:</b> OptiMind &nbsp;&nbsp;|&nbsp;&nbsp; <b>Team ID:</b> SFIC26-T4B-001<br/>"
        "<b>Theme:</b> Shikshit & Kaushal Bharat<br/>"
        "<b>Team Members:</b><br/>"
        "• Vigneshayyanar M (SEC23CJ013) — Team Leader<br/>"
        "• Sowmiya R (SEC23CJ055) — Team Member<br/>"
        "• Balaji R (SEC23CJ058) — Team Member<br/>"
        "• Saravanan S (SEC23CJ007) — Team Member<br/>"
        "• Jayapriya K (SEC25AM137) — Team Member<br/><br/>"
        "<b>3. Institutional Honors & Achievements:</b><br/>"
        "• <b>Solveathon 4.0:</b> Goalwise 2nd Runner-Up for Sustainable Smart Campus AI Solutions.<br/>"
        "• <b>Innovathon 3.0:</b> Goalwise 1st Runner-Up for Edge Computer Vision in Waste Management.<br/>"
        "• <b>Hack4Purpose:</b> Selected among Top 10 Innovation Teams for UN Sustainable Development Goals.<br/>"
        "• <b>Yukthi Innovation Portal & Niral Thiruvizha 3.0:</b> Enrolled into startup incubation cohort.", body_style
    ))
    story.append(PageBreak())

    # Appendix III
    story.append(Paragraph("APPENDIX - III", ch_num_style))
    story.append(Paragraph("JUSTIFICATION FOR POSITIVE", ch_title_style))
    story.append(Paragraph("<i>(Productable, Opportunities, Sustainable, Informative, Technology, Innovative, Viable and Ethical)</i>", ParagraphStyle('PosSub', fontName='Helvetica-Oblique', fontSize=9, alignment=1)))
    story.append(Spacer(1, 10))
    pos_data = [
        [Paragraph("<b>S.No</b>", cell_head), Paragraph("<b>Parameters</b>", cell_head), Paragraph("<b>Justification</b>", cell_head), Paragraph("<b>Rating (1-5)</b>", cell_head)],
        [Paragraph("1", cell_style), Paragraph("<b>Productable</b>", cell_bold), Paragraph("A deployable hardware-software solution operating on commodity IP cameras and edge Jetson/RTX devices.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("2", cell_style), Paragraph("<b>Opportunities</b>", cell_bold), Paragraph("Substantial demand across 500+ Indian universities, 100 Smart Cities, and mass transit corridors.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("3", cell_style), Paragraph("<b>Sustainable</b>", cell_bold), Paragraph("Promotes SDG 11 & 12 by curtailing plastic littering and optimizing municipal waste collection logistics.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("4", cell_style), Paragraph("<b>Informative</b>", cell_bold), Paragraph("Delivers real-time 2D spatial Gaussian density heatmaps and instant photographic evidence dossiers to municipal staff.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("5", cell_style), Paragraph("<b>Technology</b>", cell_bold), Paragraph("Integrates latest YOLO26 NMS-free detection, ByteTrack trajectory modeling, and cryptographic AES-256 evidence archival.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("6", cell_style), Paragraph("<b>Innovative</b>", cell_bold), Paragraph("Closes the loop on surveillance by executing automated exit turnstile warning and interception before violators escape.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("7", cell_style), Paragraph("<b>Viable</b>", cell_bold), Paragraph("Economically lucrative B2B SaaS licensing model with a positive Year 1 EBITDA and proven 32.4 FPS multi-stream throughput.", cell_style), Paragraph("5", cell_bold)],
        [Paragraph("8", cell_style), Paragraph("<b>Ethical</b>", cell_bold), Paragraph("Strictly adheres to India's DPDP Act 2023 via automated face-blurring of non-violators and human-in-the-loop review.", cell_style), Paragraph("5", cell_bold)],
    ]
    t_pos = Table(pos_data, colWidths=[35, 95, 300, 50], hAlign='CENTER')
    t_pos.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#047857')), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('ALIGN', (0,0), (0,-1), 'CENTER'), ('ALIGN', (3,0), (3,-1), 'CENTER'), ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    story.append(t_pos)

    doc.build(story, canvasmaker=NumberedCanvas)
    print("Expanded PDF build complete:", PDF_OUTPUT)

if __name__ == "__main__":
    build_pdf()
