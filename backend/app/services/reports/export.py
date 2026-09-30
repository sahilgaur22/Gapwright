"""Report generation service for curriculum gap analysis reports."""

import csv
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.db.models.analysis import Analysis
from app.db.models.syllabus import Syllabus
from app.schemas.analysis import CurriculumRecommendationsResponse


def generate_csv_report(
    analysis: Analysis,
    syllabus: Syllabus | None = None,
) -> bytes:
    """Generate an RFC 4180 compliant CSV export for a gap analysis."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Document Header Metadata
    writer.writerow(["Gapwright - Curriculum Gap Analysis Report"])
    writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Analysis ID", str(analysis.id)])
    writer.writerow(["Target Role", analysis.role_query])
    writer.writerow(["Market Location", analysis.location or "Global Remote Market"])
    writer.writerow(["Curriculum Gap %", f"{analysis.gap_pct:.1f}%"])
    writer.writerow(["Market Coverage %", f"{analysis.coverage_pct:.1f}%"])
    if syllabus:
        writer.writerow(["Course Title", syllabus.title])
        writer.writerow(["Department", syllabus.department or "N/A"])
        inst_name = syllabus.institution.name if syllabus.institution else "N/A"
        writer.writerow(["Institution", inst_name])
    writer.writerow([])  # Blank spacer

    # Table Header
    writer.writerow(
        [
            "Rank",
            "Competency Name",
            "Domain Category",
            "Alignment Status",
            "Market Demand %",
            "Active Vacancies",
        ]
    )

    # Sorted items
    sorted_items = sorted(analysis.items, key=lambda x: x.rank or 999)
    for it in sorted_items:
        skill_name = it.skill.canonical_name if it.skill else ""
        category = it.skill.category if it.skill and it.skill.category else "General"
        writer.writerow(
            [
                it.rank or 0,
                skill_name,
                category,
                it.kind.capitalize(),
                f"{it.demand_pct:.1f}%",
                it.demand_count,
            ]
        )

    return output.getvalue().encode("utf-8")


def generate_pdf_report(
    analysis: Analysis,
    syllabus: Syllabus | None = None,
    recommendations: CurriculumRecommendationsResponse | None = None,
) -> bytes:
    """Generate an institutional PDF export for a gap analysis using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Brand Colors
    navy = colors.HexColor("#0C2C47")
    green = colors.HexColor("#2D5652")
    mint = colors.HexColor("#E4F2EA")
    stone = colors.HexColor("#EFEAE6")
    charcoal = colors.HexColor("#1E293B")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=navy,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=charcoal,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=green,
        spaceBefore=10,
        spaceAfter=6,
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=charcoal,
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.white,
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("GAPWRIGHT | CURRICULUM GAP ASSESSMENT REPORT", title_style))
    story.append(
        Paragraph(
            "Labour Market Intelligence & Higher Education Curriculum "
            "Alignment Benchmark",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 12))

    # 2. Executive Summary Metadata Box
    course_name = syllabus.title if syllabus else "Academic Syllabus"
    inst_name = (
        syllabus.institution.name
        if syllabus and syllabus.institution
        else "Accredited Institution"
    )
    loc_str = analysis.location or "Global Remote Market"

    eval_date_str = analysis.created_at.strftime("%Y-%m-%d %H:%M UTC")
    meta_data = [
        [
            Paragraph("<b>Target Role:</b>", subtitle_style),
            Paragraph(analysis.role_query, subtitle_style),
            Paragraph("<b>Curriculum Gap:</b>", subtitle_style),
            Paragraph(
                f"<b>{analysis.gap_pct:.1f}%</b> (Skill Deficit)", subtitle_style
            ),
        ],
        [
            Paragraph("<b>Market Location:</b>", subtitle_style),
            Paragraph(loc_str, subtitle_style),
            Paragraph("<b>Market Coverage:</b>", subtitle_style),
            Paragraph(f"<b>{analysis.coverage_pct:.1f}%</b> Covered", subtitle_style),
        ],
        [
            Paragraph("<b>Course Program:</b>", subtitle_style),
            Paragraph(course_name, subtitle_style),
            Paragraph("<b>Institution:</b>", subtitle_style),
            Paragraph(inst_name, subtitle_style),
        ],
        [
            Paragraph("<b>Evaluation Date:</b>", subtitle_style),
            Paragraph(eval_date_str, subtitle_style),
            Paragraph("<b>Total Assessed:</b>", subtitle_style),
            Paragraph(f"{len(analysis.items)} competencies", subtitle_style),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[100, 160, 110, 170])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), stone),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Itemized Competency Table
    story.append(Paragraph("Itemized Market Competency Evaluation", section_heading))

    col_widths = [35, 180, 100, 95, 65, 65]
    table_rows = [
        [
            Paragraph("Rank", table_header),
            Paragraph("Competency", table_header),
            Paragraph("Domain", table_header),
            Paragraph("Alignment Status", table_header),
            Paragraph("Demand %", table_header),
            Paragraph("Postings", table_header),
        ]
    ]

    sorted_items = sorted(analysis.items, key=lambda x: x.rank or 999)
    for it in sorted_items:
        s_name = it.skill.canonical_name if it.skill else ""
        s_cat = it.skill.category if it.skill and it.skill.category else "General"
        if it.kind == "covered":
            status_label = "Covered"
        elif it.kind == "missing":
            status_label = "Missing Gap"
        else:
            status_label = "Obsolete"

        table_rows.append(
            [
                Paragraph(f"#{it.rank or 0}", table_cell),
                Paragraph(s_name, table_cell),
                Paragraph(s_cat, table_cell),
                Paragraph(status_label, table_cell),
                Paragraph(f"{it.demand_pct:.1f}%", table_cell),
                Paragraph(str(it.demand_count), table_cell),
            ]
        )

    comp_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
    comp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (4, 0), (5, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, mint]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(comp_table)
    story.append(Spacer(1, 14))

    # 4. Actionable Recommendations (if available)
    if recommendations:
        if recommendations.skills_to_add:
            story.append(
                Paragraph(
                    "Priority Curricula Recommendations: Skills to Introduce",
                    section_heading,
                )
            )
            for rec in recommendations.skills_to_add[:4]:
                rec_text = (
                    f"<b>{rec.skill_name}</b> ({rec.demand_pct:.1f}% Market Demand) — "
                    f"{rec.rationale} <i>Suggested Module: {rec.suggested_module} "
                    f"(~{rec.suggested_weeks} wks)</i>"
                )
                story.append(Paragraph(f"• {rec_text}", subtitle_style))
                story.append(Spacer(1, 4))

        if recommendations.skills_to_drop:
            story.append(Spacer(1, 6))
            story.append(
                Paragraph(
                    "Curricula Optimization: Topics to Prune or Modernize",
                    section_heading,
                )
            )
            for rec in recommendations.skills_to_drop[:3]:
                rec_text = (
                    f"<b>{rec.skill_name}</b> ({rec.demand_pct:.1f}% Market Demand) — "
                    f"{rec.rationale} <i>Reallocate teaching hours: "
                    f"~{rec.suggested_weeks} wks</i>"
                )
                story.append(Paragraph(f"• {rec_text}", subtitle_style))
                story.append(Spacer(1, 4))

    # Build the document
    doc.build(story)
    return buffer.getvalue()
