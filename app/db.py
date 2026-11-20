"""SQLite storage: schema, seed lookup tables and small CRUD helpers."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from .normalize import norm

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS branches (
    id     INTEGER PRIMARY KEY,
    name_ar TEXT NOT NULL,
    name_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS departments (
    id      INTEGER PRIMARY KEY,
    name_ar TEXT NOT NULL UNIQUE,
    name_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS locations (
    id      INTEGER PRIMARY KEY,
    name_ar TEXT NOT NULL UNIQUE,
    name_en TEXT NOT NULL,
    zone_ar TEXT NOT NULL DEFAULT 'داخل المركز'
);

CREATE TABLE IF NOT EXISTS categories (
    id        INTEGER PRIMARY KEY,
    name_ar   TEXT NOT NULL,
    name_en   TEXT NOT NULL,
    section   TEXT NOT NULL CHECK(section IN ('devices','furniture','electrical','network')),
    parent_id INTEGER REFERENCES categories(id),
    UNIQUE(name_ar, section)
);

CREATE TABLE IF NOT EXISTS import_batches (
    id          INTEGER PRIMARY KEY,
    file_name   TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT (datetime('now')),
    source_sheet TEXT NOT NULL DEFAULT '',
    row_count   INTEGER NOT NULL DEFAULT 0,
    note        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS assets (
    id             INTEGER PRIMARY KEY,
    asset_code     TEXT UNIQUE,
    branch_id      INTEGER NOT NULL REFERENCES branches(id),
    batch_id       INTEGER REFERENCES import_batches(id),
    section        TEXT NOT NULL CHECK(section IN ('devices','furniture','electrical','network')),
    category_id    INTEGER REFERENCES categories(id),
    name_ar        TEXT NOT NULL,
    name_en        TEXT NOT NULL DEFAULT '',
    search_key     TEXT NOT NULL DEFAULT '',
    serial_number  TEXT NOT NULL DEFAULT '',
    brand_model    TEXT NOT NULL DEFAULT '',
    department_id  INTEGER REFERENCES departments(id),
    location_id    INTEGER REFERENCES locations(id),
    area_ar        TEXT NOT NULL DEFAULT '',
    mount          TEXT NOT NULL DEFAULT '',
    quantity       INTEGER NOT NULL DEFAULT 1,
    condition_ar   TEXT NOT NULL DEFAULT '',
    notes          TEXT NOT NULL DEFAULT '',
    source_sheet   TEXT NOT NULL DEFAULT '',
    source_row     INTEGER NOT NULL DEFAULT 0,
    source_column  INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_assets_serial    ON assets(serial_number);
CREATE INDEX IF NOT EXISTS idx_assets_search    ON assets(search_key);
CREATE INDEX IF NOT EXISTS idx_assets_category  ON assets(category_id);
CREATE INDEX IF NOT EXISTS idx_assets_department ON assets(department_id);
CREATE INDEX IF NOT EXISTS idx_assets_location  ON assets(location_id);
CREATE INDEX IF NOT EXISTS idx_assets_section   ON assets(section);

CREATE TABLE IF NOT EXISTS movements (
    id                 INTEGER PRIMARY KEY,
    asset_id           INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    from_department_id INTEGER REFERENCES departments(id),
    to_department_id   INTEGER REFERENCES departments(id),
    from_location_id   INTEGER REFERENCES locations(id),
    to_location_id     INTEGER REFERENCES locations(id),
    moved_at           TEXT NOT NULL DEFAULT (datetime('now')),
    reason             TEXT NOT NULL DEFAULT '',
    note               TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS quality_issues (
    id            INTEGER PRIMARY KEY,
    batch_id      INTEGER REFERENCES import_batches(id),
    asset_id      INTEGER REFERENCES assets(id),
    issue_type    TEXT NOT NULL,
    severity      TEXT NOT NULL DEFAULT 'warning',
    detail_ar     TEXT NOT NULL DEFAULT '',
    detail_en     TEXT NOT NULL DEFAULT '',
    source_sheet  TEXT NOT NULL DEFAULT '',
    source_row    INTEGER NOT NULL DEFAULT 0,
    resolved      INTEGER NOT NULL DEFAULT 0
);

CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
    asset_code, name_ar, name_en, serial_number, brand_model, notes,
    content='assets', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS assets_ai AFTER INSERT ON assets BEGIN
    INSERT INTO assets_fts(rowid, asset_code, name_ar, name_en, serial_number, brand_model, notes)
    VALUES (new.id, new.asset_code, new.name_ar, new.name_en, new.serial_number, new.brand_model, new.notes);
END;
CREATE TRIGGER IF NOT EXISTS assets_ad AFTER DELETE ON assets BEGIN
    INSERT INTO assets_fts(assets_fts, rowid, asset_code, name_ar, name_en, serial_number, brand_model, notes)
    VALUES ('delete', old.id, old.asset_code, old.name_ar, old.name_en, old.serial_number, old.brand_model, old.notes);
END;
CREATE TRIGGER IF NOT EXISTS assets_au AFTER UPDATE ON assets BEGIN
    INSERT INTO assets_fts(assets_fts, rowid, asset_code, name_ar, name_en, serial_number, brand_model, notes)
    VALUES ('delete', old.id, old.asset_code, old.name_ar, old.name_en, old.serial_number, old.brand_model, old.notes);
    INSERT INTO assets_fts(rowid, asset_code, name_ar, name_en, serial_number, brand_model, notes)
    VALUES (new.id, new.asset_code, new.name_ar, new.name_en, new.serial_number, new.brand_model, new.notes);
END;
"""

DEPARTMENTS = [
    ("مدير المركز", "Center Manager"),
    ("الحفظ", "Records / Archive"),
    ("عضو النيابه العامه", "Public Prosecution Member"),
    ("Security", "Security"),
    ("officee", "Office"),
    ("Supervaisor", "Supervisor"),
    ("REC", "REC"),
    ("الادلة الجنائيه", "Forensic Evidence"),
    ("الاحوال المدنيه", "Civil Status"),
    ("الشهر العقاري", "Real Estate Registration"),
    ("المرور", "Traffic"),
    ("التامينات الجتماعية", "Social Insurance"),
    ("الجوازات", "Passports"),
    ("النيابه", "Prosecution"),
    ("السجل التجارى", "Commercial Registry"),
    ("كعب العمل", "Labour Card"),
    ("المعاشات", "Pensions"),
    ("front Office", "Front Office"),
    ("المخزن", "Store"),
    ("مكتب البنك", "Bank Office"),
    ("مكتب أمان جوازات", "Passport Safe Office"),
    ("مكتب مدير خدمه عملاء الفرع", "Branch Customer Service Manager"),
    ("مكتب عضو النيابه", "Prosecution Member Office"),
    ("مكتب الجهات الحكوميه", "Government Agencies Office"),
    ("غرفة IT", "IT Room"),
    ("الجهات الحكوميه", "Government Agencies"),
    ("الجزء الخاص بالتصوير والمرور والفيش", "Photography / Traffic / Records"),
]

LOCATIONS = [
    ("مدخل المركز", "Center Entrance", "داخل المركز"),
    ("منطقه انتظار العملاء", "Customer Waiting Area", "داخل المركز"),
    ("مكتب البنك", "Bank Office", "داخل المركز"),
    ("مكتب أمان جوازات", "Passport Safe Office", "داخل المركز"),
    ("مكتب مدير المركز", "Center Manager Office", "داخل المركز"),
    ("غرفة الكهرباء", "Electrical Room", "داخل المركز"),
    ("حمام ذوى المهام", "Accessible WC", "داخل المركز"),
    ("غرفة حفظ خامات النظافه", "Cleaning Supplies Room", "داخل المركز"),
    ("ممر دخوال الموظفين", "Staff Entrance Corridor", "داخل المركز"),
    ("حمام الرجالى", "Men's WC", "داخل المركز"),
    ("حمام السيدات", "Ladies' WC", "داخل المركز"),
    ("البوفيه", "Pantry", "داخل المركز"),
    ("منطقة عمل الجهات الحكوميه", "Government Agencies Area", "داخل المركز"),
    ("مكتب مدير الفرع", "Branch Manager Office", "داخل المركز"),
    ("مكتب عضو النيابه", "Prosecution Member Office", "داخل المركز"),
    ("مكتب Admin", "Admin Office", "داخل المركز"),
    ("مكتب الجهات الحكوميه", "Government Agencies Office", "داخل المركز"),
    ("غرفة IT", "IT Room", "داخل المركز"),
    ("IT room", "IT Room 2", "داخل المركز"),
    ("امام غرفه it", "In front of IT Room", "داخل المركز"),
    ("الجزء الخاص بالتصوير والمرور والفيش", "Photography / Traffic / Records", "داخل المركز"),
    ("Terminal", "Terminal", "داخل المركز"),
    ("خارج المركز", "Outside the Center", "خارج المركز"),
    ("منطقه كهرباء الامن", "Security Power Area", "داخل المركز"),
    ("المخازن(ادوات النظافه)", "Cleaning Supplies Store", "داخل المركز"),
    ("طرقه الحمام", "WC Corridor", "داخل المركز"),
    ("منطقه الاستقبال rep", "Reception Area", "داخل المركز"),
    ("Back office", "Back Office", "داخل المركز"),
    ("امام باب غرفة IT support", "In front of IT Support", "داخل المركز"),
    ("منطقه أنتظار العملاء", "Customer Waiting Area", "داخل المركز"),
]

CATEGORIES = {
    "devices": [
        ("كمبيوتر", "PC"), ("شاشة", "Monitor"), ("طابعة", "Printer"),
        ("سكانر", "Scanner"), ("All-in-1", "All-in-One"), ("تليفون", "Telephone"),
        ("X-Ray", "X-Ray"), ("بوابة أمنية", "Security Gate"), ("أخرى", "Other"),
    ],
    "furniture": [
        ("كرسي", "Chair"), ("مكتب", "Desk"), ("وحدة أدراج", "Drawer Unit"),
        ("ترابيزة", "Table"), ("كنبة", "Sofa"), ("شاشة عرض", "Display Screen"),
        ("رف", "Shelf"), ("دولاب", "Cabinet"), ("ستارة", "Curtain"),
        ("زرع صناعي", "Artificial Plant"), ("طفاية حريق", "Fire Extinguisher"),
        ("سلة مهملات", "Waste Bin"), ("ميكرويف", "Microwave"), ("ثلاجة", "Refrigerator"),
        ("ماكينة قهوة", "Coffee Machine"), ("كولدير مياه", "Water Cooler"),
        ("مكيف", "Air Conditioner"), ("سخان كهربى", "Water Heater"),
        ("مرآة", "Mirror"), ("كمبيوتر", "PC"), ("طابعة", "Printer"),
        ("ماسح بصمه", "Fingerprint Scanner"), ("جهاز كمبيوتر", "PC"),
        ("صوت", "Sound System"), ("أخرى", "Other"),
    ],
    "electrical": [
        ("فيشة كهرباء", "Power Socket"), ("فيش كهرباء", "Power Socket"),
        ("فيشه كهرباء احتياطى", "Spare Power Socket"),
        ("فيش كهرباء (حمراء)", "Red Power Socket"),
        ("وصلة نت", "Network Point"), ("نت", "Network Point"),
        ("تليفون", "Telephone Point"), ("تليفونات", "Telephone Points"),
        ("مفتاح كهرباء", "Light Switch"), ("مفتاح", "Light Switch"),
        ("مفتاح باب خروج", "Exit Door Switch"),
        ("مفتاج باب خروج", "Exit Door Switch"),
        ("مفتاح باب خروج ودخوال", "Door Access Switch"),
        ("مفتاج باب خروج ودخوال", "Door Access Switch"),
        ("وحدة تحكم تكيف", "AC Control"),
        ("بوكس كهرباء مجمعه", "Floor Box"), ("بوكسات كهرباء مجمعه", "Floor Boxes"),
        ("بوكس ارضى كهرباء", "Floor Electrical Box"),
        ("وصله دش", "Shower Mixer"), ("لوحه حريق", "Fire Panel"),
        ("طفايه حريق", "Fire Extinguisher"), ("أخرى", "Other"),
    ],
    "network": [
        ("راوتر", "Router"), ("سويتش", "Switch"), ("نقطة وصول", "Access Point"),
        ("لوحة منافذ", "Patch Panel"), ("نظام صوت", "Sound System"),
        ("مضخم صوت", "Amplifier"), ("أخرى", "Other"),
    ],
}

# Keyword -> (section, canonical category name) for rows with no explicit category.
CATEGORY_RULES = [
    ("كمبيوتر", "devices", "كمبيوتر"),
    ("شاشه", "devices", "شاشة"),
    ("شاشة", "devices", "شاشة"),
    ("monitor", "devices", "شاشة"),
    ("طابع", "devices", "طابعة"),
    ("print", "devices", "طابعة"),
    ("سكانر", "devices", "سكانر"),
    ("ماسح ضوئى", "devices", "سكانر"),
    ("اسبرسو", "furniture", "ماكينة قهوة"),
    ("قهوه", "furniture", "ماكينة قهوة"),
    ("كولدير", "furniture", "كولدير مياه"),
    ("ثلاجه", "furniture", "ثلاجة"),
    ("ميكرويف", "furniture", "ميكرويف"),
    ("غلايه", "furniture", "كولدير مياه"),
    ("سخان", "furniture", "سخان كهربى"),
    ("تكيف", "furniture", "مكيف"),
    ("تليفون", "devices", "تليفون"),
    ("بصمه", "furniture", "ماسح بصمه"),
    ("طفايه", "furniture", "طفاية حريق"),
    ("طفاية", "furniture", "طفاية حريق"),
    ("كرسى", "furniture", "كرسي"),
    ("كراسى", "furniture", "كرسي"),
    ("كنبه", "furniture", "كنبة"),
    ("ترابيز", "furniture", "ترابيزة"),
    ("مكتب", "furniture", "مكتب"),
    ("خليه عمل", "furniture", "مكتب"),
    ("ادراج", "furniture", "وحدة أدراج"),
    ("رف", "furniture", "رف"),
    ("دولاب", "furniture", "دولاب"),
    ("ستارة", "furniture", "ستارة"),
    ("زرع", "furniture", "زرع صناعي"),
    ("شاشه عرض", "furniture", "شاشة عرض"),
    ("تليفزيون", "furniture", "شاشة عرض"),
    ("مرايه", "furniture", "مرآة"),
    ("سله مهملات", "furniture", "سلة مهملات"),
    ("صوت", "network", "نظام صوت"),
    ("راوتر", "network", "راوتر"),
    ("رواتر", "network", "راوتر"),
    ("سويتش", "network", "سويتش"),
    ("switch", "network", "سويتش"),
    ("acess point", "network", "نقطة وصول"),
    ("access point", "network", "نقطة وصول"),
    ("port panel", "network", "لوحة منافذ"),
    ("فيش", "electrical", "فيشة كهرباء"),
    ("مفتاح", "electrical", "مفتاح كهرباء"),
    ("نت", "electrical", "وصلة نت"),
    ("بوكس", "electrical", "بوكس كهرباء مجمعه"),
    ("تحكم تكيف", "electrical", "وحدة تحكم تكيف"),
    ("حريق", "electrical", "لوحه حريق"),
    ("دش", "electrical", "وصله دش"),
]


def default_db_path() -> Path:
    """DB lives next to the exe after packaging, in ./data during development."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent.parent / "data"
    base.mkdir(parents=True, exist_ok=True)
    return base / "inventory.db"


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or default_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR IGNORE INTO branches(id, name_ar, name_en) VALUES (1, ?, ?)",
        ("مركز خدمات مصر - الإسكندرية", "Egypt Services Center - Alexandria"),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO departments(name_ar, name_en) VALUES (?, ?)", DEPARTMENTS
    )
    conn.executemany(
        "INSERT OR IGNORE INTO locations(name_ar, name_en, zone_ar) VALUES (?, ?, ?)",
        LOCATIONS,
    )
    for section, rows in CATEGORIES.items():
        conn.executemany(
            "INSERT OR IGNORE INTO categories(name_ar, name_en, section) VALUES (?, ?, ?)",
            [(ar, en, section) for ar, en in rows],
        )
    conn.commit()


def get_or_create(conn: sqlite3.Connection, table: str, name_ar: str, name_en: str = "", **extra):
    """Return id of a lookup row, creating it when the normalized name is new."""
    name_ar = (name_ar or "").strip()
    if not name_ar:
        return None
    row = conn.execute(
        f"SELECT id FROM {table} WHERE name_ar = ?", (name_ar,)
    ).fetchone()
    if row:
        return row["id"]
    columns = ["name_ar", "name_en", *extra.keys()]
    values = [name_ar, name_en or name_ar, *extra.values()]
    placeholders = ", ".join("?" for _ in values)
    cur = conn.execute(
        f"INSERT INTO {table}({', '.join(columns)}) VALUES ({placeholders})", values
    )
    return cur.lastrowid


def infer_category(section: str, name_ar: str) -> str:
    """Guess a canonical category name from an item description."""
    text = norm(name_ar)
    for keyword, sec, category in CATEGORY_RULES:
        if norm(keyword) in text and (sec == section or section == "devices"):
            return category
    fallback = {
        "devices": "أخرى",
        "furniture": "أخرى",
        "electrical": "أخرى",
        "network": "أخرى",
    }
    return fallback[section]


def build_search_key(*parts: object) -> str:
    """Normalized, compact text used for spelling-tolerant searching."""
    return " ".join(norm(p) for p in parts if p)


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    out = {"total": 0}
    for row in conn.execute("SELECT section, COUNT(*) n FROM assets GROUP BY section"):
        out[row["section"]] = row["n"]
        out["total"] += row["n"]
    out["issues"] = conn.execute(
        "SELECT COUNT(*) n FROM quality_issues WHERE resolved = 0"
    ).fetchone()["n"]
    out["batches"] = conn.execute("SELECT COUNT(*) n FROM import_batches").fetchone()["n"]
    return out
