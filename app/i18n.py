"""Bilingual labels (Arabic / English) for the Windows application."""
from __future__ import annotations

LABELS = {
    "app_title": ("حصر مركز خدمات مصر - الإسكندرية", "Egypt Services Center - Alexandria Inventory"),
    "tab_dashboard": ("لوحة التحكم", "Dashboard"),
    "tab_search": ("البحث المتوسع", "Advanced Search"),
    "tab_import": ("استيراد إكسل", "Excel Import"),
    "tab_issues": ("مراجعة البيانات", "Data Review"),
    "all": ("الكل", "All"),
    "devices": ("الأجهزة", "Devices"),
    "furniture": ("المنقولات", "Furniture"),
    "electrical": ("الكهرباء", "Electrical"),
    "network": ("الشبكات", "Network"),
    "quick_search": ("بحث سريع بالسريال أو اسم القطعة...", "Quick search by serial or item..."),
    "search_placeholder": ("نص حر: اسم القطعة، الماركة، أي كلمة...", "Free text: item name, brand, any word..."),
    "serial_placeholder": ("رقم السريال", "Serial number"),
    "department": ("الإدارة / الجهة", "Department"),
    "location": ("المكان", "Location"),
    "category": ("التصنيف", "Category"),
    "search": ("بحث", "Search"),
    "clear": ("مسح الفلاتر", "Clear filters"),
    "export_excel": ("تصدير إكسل", "Export Excel"),
    "export_pdf": ("تقرير PDF", "PDF Report"),
    "print": ("طباعة", "Print"),
    "results": ("نتيجة", "Results"),
    "count": ("العدد", "Count"),
    "code": ("الكود", "Code"),
    "item": ("القطعة", "Item"),
    "item_en": ("بالإنجليزي", "English"),
    "brand": ("الماركة / الموديل", "Brand / Model"),
    "qty": ("الكمية", "Qty"),
    "notes": ("ملاحظات", "Notes"),
    "area": ("المنطقة", "Area"),
    "mount": ("المكان (حائط/أرضي)", "Mount (wall/floor)"),
    "section": ("القسم", "Section"),
    "status": ("الحالة", "Status"),
    "browse": ("اختيار ملف...", "Browse..."),
    "preview": ("معاينة الملف", "Preview file"),
    "do_import": ("استيراد في قاعدة البيانات", "Import into database"),
    "import_hint": ("اختر ملف إكسل بنفس هيكل الملف الأصلي (4 أوراق).", "Choose an Excel file with the same 4-sheet structure."),
    "unresolved": ("ملاحظات غير محلولة", "Unresolved issues"),
    "resolve": ("تمت المراجعة", "Mark reviewed"),
    "details": ("تفاصيل القطعة", "Asset details"),
    "movements": ("حركات النقل", "Movement history"),
    "close": ("إغلاق", "Close"),
    "total_assets": ("إجمالي القطع", "Total assets"),
    "import_batches": ("دفعات الاستيراد", "Import batches"),
    "by_department": ("حسب الإدارة", "By department"),
    "by_location": ("حسب المكان", "By location"),
    "by_category": ("حسب التصنيف", "By category"),
    "select_file": ("اختر ملف إكسل", "Select Excel file"),
    "ready": ("جاهز", "Ready"),
    "imported": ("تم الاستيراد", "Imported"),
    "saved": ("تم الحفظ", "Saved"),
    "error": ("خطأ", "Error"),
    "no_results": ("لا توجد نتائج مطابقة", "No matching results"),
    "report_title": ("تقرير حصر مركز خدمات مصر - الإسكندرية", "Egypt Services Center - Alexandria Inventory Report"),
    "generated": ("تاريخ التقرير", "Generated"),
    "page": ("صفحة", "Page"),
}


def tr(key: str, lang: str = "ar") -> str:
    ar, en = LABELS.get(key, (key, key))
    return ar if lang == "ar" else en


def section_name(section: str, lang: str = "ar") -> str:
    return tr(section, lang)
