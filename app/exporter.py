"""Excel export in the original 4-sheet layout + printable PDF report."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from .i18n import tr

DEVICE_COLS = ["كمبيوتر", "شاشة", "طابعة", "سكانر", "All-in-1", "تليفون", "X-Ray", "بوابة أمنية"]
DEVICE_HEADERS = ["Branch Name", "Totall PC", "Monitor", "printer", "scanner",
                  "All in 1", "TEL", "X-Ray", "Security Gate"]


def _style_sheet(ws, widths: dict[str, float], rtl: bool = True) -> None:
    ws.sheet_view.rightToLeft = rtl
    for col, width in widths.items():
        ws.column_dimensions[col].width = width
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="center", wrap_text=False)
            if cell.row in (1,):
                cell.font = Font(bold=True, size=13)
            elif isinstance(cell.value, str) and cell.value in {"ملاحظات", "المكان", "عدد", "عنصر", "التصنيف"}:
                cell.font = Font(bold=True)


def export_excel(rows, path: str | Path) -> None:
    """Write an Excel workbook with the same 4 sheets and column layout as the source."""
    wb = openpyxl.Workbook()
    devices = wb.active
    devices.title = "حصر الاجهزه بالسريال نمبر"
    furniture = wb.create_sheet("حصر بكامل منقولات المركز")
    network = wb.create_sheet("حصر راواتر المركز")
    electrical = wb.create_sheet("حصر كامل بكهرباء المركز")

    # --- Sheet 1: devices -------------------------------------------------
    devices.append(["Devaices"])
    devices.append(DEVICE_HEADERS)
    device_rows = [r for r in rows if r["section"] == "devices"]
    counts = defaultdict(int)
    for r in device_rows:
        counts[r["name_ar"]] += 1
    devices.append(["Alex", *[counts[c] for c in DEVICE_COLS]])
    devices.append([""] + ["serial"] * 8)

    groups: dict[tuple[str, str], dict[str, list[str]]] = {}
    for r in device_rows:
        key = (r["dept_ar"] or "", r["loc_ar"] or "")
        groups.setdefault(key, defaultdict(list))[r["name_ar"]].append(
            r["serial_number"] or r["name_ar"]
        )
    for (dept, sub), values in groups.items():
        label = sub or dept
        height = max((len(v) for v in values.values()), default=1)
        for i in range(height):
            line = [label if i == 0 else ""]
            for col_name in DEVICE_COLS:
                items = values.get(col_name, [])
                line.append(items[i] if i < len(items) else "")
            devices.append(line)

    # --- Sheet 2: furniture ----------------------------------------------
    furniture.append(["خدمات مصر - الاسكندريه"])
    areas: dict[str, list] = {}
    for r in rows:
        if r["section"] == "furniture":
            areas.setdefault(r["loc_ar"] or r["area_ar"] or "غير محدد", []).append(r)
    for area, items in areas.items():
        furniture.append([area])
        furniture.append(["ملاحظات", "", "", "المكان", "", "عدد", "عنصر"])
        for r in items:
            line = [""] * 9
            line[0] = r["notes"] or ""
            line[3] = area
            line[5] = r["quantity"]
            line[6] = r["name_ar"]
            furniture.append(line)

    # --- Sheet 3: network -------------------------------------------------
    network.append(["مركز خدمات مصر- الاسكندريه"])
    network.append(["prorack 2", "prorack 1"])
    columns = {1: [], 2: []}
    for r in rows:
        if r["section"] == "network":
            columns[r["source_column"] or 1].append(r)
    for i in range(max(len(columns[1]), len(columns[2]))):
        left = columns[1][i] if i < len(columns[1]) else None
        right = columns[2][i] if i < len(columns[2]) else None
        def text(r):
            if not r:
                return ""
            qty = f"عدد {r['quantity']} " if r["quantity"] > 1 else ""
            model = f" ({r['brand_model']})" if r["brand_model"] else ""
            return f"{qty}{r['name_ar']}{model}"
        network.append([text(left), text(right)])

    # --- Sheet 4: electrical ---------------------------------------------
    electrical.append(["خدمات مصر -الاسكندريه(الكهرباء)"])
    el_areas: dict[str, list] = {}
    for r in rows:
        if r["section"] == "electrical":
            el_areas.setdefault(r["loc_ar"] or "غير محدد", []).append(r)
    for area, items in el_areas.items():
        electrical.append([area])
        electrical.append(["ملاحظات", "", "", "", "", "المكان", "العدد", "التصنيف"])
        for r in items:
            line = [""] * 9
            line[0] = r["notes"] or ""
            line[5] = r["mount"] or ""
            line[6] = r["quantity"]
            line[7] = r["name_ar"]
            electrical.append(line)

    _style_sheet(devices, {"A": 26, "B": 18, "C": 16, "D": 14, "E": 14, "F": 14, "G": 26, "H": 16, "I": 16})
    _style_sheet(furniture, {"A": 42, "D": 28, "F": 10, "G": 38})
    _style_sheet(network, {"A": 55, "B": 55})
    _style_sheet(electrical, {"A": 48, "F": 14, "G": 10, "H": 24})

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def build_report_html(rows, group_by: str = "department", lang: str = "ar") -> str:
    """RTL HTML suitable for QTextDocument -> PDF / printing."""
    groups: dict[str, list] = {}
    for r in rows:
        key = {
            "department": r["dept_ar"] or tr("all", lang),
            "location": r["loc_ar"] or tr("all", lang),
            "category": r["category_ar"] or tr("all", lang),
        }.get(group_by, tr("all", lang))
        groups.setdefault(key, []).append(r)

    css = """
    body { font-family: 'Segoe UI', Tahoma, Arial; font-size: 10pt; color:#222; }
    h1 { font-size: 17pt; text-align:center; margin-bottom:4px; }
    .meta { text-align:center; color:#666; font-size:9pt; margin-bottom:16px; }
    h2 { font-size:12pt; background:#eef3f8; padding:5px 8px; border-right:4px solid #2f6da3; }
    table { width:100%; border-collapse:collapse; margin-bottom:14px; }
    th { background:#2f6da3; color:white; padding:4px; }
    td { border:1px solid #c9d3dd; padding:3px 5px; }
    tr:nth-child(even) td { background:#f7f9fb; }
    .total { font-weight:bold; }
    """
    parts = [
        "<html dir='rtl'><head><meta charset='utf-8'><style>", css, "</style></head><body>",
        f"<h1>{escape(tr('report_title', lang))}</h1>",
        f"<p class='meta'>{escape(tr('generated', lang))}: {datetime.now():%Y-%m-%d %H:%M}</p>",
    ]
    for title, items in groups.items():
        parts.append(f"<h2>{escape(title)} &nbsp; ({len(items)})</h2>")
        parts.append("<table><thead><tr>")
        headers = [tr("code", lang), tr("item", lang), tr("serial_placeholder", lang),
                   tr("category", lang), tr("qty", lang), tr("notes", lang)]
        parts.extend(f"<th>{escape(h)}</th>" for h in headers)
        parts.append("</tr></thead><tbody>")
        for r in items:
            cells = [r["asset_code"], r["name_ar"], r["serial_number"],
                     r["category_ar"] or "", str(r["quantity"]), r["notes"] or ""]
            parts.append("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in cells) + "</tr>")
        parts.append("</tbody></table>")
    parts.append("</body></html>")
    return "".join(parts)


def render_pdf(rows, path: str | Path, group_by: str = "department", lang: str = "ar") -> None:
    """Render the report to a PDF file using Qt (keeps Arabic shaping correct)."""
    from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
    from PySide6.QtPrintSupport import QPrinter

    doc = QTextDocument()
    doc.setHtml(build_report_html(rows, group_by, lang))
    printer = QPrinter()
    printer.setResolution(300)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(path))
    printer.setPageOrientation(QPageLayout.Orientation.Portrait)
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    doc.print_(printer)
