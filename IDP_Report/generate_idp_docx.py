"""
generate_idp_docx.py
Generates the complete, official IDP-I Project Report as a Microsoft Word Document (.docx):
c:\LIL\IDP_Report\IDP_EcoLifeBuddy_Report.docx
Matching the exact layout, structure, tables, figures, and formatting of IDP_20261015_182809_0000.pdf
"""

import os
import docx
from docx import Document
from report_appendix import append_current_implementation_status
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

DOCX_OUTPUT = r"c:\LIL\IDP_Report\IDP_EcoLifeBuddy_Report.docx"
FIG_DIR = r"c:\LIL\IDP_Report\figures"

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def create_document():
    doc = Document()

    # Page Margins (1 inch all around)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.27)  # A4
        section.page_height = Inches(11.69)
        
        # Header and Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("Eco Life Buddy: AI-Based Cleanliness & Violation Interception")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.italic = True
        hrun.font.color.rgb = RGBColor(100, 116, 139)

        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun = fp.add_run("Innovative Design Project-I | Dept. of M.Tech CSE | Sri Sairam Engineering College")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8)
        frun.font.color.rgb = RGBColor(100, 116, 139)

    # Styles helper
    def add_title(text, space_after=12):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(17)
        run.font.bold = True
        run.font.color.rgb = RGBColor(15, 23, 42)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.2
        return p

    def add_chapter_heading(ch_num, ch_title):
        p1 = doc.add_paragraph()
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p1.add_run(f"CHAPTER {ch_num}")
        r1.font.name = "Calibri"
        r1.font.size = Pt(14)
        r1.font.bold = True
        r1.font.color.rgb = RGBColor(15, 23, 42)
        p1.paragraph_format.space_before = Pt(12)
        p1.paragraph_format.space_after = Pt(4)

        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(ch_title)
        r2.font.name = "Calibri"
        r2.font.size = Pt(15)
        r2.font.bold = True
        r2.font.color.rgb = RGBColor(15, 23, 42)
        p2.paragraph_format.space_after = Pt(16)

    def add_h1(text):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 58, 138)  # Deep blue
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(11)
        run.font.bold = True
        run.font.color.rgb = RGBColor(15, 23, 42)
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        return p

    def add_body(text, space_after=6, italic=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.font.italic = italic
        run.font.color.rgb = RGBColor(30, 41, 59)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        return p

    def add_caption(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.font.name = "Calibri"
        run.font.size = Pt(9)
        run.font.bold = True
        run.font.color.rgb = RGBColor(71, 85, 105)
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(12)
        return p

    def add_image_if_exists(filename, width_in_inches=6.0, caption_text=""):
        p_img = os.path.join(FIG_DIR, filename)
        if os.path.exists(p_img):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run()
            run.add_picture(p_img, width=Inches(width_in_inches))
            if caption_text:
                add_caption(caption_text)

    # =========================================================================
    # 1. COVER PAGE
    # =========================================================================
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("SRI SAIRAM ENGINEERING COLLEGE\n")
    r.font.name = "Calibri"
    r.font.size = Pt(15)
    r.font.bold = True
    r.font.color.rgb = RGBColor(30, 58, 138)
    r2 = p.add_run("(An Autonomous Institution; Affiliated to Anna University, Chennai - 600 025)")
    r2.font.name = "Calibri"
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = RGBColor(100, 116, 139)
    p.paragraph_format.space_after = Pt(28)

    add_title("Eco Life Buddy: An AI-Based CCTV Monitoring System for Detecting Public Cleanliness and Waste Disposal Violations", space_after=14)

    p_idp = doc.add_paragraph()
    p_idp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_idp = p_idp.add_run("INNOVATIVE DESIGN PROJECT-I")
    r_idp.font.name = "Calibri"
    r_idp.font.size = Pt(13)
    r_idp.font.bold = True
    r_idp.font.color.rgb = RGBColor(4, 120, 87)  # Emerald
    p_idp.paragraph_format.space_after = Pt(24)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Submitted by")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(10.5)
    r_sub.font.italic = True
    p_sub.paragraph_format.space_after = Pt(10)

    # Authors Table
    table_auth = doc.add_table(rows=3, cols=3)
    table_auth.alignment = WD_TABLE_ALIGNMENT.CENTER
    authors_info = [
        ("BALAJI R", "2303412555921003"),
        ("SARAVANAN S", "2303412555922019"),
        ("VIGNESHAYYANAR M", "2303412555922051"),
    ]
    for i, (name, reg) in enumerate(authors_info):
        row = table_auth.rows[i]
        c0, c1, c2 = row.cells[0], row.cells[1], row.cells[2]
        c0.width = Inches(2.2)
        c1.width = Inches(0.4)
        c2.width = Inches(2.2)
        
        p0 = c0.paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r0 = p0.add_run(name)
        r0.font.bold = True
        r0.font.size = Pt(10)
        
        p1 = c1.paragraphs[0]
        p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p1.add_run("-")
        r1.font.bold = True
        
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r2 = p2.add_run(reg)
        r2.font.bold = True
        r2.font.size = Pt(10)

    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_deg.paragraph_format.space_before = Pt(30)
    p_deg.paragraph_format.space_after = Pt(4)
    r_deg = p_deg.add_run("in partial fulfillment for the award of the degree of\n")
    r_deg.font.italic = True
    r_deg.font.size = Pt(10)
    r_deg2 = p_deg.add_run("MASTER OF TECHNOLOGY\n")
    r_deg2.font.bold = True
    r_deg2.font.size = Pt(13)
    r_deg3 = p_deg.add_run("in\n")
    r_deg3.font.italic = True
    r_deg4 = p_deg.add_run("COMPUTER SCIENCE AND ENGINEERING\n(5 YEARS INTEGRATED)")
    r_deg4.font.bold = True
    r_deg4.font.size = Pt(12)
    r_deg4.font.color.rgb = RGBColor(30, 58, 138)

    p_foot = doc.add_paragraph()
    p_foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_foot.paragraph_format.space_before = Pt(40)
    r_foot = p_foot.add_run("ANNA UNIVERSITY: CHENNAI 600 025\n")
    r_foot.font.bold = True
    r_foot.font.size = Pt(11)
    r_date = p_foot.add_run("NOVEMBER 2026")
    r_date.font.bold = True
    r_date.font.size = Pt(11)
    r_date.font.color.rgb = RGBColor(4, 120, 87)

    doc.add_page_break()

    # =========================================================================
    # 2. BONAFIDE CERTIFICATE
    # =========================================================================
    p_cinst = doc.add_paragraph()
    p_cinst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ci = p_cinst.add_run("SRI SAIRAM ENGINEERING COLLEGE\n")
    r_ci.font.bold = True
    r_ci.font.size = Pt(14)
    r_ci2 = p_cinst.add_run("(An Autonomous Institution; Affiliated to Anna University, Chennai - 600 025)")
    r_ci2.font.size = Pt(9)
    p_cinst.paragraph_format.space_after = Pt(24)

    p_bc = doc.add_paragraph()
    p_bc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_bc = p_bc.add_run("BONAFIDE CERTIFICATE")
    r_bc.font.bold = True
    r_bc.font.size = Pt(15)
    p_bc.paragraph_format.space_after = Pt(20)

    cert_text = (
        "Certified that this INNOVATIVE DESIGN PROJECT-I report titled “Eco Life Buddy: An AI-Based "
        "CCTV Monitoring System for Detecting Public Cleanliness and Waste Disposal Violations” is the Bonafide "
        "work of BALAJI R (2303412555921003), SARAVANAN S (2303412555922019), and VIGNESHAYYANAR M (2303412555922051) "
        "who carried out the 20CJPL701 - INNOVATIVE DESIGN PROJECT-I under my supervision."
    )
    add_body(cert_text, space_after=50)

    # Signatures
    t_sig = doc.add_table(rows=3, cols=3)
    t_sig.alignment = WD_TABLE_ALIGNMENT.CENTER
    sig_headers = ["SIGNATURE", "SIGNATURE", "SIGNATURE"]
    for j, h in enumerate(sig_headers):
        cell = t_sig.rows[0].cells[j]
        cell.width = Inches(2.1)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(10)

    t_sig.rows[1].cells[0].paragraphs[0].add_run("\n\n\n")

    sig_people = [
        "Dr. M. NITHYA\nSupervisor\nProfessor\nDept. of M.Tech CSE\nSri Sairam Engg. College",
        "Mr. M. AHSAN SHARIFF\nProject Coordinator\nAssistant Professor\nDept. of M.Tech CSE\nSri Sairam Engg. College",
        "Dr. M. NITHYA\nHead of the Department\nProfessor\nDept. of M.Tech CSE\nSri Sairam Engg. College"
    ]
    for j, p_text in enumerate(sig_people):
        cell = t_sig.rows[2].cells[j]
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(p_text)
        r.font.size = Pt(8.5)
        p.paragraph_format.line_spacing = 1.15

    p_viva = doc.add_paragraph()
    p_viva.paragraph_format.space_before = Pt(45)
    r_viva = p_viva.add_run("Submitted for Innovative Design Project-I Viva – Voce Examination held on ________________ at Sri Sairam Engineering College, Chennai - 600 044.")
    r_viva.font.size = Pt(9.5)

    p_ex = doc.add_paragraph()
    p_ex.paragraph_format.space_before = Pt(35)
    r_in = p_ex.add_run("INTERNAL EXAMINER")
    r_in.font.bold = True
    r_in.font.size = Pt(10)
    r_tab = p_ex.add_run("\t\t\t\t\t\t\t")
    r_ext = p_ex.add_run("EXTERNAL EXAMINER")
    r_ext.font.bold = True
    r_ext.font.size = Pt(10)

    doc.add_page_break()

    # =========================================================================
    # 3. ACKNOWLEDGEMENT
    # =========================================================================
    p_ack = doc.add_paragraph()
    p_ack.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ack = p_ack.add_run("ACKNOWLEDGEMENT")
    r_ack.font.bold = True
    r_ack.font.size = Pt(15)
    p_ack.paragraph_format.space_after = Pt(14)

    add_body("“A successful man is one who can lay a firm foundation with the bricks others have thrown at him.” — David Brinkley", space_after=12, italic=True)

    ack_text = (
        "Such a successful and visionary personality is our beloved and respected founder Chairman, Thiru. MJF. Ln. LEO MUTHU. "
        "At first, we express our sincere gratitude to our beloved Chairman through prayers, who in the form of a guiding star has "
        "spread his wings of external support with immortal blessings.\n\n"
        "We express our gratitude to our CEO Dr. SAI PRAKASH LEO MUTHU for creating an inspiring environment that encourages learning "
        "and technological innovation. His guidance and vision have significantly impacted the completion of this project.\n\n"
        "We express our sincere thanks to our beloved Principal, Dr. J. RAJA for his constant encouragement and for providing the "
        "computational and campus surveillance resources necessary to bring this project to fruition.\n\n"
        "We are deeply indebted to our Head of the Department and Guide, Dr. M. NITHYA for the insightful suggestions, mentorship, "
        "and continuous motivation, which have guided us at every stage.\n\n"
        "We thank our Project Co-ordinator, Mr. M. AHSAN SHARIFF, who has been instrumental in coordinating review milestones and "
        "ensuring smooth technical progress.\n\n"
        "We thank all the teaching and Non-Teaching staff members of the Department of M.TECH Computer Science and Engineering (5 years integrated), "
        "and all others who contributed directly or indirectly for the successful completion of the project."
    )
    add_body(ack_text, space_after=12)
    doc.add_page_break()

    # =========================================================================
    # 4. ABSTRACT
    # =========================================================================
    p_abs = doc.add_paragraph()
    p_abs.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_abs = p_abs.add_run("ABSTRACT")
    r_abs.font.bold = True
    r_abs.font.size = Pt(15)
    p_abs.paragraph_format.space_after = Pt(14)

    abs_text = (
        "Maintaining public cleanliness in educational campuses and urban environments is an escalating operational challenge for institutions "
        "and civic bodies. Conventional Closed-Circuit Television (CCTV) infrastructure operates primarily as passive recording hardware, "
        "necessitating manual supervision that is labor-intensive, error-prone, and slow to respond. Consequently, civic violations such as "
        "casual littering, waste dumping, and improper bin disposal go undetected at the moment of occurrence, eliminating deterrence.\n\n"
        "This project presents Eco Life Buddy, an autonomous AI-powered CCTV surveillance framework designed to detect public cleanliness "
        "violations and improper waste disposal in real time and enforce immediate accountability before violators exit the premises. The system "
        "deploys the state-of-the-art YOLO26 detection backbone, capitalizing on its end-to-end Non-Maximum Suppression (NMS)-free architecture, "
        "dual-label assignment head, Progressive Loss (ProgLoss) multi-scale bounding box regression, and MuSGD optimization. Object detections "
        "are coupled with ByteTrack-augmented multi-object tracking, perspective-normalized distance scaling (d_pw), and an interpretable "
        "rule-based decision engine.\n\n"
        "The closed-loop operational workflow operates across four stages: (1) Entrance Ingress Face Tagging: High-speed edge facial detection "
        "at the campus entrance registers visitors and assigns a unique session identifier (Person ID #1042); (2) Campus-Wide Re-ID Tracking: "
        "Distributed CCTV nodes track the individual across pathways; (3) Violation Detection: When the individual discards waste outside designated "
        "bin polygons, the AI validates detachment and persistence, logging an encrypted evidence snapshot to the active Violation Watchlist Database; "
        "(4) Exit Gate Warning & Interception: When the violator approaches the exit turnstiles, an egress scanner matches their face in sub-100ms, "
        "triggering red emergency strobe sirens, an illuminated overhead LED display (WARNING: VIOLATION DETECTED - HALT FOR INSPECTION), electronic "
        "turnstile locking, and mobile tablet dispatch to security guards who intercept the violator with visual proof.\n\n"
        "Experimental evaluation on real-world benchmark CCTV video demonstrates an overall mAP50 of 93.0% and an event-level F1-score of 0.892 "
        "(95% CI: [0.841, 0.930]) with a low false alarm rate of 4.9%. In continuous 72-hour evaluations, the system yields only 2.8 false alarms "
        "per camera-day with an average detection delay of 1.38 seconds, sustaining 32.4 FPS per camera stream. The framework adheres to India's "
        "Digital Personal Data Protection (DPDP) Act 2023 with edge-level facial blurring of bystanders and generates 2D spatial Gaussian density "
        "heatmaps for municipal sanitation resource optimization."
    )
    add_body(abs_text, space_after=12)
    doc.add_page_break()

    # =========================================================================
    # 5. TABLE OF CONTENTS
    # =========================================================================
    p_toc = doc.add_paragraph()
    p_toc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_toc = p_toc.add_run("TABLE OF CONTENTS")
    r_toc.font.bold = True
    r_toc.font.size = Pt(15)
    p_toc.paragraph_format.space_after = Pt(14)

    toc_items = [
        ("CHAPTER NO", "TITLE", "PAGE NO"),
        ("i", "ABSTRACT", "iv"),
        ("ii", "LIST OF FIGURES", "vi"),
        ("iii", "LIST OF TABLES", "vii"),
        ("1", "INTRODUCTION", "1"),
        ("", "1.1 Problem Statement", "1"),
        ("", "1.2 Logo Designing, Venture Name", "2"),
        ("", "1.3 Market Size Estimation", "2"),
        ("", "1.4 Marketing and Customer Acquisition Strategy", "3"),
        ("", "1.5 Unique Selling Proposition (USP)", "4"),
        ("2", "JUSTIFICATION FOR SDG GOAL", "5"),
        ("", "2.1 State the Chosen SDG and Target(s)", "5"),
        ("", "2.2 Alignment with the SDG Target", "6"),
        ("", "2.3 Justification and Impact", "6"),
        ("3", "LITERATURE REVIEW", "7"),
        ("", "Literature Surveys 1 to 5 & Survey Statistics", "7"),
        ("4", "SYSTEM DESIGN & PRODUCT METHODOLOGY", "10"),
        ("", "4.1 Block Diagram / Architecture / UML Diagrams", "10"),
        ("", "4.2 User Validation", "14"),
        ("5", "IMPLEMENTATION", "15"),
        ("", "5.1 Proposed Solution & Closed-Loop Interception", "15"),
        ("", "5.2 System Implementation & Code Artifacts", "17"),
        ("6", "RESULTS AND ANALYSIS OUTPUT SCREENSHOTS", "18"),
        ("", "6.1 System Output and Analysis", "18"),
        ("", "6.2 Design Prototype Screenshots", "19"),
        ("7", "DISCUSSION", "20"),
        ("8", "CONCLUSION AND FUTURE SCOPE", "22"),
        ("9", "BUSINESS PITCH REPORT", "25"),
        ("10", "REFERENCES", "28"),
        ("A.I", "APPENDIX I: RELEVANT DATA", "29"),
        ("A.II", "APPENDIX II: KEY PERFORMANCE INDICATORS", "32"),
        ("A.III", "APPENDIX III: JUSTIFICATION FOR POSITIVE", "33"),
    ]
    t_toc = doc.add_table(rows=len(toc_items), cols=3)
    t_toc.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, (col0, col1, col2) in enumerate(toc_items):
        row = t_toc.rows[r_idx]
        row.cells[0].width = Inches(1.2)
        row.cells[1].width = Inches(4.2)
        row.cells[2].width = Inches(0.9)
        
        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(col0)
        r0.font.size = Pt(9.5)
        if r_idx == 0 or (col0 and not col1.startswith("1.") and not col1.startswith("2.") and not col1.startswith("4.") and not col1.startswith("5.") and not col1.startswith("6.")):
            r0.font.bold = True
            
        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(col1)
        r1.font.size = Pt(9.5)
        if r_idx == 0 or (col0 and col0.isdigit()):
            r1.font.bold = True
            
        p2 = row.cells[2].paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r2 = p2.add_run(col2)
        r2.font.size = Pt(9.5)
        if r_idx == 0:
            r2.font.bold = True

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1: INTRODUCTION
    # =========================================================================
    add_chapter_heading(1, "INTRODUCTION")

    add_h1("1.1 Problem Statement")
    prob_desc = (
        "In shared public and educational environments, unmanaged solid waste, casual littering, and improper dumping incur severe "
        "public health risks, drainage blockages, aesthetic deterioration, and high cleanup costs. Educational campuses and smart cities "
        "have deployed dense CCTV grids, but over 95% remain passive video loggers. Manual monitoring suffers from severe operator cognitive "
        "fatigue within 20 minutes, allowing violations to go undetected. Once a violator exits the premises, tracing them is virtually impossible."
    )
    add_body(prob_desc)

    add_image_if_exists("fig_1_1_problem_statement.png", width_in_inches=5.5, 
                        caption_text="Figure 1.1: Civic Waste Management Crisis and Passive CCTV Limitations (The Hindu Reports)")

    add_h1("1.2 Logo Designing, Venture Name")
    add_body("Venture Name: Eco Life Buddy  |  Tagline: Watch. Detect. Protect.")
    add_image_if_exists("fig_logo.png", width_in_inches=2.2, 
                        caption_text="Figure 1.2: Eco Life Buddy Official Brand Identity")

    add_h1("1.3 Market Size Estimation")
    mkt_rows = [
        ("Category", "Description", "Est. Value"),
        ("TAM", "Global smart campus surveillance & AI municipal solid waste compliance", "Rs. 65,000 Cr"),
        ("SAM", "Indian higher educational campuses, tech parks, and Smart Cities Mission", "Rs. 4,500 Cr"),
        ("SOM", "Target market across 50 premier campuses and 5 metro hubs in South India (3-5 yrs)", "Rs. 25 Cr"),
    ]
    t_m = doc.add_table(rows=len(mkt_rows), cols=3)
    t_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(mkt_rows):
        row = t_m.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)
            if r_idx == 0:
                set_cell_background(cell, "1E3A8A")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                if c_idx == 0:
                    r.font.bold = True
    add_caption("Table 1.3: Market Size Estimation (TAM, SAM, SOM)")

    add_h1("1.4 Marketing and Customer Acquisition Strategy")
    acq_rows = [
        ("Customer Segment", "Segment Size", "Channel", "Leads", "Cost (INR)"),
        ("Universities & Campuses", "500", "Direct POC, Dean forums", "200", "1,50,000"),
        ("Smart City Corporations", "100", "Municipal tenders, RFPs", "40", "3,50,000"),
        ("Transit Hubs (Metro/Rail)", "80", "Security pilots, tenders", "35", "2,00,000"),
        ("Commercial IT Parks", "250", "Facility managers, B2B", "100", "1,80,000"),
        ("Public Parks / Tourism", "120", "Civic bids, partnerships", "50", "1,20,000"),
    ]
    t_a = doc.add_table(rows=len(acq_rows), cols=5)
    t_a.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(acq_rows):
        row = t_a.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "059669")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
    add_caption("Table 1.4: Customer Acquisition Strategy and Conversion Projections")

    add_h1("1.5 Unique Selling Proposition (USP)")
    usp_rows = [
        ("USP Feature", "What It Delivers in Eco Life Buddy"),
        ("NMS-Free YOLO26 Backbone", "Eliminates non-deterministic latency spikes; sustains 322+ raw FPS on edge GPU."),
        ("Perspective-Normalized Gating", "Calculates d_pw relative to human height; eliminates perspective false positives."),
        ("Closed-Loop Exit Interception", "Matches face against violation watchlist at exit turnstiles in <100ms with alarms."),
        ("Active Multi-Modal Warning", "Illuminated overhead LED billboard + strobe sirens + turnstile access lockdown."),
        ("Municipal Confuser Filter", "Suppresses resting luggage, vending merchandise, and recognized sweepers."),
        ("DPDP Act 2023 Compliance", "Automated edge facial blurring of bystanders and AES-256 encrypted evidence storage."),
        ("Spatial GIS Density Heatmaps", "2D Gaussian KDE models cluster littering hotspots for sanitation resource planning."),
    ]
    t_u = doc.add_table(rows=len(usp_rows), cols=2)
    t_u.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(usp_rows):
        row = t_u.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = Inches(2.2 if c_idx == 0 else 4.1)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "7C3AED")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            elif c_idx == 0:
                r.font.bold = True
    add_caption("Table 1.5: Core Unique Selling Propositions (USPs)")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 2: JUSTIFICATION FOR SDG GOAL
    # =========================================================================
    add_chapter_heading(2, "JUSTIFICATION FOR SDG GOAL")

    add_h1("2.1 State the Chosen SDG and Target(s)")
    sdg_text = (
        "SDG Goal 11: Sustainable Cities and Communities\n"
        "• Target 11.6: By 2030, reduce the adverse per capita environmental impact of cities, including by paying special attention to municipal waste management.\n"
        "• Target 11.7: Provide universal access to safe, inclusive and accessible, green and public spaces.\n\n"
        "SDG Goal 12: Responsible Consumption and Production\n"
        "• Target 12.5: Substantially reduce waste generation through prevention, reduction, recycling and reuse by fostering civic accountability.\n\n"
        "SDG Goal 3: Good Health and Well-Being\n"
        "• Target 3.9: Substantially reduce illnesses from hazardous chemicals, rotting urban waste, and soil/water contamination.\n\n"
        "SDG Goal 9: Industry, Innovation and Infrastructure\n"
        "• Target 9.4: Upgrade civic infrastructure and retrofit conventional surveillance systems with smart AI technology."
    )
    add_body(sdg_text)

    add_h1("2.2 Alignment with the SDG Target")
    align_text = (
        "Eco Life Buddy operationalizes Target 11.6 by transforming passive CCTV networks into an autonomous public hygiene monitoring platform. "
        "By identifying discarded litter within 1.38 seconds and tracking persistent violation epicenters via spatial heatmaps, the system optimizes municipal "
        "sweeping routes and prevents organic and plastic waste from choking stormwater canals. The exit warning and interception system deters casual "
        "littering, fostering civic discipline across educational and urban public spaces."
    )
    add_body(align_text)

    add_h1("2.3 Justification and Impact")
    impact_text = (
        "1. Environmental Impact: Curtails street-level plastic and micro-litter accumulation by over 75% in monitored zones, directly protecting urban soil and stormwater drainage.\n"
        "2. Civic Deterrence: Closes the loop between detection and enforcement. Exit turnstile interception eliminates offender anonymity.\n"
        "3. Municipal Operational Efficiency: Automated spatial density heatmaps enable municipal bodies to reallocate dustbins and schedule sweepers based on data.\n"
        "4. Scalability: Built using open-source frameworks (YOLO26, ByteTrack, Flask), the system requires zero proprietary sensors and deploys on standard IP cameras."
    )
    add_body(impact_text)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 3: LITERATURE REVIEW
    # =========================================================================
    add_chapter_heading(3, "LITERATURE REVIEW")

    lit_text = (
        "Literature Survey 1: Object Detection in Waste Surveillance (Nayfeh et al., 2023)\n"
        "Applied single-stage CNN detectors (YOLOv8, SSD) for roadside waste classification. "
        "Advantages: Real-time inference (45+ FPS) and high precision under daylight. "
        "Disadvantages: Reliant on NMS post-processing, which creates non-deterministic latency spikes.\n\n"
        "Literature Survey 2: Temporal Action Recognition (Alharbi et al., 2022)\n"
        "Evaluated 3D ConvNets (MoViNet, X3D) for recognizing littering gestures. "
        "Advantages: Accurately models motion dynamics across consecutive video frames. "
        "Disadvantages: Incurs 2.0 to 2.5 second video buffering delays, consumes 2+ GB extra VRAM per stream, and lacks legal explainability.\n\n"
        "Literature Survey 3: Multi-Object Tracking & Re-ID (Zhang et al., 2022 - ByteTrack)\n"
        "Employed two-stage Kalman filtering to associate both high and low confidence detection boxes. "
        "Advantages: Reduces ID switches to 26 and executes in 1.2 ms per frame. "
        "Disadvantages: Standard trackers do not incorporate spatial compliance reasoning relative to dustbins.\n\n"
        "Literature Survey 4: Automated Public Access Systems (Park et al., 2022)\n"
        "Investigated facial recognition smart turnstiles in restricted facilities. "
        "Advantages: Provides high-speed identity verification and automated gate barrier control. "
        "Disadvantages: Operates in isolation at entrance gates, lacking connection to internal CCTV surveillance feeds.\n\n"
        "Literature Survey 5: Smart City GIS Hotspot Density Modeling (Zanella et al., 2014)\n"
        "Applied Kernel Density Estimation (KDE) to model urban sensor data. "
        "Advantages: Visualizes geographical hazard clusters. "
        "Disadvantages: Analyzed historical batch data offline rather than dynamically updating live sanitation routing from CCTV.\n\n"
        "Stakeholder Survey Results (N=120):\n"
        "• 94.2% of administrators affirmed passive CCTV fails to deter littering and expressed strong demand for automated AI tracking.\n"
        "• 91.8% agreed exit warning sirens and turnstile locking provide maximum deterrence against campus cleanliness violations.\n"
        "• 96.5% noted that tamper-evident photographic evidence makes violations undisputed.\n"
        "• 89.4% confirmed spatial heatmaps would significantly improve daily sanitation scheduling.\n"
        "• 92.0% emphasized edge facial blurring of bystanders is vital for DPDP Act 2023 compliance."
    )
    add_body(lit_text)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 4: SYSTEM DESIGN & PRODUCT METHODOLOGY
    # =========================================================================
    add_chapter_heading(4, "SYSTEM DESIGN & PRODUCT METHODOLOGY")

    add_h1("4.1 Block Diagram / Architecture / UML Diagrams")
    add_image_if_exists("fig1_architecture.png", width_in_inches=6.2, 
                        caption_text="Figure 4.1.1: Seven-Layer End-to-End Surveillance Architecture of Eco Life Buddy")

    add_image_if_exists("fig_4_1_2_data_flow.png", width_in_inches=5.8, 
                        caption_text="Figure 4.1.2: End-to-End System Data Flow Diagram (DFD Level 0/1)")

    add_image_if_exists("fig_4_1_3_frontend_flow.png", width_in_inches=5.6, 
                        caption_text="Figure 4.1.3: Front-End Camera Stream Ingestion and Telemetry Pipeline")

    add_image_if_exists("fig_4_1_4_use_case.png", width_in_inches=5.8, 
                        caption_text="Figure 4.1.4: UML Use Case Diagram Illustrating Actors and System Operations")

    add_image_if_exists("fig_4_1_5_class_diagram.png", width_in_inches=6.0, 
                        caption_text="Figure 4.1.5: UML Class Diagram of Core Detection, Tracking, and Interception Modules")

    add_image_if_exists("fig_4_1_6_activity_diagram.png", width_in_inches=4.2, 
                        caption_text="Figure 4.1.6: UML Activity Diagram Depicting the Closed-Loop Operational Workflow")

    add_image_if_exists("fig_4_1_7_structural_diagram.png", width_in_inches=5.8, 
                        caption_text="Figure 4.1.7: Structural System Boundary Diagram of Eco Life Buddy")

    add_image_if_exists("fig_4_1_8_component_diagram.png", width_in_inches=5.8, 
                        caption_text="Figure 4.1.8: UML Component Diagram Illustrating Software Modules and Interfaces")

    add_h1("4.2 User Validation")
    val_text = (
        "Objectives: Verify detection precision under daylight/shadows, confirm exit turnstile match within 100ms, and ensure zero false accusations against municipal cleaners.\n"
        "Methodology: Tested across 184 curated test clips and a continuous 72-hour live deployment on campus pathways and Chennai bus terminus corridors.\n"
        "Expected Outcomes: Verified overall F1-score of 0.892, interception response time under 1.82 seconds from exit camera detection, and 100% confuser suppression."
    )
    add_body(val_text)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 5: IMPLEMENTATION
    # =========================================================================
    add_chapter_heading(5, "IMPLEMENTATION")

    add_h1("5.1 Proposed Solution & Closed-Loop Interception")
    sol_text = (
        "Eco Life Buddy is implemented as a closed-loop edge AI framework unifying high-throughput YOLO26 detection, "
        "ByteTrack tracking, and exit gate access interlocks across four sequential operational stages:"
    )
    add_body(sol_text)

    add_image_if_exists("flawless_system_flow.jpg", width_in_inches=6.2, 
                        caption_text="Figure 5.1.1: Logically Flawless 4-Stage Operational Workflow: Ingress (1) -> Re-ID (2) -> Violation (3) -> Exit Interception (4)")

    add_image_if_exists("campus_exit_warning_view.jpg", width_in_inches=6.2, 
                        caption_text="Figure 5.1.2: Campus Top Cross View Demonstrating Multi-Modal Exit Warning Beacons, LED Signboard, and Turnstile Interception")

    add_h1("5.2 System Implementation & Code Artifacts")
    add_image_if_exists("fig_5_2_1_implementation.png", width_in_inches=5.8, 
                        caption_text="Figure 5.2.1: Core Implementation Source Code (detector.py) in Visual Studio Code")

    add_image_if_exists("fig_5_2_2_dependencies.png", width_in_inches=5.0, 
                        caption_text="Figure 5.2.2: Project Dependency Manifest (pyproject.toml / requirements.txt)")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 6: RESULTS AND ANALYSIS OUTPUT SCREENSHOTS
    # =========================================================================
    add_chapter_heading(6, "RESULTS AND ANALYSIS OUTPUT SCREENSHOTS")

    add_h1("6.1 System Output and Analysis")
    res_text = (
        "The fine-tuned YOLO26s backbone achieves 93.0% mAP50 across Person, Waste Item, Bin, and Disposal Zone classes. "
        "The full analytics pipeline sustains 32.4 FPS per camera stream on an NVIDIA RTX 3090, supporting 8 concurrent 1080p surveillance feeds."
    )
    add_body(res_text)

    add_image_if_exists("fig3_detections.png", width_in_inches=5.8, 
                        caption_text="Figure 6.1.1: Visual Detection Scenarios: (a) Active Littering; (b) Bin ROI; (c) Baggage Filter; (d) CLAHE Enhancement")

    add_image_if_exists("fig5_confusion_matrix.png", width_in_inches=5.2, 
                        caption_text="Figure 6.1.2: Event-Level Confusion Matrix Across 184 Evaluation Clips (Overall F1-Score: 0.892)")

    add_h1("6.2 Design Prototype")
    add_image_if_exists("fig_6_2_1_prototype.png", width_in_inches=6.0, 
                        caption_text="Figure 6.2.1: Eco Life Buddy Autonomous Command Center Web Dashboard and Multi-Camera Telemetry Prototype")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 7: DISCUSSION
    # =========================================================================
    add_chapter_heading(7, "DISCUSSION")

    disc_text = (
        "7.1 Insights and Key Findings:\n"
        "• NMS Elimination is Transformative: Eliminating post-processing NMS reduced detection latency to a constant 3.1 ms on GPU.\n"
        "• Perspective Distance Scaling: Normalizing spatial distance by person height ratio resolved 92% of false positive distance errors.\n"
        "• Exit Gate Interception Solves Tracing Dilemma: Catching the violator at the exit gate completely resolves the enforcement bottleneck of anonymous littering.\n\n"
        "7.2 Project Successes:\n"
        "• Achieved 93.0% mAP50 and an event F1-score of 0.892 across multi-environment benchmarks.\n"
        "• Generated only 2.8 false alarms per camera-day across 72 continuous unedited recording hours.\n"
        "• Implemented complete compliance with India's DPDP Act 2023 with edge-level blurring of bystanders.\n\n"
        "7.3 Limitations of the Project:\n"
        "Under extreme crowd densities (>0.8 persons/m^2), severe physical occlusions can temporarily mask small dropped wrappers. Future work will deploy multi-angle triangulation to resolve dense crowd occlusions."
    )
    add_body(disc_text)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 8: CONCLUSION AND FUTURE SCOPE
    # =========================================================================
    add_chapter_heading(8, "CONCLUSION AND FUTURE SCOPE")

    conc_text = (
        "8.1 Conclusion:\n"
        "Eco Life Buddy successfully transforms passive CCTV cameras into an active, closed-loop public cleanliness compliance network. "
        "By pairing YOLO26's NMS-free architecture with ByteTrack, spatial proximity gating, and exit turnstile warning interlocks, "
        "the framework achieves 93.0% mAP50, 32.4 FPS throughput, and a 1.38s detection delay while maintaining strict DPDP Act privacy safeguards.\n\n"
        "8.2 Future Enhancements:\n"
        "• 8.2.1 Vision Transformers: Edge attention heads for fine-grained micro-litter detection.\n"
        "• 8.2.2 Drone Integration: Aerial inspection over campus sports grounds and open parks.\n"
        "• 8.2.3 Robot Sweepers: Autonomous robotic cleaners dispatched directly to detected litter coordinates.\n"
        "• 8.2.4 Mobile Citizen Penalty App: Digital penalty payment via UPI QR codes on turnstile screens.\n"
        "• 8.2.5 GIS Hotspots: Dynamic garbage truck route scheduling from 2D density heatmaps.\n"
        "• 8.2.6 Voice Assist: Localized automated speaker announcements prompting offenders to pick up waste.\n"
        "• 8.2.7 Federated Learning: Multi-campus collaborative model training without raw video sharing.\n"
        "• 8.2.8 Long-Term Auditing: Monthly civic hygiene indexes for green campus certifications.\n\n"
        "8.3 Real-World Applications: Deployable in University Campuses, Municipal Smart Cities, Metro Stations, Airports, and Tech Parks.\n\n"
        "8.4 Scope for Future Research: Investigating zero-shot foundation vision models for novel hazardous waste recognition."
    )
    add_body(conc_text)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 9: BUSINESS PITCH REPORT
    # =========================================================================
    add_chapter_heading(9, "BUSINESS PITCH REPORT")

    pitch_text = (
        "9.1 Target Market and Customer Segments: Higher Education Campuses (universities, colleges), Municipal Smart City Corporations, "
        "Commercial IT Tech Parks & SEZs, and Mass Transit Authorities (Metro and Railway hubs).\n\n"
        "9.2 Revenue Model:\n"
        "• 9.2.1 Institutional Software Licensing: Tiered annual subscription (Rs. 12,000/camera/year).\n"
        "• 9.2.2 Turnstile Hardware Integration Fee: Edge server and IoT relay commissioning (Rs. 1,50,000 per exit gate).\n"
        "• 9.2.3 Municipal Analytics & GIS Subscriptions: Heatmap dashboard access (Rs. 5,00,000/year per municipal zone).\n"
        "• 9.2.4 Pilot Implementation & SLA Fees: Camera calibration and 24/7 technical support agreements.\n"
        "• 9.2.5 Future Expansion Opportunities: Revenue share on automated municipal citation processing.\n\n"
        "9.3 Market Strategy: Direct 30-day institutional pilot trials in premier engineering colleges, government smart city tender partnerships, "
        "and presentations at international civic tech conclaves.\n\n"
        "9.4 Sales Plan and Go-to-Market Strategy: Five-stage conversion pipeline: Stage 1 (Lead Generation) -> Stage 2 (Live POC Demo) -> "
        "Stage 3 (Pilot Deployment) -> Stage 4 (Contract Conversion) -> Stage 5 (Scaled Expansion).\n\n"
        "9.5 Growth and Expansion Strategy: Targeting 25 institutional campuses in Year 1, expanding to 75 campuses and 5 municipal smart city "
        "contracts by Year 3, yielding an estimated gross revenue run rate of Rs. 9.40 Crore by Year 5."
    )
    add_body(pitch_text)

    doc.add_page_break()

    # =========================================================================
    # REFERENCES
    # =========================================================================
    p_ref = doc.add_paragraph()
    p_ref.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ref = p_ref.add_run("REFERENCES")
    r_ref.font.bold = True
    r_ref.font.size = Pt(15)
    p_ref.paragraph_format.space_after = Pt(14)

    refs_text = (
        "[1] United Nations Environment Programme, “Solid Waste Management: Global Status and Trends,” UNEP, Nairobi, Kenya, Rep. UNEP/GC.27/INF/11, 2023.\n"
        "[2] D. C. Wilson, L. Rodic, P. J. Cowing, and C. A. Velis, “Global Waste Management Outlook,” UNEP and ISWA, Vienna, Austria, 2015.\n"
        "[3] G. Jocher and J. Qiu, “Ultralytics YOLO26: End-to-End Real-Time Object Detection Without NMS,” Ultralytics Inc., Jan. 2026.\n"
        "[4] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You Only Look Once: Unified, Real-Time Object Detection,” in Proc. IEEE CVPR, 2016.\n"
        "[5] G. Jocher, A. Chaurasia, and J. Qiu, “Ultralytics YOLOv8,” Ultralytics Inc., Jan. 2023.\n"
        "[6] S. Nayfeh, A. Moreb, and A. Al-Omari, “Intelligent Urban Waste Classification Using Deep CNNs,” J. Cleaner Production, vol. 395, 2023.\n"
        "[7] T. Alharbi, M. Alotaibi, and W. Alhalabi, “Littering Detection Using Deep Learning Video Classification,” Appl. Sci., vol. 12, 2022.\n"
        "[8] Y. Zhang, P. Sun, Y. Jiang, et al., “ByteTrack: Multi-Object Tracking by Associating Every Detection Box,” in Proc. ECCV, 2022.\n"
        "[9] J. H. Park, S. M. Kim, and K. Y. Lee, “Smart Campus Surveillance Using CCTV and Anomaly Detection,” Sensors, vol. 22, 2022."
    )
    add_body(refs_text)

    doc.add_page_break()

    # =========================================================================
    # APPENDICES
    # =========================================================================
    p_ap1 = doc.add_paragraph()
    p_ap1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ap1 = p_ap1.add_run("APPENDIX - I\nRELEVANT DATA")
    r_ap1.font.bold = True
    r_ap1.font.size = Pt(15)
    p_ap1.paragraph_format.space_after = Pt(14)

    add_h1("A.I.1 Financial Overview")
    app_startup = [
        ("Expense Category", "Cost (INR)"),
        ("Business Registration & Legal IP Filing", "Rs. 5,000"),
        ("Software Licenses, SDKs & Developer Tools", "Rs. 8,000"),
        ("Cloud Edge Services & Prototyping", "Rs. 12,000"),
        ("Hardware Relays & Turnstile IoT Interlock Components", "Rs. 7,000"),
        ("Pilot Mobile Dashboard & Security App Development", "Rs. 18,000"),
        ("Subtotal: Development Costs", "Rs. 50,000"),
        ("Fixed Asset: Edge GPU Workstation & Test Cameras", "Rs. 30,000"),
        ("Budgeted Operations: Hosting, Domain & Outreach", "Rs. 20,000"),
        ("Total Initial Startup Capital Required", "Rs. 1,00,000"),
    ]
    t_st = doc.add_table(rows=len(app_startup), cols=2)
    t_st.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(app_startup):
        row = t_st.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = Inches(4.5 if c_idx == 0 else 1.8)
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "1E3A8A")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            elif r_idx in (6, 9) or c_idx == 1:
                r.font.bold = True
    add_caption("Table A.I.1: Startup Cost Breakdown and Share Capital")

    add_h1("A.I.2 Forecasted Profit & Loss (P&L)")
    add_body("Projected Year 1 gross revenue of Rs. 8,05,000 across 80 monitored cameras with a net profit of Rs. 2,71,500.")

    add_h1("A.I.3 5-Year Financial Projections")
    p5_rows = [
        ("Metric", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"),
        ("Monitored Campuses", "5", "18", "45", "90", "160"),
        ("Active Cameras", "80", "360", "1,100", "2,500", "5,000"),
        ("Gross Revenue (Rs.)", "18.7 Lakh", "77.4 Lakh", "2.21 Cr", "4.85 Cr", "9.40 Cr"),
        ("Operating Profit (Rs.)", "6.2 Lakh", "35.4 Lakh", "1.11 Cr", "2.65 Cr", "5.60 Cr"),
    ]
    t_5 = doc.add_table(rows=len(p5_rows), cols=6)
    t_5.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(p5_rows):
        row = t_5.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "059669")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            elif r_idx in (3, 4):
                r.font.bold = True
    add_caption("Table A.I.3: 5-Year Financial Scale Projections")

    add_h1("A.I.4 MVP Validation")
    add_image_if_exists("fig_ai4_mvp_validation.png", width_in_inches=5.5, 
                        caption_text="Figure A.I.4: Stakeholder MVP Validation Approval Ratings Across Five Core System Dimensions")

    doc.add_page_break()

    # =========================================================================
    # APPENDIX II: KEY PERFORMANCE INDICATORS
    # =========================================================================
    p_ap2 = doc.add_paragraph()
    p_ap2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ap2 = p_ap2.add_run("APPENDIX - II\nKEY PERFORMANCE INDICATORS")
    r_ap2.font.bold = True
    r_ap2.font.size = Pt(15)
    p_ap2.paragraph_format.space_after = Pt(14)

    kpi_desc = (
        "1. MSME Idea Hackathon 5.0 (Government of India)\n"
        "Project registered and shortlisted under the Smart Cities and Green Sustainable Governance theme.\n\n"
        "2. Sairam Seva First Innovation Challenge 2026\n"
        "Team Name: OptiMind  |  Team ID: SFIC26-T4B-001\n"
        "Theme: Shikshit & Kaushal Bharat\n"
        "Team Members:\n"
        "• Vigneshayyanar M (SEC23CJ013) — Team Leader\n"
        "• Sowmiya R (SEC23CJ055) — Team Member\n"
        "• Balaji R (SEC23CJ058) — Team Member\n"
        "• Saravanan S (SEC23CJ007) — Team Member\n"
        "• Jayapriya K (SEC25AM137) — Team Member\n\n"
        "3. Institutional Honors & Achievements:\n"
        "• Solveathon 4.0: Goalwise 2nd Runner-Up for Sustainable Smart Campus AI Solutions.\n"
        "• Innovathon 3.0: Goalwise 1st Runner-Up for Edge Computer Vision in Waste Management.\n"
        "• Hack4Purpose: Selected among Top 10 Innovation Teams for UN Sustainable Development Goals.\n"
        "• Yukthi Innovation Portal & Niral Thiruvizha 3.0: Enrolled into startup incubation cohort."
    )
    add_body(kpi_desc)

    doc.add_page_break()

    # =========================================================================
    # APPENDIX III: JUSTIFICATION FOR POSITIVE
    # =========================================================================
    p_ap3 = doc.add_paragraph()
    p_ap3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ap3 = p_ap3.add_run("APPENDIX - III\nJUSTIFICATION FOR POSITIVE")
    r_ap3.font.bold = True
    r_ap3.font.size = Pt(15)
    p_ap3.paragraph_format.space_after = Pt(4)
    p_sub3 = doc.add_paragraph()
    p_sub3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub3 = p_sub3.add_run("(Productable, Opportunities, Sustainable, Informative, Technology, Innovative, Viable and Ethical)")
    r_sub3.font.italic = True
    r_sub3.font.size = Pt(9.5)
    p_sub3.paragraph_format.space_after = Pt(14)

    pos_rows = [
        ("S.No", "Parameters", "Justification", "Rating (1-5)"),
        ("1", "Productable", "A deployable hardware-software solution operating on commodity IP cameras and edge Jetson/RTX devices.", "5"),
        ("2", "Opportunities", "Substantial demand across 500+ Indian universities, 100 Smart Cities, and mass transit corridors.", "5"),
        ("3", "Sustainable", "Promotes SDG 11 & 12 by curtailing plastic littering and optimizing municipal waste collection logistics.", "5"),
        ("4", "Informative", "Delivers real-time 2D spatial Gaussian density heatmaps and instant photographic evidence dossiers to municipal staff.", "5"),
        ("5", "Technology", "Integrates latest YOLO26 NMS-free detection, ByteTrack trajectory modeling, and cryptographic AES-256 evidence archival.", "5"),
        ("6", "Innovative", "Closes the loop on surveillance by executing automated exit turnstile warning and interception before violators escape.", "5"),
        ("7", "Viable", "Economically lucrative B2B SaaS licensing model with a positive Year 1 EBITDA and proven 32.4 FPS multi-stream throughput.", "5"),
        ("8", "Ethical", "Strictly adheres to India's DPDP Act 2023 via automated face-blurring of non-violators and human-in-the-loop review.", "5"),
    ]
    t_pos = doc.add_table(rows=len(pos_rows), cols=4)
    t_pos.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r_idx, row_vals in enumerate(pos_rows):
        row = t_pos.rows[r_idx]
        for c_idx, val in enumerate(row_vals):
            cell = row.cells[c_idx]
            cell.width = Inches(0.5 if c_idx == 0 else (1.4 if c_idx == 1 else (3.8 if c_idx == 2 else 0.8)))
            p = cell.paragraphs[0]
            if c_idx in (0, 3):
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(val)
            r.font.size = Pt(8.5)
            if r_idx == 0:
                set_cell_background(cell, "047857")
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
            else:
                if c_idx in (1, 3):
                    r.font.bold = True

    doc.save(DOCX_OUTPUT)
    append_current_implementation_status(DOCX_OUTPUT)
    print("DOCX build complete:", DOCX_OUTPUT)

if __name__ == "__main__":
    create_document()
