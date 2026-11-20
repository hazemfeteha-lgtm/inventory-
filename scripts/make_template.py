"""Create a blank 4-sheet Excel template for future inventories."""
from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Font

OUT = Path(__file__).resolve().parent.parent / "templates" / "inventory_template.xlsx"


def main() -> None:
    wb = openpyxl.Workbook()
    a = wb.active
    a.title = "حصر الاجهزه بالسريال نمبر"
    a.append(["Devaices"])
    a.append(["Branch Name", "Totall PC", "Monitor", "printer", "scanner", "All in 1", "TEL", "X-Ray", "Security Gate"])
    a.append(["Alex", "", "", "", "", "", "", "", ""])
    a.append(["", *["serial"] * 8])

    b = wb.create_sheet("حصر بكامل منقولات المركز")
    b.append(["خدمات مصر - الاسكندريه"])
    b.append(["اسم المكان/المنطقة"])
    b.append(["ملاحظات", "", "", "المكان", "", "عدد", "عنصر"])

    c = wb.create_sheet("حصر راواتر المركز")
    c.append(["مركز خدمات مصر- الاسكندريه"])
    c.append(["prorack 2", "prorack 1"])

    d = wb.create_sheet("حصر كامل بكهرباء المركز")
    d.append(["خدمات مصر -الاسكندريه(الكهرباء)"])
    d.append(["اسم المنطقة"])
    d.append(["ملاحظات", "", "", "", "", "المكان", "العدد", "التصنيف"])

    for ws in wb.worksheets:
        ws.sheet_view.rightToLeft = True
        for cell in ws[1]:
            cell.font = Font(bold=True, size=13)
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["G"].width = 26

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
