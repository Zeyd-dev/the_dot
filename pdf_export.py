"""
pdf_export.py — Génération de rapports PDF pour The Dot Resource Matcher
Utilise ReportLab pour produire un PDF propre et professionnel.
Fallback : si ReportLab n'est pas installé, retourne un PDF minimal valide.

Fix: _generate_minimal_pdf() calculait le startxref offset à 0, produisant
     un PDF illisible par tout lecteur conforme. L'offset est maintenant
     calculé en suivant les positions réelles dans le buffer de sortie.
"""

import io
from datetime import datetime


def generate_diagnostic_pdf(diagnostic: dict) -> bytes:
    """
    Génère un rapport PDF complet à partir d'un diagnostic.

    Args:
        diagnostic: dict retourné par get_diagnostic_with_recs()

    Returns:
        bytes: contenu PDF prêt à être téléchargé
    """
    try:
        from reportlab.lib import colors          # noqa: F401 — import check only
        return _generate_with_reportlab(diagnostic)
    except ImportError:
        return _generate_minimal_pdf(diagnostic)


def _generate_with_reportlab(diagnostic: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: F401

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Rapport The Dot — {diagnostic.get('startup_name', 'Startup')}",
    )

    # Couleurs
    BLUE_DARK  = colors.HexColor("#0f2557")
    BLUE_MID   = colors.HexColor("#2563eb")   # noqa: F841
    BLUE_LIGHT = colors.HexColor("#eff6ff")   # noqa: F841
    GRAY       = colors.HexColor("#64748b")
    GRAY_LIGHT = colors.HexColor("#f1f5f9")
    GREEN      = colors.HexColor("#16a34a")
    ORANGE     = colors.HexColor("#d97706")

    styles = getSampleStyleSheet()
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"],
        fontSize=11, textColor=BLUE_DARK, spaceAfter=6, spaceBefore=14,
        fontName="Helvetica-Bold", borderPad=0)
    style_body = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9, textColor=GRAY, leading=14, spaceAfter=4)

    content = []
    name    = diagnostic.get("startup_name", "Startup")
    sector  = diagnostic.get("sector", "—")
    stage   = diagnostic.get("stage", "—")
    date    = str(diagnostic.get("created_at", datetime.now().strftime("%Y-%m-%d")))[:10]

    # ── Header banner ──────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"<b>The Dot</b> · Rapport de diagnostic", ParagraphStyle("hd",fontSize=9,textColor=colors.HexColor("#93c5fd"),fontName="Helvetica")),
        Paragraph(f"<b>{name}</b>", ParagraphStyle("hd2",fontSize=16,textColor=colors.white,fontName="Helvetica-Bold",alignment=TA_CENTER)),
        Paragraph(f"Généré le {date}", ParagraphStyle("hd3",fontSize=8,textColor=colors.HexColor("#93c5fd"),alignment=2)),
    ]]
    header_table = Table(header_data, colWidths=[5*cm, 8*cm, 4*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLUE_DARK),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 14),
        ("RIGHTPADDING", (0,0), (-1,-1), 14),
        ("TOPPADDING", (0,0), (-1,-1), 18),
        ("BOTTOMPADDING", (0,0), (-1,-1), 18),
        ("ROUNDEDCORNERS", [8]),
    ]))
    content.append(header_table)
    content.append(Spacer(1, 0.5*cm))

    # ── Infos startup ──────────────────────────────────────────────────────
    content.append(Paragraph("Profil de la startup", style_h2))
    info_data = [
        ["Secteur", sector.capitalize(), "Stage", stage.capitalize()],
        ["Taille équipe", str(diagnostic.get("team_size", "—")),
         "Statut légal", "Constituée" if diagnostic.get("is_incorporated") else "Non constituée"],
        ["A un produit", "Oui" if diagnostic.get("has_product") else "Non",
         "Clients actifs", "Oui" if diagnostic.get("has_clients") else "Non"],
        ["Chiffre d'affaires", "Oui" if diagnostic.get("has_revenue") else "Non",
         "Startup Act", "Oui" if diagnostic.get("has_startup_act") else "Non"],
    ]
    info_table = Table(info_data, colWidths=[3.5*cm, 5.5*cm, 3.5*cm, 4.5*cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), GRAY_LIGHT),
        ("BACKGROUND", (2,0), (2,-1), GRAY_LIGHT),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8.5),
        ("TEXTCOLOR", (0,0), (0,-1), BLUE_DARK),
        ("TEXTCOLOR", (2,0), (2,-1), BLUE_DARK),
        ("TEXTCOLOR", (1,0), (1,-1), GRAY),
        ("TEXTCOLOR", (3,0), (3,-1), GRAY),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#fafbff")]),
    ]))
    content.append(info_table)
    content.append(Spacer(1, 0.4*cm))

    # ── Scores de maturité ─────────────────────────────────────────────────
    scores = diagnostic.get("scores", {})
    if scores:
        content.append(Paragraph("Scores de maturité", style_h2))
        score_rows = []
        for dim, sc in scores.items():
            sc_int = int(sc) if sc else 0
            level = "Fort" if sc_int >= 70 else ("Modéré" if sc_int >= 40 else "Faible")
            level_color = GREEN if sc_int >= 70 else (ORANGE if sc_int >= 40 else colors.red)
            bar_filled = "█" * (sc_int // 10) + "░" * (10 - sc_int // 10)
            score_rows.append([
                Paragraph(f"<b>{dim}</b>", ParagraphStyle("sc_dim", fontSize=8.5, textColor=BLUE_DARK, fontName="Helvetica-Bold")),
                Paragraph(f"<font color='#{level_color.hexval()[2:]}'>{bar_filled}</font>", ParagraphStyle("bar", fontSize=7, fontName="Courier")),
                Paragraph(f"<b>{sc_int}</b>/100", ParagraphStyle("sc_val", fontSize=9, textColor=BLUE_DARK, fontName="Helvetica-Bold")),
                Paragraph(level, ParagraphStyle("sc_lev", fontSize=8, textColor=level_color)),
            ])
        score_table = Table(score_rows, colWidths=[3.5*cm, 8*cm, 2.5*cm, 3*cm])
        score_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#fafbff")]),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        content.append(score_table)
        content.append(Spacer(1, 0.4*cm))

    # ── Besoins identifiés ─────────────────────────────────────────────────
    needs = diagnostic.get("needs", [])
    if needs:
        content.append(Paragraph("Besoins identifiés", style_h2))
        needs_text = " · ".join([n.replace("_"," ").capitalize() for n in sorted(needs)])
        content.append(Paragraph(needs_text, style_body))
        content.append(Spacer(1, 0.3*cm))

    # ── Recommandations ────────────────────────────────────────────────────
    recs = diagnostic.get("recommendations", [])
    if recs:
        content.append(Paragraph("Programmes recommandés", style_h2))
        rec_data = [["#", "Programme", "Score", "Priorité"]]
        for i, rec in enumerate(recs, 1):
            priority_map = {"immediate": "🔴 Immédiat", "short-term": "🟡 Court terme", "when-ready": "🟢 Quand prêt"}
            priority_text = priority_map.get(rec.get("priority",""), rec.get("priority","—"))
            rec_data.append([
                str(i),
                rec.get("program_name", "—"),
                f"{rec.get('score', 0):.0f}/100",
                priority_text,
            ])
        rec_table = Table(rec_data, colWidths=[1*cm, 9*cm, 2.5*cm, 4.5*cm])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BLUE_DARK),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8.5),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fafbff")]),
            ("LEFTPADDING", (0,0), (-1,-1), 10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
            ("TOPPADDING", (0,0), (-1,-1), 7),
            ("BOTTOMPADDING", (0,0), (-1,-1), 7),
            ("ALIGN", (0,0), (0,-1), "CENTER"),
            ("ALIGN", (2,0), (2,-1), "CENTER"),
        ]))
        content.append(rec_table)

    # ── Footer ─────────────────────────────────────────────────────────────
    content.append(Spacer(1, 1*cm))
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    content.append(Spacer(1, 0.3*cm))
    content.append(Paragraph(
        f"© The Dot · thedot.tn · Rapport généré le {date} · Confidentiel",
        ParagraphStyle("footer", fontSize=7.5, textColor=colors.HexColor("#94a3b8"), alignment=TA_CENTER)
    ))

    doc.build(content)
    return buffer.getvalue()


def _generate_minimal_pdf(diagnostic: dict) -> bytes:
    """
    Fallback PDF if ReportLab is not installed.
    Produces a valid, reader-parseable PDF by tracking actual byte offsets
    and writing a correct xref table — previously startxref was hardcoded
    to 0 which made the file unreadable.
    """
    name  = diagnostic.get("startup_name", "Startup")
    stage = diagnostic.get("stage", "—")
    date  = str(diagnostic.get("created_at", datetime.now().strftime("%Y-%m-%d")))[:10]

    scores      = diagnostic.get("scores", {})
    scores_text = "\n".join([f"  {k}: {v}/100" for k, v in scores.items()])
    needs       = diagnostic.get("needs", [])
    needs_text  = ", ".join(sorted(needs)) if needs else "—"
    recs        = diagnostic.get("recommendations", [])
    recs_text   = "\n".join([
        f"  {i+1}. {r.get('program_name','?')} — {r.get('score',0):.0f}/100"
        for i, r in enumerate(recs)
    ])

    body_text = (
        f"THE DOT - RAPPORT DE DIAGNOSTIC\n"
        f"================================\n\n"
        f"Startup    : {name}\n"
        f"Stage      : {stage}\n"
        f"Date       : {date}\n\n"
        f"SCORES DE MATURITE\n"
        f"------------------\n"
        f"{scores_text}\n\n"
        f"BESOINS IDENTIFIES\n"
        f"------------------\n"
        f"{needs_text}\n\n"
        f"PROGRAMMES RECOMMANDES\n"
        f"----------------------\n"
        f"{recs_text}\n\n"
        f"© The Dot · thedot.tn\n"
    )

    # Build stream content (PDF text operators)
    pdf_lines = []
    for line in body_text.split("\n"):
        safe = (
            line
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )
        pdf_lines.append(f"({safe}) Tj T*")
    stream_body = ("BT /F1 10 Tf 50 800 Td 14 TL\n" + " ".join(pdf_lines) + "\nET\n")
    stream_bytes = stream_body.encode("latin-1", errors="replace")

    # ── Build PDF byte-by-byte, tracking offsets for a valid xref ─────────
    buf = io.BytesIO()

    def w(s):
        if isinstance(s, str):
            s = s.encode("latin-1", errors="replace")
        buf.write(s)

    w("%PDF-1.4\n")

    offsets = {}

    offsets[1] = buf.tell()
    w("1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n")

    offsets[2] = buf.tell()
    w("2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n")

    offsets[3] = buf.tell()
    w("3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R"
      "/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n")

    offsets[4] = buf.tell()
    w(f"4 0 obj<</Length {len(stream_bytes)}>>\nstream\n")
    buf.write(stream_bytes)
    w("endstream\nendobj\n")

    offsets[5] = buf.tell()
    w("5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Courier>>endobj\n")

    # ── xref table at the correct byte offset ─────────────────────────────
    xref_offset = buf.tell()
    w("xref\n")
    w(f"0 6\n")
    w("0000000000 65535 f \n")          # object 0 — free head
    for i in range(1, 6):
        w(f"{offsets[i]:010d} 00000 n \n")

    w("trailer<</Size 6/Root 1 0 R>>\n")
    w(f"startxref\n{xref_offset}\n%%EOF\n")

    return buf.getvalue()
