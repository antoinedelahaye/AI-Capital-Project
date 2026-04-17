"""
generate_water_quotes_pdf.py

Generates professional PDF quote documents for 4 water industry capital projects.
Pricing benchmarked against AMP8 (2025-2030) UK water industry data.
"""

import os
from datetime import date
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# ── Output directory ───────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "quotes_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Colour palette ─────────────────────────────────────────────────────────────
BRAND_BLUE   = colors.HexColor("#003B6F")   # deep utility blue
ACCENT_BLUE  = colors.HexColor("#0072BC")   # lighter accent
LIGHT_GREY   = colors.HexColor("#F2F4F7")
MID_GREY     = colors.HexColor("#8A97A8")
TEXT_DARK    = colors.HexColor("#1A1A2E")
GREEN_OK     = colors.HexColor("#1B7A34")
RED_ALERT    = colors.HexColor("#C0392B")
WHITE        = colors.white

# ── Quote data ─────────────────────────────────────────────────────────────────
QUOTES = [
    {
        "ref":        "WQ-2026-001",
        "date":       date(2026, 2, 14),
        "valid_until": date(2026, 5, 14),
        "client":     "Severn Trent Water Ltd",
        "client_ref": "STW/AMP8/WTW/2026-041",
        "supplier":   "Veolia Water Technologies UK Ltd",
        "supplier_addr": "Porterstown Road, Clonsilla, Dublin / UK Office: Birmingham B7 4BJ",
        "contact":    "James Hartley | j.hartley@veolia.com | +44 121 555 0194",
        "project":    "AMP8 Water Treatment Works Capacity Enhancement — Frankley WTW",
        "category":   "Water Treatment Infrastructure",
        "description": (
            "Design, supply, and installation of capacity enhancement works at Frankley WTW "
            "to increase treated water output by 30 ML/day. Scope includes UV disinfection, "
            "enhanced coagulation/flocculation, dissolved air flotation (DAF) units, and "
            "full SCADA/control system upgrade. Includes commissioning, 12-month defects "
            "liability, and operator training programme."
        ),
        "line_items": [
            ("UV Disinfection Units — Trojan UV3000Plus (×4)", 4, "No.", 1_250_000.00),
            ("Dissolved Air Flotation (DAF) Units, 15 ML/day capacity (×2)", 2, "No.", 2_480_000.00),
            ("Enhanced Coagulation & Flocculation Dosing System", 1, "Item", 1_920_000.00),
            ("SCADA / Control System Upgrade & Integration", 1, "Item", 1_310_000.00),
            ("Civil & Structural Works (tankage, pipework, platforms)", 1, "Item", 3_450_000.00),
            ("Electrical & Mechanical Installation", 1, "Item", 1_870_000.00),
            ("Commissioning, Testing & Performance Verification", 1, "Item",   880_000.00),
            ("Operator Training Programme & O&M Documentation", 1, "Item",   340_000.00),
        ],
        "notes": [
            "Prices are fixed-price lump sums inclusive of design, supply, and installation.",
            "Provisional sum for ground investigation works: £180,000 (to be confirmed).",
            "Programme: 22 months from NTP. Works to be phased to maintain supply continuity.",
            "Exclusions: land acquisition, statutory consents, third-party diversions.",
            "Payment terms: 30% mobilisation, monthly valuations, 5% retention released after DLP.",
        ],
        "currency": "GBP",
    },
    {
        "ref":        "WQ-2026-002",
        "date":       date(2026, 1, 20),
        "valid_until": date(2026, 4, 20),
        "client":     "Yorkshire Water Services Ltd",
        "client_ref": "YW/CAP/PIPE/2026-018",
        "supplier":   "Murphy Water Infrastructure Ltd",
        "supplier_addr": "Hiview House, Highgate Road, London NW5 1TN",
        "contact":    "Sarah Nolan | s.nolan@murphygroup.co.uk | +44 20 7267 0300",
        "project":    "Northern Transfer Scheme Phase 2 — Washburn to Eccup DN500 Strategic Main",
        "category":   "Pipeline Infrastructure",
        "description": (
            "Construction of a new 8.2 km DN500 ductile iron strategic water main from "
            "Washburn Treatment Works to Eccup Service Reservoir, including six inline valve "
            "chambers, one horizontal directional drill (HDD) river crossing beneath the River "
            "Wharfe, full cathodic protection system, and statutory reinstatement. Works form "
            "part of Yorkshire Water's AMP8 strategic interconnection programme."
        ),
        "line_items": [
            ("DN500 Ductile Iron Pipe — supply and lay (8,200 m @ £1,420/m)", 8200, "m", 1_420.00),
            ("Inline Valve Chambers — PN16 butterfly valves, concrete chamber (×6)", 6, "No.", 82_000.00),
            ("HDD River Crossing — River Wharfe (220 m, DN500)", 1, "Item", 1_380_000.00),
            ("Cathodic Protection System — sacrificial anode impressed current", 1, "Item",   545_000.00),
            ("Pressure Testing, Commissioning & Chlorination", 1, "Item",   285_000.00),
            ("Highway & Statutory Reinstatement (A659 corridor)", 1, "Item",   620_000.00),
            ("Environmental Mitigation & Site Restoration", 1, "Item",   310_000.00),
        ],
        "notes": [
            "Unit rate for pipe supply and lay based on Q1 2026 material indices (CECA).",
            "HDD pricing subject to ground investigation results; variance mechanism applies.",
            "Programme: 16 months from NTP. Traffic management strategy pre-agreed with WYCA.",
            "All works to comply with Water Regulations 2016 and Specification for the Reinstatement of Openings in Highways (SROH).",
            "Exclusions: statutory undertaker diversions, land access agreements, archaeological watching brief.",
        ],
        "currency": "GBP",
    },
    {
        "ref":        "WQ-2025-003",
        "date":       date(2025, 11, 7),
        "valid_until": date(2026, 2, 7),
        "client":     "Anglian Water Services Ltd",
        "client_ref": "AW/WW/PS/2025-097",
        "supplier":   "Jacobs Engineering Group UK Ltd",
        "supplier_addr": "1 The Village, Westbury-on-Trym, Bristol BS9 3NQ",
        "contact":    "Dr Priya Mehta | priya.mehta@jacobs.com | +44 117 940 5500",
        "project":    "Wastewater Network Resilience Programme — Peterborough East SPS Replacement",
        "category":   "Pumping Infrastructure",
        "description": (
            "Full decommission and replacement of the existing Peterborough East Sewage "
            "Pumping Station (SPS). Scope covers new wet well (reinforced concrete caisson, "
            "8.5m dia.), duty/standby KSB Amarex NFK submersible pump sets (450 kW each), "
            "2.1 km DN400 uPVC rising main, 500 kVA standby generator, MCC/electrical "
            "installation, telemetry integration with Anglian Water's AMI network, and "
            "decommissioning of the existing facility."
        ),
        "line_items": [
            ("Wet Well Construction — RC caisson 8.5m dia., depth 12m", 1, "Item", 1_920_000.00),
            ("KSB Amarex NFK Submersible Pump Sets 450 kW — duty/standby (×2)", 2, "No.",   345_000.00),
            ("DN400 uPVC Rising Main — supply and lay (2,100 m)", 2100, "m",      680.00),
            ("Standby Generator — Cummins C500D5 500 kVA, acoustic enclosure", 1, "No.",   198_000.00),
            ("MCC, Electrical & Cable Installation", 1, "Item",   645_000.00),
            ("SCADA Telemetry & AMI Network Integration", 1, "Item",   252_000.00),
            ("Civil Works — kiosk building, access road, boundary fencing", 1, "Item",   395_000.00),
            ("Decommissioning & Demolition of Existing SPS", 1, "Item",   218_000.00),
        ],
        "notes": [
            "Detailed design included; IFC drawings issued within 10 weeks of contract award.",
            "Pump selection based on hydraulic model outputs provided by Anglian Water (ref: HM-PE-2025-03).",
            "Programme: 14 months from NTP. Temporary bypass pumping provided throughout works.",
            "12-month defects liability period. Pump manufacturer's 5-year warranty included.",
            "Exclusions: ground contamination remediation, statutory diversions, planning fees.",
        ],
        "currency": "GBP",
    },
    {
        "ref":        "WQ-2026-004",
        "date":       date(2026, 3, 12),
        "valid_until": date(2026, 6, 12),
        "client":     "United Utilities Water Ltd",
        "client_ref": "UU/MAINT/SEWER/2026-034",
        "supplier":   "Barhale Construction plc",
        "supplier_addr": "Barhale House, Tempus 10, Heartlands Parkway, Birmingham B7 5PL",
        "contact":    "Mark Connelly | m.connelly@barhale.co.uk | +44 121 356 6886",
        "project":    "Asset Management Plan AMP8 — Condition Index 4 & 5 Sewer Rehabilitation, Greater Manchester Zone 3",
        "category":   "Network Rehabilitation",
        "description": (
            "CCTV condition survey, structural CIPP lining, patch repair, and manhole "
            "rehabilitation across 18.4 km of combined and foul sewers rated CI4/CI5 in "
            "Greater Manchester Zone 3. Works include DN150–DN450 CIPP close-fit lining, "
            "large-diameter (DN600+) spiral-wound relining, spot patch repairs, and "
            "manhole frame/cover renewal with structural lining of brickwork chambers. "
            "All works to UU's latest Sewer Rehabilitation Technical Specification (SRTS Rev.5)."
        ),
        "line_items": [
            ("CCTV Condition Survey & Reporting — pre and post (18,400 m)", 18400, "m",     14.50),
            ("CIPP Structural Lining DN150–DN300 (9,800 m @ £295/m)", 9800, "m",    295.00),
            ("CIPP Structural Lining DN350–DN450 (2,400 m @ £420/m)", 2400, "m",    420.00),
            ("Spiral-Wound Relining DN600–DN900 (1,200 m @ £810/m)", 1200, "m",    810.00),
            ("CIPP Patch Repair — 500 mm sleeve (45 locations)", 45, "No.",    7_500.00),
            ("Manhole Frame & Cover Renewal — D400 medium duty (120 No.)", 120, "No.",    1_820.00),
            ("Manhole Structural CIPP Lining — brick chamber (85 No.)", 85, "No.",    4_500.00),
            ("Traffic Management — zone permits, TM operative, signing (lump)", 1, "Item",  192_000.00),
        ],
        "notes": [
            "All lining materials CE-marked and compliant with EN ISO 11296.",
            "Works programmed in 4 campaigns of 5 weeks to minimise network disruption.",
            "Programme: 20 months from NTP across two winter-avoiding seasons.",
            "Post-rehabilitation CCTV inspection and hydraulic capacity test included in rates.",
            "Exclusions: root-cutting pre-treatment beyond agreed allowance (>5% of total length), dewatering for collapsed sections.",
        ],
        "currency": "GBP",
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_currency(val: float) -> str:
    return f"£{val:,.2f}"


def compute_total(items) -> float:
    return sum(qty * unit for _, qty, _, unit in items)


# ── Style helpers ──────────────────────────────────────────────────────────────

def get_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "QuoteTitle",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=WHITE,
            leading=20,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "QuoteSubtitle",
            fontName="Helvetica",
            fontSize=9,
            textColor=colors.HexColor("#BDD7EE"),
            leading=13,
        ),
        "section_header": ParagraphStyle(
            "SectionHeader",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=BRAND_BLUE,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=TEXT_DARK,
            leading=12,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=MID_GREY,
            leading=11,
        ),
        "note": ParagraphStyle(
            "Note",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=TEXT_DARK,
            leading=11,
            leftIndent=8,
        ),
        "total_label": ParagraphStyle(
            "TotalLabel",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),
        "total_val": ParagraphStyle(
            "TotalVal",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=WHITE,
            alignment=TA_RIGHT,
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="Helvetica",
            fontSize=7,
            textColor=MID_GREY,
            alignment=TA_CENTER,
            leading=10,
        ),
    }
    return styles


# ── PDF builder ────────────────────────────────────────────────────────────────

def build_pdf(quote: dict, output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
    )

    W = A4[0] - 36 * mm   # usable width
    styles = get_styles()
    story = []

    # ── Header banner ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"CAPITAL PROJECT QUOTATION", styles["title"]),
        Paragraph(
            f"<b>{quote['ref']}</b><br/>"
            f"Date: {quote['date'].strftime('%d %B %Y')}<br/>"
            f"Valid until: {quote['valid_until'].strftime('%d %B %Y')}",
            ParagraphStyle("HdrRight", fontName="Helvetica-Bold", fontSize=9,
                           textColor=WHITE, alignment=TA_RIGHT, leading=14),
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[W * 0.60, W * 0.40])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), BRAND_BLUE),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (0, -1), 14),
        ("RIGHTPADDING", (1, 0), (1, -1), 14),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Category pill ──────────────────────────────────────────────────────────
    cat_data = [[Paragraph(f"  {quote['category'].upper()}  ",
                           ParagraphStyle("CatPill", fontName="Helvetica-Bold",
                                          fontSize=7.5, textColor=WHITE))]]
    cat_tbl = Table(cat_data, colWidths=[None])
    cat_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), ACCENT_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
    ]))
    story.append(cat_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Parties grid ───────────────────────────────────────────────────────────
    party_data = [
        [
            Paragraph("<b>PREPARED FOR</b>", styles["section_header"]),
            Paragraph("<b>PREPARED BY</b>", styles["section_header"]),
        ],
        [
            Paragraph(f"<b>{quote['client']}</b><br/>"
                      f"Client Reference: {quote['client_ref']}", styles["body"]),
            Paragraph(f"<b>{quote['supplier']}</b><br/>"
                      f"{quote['supplier_addr']}<br/>"
                      f"{quote['contact']}", styles["body"]),
        ],
    ]
    party_tbl = Table(party_data, colWidths=[W / 2, W / 2])
    party_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 1), (-1, 1), LIGHT_GREY),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 1), (-1, 1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 1), (-1, 1), 0.5, MID_GREY),
    ]))
    story.append(party_tbl)
    story.append(Spacer(1, 4 * mm))

    # ── Project / scope ────────────────────────────────────────────────────────
    story.append(Paragraph("PROJECT SCOPE", styles["section_header"]))
    story.append(HRFlowable(width=W, thickness=1, color=ACCENT_BLUE, spaceAfter=3))
    story.append(Paragraph(f"<b>{quote['project']}</b>", styles["body"]))
    story.append(Paragraph(quote["description"], styles["body"]))
    story.append(Spacer(1, 3 * mm))

    # ── Line items table ───────────────────────────────────────────────────────
    story.append(Paragraph("SCHEDULE OF RATES", styles["section_header"]))
    story.append(HRFlowable(width=W, thickness=1, color=ACCENT_BLUE, spaceAfter=3))

    col_desc  = W * 0.46
    col_qty   = W * 0.09
    col_unit  = W * 0.08
    col_rate  = W * 0.18
    col_total = W * 0.19

    tbl_header = ["Description", "Qty", "Unit", "Unit Rate", "Line Total"]
    tbl_rows = [tbl_header]

    running_total = 0.0
    for desc, qty, unit, unit_rate in quote["line_items"]:
        line_total = qty * unit_rate
        running_total += line_total
        tbl_rows.append([
            desc,
            f"{qty:,}",
            unit,
            fmt_currency(unit_rate),
            fmt_currency(line_total),
        ])

    # Subtotal / VAT / Grand total rows
    vat = running_total * 0.20
    grand = running_total + vat

    tbl_rows.append(["", "", "", "Subtotal (excl. VAT)", fmt_currency(running_total)])
    tbl_rows.append(["", "", "", "VAT @ 20%",           fmt_currency(vat)])
    tbl_rows.append(["", "", "", "GRAND TOTAL",         fmt_currency(grand)])

    items_tbl = Table(
        tbl_rows,
        colWidths=[col_desc, col_qty, col_unit, col_rate, col_total],
        repeatRows=1,
    )

    n = len(tbl_rows)
    subtotal_row = n - 3
    vat_row      = n - 2
    grand_row    = n - 1

    items_tbl.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Data rows — alternating
        ("FONTNAME",      (0, 1), (-1, subtotal_row - 1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, subtotal_row - 1), 7.5),
        ("TOPPADDING",    (0, 1), (-1, subtotal_row - 1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, subtotal_row - 1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, subtotal_row - 1), [WHITE, LIGHT_GREY]),
        # Numeric columns right-aligned
        ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN",         (0, 0), (0, -1), "LEFT"),
        # Subtotal / VAT rows
        ("FONTNAME",      (0, subtotal_row), (-1, vat_row), "Helvetica-Oblique"),
        ("FONTSIZE",      (0, subtotal_row), (-1, vat_row), 8),
        ("TOPPADDING",    (0, subtotal_row), (-1, vat_row), 4),
        ("BOTTOMPADDING", (0, subtotal_row), (-1, vat_row), 4),
        ("LINEABOVE",     (3, subtotal_row), (-1, subtotal_row), 0.8, MID_GREY),
        # Grand total row
        ("BACKGROUND",    (0, grand_row), (-1, grand_row), BRAND_BLUE),
        ("TEXTCOLOR",     (0, grand_row), (-1, grand_row), WHITE),
        ("FONTNAME",      (0, grand_row), (-1, grand_row), "Helvetica-Bold"),
        ("FONTSIZE",      (0, grand_row), (-1, grand_row), 9),
        ("TOPPADDING",    (0, grand_row), (-1, grand_row), 7),
        ("BOTTOMPADDING", (0, grand_row), (-1, grand_row), 7),
        # Outer border
        ("BOX",           (0, 0), (-1, -1), 0.5, MID_GREY),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D8E4")),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 5 * mm))

    # ── Notes ─────────────────────────────────────────────────────────────────
    story.append(Paragraph("NOTES & CONDITIONS", styles["section_header"]))
    story.append(HRFlowable(width=W, thickness=1, color=ACCENT_BLUE, spaceAfter=3))
    for i, note in enumerate(quote["notes"], 1):
        story.append(Paragraph(f"{i}.  {note}", styles["note"]))
    story.append(Spacer(1, 3 * mm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=0.5, color=MID_GREY, spaceBefore=4, spaceAfter=4))
    story.append(Paragraph(
        f"Quote reference: {quote['ref']}  |  Issued: {quote['date'].strftime('%d %B %Y')}  |  "
        f"Valid until: {quote['valid_until'].strftime('%d %B %Y')}  |  "
        f"All prices in GBP. Prices exclude VAT unless stated.  |  "
        f"This document is commercially confidential and intended solely for the named client.",
        styles["footer"],
    ))

    doc.build(story)
    print(f"  [OK]  {os.path.basename(output_path)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\nGenerating {len(QUOTES)} water industry capital project PDF quotes...\n")
    for q in QUOTES:
        fname = f"{q['ref']}_{q['date'].strftime('%Y%m%d')}.pdf"
        path  = os.path.join(OUTPUT_DIR, fname)
        build_pdf(q, path)
    print(f"\nAll PDFs saved to: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
