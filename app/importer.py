"""Excel -> clean asset rows -> SQLite import, with a data-quality report."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from .db import build_search_key, get_or_create, infer_category
from .normalize import clean_serial, norm, norm_key, numeric

SECTIONS = {
    "حصر الاجهزه بالسريال نمبر": "devices",
    "حصر بكامل منقولات المركز": "furniture",
    "حصر راواتر المركز": "network",
    "حصر كامل بكهرباء المركز": "electrical",
}

DEVICE_COLUMNS = [
    (1, "كمبيوتر", "PC"),
    (2, "شاشة", "Monitor"),
    (3, "طابعة", "Printer"),
    (4, "سكانر", "Scanner"),
    (5, "All-in-1", "All-in-One"),
    (6, "تليفون", "Telephone"),
    (7, "X-Ray", "X-Ray"),
    (8, "بوابة أمنية", "Security Gate"),
]
DEVICE_EN = {ar: en for _, ar, en in DEVICE_COLUMNS}

RACK_LABELS = {"prorack 1", "prorack 2", "sound system rack"}


@dataclass
class ParsedAsset:
    section: str
    name_ar: str
    name_en: str = ""
    serial_number: str = ""
    brand_model: str = ""
    department: str = ""
    location: str = ""
    area_ar: str = ""
    mount: str = ""
    quantity: int = 1
    notes: str = ""
    source_sheet: str = ""
    source_row: int = 0
    source_column: int = 0
    flags: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    assets: list[ParsedAsset]
    issues: list[dict]
    totals: dict[str, int]


def _cell(row, index: int) -> str:
    try:
        value = row[index]
    except (IndexError, TypeError):
        return ""
    return clean_serial(value)


def _issue(kind: str, detail_ar: str, detail_en: str, sheet: str, row: int,
           severity: str = "warning") -> dict:
    return {
        "issue_type": kind,
        "severity": severity,
        "detail_ar": detail_ar,
        "detail_en": detail_en,
        "source_sheet": sheet,
        "source_row": row,
    }


def _looks_serial(text: str) -> bool:
    """A PC serial is alphanumeric with at least one digit; dept labels are not."""
    return bool(re.search(r"\d", text)) and bool(re.search(r"[A-Za-z]", text))


# ---------------------------------------------------------------------------
# Sheet 1: devices by serial number, grouped by department
# ---------------------------------------------------------------------------
def parse_devices(rows, sheet: str) -> tuple[list[ParsedAsset], list[dict]]:
    assets: list[ParsedAsset] = []
    issues: list[dict] = []
    department = ""
    sub_location = ""

    for row_no, row in enumerate(rows, start=1):
        # The file repeats its header block at the bottom (rows 85-93).
        if row_no >= 85:
            break
        if row_no <= 4:
            continue

        first = _cell(row, 0)
        values = [_cell(row, idx) for idx in range(1, 9)]
        if not first and not any(values):
            continue

        if first:
            second = values[0]
            rest_empty = not any(values[1:])
            if second == first and rest_empty:
                department, sub_location = first, ""
                continue
            if re.fullmatch(r"T\s*\d+", first, flags=re.IGNORECASE):
                sub_location = first  # Terminal counter inside Front Office
            else:
                department, sub_location = first, ""

        for idx, label, english in DEVICE_COLUMNS:
            value = _cell(row, idx)
            if not value or (idx == 1 and value == first):
                continue
            flags: list[str] = []
            name, serial, name_en = label, value, english
            if idx == 1 and not _looks_serial(value):
                # e.g. "جهاز خاص بالمرور" sits in the PC column but is not a PC.
                flags.append("non_serial_value")
                name, serial, name_en = value, "", "Special device"
            assets.append(
                ParsedAsset(
                    section="devices",
                    name_ar=name,
                    name_en=name_en,
                    serial_number=serial,
                    department=department,
                    location=sub_location,
                    notes=("رقم/frontdesk: " + sub_location) if sub_location else "",
                    source_sheet=sheet,
                    source_row=row_no,
                    source_column=idx + 1,
                    flags=flags,
                )
            )
            if "non_serial_value" in flags:
                issues.append(
                    _issue(
                        "non_serial_value",
                        f"قيمة غير صحيحة في عمود الكمبيوتر: {value}",
                        f"Non-serial value in PC column: {value}",
                        sheet,
                        row_no,
                        "info",
                    )
                )
    # Compare the row counts printed in the header (row 3) with reality.
    if len(rows) >= 3:
        declared_row = rows[2]
        actual = Counter(a.name_ar for a in assets)
        for idx, label, _ in DEVICE_COLUMNS:
            try:
                declared = numeric(declared_row[idx], 0)
            except (IndexError, TypeError):
                continue
            if declared and actual[label] != declared:
                issues.append(
                    _issue(
                        "total_mismatch",
                        f"الإجمالي المعلن لـ {label}: {declared}، الموجود فعلياً: {actual[label]}",
                        f"Declared total for {label}: {declared}, found: {actual[label]}",
                        sheet, 3, "info",
                    )
                )
    return assets, issues


# ---------------------------------------------------------------------------
# Sheet 2: movable assets by location
# ---------------------------------------------------------------------------
def parse_furniture(rows, sheet: str) -> tuple[list[ParsedAsset], list[dict]]:
    assets: list[ParsedAsset] = []
    issues: list[dict] = []
    area = ""

    for row_no, row in enumerate(rows, start=1):
        notes = _cell(row, 0)
        place = _cell(row, 3)
        quantity_raw = _cell(row, 5)
        item = _cell(row, 6)

        if row_no == 3 or item == "عنصر" or place == "المكان":
            continue
        if notes.startswith("ملاحظات:") or notes.startswith("عدد ") and not item:
            if notes:
                issues.append(
                    _issue("note_only_row", notes, notes, sheet, row_no, "info")
                )
            continue
        if item:
            location = place or area
            if not location:
                issues.append(
                    _issue("missing_location", "لا يوجد مكان للقطعة", "Asset has no location",
                           sheet, row_no)
                )
            quantity = numeric(quantity_raw or "1", 1)
            flags = []
            if not quantity_raw:
                flags.append("missing_quantity")
                issues.append(
                    _issue("missing_quantity", f"الكمية غير محددة: {item}",
                           f"Missing quantity: {item}", sheet, row_no)
                )
            assets.append(
                ParsedAsset(
                    section="furniture",
                    name_ar=item,
                    location=location,
                    area_ar=area,
                    mount=place if place in {"حائط", "أرضى"} else "",
                    quantity=quantity,
                    notes=notes,
                    source_sheet=sheet,
                    source_row=row_no,
                    flags=flags,
                )
            )
        elif notes and not place and not quantity_raw and not _cell(row, 7):
            if len(notes) < 90 and not notes.startswith("تم ") and not notes.startswith("ملاحظات"):
                area = notes
    return assets, issues


# ---------------------------------------------------------------------------
# Sheet 3: routers / switches / sound system
# ---------------------------------------------------------------------------
def parse_network(rows, sheet: str) -> tuple[list[ParsedAsset], list[dict]]:
    assets: list[ParsedAsset] = []
    issues: list[dict] = []
    rack = {0: "", 1: ""}
    last_by_column: dict[int, ParsedAsset] = {}

    for row_no, row in enumerate(rows, start=1):
        for col in (0, 1):
            text = _cell(row, col)
            if not text:
                continue
            if row_no == 1:  # title row
                continue
            low = norm(text)
            if low in {norm(x) for x in RACK_LABELS}:
                rack[col] = text
                continue
            if text.startswith("(") and col in last_by_column:
                last_by_column[col].brand_model = (
                    last_by_column[col].brand_model + " " + text
                ).strip()
                continue

            quantity_match = re.search(r"عدد\s*(\d+)", text)
            leading_match = re.match(r"^\s*(\d+)\s+", text)
            quantity = int(quantity_match.group(1)) if quantity_match else (
                int(leading_match.group(1)) if leading_match else 1
            )
            name = re.sub(r"عدد\s*\d+", "", text)
            name = re.sub(r"^\s*\d+\s+", "", name)
            model_match = re.search(r"\(([^)]*)\)", name)
            brand = ""
            if model_match:
                brand = model_match.group(1).strip()
                candidate = re.sub(r"\([^)]*\)", "", name).strip()
                if candidate:
                    name = candidate  # parenthesized text is a model
                else:
                    name, brand = brand, ""  # parenthesized text is the item itself
            name = re.sub(r"\s+", " ", name).strip(" -")

            asset = ParsedAsset(
                section="network",
                name_ar=name or text,
                brand_model=brand,
                quantity=quantity,
                location="غرفة IT",
                notes=rack[col],
                source_sheet=sheet,
                source_row=row_no,
                source_column=col + 1,
            )
            assets.append(asset)
            last_by_column[col] = asset
    return assets, issues


# ---------------------------------------------------------------------------
# Sheet 4: electrical points by area
# ---------------------------------------------------------------------------
def parse_electrical(rows, sheet: str) -> tuple[list[ParsedAsset], list[dict]]:
    assets: list[ParsedAsset] = []
    issues: list[dict] = []
    area = ""

    for row_no, row in enumerate(rows, start=1):
        notes = _cell(row, 0)
        place = _cell(row, 5)
        quantity_raw = _cell(row, 6)
        item = _cell(row, 7)

        if row_no == 3 or item in {"التصنيف", ""} and place == "المكان":
            continue
        if item:
            if not area:
                issues.append(
                    _issue("missing_area", "لا يوجد منطقة للنقطة الكهربائية",
                           "Electrical point has no area", sheet, row_no)
                )
            flags = []
            if not quantity_raw:
                flags.append("missing_quantity")
                issues.append(
                    _issue("missing_quantity", f"الكمية غير محددة: {item}",
                           f"Missing quantity: {item}", sheet, row_no)
                )
            assets.append(
                ParsedAsset(
                    section="electrical",
                    name_ar=item,
                    location=area or "غير محدد",
                    area_ar=area,
                    mount=place,
                    quantity=numeric(quantity_raw or "1", 1),
                    notes=notes,
                    source_sheet=sheet,
                    source_row=row_no,
                    flags=flags,
                )
            )
        elif notes and not place and not quantity_raw and not item:
            if (len(notes) < 90 and not notes.startswith("ملاحظات")
                    and not notes.startswith("عدد ") and not notes.startswith("مفتاح")):
                area = notes
    return assets, issues


def parse_workbook(path: str | Path) -> ParseResult:
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    all_assets: list[ParsedAsset] = []
    all_issues: list[dict] = []
    totals: dict[str, int] = {}

    parsers = {
        "devices": parse_devices,
        "furniture": parse_furniture,
        "network": parse_network,
        "electrical": parse_electrical,
    }
    # Match worksheets tolerantly (extra spaces / minor spelling differences).
    hints = {
        "devices": ("اجهزه",),
        "furniture": ("منقولات",),
        "network": ("راواتر", "شبكات"),
        "electrical": ("كهرباء",),
    }
    resolved: dict[str, str] = {}
    for section, keywords in hints.items():
        for name in wb.sheetnames:
            candidate = norm(name)
            if any(norm(k) in candidate for k in keywords):
                resolved[section] = name
                break

    for sheet_name, section in SECTIONS.items():
        actual_name = resolved.get(section)
        if not actual_name:
            all_issues.append(
                _issue("missing_sheet", f"الورقة غير موجودة: {sheet_name}",
                       f"Missing worksheet: {sheet_name}", sheet_name, 0)
            )
            totals[section] = 0
            continue
        assets, issues = parsers[section](list(wb[actual_name].iter_rows(values_only=True)), actual_name)
        all_assets.extend(assets)
        all_issues.extend(issues)
        totals[section] = len(assets)
    wb.close()

    # Duplicate serial numbers: keep both rows and flag them for review.
    seen: dict[str, ParsedAsset] = {}
    for asset in all_assets:
        key = norm_key(asset.serial_number) if asset.serial_number else ""
        if not key:
            continue
        if key in seen:
            first = seen[key]
            for target in (first, asset):
                if "duplicate_serial" not in target.flags:
                    target.flags.append("duplicate_serial")
            all_issues.append(
                _issue(
                    "duplicate_serial",
                    f"سريال مكرر {asset.serial_number} في {asset.department or asset.location} "
                    f"و{first.department or first.location}",
                    f"Duplicate serial {asset.serial_number} in {asset.department or asset.location} "
                    f"and {first.department or first.location}",
                    asset.source_sheet,
                    asset.source_row,
                )
            )
            all_issues.append(
                _issue(
                    "duplicate_serial",
                    f"الظهور الأول للسريال {first.serial_number}",
                    f"First occurrence of serial {first.serial_number}",
                    first.source_sheet,
                    first.source_row,
                )
            )
        else:
            seen[key] = asset

    totals["total"] = len(all_assets)
    totals["issues"] = len(all_issues)
    return ParseResult(all_assets, all_issues, totals)


def write_to_db(result: ParseResult, conn, file_name: str = "") -> int:
    """Insert parsed rows as a new import batch; returns the batch id."""
    batch_id = conn.execute(
        "INSERT INTO import_batches(file_name, source_sheet, row_count, note) VALUES (?,?,?,?)",
        (file_name, ", ".join(SECTIONS), result.totals["total"],
         f"devices={result.totals.get('devices',0)}, furniture={result.totals.get('furniture',0)}, "
         f"network={result.totals.get('network',0)}, electrical={result.totals.get('electrical',0)}"),
    ).lastrowid

    for asset in result.assets:
        category_id = None
        canonical = infer_category(asset.section, asset.name_ar)
        row = conn.execute(
            "SELECT id FROM categories WHERE section=? AND name_ar=?",
            (asset.section, canonical),
        ).fetchone()
        if row:
            category_id = row["id"]

        dept_id = get_or_create(conn, "departments", asset.department, "") if asset.department else None
        loc_id = get_or_create(conn, "locations", asset.location, "") if asset.location else None
        search_key = build_search_key(
            asset.name_ar, asset.name_en, asset.serial_number, asset.brand_model,
            asset.department, asset.location, asset.area_ar, asset.notes,
        )
        cur = conn.execute(
            """INSERT INTO assets(branch_id, batch_id, section, category_id, name_ar, name_en,
                   search_key, serial_number, brand_model, department_id, location_id, area_ar, mount,
                   quantity, notes, source_sheet, source_row, source_column)
               VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                batch_id, asset.section, category_id, asset.name_ar, asset.name_en,
                search_key, asset.serial_number, asset.brand_model, dept_id, loc_id, asset.area_ar,
                asset.mount, asset.quantity, asset.notes, asset.source_sheet,
                asset.source_row, asset.source_column,
            ),
        )
        asset_id = cur.lastrowid
        conn.execute(
            "UPDATE assets SET asset_code = ? WHERE id = ?", (f"AST-{asset_id:06d}", asset_id)
        )
        for flag in asset.flags:
            if flag == "duplicate_serial":
                detail = f"سريال مكرر: {asset.serial_number}"
                detail_en = f"Duplicate serial: {asset.serial_number}"
            elif flag == "missing_quantity":
                detail = f"كمية غير محددة: {asset.name_ar}"
                detail_en = f"Missing quantity: {asset.name_ar}"
            else:
                detail = f"{flag}: {asset.name_ar}"
                detail_en = detail
            conn.execute(
                """INSERT INTO quality_issues(batch_id, asset_id, issue_type, severity,
                       detail_ar, detail_en, source_sheet, source_row)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (batch_id, asset_id, flag, "warning", detail, detail_en,
                 asset.source_sheet, asset.source_row),
            )

    for issue in result.issues:
        if issue["issue_type"] in {"duplicate_serial", "missing_quantity"}:
            continue  # already stored per asset above
        conn.execute(
            """INSERT INTO quality_issues(batch_id, issue_type, severity, detail_ar,
                   detail_en, source_sheet, source_row)
               VALUES (?,?,?,?,?,?,?)""",
            (batch_id, issue["issue_type"], issue["severity"], issue["detail_ar"],
             issue["detail_en"], issue["source_sheet"], issue["source_row"]),
        )
    conn.commit()
    return batch_id
