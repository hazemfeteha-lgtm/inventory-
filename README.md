# حصر مركز خدمات مصر - الإسكندرية
# Egypt Services Center - Alexandria Inventory

برنامج ويندوز لحصر وإدارة كل قطع المركز (أجهزة، منقولات، شبكات، كهرباء)
مع بحث متوسع وتصدير إكسل وتقارير طباعة/PDF.

A Windows desktop application for inventorying every asset in the center,
with segmented search, Excel export and printable PDF reports.

## التشغيل / Running from source

```bash
pip install -r requirements.txt
python scripts/import_excel.py "path/to/حصر مركز  خدمات مصر الاسكندريه.xlsx" --write
python run.py
```

قاعدة البيانات تُCREATE تلقائياً في `data/inventory.db` أثناء التطوير،
وبجانب ملف الـ exe بعد التغليف.
The SQLite database is created at `data/inventory.db` in development and
next to the EXE after packaging.

## الشاشات / Screens

- **لوحة التحكم / Dashboard** — أعداد القطع حسب القسم والإدارة والمكان.
- **البحث المتوسع / Advanced Search** — تبويبات (أجهزة/منقولات/كهرباء/شبكات)
  + فلاتر الإدارة والمكان والتصنيف + بحث نصي متسامح مع اختلاف الكتابة العربية
  + بحث بالسريال. عند فتح نتيجة بالضغط المزدوج تظهر التفاصيل وحركة النقل.
- **استيراد إكسل / Excel Import** — اختر ملف بنفس هيكل الملف الأصلي (4 أوراق)،
  اعرض المعاينة ثم استورد. كل استيراد = دفعة جديدة (`import_batches`).
- **مراجعة البيانات / Data Review** — الصفوف المعلّمة (سريال مكرر، كمية ناقصة،
  تعارض الإجماليات) مع إمكانية تحديد "تمت المراجعة".
- **تصدير / Export** — إكسل بنفس شكل الملف الأصلي (4 أوراق)، أو تقرير PDF/طباعة
  مجمّع حسب الإدارة.

## قالب الحصر الجديد / New inventory template

`templates/inventory_template.xlsx` — انسخه واملأه بنفس الأعمدة، ثم استورده من
تبويب "استيراد إكسل". كل استيراد يُسجّل كدفعة جديدة. إذا أردت استيراد نسخة
محدّثة من نفس الملف، راجع الدفعات القديمة قبل حذفها (النسخة الحالية تضيف صفوفاً
جديدة ولا تحذف القديمة تلقائياً).

Copy `templates/inventory_template.xlsx`, fill it with the same columns and import
it from the Excel Import tab. Each import is stored as a new batch. Re-importing an
updated file currently adds new rows rather than replacing old ones - review batches
before deleting them.

`exports/sample_inventory_export.xlsx` is a sample export of the current database.

## بناء ملف exe / Building the EXE

أضف المستودع إلى GitHub ثم شغّل الـ workflow `Build Windows EXE`
من تبويب Actions (أو ادفع tag يبدأ بـ `v`). الملف الجاهز ينزل كـ Artifact.

Push to GitHub and run the **Build Windows EXE** workflow from the Actions tab
(or push a `v*` tag). The built EXE is uploaded as an artifact.
