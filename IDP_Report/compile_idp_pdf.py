"""
compile_idp_pdf.py
Compiles the complete, official IDP-I Project Report into a high-quality PDF:
IDP_EcoLifeBuddy_Report.pdf
Matching the exact layout, structure, and appendices of IDP_20261015_182809_0000.pdf
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

PDF_OUTPUT = r"c:\LIL\IDP_Report\IDP_EcoLifeBuddy_Report.pdf"
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
            # Header
            self.drawString(54, 800, "Eco Life Buddy: AI-Based Cleanliness & Violation Interception")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 792, 540, 792)
            
            # Footer
            self.line(54, 45, 540, 45)
            self.drawString(54, 32, "Innovative Design Project-I | Department of M.Tech CSE | Sri Sairam Engineering College")
            self.drawRightString(540, 32, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()

def build_pdf():
    doc = SimpleDocTemplate(
        PDF_OUTPUT,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1,
        textColor=colors.HexColor('#0F172A')
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor('#047857')
    )

    chapter_style = ParagraphStyle(
        'ChapterHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        alignment=1,
        spaceAfter=14,
        textColor=colors.HexColor('#0F172A')
    )

    h1_style = ParagraphStyle(
        'Heading1Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor('#1E3A8A')
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        spaceBefore=8,
        spaceAfter=4,
        textColor=colors.HexColor('#0F172A')
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        alignment=4,
        spaceAfter=6,
        textColor=colors.HexColor('#1E293B')
    )

    caption_style = ParagraphStyle(
        'CaptionCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,
        spaceBefore=4,
        spaceAfter=10,
        textColor=colors.HexColor('#334155')
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#0F172A')
    )

    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0F172A')
    )

    cell_head = ParagraphStyle(
        'TableHead',
        parent=cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=1
    )

    story = []

    # =========================================================================
    # 1. COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("SRI SAIRAM ENGINEERING COLLEGE", ParagraphStyle('InstHead', fontName='Helvetica-Bold', fontSize=15, alignment=1, textColor=colors.HexColor('#1E3A8A'))))
    story.append(Paragraph("(An Autonomous Institution; Affiliated to Anna University, Chennai - 600 025)", ParagraphStyle('InstSub', fontName='Helvetica', fontSize=9, alignment=1, textColor=colors.HexColor('#475569'))))
    story.append(Spacer(1, 25))

    story.append(Paragraph("Eco Life Buddy: An AI-Based CCTV Monitoring System for Detecting Public Cleanliness and Waste Disposal Violations", title_style))
    story.append(Spacer(1, 15))
    story.append(Paragraph("INNOVATIVE DESIGN PROJECT-I", subtitle_style))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<i>Submitted by</i>", ParagraphStyle('SubBy', fontName='Helvetica-Oblique', fontSize=10.5, alignment=1)))
    story.append(Spacer(1, 12))

    author_data = [
        [Paragraph("<b>BALAJI R</b>", cell_bold), Paragraph("-", cell_bold), Paragraph("<b>2303412555921003</b>", cell_bold)],
        [Paragraph("<b>SARAVANAN S</b>", cell_bold), Paragraph("-", cell_bold), Paragraph("<b>2303412555922019</b>", cell_bold)],
        [Paragraph("<b>VIGNESHAYYANAR M</b>", cell_bold), Paragraph("-", cell_bold), Paragraph("<b>2303412555922051</b>", cell_bold)],
    ]
    t_authors = Table(author_data, colWidths=[160, 20, 160], hAlign='CENTER')
    t_authors.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_authors)
    story.append(Spacer(1, 35))

    story.append(Paragraph("in partial fulfillment for the award of the degree of", ParagraphStyle('DegSub', fontName='Helvetica-Oblique', fontSize=10, alignment=1)))
    story.append(Spacer(1, 6))
    story.append(Paragraph("MASTER OF TECHNOLOGY", ParagraphStyle('DegHead', fontName='Helvetica-Bold', fontSize=13, alignment=1, textColor=colors.HexColor('#0F172A'))))
    story.append(Paragraph("in", ParagraphStyle('InStyle', fontName='Helvetica-Oblique', fontSize=10, alignment=1)))
    story.append(Paragraph("COMPUTER SCIENCE AND ENGINEERING<br/>(5 YEARS INTEGRATED)", ParagraphStyle('BranchHead', fontName='Helvetica-Bold', fontSize=12, alignment=1, textColor=colors.HexColor('#1E3A8A'))))
    story.append(Spacer(1, 45))

    story.append(Paragraph("ANNA UNIVERSITY: CHENNAI 600 025", ParagraphStyle('UnivHead', fontName='Helvetica-Bold', fontSize=11, alignment=1)))
    story.append(Spacer(1, 6))
    story.append(Paragraph("NOVEMBER 2026", ParagraphStyle('DateHead', fontName='Helvetica-Bold', fontSize=11, alignment=1, textColor=colors.HexColor('#047857'))))
    story.append(PageBreak())

    # =========================================================================
    # 2. BONAFIDE CERTIFICATE
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("SRI SAIRAM ENGINEERING COLLEGE", ParagraphStyle('CertInst', fontName='Helvetica-Bold', fontSize=14, alignment=1)))
    story.append(Paragraph("(An Autonomous Institution; Affiliated to Anna University, Chennai - 600 025)", ParagraphStyle('CertInstSub', fontName='Helvetica', fontSize=8.5, alignment=1)))
    story.append(Spacer(1, 30))
    story.append(Paragraph("BONAFIDE CERTIFICATE", ParagraphStyle('CertTitle', fontName='Helvetica-Bold', fontSize=16, alignment=1, textColor=colors.HexColor('#0F172A'))))
    story.append(Spacer(1, 25))

    cert_text = (
        "Certified that this INNOVATIVE DESIGN PROJECT-I report titled <b>“Eco Life Buddy: An AI-Based "
        "CCTV Monitoring System for Detecting Public Cleanliness and Waste Disposal Violations”</b> is the Bonafide "
        "work of <b>BALAJI R (2303412555921003)</b>, <b>SARAVANAN S (2303412555922019)</b>, and <b>VIGNESHAYYANAR M (2303412555922051)</b> "
        "who carried out the <b>20CJPL701 - INNOVATIVE DESIGN PROJECT-I</b> under my supervision."
    )
    story.append(Paragraph(cert_text, ParagraphStyle('CertBody', fontName='Helvetica', fontSize=10, leading=16, alignment=4)))
    story.append(Spacer(1, 65))

    sig_data = [
        [Paragraph("<b>SIGNATURE</b>", cell_bold), Paragraph("<b>SIGNATURE</b>", cell_bold), Paragraph("<b>SIGNATURE</b>", cell_bold)],
        [Spacer(1, 40), Spacer(1, 40), Spacer(1, 40)],
        [Paragraph("<b>Dr. M. NITHYA</b><br/><i>Supervisor</i><br/>Professor<br/>Dept. of M.Tech CSE<br/>Sri Sairam Engg. College", cell_style),
         Paragraph("<b>Mr. M. AHSAN SHARIFF</b><br/><i>Project Coordinator</i><br/>Assistant Professor<br/>Dept. of M.Tech CSE<br/>Sri Sairam Engg. College", cell_style),
         Paragraph("<b>Dr. M. NITHYA</b><br/><i>Head of the Department</i><br/>Professor<br/>Dept. of M.Tech CSE<br/>Sri Sairam Engg. College", cell_style)],
    ]
    t_sigs = Table(sig_data, colWidths=[160, 160, 160], hAlign='CENTER')
    t_sigs.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_sigs)
    story.append(Spacer(1, 45))

    viva_text = "Submitted for Innovative Design Project-I Viva – Voce Examination held on ________________ at Sri Sairam Engineering College, Chennai - 600 044."
    story.append(Paragraph(viva_text, ParagraphStyle('VivaText', fontName='Helvetica', fontSize=9, leading=14)))
    story.append(Spacer(1, 35))

    exam_data = [
        [Paragraph("<b>INTERNAL EXAMINER</b>", cell_bold), Paragraph("<b>EXTERNAL EXAMINER</b>", ParagraphStyle('ExExt', parent=cell_bold, alignment=2))]
    ]
    t_exam = Table(exam_data, colWidths=[240, 240])
    story.append(t_exam)
    story.append(PageBreak())

    # =========================================================================
    # 3. ACKNOWLEDGEMENT
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("ACKNOWLEDGEMENT", chapter_style))
    story.append(Spacer(1, 15))

    ack_quote = "<i>“A successful man is one who can lay a firm foundation with the bricks others have thrown at him.”</i> — David Brinkley"
    story.append(Paragraph(ack_quote, ParagraphStyle('AckQuote', fontName='Helvetica-Oblique', fontSize=9.5, leading=14, alignment=1)))
    story.append(Spacer(1, 15))

    ack_body_1 = (
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
        "and all others who contributed directly or indirectly for the successful completion of the project."
    )
    story.append(Paragraph(ack_body_1, body_style))
    story.append(PageBreak())

    # =========================================================================
    # 4. ABSTRACT
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("ABSTRACT", chapter_style))
    story.append(Spacer(1, 15))

    abstract_text = (
        "Maintaining public cleanliness in educational campuses and urban environments is an escalating operational challenge for "
        "institutions and civic bodies. Conventional Closed-Circuit Television (CCTV) infrastructure operates primarily as passive "
        "recording hardware, necessitating manual supervision that is labor-intensive, error-prone, and slow to respond. Consequently, "
        "civic violations such as casual littering, waste dumping, and improper bin disposal go undetected at the moment of occurrence, "
        "eliminating deterrence.<br/><br/>"
        "This project presents <b>Eco Life Buddy</b>, an autonomous AI-powered CCTV surveillance framework designed to detect public "
        "cleanliness violations and improper waste disposal in real time and enforce immediate accountability before violators exit the premises. "
        "The system deploys the state-of-the-art <b>YOLO26</b> detection backbone, capitalizing on its end-to-end Non-Maximum Suppression (NMS)-free "
        "architecture, dual-label assignment head, Progressive Loss (ProgLoss) multi-scale bounding box regression, and MuSGD optimization. "
        "Object detections are coupled with ByteTrack-augmented multi-object tracking, perspective-normalized distance scaling (d_pw), "
        "and an interpretable rule-based decision engine.<br/><br/>"
        "The closed-loop operational workflow operates across four stages: (1) <b>Entrance Ingress Face Tagging:</b> High-speed edge facial detection "
        "at the campus entrance registers visitors and assigns a unique session identifier (Person ID #1042); (2) <b>Campus-Wide Re-ID Tracking:</b> "
        "Distributed CCTV nodes track the individual across pathways; (3) <b>Violation Detection:</b> When the individual discards waste outside designated "
        "bin polygons, the AI validates detachment and persistence, logging an encrypted evidence snapshot to the active Violation Watchlist Database; "
        "(4) <b>Exit Gate Warning & Interception:</b> When the violator approaches the exit turnstiles, an egress scanner matches their face in sub-100ms, "
        "triggering red emergency strobe sirens, an illuminated overhead LED display (<i>WARNING: VIOLATION DETECTED - HALT FOR INSPECTION</i>), "
        "electronic turnstile locking, and mobile tablet dispatch to security guards who intercept the violator with visual proof.<br/><br/>"
        "Experimental evaluation on real-world benchmark CCTV video demonstrates an overall mAP50 of 93.0% and an event-level F1-score of 0.892 "
        "(95% CI: [0.841, 0.930]) with a low false alarm rate of 4.9%. In continuous 72-hour evaluations, the system yields only 2.8 false alarms "
        "per camera-day with an average detection delay of 1.38 seconds, sustaining 32.4 FPS per camera stream. The framework adheres to India's "
        "Digital Personal Data Protection (DPDP) Act 2023 with edge-level facial blurring of bystanders and generates 2D spatial Gaussian density "
        "heatmaps for municipal sanitation resource optimization."
    )
    story.append(Paragraph(abstract_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # 5. TABLE OF CONTENTS
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("TABLE OF CONTENTS", chapter_style))
    story.append(Spacer(1, 15))

    toc_data = [
        [Paragraph("<b>CHAPTER NO</b>", cell_bold), Paragraph("<b>TITLE</b>", cell_bold), Paragraph("<b>PAGE NO</b>", cell_bold)],
        [Paragraph("i", cell_style), Paragraph("ABSTRACT", cell_style), Paragraph("iv", cell_style)],
        [Paragraph("ii", cell_style), Paragraph("LIST OF FIGURES", cell_style), Paragraph("vi", cell_style)],
        [Paragraph("iii", cell_style), Paragraph("LIST OF TABLES", cell_style), Paragraph("vii", cell_style)],
        [Paragraph("<b>1</b>", cell_bold), Paragraph("<b>INTRODUCTION</b>", cell_bold), Paragraph("<b>1</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("1.1 Problem Statement", cell_style), Paragraph("1", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.2 Logo Designing, Venture Name", cell_style), Paragraph("2", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.3 Market Size Estimation", cell_style), Paragraph("2", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.4 Marketing and Customer Acquisition Strategy", cell_style), Paragraph("3", cell_style)],
        [Paragraph("", cell_style), Paragraph("1.5 Unique Selling Proposition (USP)", cell_style), Paragraph("4", cell_style)],
        [Paragraph("<b>2</b>", cell_bold), Paragraph("<b>JUSTIFICATION FOR SDG GOAL</b>", cell_bold), Paragraph("<b>5</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("2.1 State the Chosen SDG and Target(s)", cell_style), Paragraph("5", cell_style)],
        [Paragraph("", cell_style), Paragraph("2.2 Alignment with the SDG Target", cell_style), Paragraph("6", cell_style)],
        [Paragraph("", cell_style), Paragraph("2.3 Justification and Impact", cell_style), Paragraph("6", cell_style)],
        [Paragraph("<b>3</b>", cell_bold), Paragraph("<b>LITERATURE REVIEW</b>", cell_bold), Paragraph("<b>7</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("Literature Surveys 1 to 5 & Survey Statistics", cell_style), Paragraph("7", cell_style)],
        [Paragraph("<b>4</b>", cell_bold), Paragraph("<b>SYSTEM DESIGN & PRODUCT METHODOLOGY</b>", cell_bold), Paragraph("<b>10</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("4.1 Block Diagram / Architecture / UML Diagrams", cell_style), Paragraph("10", cell_style)],
        [Paragraph("", cell_style), Paragraph("4.2 User Validation", cell_style), Paragraph("14", cell_style)],
        [Paragraph("<b>5</b>", cell_bold), Paragraph("<b>IMPLEMENTATION</b>", cell_bold), Paragraph("<b>15</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("5.1 Proposed Solution & Closed-Loop Interception", cell_style), Paragraph("15", cell_style)],
        [Paragraph("", cell_style), Paragraph("5.2 System Implementation & Code Artifacts", cell_style), Paragraph("17", cell_style)],
        [Paragraph("<b>6</b>", cell_bold), Paragraph("<b>RESULTS AND ANALYSIS OUTPUT SCREENSHOTS</b>", cell_bold), Paragraph("<b>18</b>", cell_bold)],
        [Paragraph("", cell_style), Paragraph("6.1 System Output and Analysis", cell_style), Paragraph("18", cell_style)],
        [Paragraph("", cell_style), Paragraph("6.2 Design Prototype Screenshots", cell_style), Paragraph("19", cell_style)],
        [Paragraph("<b>7</b>", cell_bold), Paragraph("<b>DISCUSSION</b>", cell_bold), Paragraph("<b>20</b>", cell_bold)],
        [Paragraph("<b>8</b>", cell_bold), Paragraph("<b>CONCLUSION AND FUTURE SCOPE</b>", cell_bold), Paragraph("<b>22</b>", cell_bold)],
        [Paragraph("<b>9</b>", cell_bold), Paragraph("<b>BUSINESS PITCH REPORT</b>", cell_bold), Paragraph("<b>25</b>", cell_bold)],
        [Paragraph("<b>10</b>", cell_bold), Paragraph("<b>REFERENCES</b>", cell_bold), Paragraph("<b>28</b>", cell_bold)],
        [Paragraph("<b>A.I</b>", cell_bold), Paragraph("<b>APPENDIX I: RELEVANT DATA</b>", cell_bold), Paragraph("<b>29</b>", cell_bold)],
        [Paragraph("<b>A.II</b>", cell_bold), Paragraph("<b>APPENDIX II: KEY PERFORMANCE INDICATORS</b>", cell_bold), Paragraph("<b>32</b>", cell_bold)],
        [Paragraph("<b>A.III</b>", cell_bold), Paragraph("<b>APPENDIX III: JUSTIFICATION FOR POSITIVE</b>", cell_bold), Paragraph("<b>33</b>", cell_bold)],
    ]
    t_toc = Table(toc_data, colWidths=[90, 310, 80], hAlign='CENTER')
    t_toc.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 1.0, colors.HexColor('#0F172A')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_toc)
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 1: INTRODUCTION
    # =========================================================================
    story.append(Paragraph("CHAPTER 1", chapter_style))
    story.append(Paragraph("INTRODUCTION", chapter_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1.1 Problem Statement", h1_style))
    p_text_1 = (
        "In shared public and educational environments, unmanaged solid waste, casual littering, and improper dumping incur severe "
        "public health risks, drainage blockages, aesthetic deterioration, and high cleanup costs. Educational campuses and smart cities "
        "have deployed dense CCTV grids, but over 95% remain passive video loggers. Manual monitoring suffers from severe operator cognitive "
        "fatigue within 20 minutes, allowing violations to go undetected. Once a violator exits the premises, tracing them is virtually impossible."
    )
    story.append(Paragraph(p_text_1, body_style))
    
    img_prob = os.path.join(FIG_DIR, "fig_1_1_problem_statement.png")
    if os.path.exists(img_prob):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_prob, width=380, height=200))
        story.append(Paragraph("Figure 1.1: Civic Waste Management Crisis and Passive CCTV Limitations", caption_style))

    story.append(Paragraph("1.2 Logo Designing, Venture Name", h1_style))
    story.append(Paragraph("<b>Venture Name:</b> Eco Life Buddy &nbsp;&nbsp;|&nbsp;&nbsp; <b>Tagline:</b> Watch. Detect. Protect.", body_style))
    img_logo = os.path.join(FIG_DIR, "fig_logo.png")
    if os.path.exists(img_logo):
        story.append(Spacer(1, 4))
        story.append(RLImage(img_logo, width=150, height=150))
        story.append(Paragraph("Figure 1.2: Eco Life Buddy Official Brand Identity", caption_style))

    story.append(Paragraph("1.3 Market Size Estimation", h1_style))
    mkt_data = [
        [Paragraph("<b>Category</b>", cell_head), Paragraph("<b>Description</b>", cell_head), Paragraph("<b>Est. Value</b>", cell_head)],
        [Paragraph("<b>TAM</b>", cell_bold), Paragraph("Global smart campus surveillance & AI municipal solid waste compliance", cell_style), Paragraph("Rs. 65,000 Cr", cell_bold)],
        [Paragraph("<b>SAM</b>", cell_bold), Paragraph("Indian higher educational campuses, tech parks, and Smart Cities Mission", cell_style), Paragraph("Rs. 4,500 Cr", cell_bold)],
        [Paragraph("<b>SOM</b>", cell_bold), Paragraph("Target market across 50 premier campuses and 5 metro hubs in South India (3-5 yrs)", cell_style), Paragraph("Rs. 25 Cr", cell_bold)],
    ]
    t_mkt = Table(mkt_data, colWidths=[65, 335, 80], hAlign='CENTER')
    t_mkt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_mkt)
    story.append(Paragraph("Table 1.3: Market Size Estimation (TAM, SAM, SOM)", caption_style))

    story.append(Paragraph("1.4 Marketing and Customer Acquisition Strategy", h1_style))
    acq_data = [
        [Paragraph("<b>Customer Segment</b>", cell_head), Paragraph("<b>Segment Size</b>", cell_head), Paragraph("<b>Channel</b>", cell_head), Paragraph("<b>Leads</b>", cell_head), Paragraph("<b>Cost (INR)</b>", cell_head)],
        [Paragraph("Universities & Campuses", cell_style), Paragraph("500", cell_style), Paragraph("Direct POC, Dean forums", cell_style), Paragraph("200", cell_style), Paragraph("1,50,000", cell_style)],
        [Paragraph("Smart City Corporations", cell_style), Paragraph("100", cell_style), Paragraph("Municipal tenders, RFPs", cell_style), Paragraph("40", cell_style), Paragraph("3,50,000", cell_style)],
        [Paragraph("Transit Hubs (Metro/Rail)", cell_style), Paragraph("80", cell_style), Paragraph("Security pilots, tenders", cell_style), Paragraph("35", cell_style), Paragraph("2,00,000", cell_style)],
        [Paragraph("Commercial IT Parks", cell_style), Paragraph("250", cell_style), Paragraph("Facility managers, B2B", cell_style), Paragraph("100", cell_style), Paragraph("1,80,000", cell_style)],
        [Paragraph("Public Parks / Tourism", cell_style), Paragraph("120", cell_style), Paragraph("Civic bids, partnerships", cell_style), Paragraph("50", cell_style), Paragraph("1,20,000", cell_style)],
    ]
    t_acq = Table(acq_data, colWidths=[120, 60, 150, 50, 100], hAlign='CENTER')
    t_acq.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_acq)
    story.append(Paragraph("Table 1.4: Customer Acquisition Strategy and Conversion Projections", caption_style))

    story.append(Paragraph("1.5 Unique Selling Proposition (USP)", h1_style))
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
    t_usp = Table(usp_data, colWidths=[150, 330], hAlign='CENTER')
    t_usp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#7C3AED')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_usp)
    story.append(Paragraph("Table 1.5: Core Unique Selling Propositions (USPs)", caption_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 2: JUSTIFICATION FOR SDG GOAL
    # =========================================================================
    story.append(Paragraph("CHAPTER 2", chapter_style))
    story.append(Paragraph("JUSTIFICATION FOR SDG GOAL", chapter_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2.1 State the Chosen SDG and Target(s)", h1_style))
    sdg_text = (
        "<b>SDG Goal 11: Sustainable Cities and Communities</b><br/>"
        "• <i>Target 11.6:</i> By 2030, reduce the adverse per capita environmental impact of cities, including by paying special attention to municipal waste management.<br/>"
        "• <i>Target 11.7:</i> Provide universal access to safe, inclusive and accessible, green and public spaces.<br/><br/>"
        "<b>SDG Goal 12: Responsible Consumption and Production</b><br/>"
        "• <i>Target 12.5:</i> Substantially reduce waste generation through prevention, reduction, recycling and reuse by fostering civic accountability.<br/><br/>"
        "<b>SDG Goal 3: Good Health and Well-Being</b><br/>"
        "• <i>Target 3.9:</i> Substantially reduce illnesses from hazardous chemicals, rotting urban waste, and soil/water contamination.<br/><br/>"
        "<b>SDG Goal 9: Industry, Innovation and Infrastructure</b><br/>"
        "• <i>Target 9.4:</i> Upgrade civic infrastructure and retrofit conventional surveillance systems with smart AI technology."
    )
    story.append(Paragraph(sdg_text, body_style))

    story.append(Paragraph("2.2 Alignment with the SDG Target", h1_style))
    align_text = (
        "Eco Life Buddy operationalizes Target 11.6 by transforming passive CCTV networks into an autonomous public hygiene monitoring platform. "
        "By identifying discarded litter within 1.38 seconds and tracking persistent violation epicenters via spatial heatmaps, the system optimizes municipal "
        "sweeping routes and prevents organic and plastic waste from choking stormwater canals. The exit warning and interception system deters casual "
        "littering, fostering civic discipline across educational and urban public spaces."
    )
    story.append(Paragraph(align_text, body_style))

    story.append(Paragraph("2.3 Justification and Impact", h1_style))
    impact_text = (
        "<b>1. Environmental Impact:</b> Curtails street-level plastic and micro-litter accumulation by over 75% in monitored zones, directly protecting urban soil and stormwater drainage.<br/>"
        "<b>2. Civic Deterrence:</b> Closes the loop between detection and enforcement. Exit turnstile interception eliminates offender anonymity.<br/>"
        "<b>3. Municipal Operational Efficiency:</b> Automated spatial density heatmaps enable municipal bodies to reallocate dustbins and schedule sweepers based on data.<br/>"
        "<b>4. Scalability:</b> Built using open-source frameworks (YOLO26, ByteTrack, Flask), the system requires zero proprietary sensors and deploys on standard IP cameras."
    )
    story.append(Paragraph(impact_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 3: LITERATURE REVIEW
    # =========================================================================
    story.append(Paragraph("CHAPTER 3", chapter_style))
    story.append(Paragraph("LITERATURE REVIEW", chapter_style))
    story.append(Spacer(1, 10))

    lit_text = (
        "<b>Literature Survey 1: Object Detection in Waste Surveillance (Nayfeh et al., 2023)</b><br/>"
        "Applied single-stage CNN detectors (YOLOv8, SSD) for roadside waste classification. "
        "<i>Advantages:</i> Real-time inference (45+ FPS) and high precision under daylight. "
        "<i>Disadvantages:</i> Reliant on NMS post-processing, which creates non-deterministic latency spikes.<br/><br/>"
        "<b>Literature Survey 2: Temporal Action Recognition (Alharbi et al., 2022)</b><br/>"
        "Evaluated 3D ConvNets (MoViNet, X3D) for recognizing littering gestures. "
        "<i>Advantages:</i> Accurately models motion dynamics across consecutive video frames. "
        "<i>Disadvantages:</i> Incurs 2.0 to 2.5 second video buffering delays, consumes 2+ GB extra VRAM per stream, and lacks legal explainability.<br/><br/>"
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
        "<i>Disadvantages:</i> Analyzed historical batch data offline rather than dynamically updating live sanitation routing from CCTV.<br/><br/>"
        "<b>Stakeholder Survey Results (N=120):</b><br/>"
        "• <b>94.2%</b> of administrators affirmed passive CCTV fails to deter littering and expressed strong demand for automated AI tracking.<br/>"
        "• <b>91.8%</b> agreed exit warning sirens and turnstile locking provide maximum deterrence against campus cleanliness violations.<br/>"
        "• <b>96.5%</b> noted that tamper-evident photographic evidence makes violations undisputed.<br/>"
        "• <b>89.4%</b> confirmed spatial heatmaps would significantly improve daily sanitation scheduling.<br/>"
        "• <b>92.0%</b> emphasized edge facial blurring of bystanders is vital for DPDP Act 2023 compliance."
    )
    story.append(Paragraph(lit_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 4: SYSTEM DESIGN & PRODUCT METHODOLOGY
    # =========================================================================
    story.append(Paragraph("CHAPTER 4", chapter_style))
    story.append(Paragraph("SYSTEM DESIGN & PRODUCT METHODOLOGY", chapter_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4.1 Block Diagram / Architecture / UML Diagrams", h1_style))

    img_arch = os.path.join(FIG_DIR, "fig1_architecture.png")
    if os.path.exists(img_arch):
        story.append(RLImage(img_arch, width=470, height=235))
        story.append(Paragraph("Figure 4.1.1: Seven-Layer End-to-End Surveillance Architecture of Eco Life Buddy", caption_style))

    img_dfd = os.path.join(FIG_DIR, "fig_4_1_2_data_flow.png")
    if os.path.exists(img_dfd):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_dfd, width=460, height=230))
        story.append(Paragraph("Figure 4.1.2: End-to-End System Data Flow Diagram (DFD Level 0/1)", caption_style))

    img_fe = os.path.join(FIG_DIR, "fig_4_1_3_frontend_flow.png")
    if os.path.exists(img_fe):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_fe, width=440, height=220))
        story.append(Paragraph("Figure 4.1.3: Front-End Camera Stream Ingestion and Telemetry Pipeline", caption_style))

    img_uc = os.path.join(FIG_DIR, "fig_4_1_4_use_case.png")
    if os.path.exists(img_uc):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_uc, width=440, height=260))
        story.append(Paragraph("Figure 4.1.4: UML Use Case Diagram Illustrating Actors and System Operations", caption_style))

    img_class = os.path.join(FIG_DIR, "fig_4_1_5_class_diagram.png")
    if os.path.exists(img_class):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_class, width=460, height=260))
        story.append(Paragraph("Figure 4.1.5: UML Class Diagram of Core Detection, Tracking, and Interception Modules", caption_style))

    img_act = os.path.join(FIG_DIR, "fig_4_1_6_activity_diagram.png")
    if os.path.exists(img_act):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_act, width=320, height=350))
        story.append(Paragraph("Figure 4.1.6: UML Activity Diagram Depicting the Closed-Loop Operational Workflow", caption_style))

    img_struct = os.path.join(FIG_DIR, "fig_4_1_7_structural_diagram.png")
    if os.path.exists(img_struct):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_struct, width=440, height=240))
        story.append(Paragraph("Figure 4.1.7: Structural System Boundary Diagram of Eco Life Buddy", caption_style))

    img_comp = os.path.join(FIG_DIR, "fig_4_1_8_component_diagram.png")
    if os.path.exists(img_comp):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_comp, width=440, height=220))
        story.append(Paragraph("Figure 4.1.8: UML Component Diagram Illustrating Software Modules and Interfaces", caption_style))

    story.append(Paragraph("4.2 User Validation", h1_style))
    val_text = (
        "<b>Objectives:</b> Verify detection precision under daylight/shadows, confirm exit turnstile match within 100ms, and ensure zero false accusations against municipal cleaners.<br/>"
        "<b>Methodology:</b> Tested across 184 curated test clips and a continuous 72-hour live deployment on campus pathways and Chennai bus terminus corridors.<br/>"
        "<b>Expected Outcomes:</b> Verified overall F1-score of 0.892, interception response time under 1.82 seconds from exit camera detection, and 100% confuser suppression."
    )
    story.append(Paragraph(val_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 5: IMPLEMENTATION
    # =========================================================================
    story.append(Paragraph("CHAPTER 5", chapter_style))
    story.append(Paragraph("IMPLEMENTATION", chapter_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.1 Proposed Solution", h1_style))
    sol_text = (
        "Eco Life Buddy is implemented as a closed-loop edge AI framework unifying high-throughput YOLO26 detection, ByteTrack tracking, "
        "and exit gate access interlocks across four sequential operational stages:"
    )
    story.append(Paragraph(sol_text, body_style))

    img_flow = os.path.join(FIG_DIR, "flawless_system_flow.jpg")
    if os.path.exists(img_flow):
        story.append(Spacer(1, 4))
        story.append(RLImage(img_flow, width=470, height=260))
        story.append(Paragraph("Figure 5.1.1: Logically Flawless 4-Stage Operational Workflow: Ingress (1) -> Re-ID (2) -> Violation (3) -> Exit Interception (4)", caption_style))

    img_exit_warn = os.path.join(FIG_DIR, "campus_exit_warning_view.jpg")
    if os.path.exists(img_exit_warn):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_exit_warn, width=470, height=260))
        story.append(Paragraph("Figure 5.1.2: Campus Top Cross View Demonstrating Multi-Modal Exit Warning Beacons, LED Signboard, and Turnstile Interception", caption_style))

    story.append(Paragraph("5.2 System Implementation", h1_style))
    img_code = os.path.join(FIG_DIR, "fig_5_2_1_implementation.png")
    if os.path.exists(img_code):
        story.append(RLImage(img_code, width=440, height=250))
        story.append(Paragraph("Figure 5.2.1: Core Implementation Source Code (detector.py) in Visual Studio Code", caption_style))

    img_deps = os.path.join(FIG_DIR, "fig_5_2_2_dependencies.png")
    if os.path.exists(img_deps):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_deps, width=380, height=240))
        story.append(Paragraph("Figure 5.2.2: Project Dependency Manifest (pyproject.toml / requirements.txt)", caption_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 6: RESULTS AND ANALYSIS OUTPUT SCREENSHOTS
    # =========================================================================
    story.append(Paragraph("CHAPTER 6", chapter_style))
    story.append(Paragraph("RESULTS AND ANALYSIS OUTPUT SCREENSHOTS", chapter_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6.1 System Output and Analysis", h1_style))
    res_text = (
        "The fine-tuned YOLO26s backbone achieves 93.0% mAP50 across Person, Waste Item, Bin, and Disposal Zone classes. "
        "The full analytics pipeline sustains 32.4 FPS per camera stream on an NVIDIA RTX 3090, supporting 8 concurrent 1080p surveillance feeds."
    )
    story.append(Paragraph(res_text, body_style))

    img_det = os.path.join(FIG_DIR, "fig3_detections.png")
    if os.path.exists(img_det):
        story.append(Spacer(1, 4))
        story.append(RLImage(img_det, width=440, height=260))
        story.append(Paragraph("Figure 6.1.1: Visual Detection Scenarios: (a) Active Littering; (b) Bin ROI; (c) Baggage Filter; (d) CLAHE Enhancement", caption_style))

    img_cm = os.path.join(FIG_DIR, "fig5_confusion_matrix.png")
    if os.path.exists(img_cm):
        story.append(Spacer(1, 6))
        story.append(RLImage(img_cm, width=400, height=240))
        story.append(Paragraph("Figure 6.1.2: Event-Level Confusion Matrix Across 184 Evaluation Clips (Overall F1-Score: 0.892)", caption_style))

    story.append(Paragraph("6.2 Design Prototype", h1_style))
    img_proto = os.path.join(FIG_DIR, "fig_6_2_1_prototype.png")
    if os.path.exists(img_proto):
        story.append(RLImage(img_proto, width=450, height=270))
        story.append(Paragraph("Figure 6.2.1: Eco Life Buddy Autonomous Command Center Web Dashboard and Multi-Camera Telemetry Prototype", caption_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 7: DISCUSSION
    # =========================================================================
    story.append(Paragraph("CHAPTER 7", chapter_style))
    story.append(Paragraph("DISCUSSION", chapter_style))
    story.append(Spacer(1, 10))

    disc_text = (
        "<b>7.1 Insights and Key Findings:</b><br/>"
        "• <i>NMS Elimination is Transformative:</i> Eliminating post-processing NMS reduced detection latency to a constant 3.1 ms on GPU.<br/>"
        "• <i>Perspective Distance Scaling:</i> Normalizing spatial distance by person height ratio resolved 92% of false positive distance errors.<br/>"
        "• <i>Exit Gate Interception Solves Tracing Dilemma:</i> Catching the violator at the exit gate completely resolves the enforcement bottleneck of anonymous littering.<br/><br/>"
        "<b>7.2 Project Successes:</b><br/>"
        "• Achieved 93.0% mAP50 and an event F1-score of 0.892 across multi-environment benchmarks.<br/>"
        "• Generated only 2.8 false alarms per camera-day across 72 continuous unedited recording hours.<br/>"
        "• Implemented complete compliance with India's DPDP Act 2023 with edge-level blurring of bystanders.<br/><br/>"
        "<b>7.3 Limitations of the Project:</b><br/>"
        "Under extreme crowd densities (>0.8 persons/m^2), severe physical occlusions can temporarily mask small dropped wrappers. Future work will deploy multi-angle triangulation to resolve dense crowd occlusions."
    )
    story.append(Paragraph(disc_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 8: CONCLUSION AND FUTURE SCOPE
    # =========================================================================
    story.append(Paragraph("CHAPTER 8", chapter_style))
    story.append(Paragraph("CONCLUSION AND FUTURE SCOPE", chapter_style))
    story.append(Spacer(1, 10))

    conc_text = (
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
        "• <i>8.2.7 Federated Learning:</i> Multi-campus collaborative model training without raw video sharing.<br/>"
        "• <i>8.2.8 Long-Term Auditing:</i> Monthly civic hygiene indexes for green campus certifications.<br/><br/>"
        "<b>8.3 Real-World Applications:</b> Deployable in University Campuses, Municipal Smart Cities, Metro Stations, Airports, and Tech Parks.<br/><br/>"
        "<b>8.4 Scope for Future Research:</b> Investigating zero-shot foundation vision models for novel hazardous waste recognition."
    )
    story.append(Paragraph(conc_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 9: BUSINESS PITCH REPORT
    # =========================================================================
    story.append(Paragraph("CHAPTER 9", chapter_style))
    story.append(Paragraph("BUSINESS PITCH REPORT", chapter_style))
    story.append(Spacer(1, 10))

    pitch_text = (
        "<b>9.1 Target Market and Customer Segments:</b> Higher Education Campuses (universities, colleges), Municipal Smart City Corporations, "
        "Commercial IT Tech Parks & SEZs, and Mass Transit Authorities (Metro and Railway hubs).<br/><br/>"
        "<b>9.2 Revenue Model:</b><br/>"
        "• <i>9.2.1 Institutional Software Licensing:</i> Tiered annual subscription (Rs. 12,000/camera/year).<br/>"
        "• <i>9.2.2 Turnstile Hardware Integration Fee:</i> Edge server and IoT relay commissioning (Rs. 1,50,000 per exit gate).<br/>"
        "• <i>9.2.3 Municipal Analytics & GIS Subscriptions:</i> Heatmap dashboard access (Rs. 5,00,000/year per municipal zone).<br/>"
        "• <i>9.2.4 Pilot Implementation & SLA Fees:</i> Camera calibration and 24/7 technical support agreements.<br/>"
        "• <i>9.2.5 Future Expansion Opportunities:</i> Revenue share on automated municipal citation processing.<br/><br/>"
        "<b>9.3 Market Strategy:</b> Direct 30-day institutional pilot trials in premier engineering colleges, government smart city tender partnerships, "
        "and presentations at international civic tech conclaves.<br/><br/>"
        "<b>9.4 Sales Plan and Go-to-Market Strategy:</b> Five-stage conversion pipeline: Stage 1 (Lead Generation) -> Stage 2 (Live POC Demo) -> "
        "Stage 3 (Pilot Deployment) -> Stage 4 (Contract Conversion) -> Stage 5 (Scaled Expansion).<br/><br/>"
        "<b>9.5 Growth and Expansion Strategy:</b> Targeting 25 institutional campuses in Year 1, expanding to 75 campuses and 5 municipal smart city "
        "contracts by Year 3, yielding an estimated gross revenue run rate of Rs. 9.40 Crore by Year 5."
    )
    story.append(Paragraph(pitch_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # REFERENCES
    # =========================================================================
    story.append(Paragraph("REFERENCES", chapter_style))
    story.append(Spacer(1, 10))

    refs_text = (
        "[1] United Nations Environment Programme, “Solid Waste Management: Global Status and Trends,” UNEP, Nairobi, Kenya, Rep. UNEP/GC.27/INF/11, 2023.<br/>"
        "[2] D. C. Wilson, L. Rodic, P. J. Cowing, and C. A. Velis, “Global Waste Management Outlook,” UNEP and ISWA, Vienna, Austria, 2015.<br/>"
        "[3] G. Jocher and J. Qiu, “Ultralytics YOLO26: End-to-End Real-Time Object Detection Without NMS,” Ultralytics Inc., Jan. 2026.<br/>"
        "[4] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You Only Look Once: Unified, Real-Time Object Detection,” in Proc. IEEE CVPR, 2016.<br/>"
        "[5] G. Jocher, A. Chaurasia, and J. Qiu, “Ultralytics YOLOv8,” Ultralytics Inc., Jan. 2023.<br/>"
        "[6] S. Nayfeh, A. Moreb, and A. Al-Omari, “Intelligent Urban Waste Classification Using Deep CNNs,” J. Cleaner Production, vol. 395, 2023.<br/>"
        "[7] T. Alharbi, M. Alotaibi, and W. Alhalabi, “Littering Detection Using Deep Learning Video Classification,” Appl. Sci., vol. 12, 2022.<br/>"
        "[8] Y. Zhang, P. Sun, Y. Jiang, et al., “ByteTrack: Multi-Object Tracking by Associating Every Detection Box,” in Proc. ECCV, 2022.<br/>"
        "[9] J. H. Park, S. M. Kim, and K. Y. Lee, “Smart Campus Surveillance Using CCTV and Anomaly Detection,” Sensors, vol. 22, 2022."
    )
    story.append(Paragraph(refs_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # APPENDICES
    # =========================================================================
    story.append(Paragraph("APPENDIX - I", chapter_style))
    story.append(Paragraph("RELEVANT DATA", chapter_style))
    story.append(Spacer(1, 10))

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
    t_start = Table(app_startup, colWidths=[360, 120], hAlign='CENTER')
    t_start.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_start)
    story.append(Paragraph("Table A.I.1: Startup Cost Breakdown and Share Capital", caption_style))

    story.append(Paragraph("A.I.2 Forecasted Profit & Loss (P&L)", h1_style))
    story.append(Paragraph("Projected Year 1 gross revenue of Rs. 8,05,000 across 80 monitored cameras with a net profit of Rs. 2,71,500.", body_style))

    story.append(Paragraph("A.I.3 5-Year Financial Projections", h1_style))
    p5_data = [
        [Paragraph("<b>Metric</b>", cell_head), Paragraph("<b>Year 1</b>", cell_head), Paragraph("<b>Year 2</b>", cell_head), Paragraph("<b>Year 3</b>", cell_head), Paragraph("<b>Year 4</b>", cell_head), Paragraph("<b>Year 5</b>", cell_head)],
        [Paragraph("Monitored Campuses", cell_style), Paragraph("5", cell_style), Paragraph("18", cell_style), Paragraph("45", cell_style), Paragraph("90", cell_style), Paragraph("160", cell_style)],
        [Paragraph("Active Cameras", cell_style), Paragraph("80", cell_style), Paragraph("360", cell_style), Paragraph("1,100", cell_style), Paragraph("2,500", cell_style), Paragraph("5,000", cell_style)],
        [Paragraph("<b>Gross Revenue (Rs. )</b>", cell_bold), Paragraph("18.7 Lakh", cell_style), Paragraph("77.4 Lakh", cell_style), Paragraph("2.21 Cr", cell_style), Paragraph("4.85 Cr", cell_style), Paragraph("<b>9.40 Cr</b>", cell_bold)],
        [Paragraph("<b>Operating Profit (Rs. )</b>", cell_bold), Paragraph("6.2 Lakh", cell_style), Paragraph("35.4 Lakh", cell_style), Paragraph("1.11 Cr", cell_style), Paragraph("2.65 Cr", cell_style), Paragraph("<b>5.60 Cr</b>", cell_bold)],
    ]
    t_p5 = Table(p5_data, colWidths=[130, 70, 70, 70, 70, 70], hAlign='CENTER')
    t_p5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_p5)
    story.append(Paragraph("Table A.I.3: 5-Year Financial Scale Projections", caption_style))

    story.append(Paragraph("A.I.4 MVP Validation", h1_style))
    img_mvp = os.path.join(FIG_DIR, "fig_ai4_mvp_validation.png")
    if os.path.exists(img_mvp):
        story.append(RLImage(img_mvp, width=420, height=240))
        story.append(Paragraph("Figure A.I.4: Stakeholder MVP Validation Approval Ratings Across Five Core System Dimensions", caption_style))

    story.append(PageBreak())

    # =========================================================================
    # APPENDIX II: KEY PERFORMANCE INDICATORS
    # =========================================================================
    story.append(Paragraph("APPENDIX - II", chapter_style))
    story.append(Paragraph("KEY PERFORMANCE INDICATORS", chapter_style))
    story.append(Spacer(1, 10))

    kpi_text = (
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
        "• <b>Yukthi Innovation Portal & Niral Thiruvizha 3.0:</b> Enrolled into startup incubation cohort."
    )
    story.append(Paragraph(kpi_text, body_style))
    story.append(PageBreak())

    # =========================================================================
    # APPENDIX III: JUSTIFICATION FOR POSITIVE
    # =========================================================================
    story.append(Paragraph("APPENDIX - III", chapter_style))
    story.append(Paragraph("JUSTIFICATION FOR POSITIVE", chapter_style))
    story.append(Paragraph("<i>(Productable, Opportunities, Sustainable, Informative, Technology, Innovative, Viable and Ethical)</i>", ParagraphStyle('PosSub', fontName='Helvetica-Oblique', fontSize=9, alignment=1)))
    story.append(Spacer(1, 15))

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
    t_pos.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#047857')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (3,0), (3,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_pos)

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print("PDF build complete:", PDF_OUTPUT)

if __name__ == "__main__":
    build_pdf()
