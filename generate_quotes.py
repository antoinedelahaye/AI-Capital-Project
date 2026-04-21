"""Generate 5 additional capital project quote PDFs matching the existing format."""
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

OUT_DIR = os.path.join(os.path.dirname(__file__), "quotes_output")
DB_DIR  = os.path.join(os.path.dirname(__file__), "database")

NAVY  = colors.HexColor("#003B6F")
TEAL  = colors.HexColor("#0097A7")
LGREY = colors.HexColor("#F0F4F8")
MGREY = colors.HexColor("#CBD5E1")
WHITE = colors.white
BLACK = colors.black

W, H = A4


def _styles():
    s = getSampleStyleSheet()
    base = s["Normal"]
    return {
        "title":    ParagraphStyle("title",    parent=base, fontSize=18, textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER, leading=22),
        "ref":      ParagraphStyle("ref",      parent=base, fontSize=13, textColor=WHITE,  fontName="Helvetica",      alignment=TA_CENTER, leading=16),
        "meta":     ParagraphStyle("meta",     parent=base, fontSize=9,  textColor=WHITE,  fontName="Helvetica",      alignment=TA_CENTER, leading=13),
        "section":  ParagraphStyle("section",  parent=base, fontSize=9,  textColor=WHITE,  fontName="Helvetica-Bold", alignment=TA_CENTER),
        "label":    ParagraphStyle("label",    parent=base, fontSize=8,  textColor=TEAL,   fontName="Helvetica-Bold", leading=12),
        "body":     ParagraphStyle("body",     parent=base, fontSize=8,  textColor=BLACK,  fontName="Helvetica",      leading=11),
        "bodyb":    ParagraphStyle("bodyb",    parent=base, fontSize=8,  textColor=BLACK,  fontName="Helvetica-Bold", leading=11),
        "scope":    ParagraphStyle("scope",    parent=base, fontSize=8,  textColor=BLACK,  fontName="Helvetica",      leading=12),
        "footer":   ParagraphStyle("footer",   parent=base, fontSize=6.5,textColor=MGREY,  fontName="Helvetica",      alignment=TA_CENTER, leading=9),
        "note":     ParagraphStyle("note",     parent=base, fontSize=7.5,textColor=BLACK,  fontName="Helvetica",      leading=11),
    }


def _header_table(ref, date, valid_until, category, st):
    """Dark navy header block."""
    data = [
        [Paragraph("CAPITAL PROJECT QUOTATION", st["title"])],
        [Paragraph(ref, st["ref"])],
        [Paragraph(f"Date: {date}     Valid until: {valid_until}", st["meta"])],
        [Paragraph(category.upper(), st["section"])],
    ]
    t = Table(data, colWidths=[W - 40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 2), NAVY),
        ("BACKGROUND", (0, 3), (-1, 3), TEAL),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    return t


def _parties_table(client, client_ref, supplier, supplier_addr, contact, st):
    lbl_for  = Paragraph("PREPARED FOR", st["label"])
    lbl_by   = Paragraph("PREPARED BY",  st["label"])
    val_for  = Paragraph(f"<b>{client}</b><br/>Client Reference: {client_ref}", st["body"])
    val_by   = Paragraph(f"<b>{supplier}</b><br/>{supplier_addr}<br/>{contact}", st["body"])
    data = [[lbl_for, lbl_by], [val_for, val_by]]
    cw = [(W - 40*mm) / 2] * 2
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), LGREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW",     (0, 0), (-1, 0), 0.5, MGREY),
        ("BOX",           (0, 0), (-1, -1), 0.5, MGREY),
        ("LINEBEFORE",    (1, 0), (1, -1), 0.5, MGREY),
    ]))
    return t


def _sor_table(rows, st):
    """Schedule of Rates table.  rows = list of (desc, qty, unit, unit_rate, line_total)."""
    header = ["Description", "Qty", "Unit", "Unit Rate", "Line Total"]
    data = [header] + [[
        Paragraph(r[0], st["body"]), r[1], r[2],
        f"£{r[3]:,.2f}", f"£{r[4]:,.2f}"
    ] for r in rows]

    cw = [W - 40*mm - 16*mm - 22*mm - 28*mm - 28*mm,  # desc
          16*mm, 22*mm, 28*mm, 28*mm]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LGREY]),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (3, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.3, MGREY),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _totals_table(subtotal, st):
    vat = subtotal * 0.20
    grand = subtotal + vat
    data = [
        ["", "", "", "Subtotal (excl. VAT)", f"£{subtotal:,.2f}"],
        ["", "", "", "VAT @ 20%",            f"£{vat:,.2f}"],
        ["", "", "", "GRAND TOTAL",           f"£{grand:,.2f}"],
    ]
    cw = [W - 40*mm - 16*mm - 22*mm - 28*mm - 28*mm, 16*mm, 22*mm, 28*mm, 28*mm]
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("FONTNAME",   (3, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN",      (3, 0), (-1, -1), "RIGHT"),
        ("ALIGN",      (4, 0), (-1, -1), "RIGHT"),
        ("BACKGROUND", (3, 2), (-1, 2), NAVY),
        ("TEXTCOLOR",  (3, 2), (-1, 2), WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("LINEABOVE",  (3, 0), (-1, 0), 0.5, MGREY),
    ]))
    return t


def _notes_table(notes, st):
    items = "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes))
    data = [[Paragraph("<b>NOTES &amp; CONDITIONS</b>", st["label"])],
            [Paragraph(items, st["note"])]]
    t = Table(data, colWidths=[W - 40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), LGREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("BOX",           (0, 0), (-1, -1), 0.5, MGREY),
    ]))
    return t


def build_quote(filename, ref, date, valid_until, category,
                client, client_ref, supplier, supplier_addr, contact,
                scope, sor_rows, notes):

    st = _styles()
    path = os.path.join(OUT_DIR, filename)

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=10*mm, bottomMargin=15*mm,
    )

    subtotal = sum(r[4] for r in sor_rows)
    footer_txt = (f"Quote reference: {ref} | Issued: {date} | Valid until: {valid_until} | "
                  f"All prices in GBP. Prices exclude VAT unless stated. | "
                  f"This document is commercially confidential and intended solely for the named client.")

    story = [
        _header_table(ref, date, valid_until, category, st),
        Spacer(1, 4*mm),
        _parties_table(client, client_ref, supplier, supplier_addr, contact, st),
        Spacer(1, 4*mm),
        Paragraph("PROJECT SCOPE", st["label"]),
        HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=3),
        Paragraph(scope, st["scope"]),
        Spacer(1, 4*mm),
        Paragraph("SCHEDULE OF RATES", st["label"]),
        HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=3),
        _sor_table(sor_rows, st),
        _totals_table(subtotal, st),
        Spacer(1, 4*mm),
        _notes_table(notes, st),
        Spacer(1, 4*mm),
        Paragraph(footer_txt, st["footer"]),
    ]

    doc.build(story)
    print(f"  Generated: {filename}  (subtotal £{subtotal:,.0f})")


# ── QUOTE DEFINITIONS ─────────────────────────────────────────────────────────

def q1():
    """WQ-2024-002 — Pumping Infrastructure — MWH Treatment, 2024 (based on WQ-2025-003)"""
    sor = [
        ("Wet Well Construction – RC caisson 8.5 m dia., depth 12 m",          1,    "Item", 1_740_000, 1_740_000),
        ("Flygt NP 3301 Submersible Pump Sets 400 kW – duty/standby (×2)",      2,    "No.",    298_000,   596_000),
        ("DN400 uPVC Rising Main – supply and lay (2,100 m)",               2_100,    "m",          610, 1_281_000),
        ("Standby Generator – FG Wilson P450-3 450 kVA, acoustic enclosure",    1,    "No.",    172_000,   172_000),
        ("MCC, Electrical & Cable Installation",                                 1,    "Item",   580_000,   580_000),
        ("SCADA Telemetry & AMI Network Integration",                            1,    "Item",   224_000,   224_000),
        ("Civil Works – kiosk building, access road, boundary fencing",          1,    "Item",   348_000,   348_000),
        ("Decommissioning & Demolition of Existing SPS",                         1,    "Item",   195_000,   195_000),
    ]
    build_quote(
        filename="WQ-2024-002_20240418.pdf",
        ref="WQ-2024-002", date="18 April 2024", valid_until="18 July 2024",
        category="Pumping Infrastructure",
        client="Anglian Water Services Ltd", client_ref="AW/WW/PS/2024-054",
        supplier="MWH Treatment Ltd",
        supplier_addr="Mott MacDonald House, 8-10 Sydenham Road, Croydon CR0 2EE",
        contact="David Okafor | d.okafor@mwhtreatment.com | +44 20 8774 2000",
        scope=(
            "Wastewater Network Resilience Programme – Peterborough East SPS Replacement. "
            "Full decommission and replacement of the existing Peterborough East Sewage Pumping Station (SPS). "
            "Scope covers new wet well (reinforced concrete caisson, 8.5 m dia.), duty/standby Flygt NP 3301 "
            "submersible pump sets (400 kW each), 2.1 km DN400 uPVC rising main, 450 kVA standby generator, "
            "MCC/electrical installation, telemetry integration with Anglian Water's AMI network, and "
            "decommissioning of the existing facility."
        ),
        sor_rows=sor,
        notes=[
            "Detailed design included; IFC drawings issued within 12 weeks of contract award.",
            "Pump selection based on hydraulic model outputs provided by Anglian Water (ref: HM-PE-2024-07).",
            "Programme: 15 months from NTP. Temporary bypass pumping provided throughout works.",
            "12-month defects liability period. Pump manufacturer's 5-year warranty included.",
            "Exclusions: ground contamination remediation, statutory diversions, planning fees.",
        ],
    )


def q2():
    """WQ-2024-007 — Water Treatment Infrastructure — Black & Veatch, 2024 (based on WQ-2026-001)"""
    sor = [
        ("UV Disinfection Units – Xylem Wedeco Duron (×4)",                      4, "No.",   1_380_000,  5_520_000),
        ("Dissolved Air Flotation (DAF) Units, 15 ML/day capacity (×2)",          2, "No.",   2_710_000,  5_420_000),
        ("Enhanced Coagulation & Flocculation Dosing System",                      1, "Item",  2_080_000,  2_080_000),
        ("SCADA / Control System Upgrade & Integration",                           1, "Item",  1_450_000,  1_450_000),
        ("Civil & Structural Works (tankage, pipework, platforms)",                1, "Item",  3_820_000,  3_820_000),
        ("Electrical & Mechanical Installation",                                   1, "Item",  2_040_000,  2_040_000),
        ("Commissioning, Testing & Performance Verification",                      1, "Item",    960_000,    960_000),
        ("Operator Training Programme & O&M Documentation",                        1, "Item",    385_000,    385_000),
    ]
    build_quote(
        filename="WQ-2024-007_20241029.pdf",
        ref="WQ-2024-007", date="29 October 2024", valid_until="29 January 2025",
        category="Water Treatment Infrastructure",
        client="Severn Trent Water Ltd", client_ref="STW/AMP8/WTW/2024-088",
        supplier="Black & Veatch Ltd",
        supplier_addr="The Broadgate Tower, 20 Primrose Street, London EC2A 2RS",
        contact="Rachel Summers | r.summers@bv.com | +44 20 7638 5000",
        scope=(
            "AMP8 Water Treatment Works Capacity Enhancement – Frankley WTW. "
            "Design, supply, and installation of capacity enhancement works at Frankley WTW to increase "
            "treated water output by 30 ML/day. Scope includes UV disinfection, enhanced coagulation/"
            "flocculation, dissolved air flotation (DAF) units, and full SCADA/control system upgrade. "
            "Includes commissioning, 12-month defects liability, and operator training programme."
        ),
        sor_rows=sor,
        notes=[
            "Prices are fixed-price lump sums inclusive of design, supply, and installation.",
            "Provisional sum for ground investigation works: £195,000 (to be confirmed).",
            "Programme: 24 months from NTP. Works to be phased to maintain supply continuity.",
            "Exclusions: land acquisition, statutory consents, third-party diversions.",
            "Payment terms: 30% mobilisation, monthly valuations, 5% retention released after DLP.",
        ],
    )


def q3():
    """WQ-2025-002 — Pipeline Infrastructure — Amey Utilities, 2025 (based on WQ-2026-002)"""
    sor = [
        ("DN500 Ductile Iron Pipe – supply and lay (8,200 m @ £1,310/m)",    8_200, "m",      1_310, 10_742_000),
        ("Inline Valve Chambers – PN16 butterfly valves, concrete (×6)",         6, "No.",     76_000,    456_000),
        ("HDD River Crossing – River Wharfe (220 m, DN500)",                     1, "Item", 1_245_000,  1_245_000),
        ("Cathodic Protection System – sacrificial anode impressed current",      1, "Item",   498_000,    498_000),
        ("Pressure Testing, Commissioning & Chlorination",                        1, "Item",   262_000,    262_000),
        ("Highway & Statutory Reinstatement (A659 corridor)",                     1, "Item",   574_000,    574_000),
        ("Environmental Mitigation & Site Restoration",                           1, "Item",   285_000,    285_000),
    ]
    build_quote(
        filename="WQ-2025-002_20250509.pdf",
        ref="WQ-2025-002", date="09 May 2025", valid_until="09 August 2025",
        category="Pipeline Infrastructure",
        client="Yorkshire Water Services Ltd", client_ref="YW/CAP/PIPE/2025-006",
        supplier="Amey Utilities Ltd",
        supplier_addr="Sherard Building, Edmund Halley Road, Oxford OX4 4DQ",
        contact="Tom Granger | t.granger@amey.co.uk | +44 1865 713 000",
        scope=(
            "Northern Transfer Scheme Phase 2 – Washburn to Eccup DN500 Strategic Main. "
            "Construction of a new 8.2 km DN500 ductile iron strategic water main from Washburn Treatment "
            "Works to Eccup Service Reservoir, including six inline valve chambers, one horizontal directional "
            "drill (HDD) river crossing beneath the River Wharfe, full cathodic protection system, and "
            "statutory reinstatement. Works form part of Yorkshire Water's AMP8 strategic interconnection programme."
        ),
        sor_rows=sor,
        notes=[
            "Unit rate for pipe supply and lay based on Q2 2025 material indices (CECA).",
            "HDD pricing subject to ground investigation results; variance mechanism applies.",
            "Programme: 17 months from NTP. Traffic management strategy pre-agreed with WYCA.",
            "All works to comply with Water Regulations 2016 and SROH specification.",
            "Exclusions: statutory undertaker diversions, land access agreements, archaeological watching brief.",
        ],
    )


def q4():
    """WQ-2025-007 — Network Rehabilitation — Lanes Group, 2025 (based on WQ-2026-004)"""
    sor = [
        ("CCTV Condition Survey & Reporting – pre and post (18,400 m)",  18_400, "m",      16.00,    294_400),
        ("CIPP Structural Lining DN150–DN300 (9,800 m @ £320/m)",         9_800, "m",     320.00,  3_136_000),
        ("CIPP Structural Lining DN350–DN450 (2,400 m @ £455/m)",         2_400, "m",     455.00,  1_092_000),
        ("Spiral-Wound Relining DN600–DN900 (1,200 m @ £870/m)",          1_200, "m",     870.00,  1_044_000),
        ("CIPP Patch Repair – 500 mm sleeve (45 locations)",                  45, "No.",  8_200.00,    369_000),
        ("Manhole Frame & Cover Renewal – D400 medium duty (120 No.)",       120, "No.",  1_980.00,    237_600),
        ("Manhole Structural CIPP Lining – brick chamber (85 No.)",           85, "No.",  4_900.00,    416_500),
        ("Traffic Management – zone permits, TM operative, signing (lump)",    1, "Item", 210_000,    210_000),
    ]
    build_quote(
        filename="WQ-2025-007_20250922.pdf",
        ref="WQ-2025-007", date="22 September 2025", valid_until="22 December 2025",
        category="Network Rehabilitation",
        client="United Utilities Water Ltd", client_ref="UU/MAINT/SEWER/2025-061",
        supplier="Lanes Group plc",
        supplier_addr="Asher Lane Business Park, Pudsey, Leeds LS28 6LS",
        contact="Karen Brophy | k.brophy@lanesgroup.co.uk | +44 113 257 7000",
        scope=(
            "Asset Management Plan AMP8 – Condition Index 4 & 5 Sewer Rehabilitation, Greater Manchester Zone 3. "
            "CCTV condition survey, structural CIPP lining, patch repair, and manhole rehabilitation across "
            "18.4 km of combined and foul sewers rated CI4/CI5 in Greater Manchester Zone 3. Works include "
            "DN150–DN450 CIPP close-fit lining, large-diameter (DN600+) spiral-wound relining, spot patch "
            "repairs, and manhole frame/cover renewal with structural lining of brickwork chambers. "
            "All works to UU's latest Sewer Rehabilitation Technical Specification (SRTS Rev.5)."
        ),
        sor_rows=sor,
        notes=[
            "All lining materials CE-marked and compliant with EN ISO 11296.",
            "Works programmed in 4 campaigns of 5 weeks to minimise network disruption.",
            "Programme: 20 months from NTP across two winter-avoiding seasons.",
            "Post-rehabilitation CCTV inspection and hydraulic capacity test included in rates.",
            "Exclusions: root-cutting pre-treatment beyond agreed allowance (>5% of total length), dewatering for collapsed sections.",
        ],
    )


def q5():
    """WQ-2027-001 — Pumping Infrastructure — Stantec UK, 2027 (based on WQ-2025-003)"""
    sor = [
        ("Wet Well Construction – RC caisson 8.5 m dia., depth 12 m",           1, "Item", 2_185_000,  2_185_000),
        ("Grundfos SL1 Submersible Pump Sets 450 kW – duty/standby (×2)",        2, "No.",   388_000,    776_000),
        ("DN400 uPVC Rising Main – supply and lay (2,100 m)",                2_100, "m",         760,  1_596_000),
        ("Standby Generator – Kohler KD550-F 550 kVA, acoustic enclosure",       1, "No.",   225_000,    225_000),
        ("MCC, Electrical & Cable Installation",                                  1, "Item",   730_000,    730_000),
        ("SCADA Telemetry & AMI Network Integration",                             1, "Item",   290_000,    290_000),
        ("Civil Works – kiosk building, access road, boundary fencing",           1, "Item",   448_000,    448_000),
        ("Decommissioning & Demolition of Existing SPS",                          1, "Item",   252_000,    252_000),
    ]
    build_quote(
        filename="WQ-2027-001_20270105.pdf",
        ref="WQ-2027-001", date="05 January 2027", valid_until="05 April 2027",
        category="Pumping Infrastructure",
        client="Anglian Water Services Ltd", client_ref="AW/WW/PS/2027-002",
        supplier="Stantec UK Ltd",
        supplier_addr="One Gosforth Park Way, Gosforth Business Park, Newcastle NE12 8ET",
        contact="Fiona Lachlan | f.lachlan@stantec.com | +44 191 229 3000",
        scope=(
            "Wastewater Network Resilience Programme – Peterborough East SPS Replacement. "
            "Full decommission and replacement of the existing Peterborough East Sewage Pumping Station (SPS). "
            "Scope covers new wet well (reinforced concrete caisson, 8.5 m dia.), duty/standby Grundfos SL1 "
            "submersible pump sets (450 kW each), 2.1 km DN400 uPVC rising main, 550 kVA standby generator, "
            "MCC/electrical installation, telemetry integration with Anglian Water's AMI network, and "
            "decommissioning of the existing facility."
        ),
        sor_rows=sor,
        notes=[
            "Detailed design included; IFC drawings issued within 10 weeks of contract award.",
            "Pump selection based on hydraulic model outputs provided by Anglian Water (ref: HM-PE-2027-01).",
            "Programme: 14 months from NTP. Temporary bypass pumping provided throughout works.",
            "12-month defects liability period. Pump manufacturer's 5-year warranty included.",
            "Exclusions: ground contamination remediation, statutory diversions, planning fees.",
        ],
    )


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Generating quotes...")
    q1(); q2(); q3(); q4(); q5()
    print("Done.")
