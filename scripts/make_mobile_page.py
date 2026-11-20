"""Generate a self-contained mobile-friendly HTML viewer with all assets embedded."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db import connect
from app.search import SearchFilters, find_assets

OUT = ROOT / "mobile" / "index.html"

HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>حصر مركز خدمات مصر - الإسكندرية</title>
<style>
:root{--blue:#2f6da3;--navy:#123a5a;--bg:#f2f6fa;--card:#fff;--line:#dce5ee}
*{box-sizing:border-box;font-family:"Noto Sans Arabic",Tahoma,Arial,sans-serif}
body{margin:0;background:var(--bg);color:#223344}
header{background:linear-gradient(135deg,#123a5a,#2f6da3);color:#fff;padding:18px 16px 14px;
       position:sticky;top:0;z-index:5;box-shadow:0 2px 10px #0002}
h1{font-size:17px;margin:0 0 4px}
.sub{font-size:12px;opacity:.85}
.wrap{padding:12px}
.search{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:10px;
        font-size:15px;background:#fff;margin-bottom:10px}
.chips{display:flex;gap:6px;overflow-x:auto;padding-bottom:6px;scrollbar-width:none}
.chip{white-space:nowrap;border:1px solid var(--line);background:#fff;color:#456;padding:7px 12px;
      border-radius:20px;font-size:13px;cursor:pointer}
.chip.on{background:var(--blue);border-color:var(--blue);color:#fff}
.row{display:flex;gap:8px;margin:10px 0}
.row select{flex:1;padding:9px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:13px}
.bar{display:flex;justify-content:space-between;align-items:center;font-size:13px;color:#567;margin:6px 2px 10px}
.btn{border:0;background:var(--blue);color:#fff;padding:8px 14px;border-radius:8px;font-size:12px;cursor:pointer}
.cards{display:grid;gap:9px}
.card{background:var(--card);border:1px solid var(--line);border-radius:11px;padding:12px;
      box-shadow:0 1px 4px #0001}
.card h3{margin:0 0 6px;font-size:15px;display:flex;justify-content:space-between;gap:8px}
.code{font-size:10px;background:#e8f1f9;color:var(--navy);padding:3px 7px;border-radius:6px;white-space:nowrap}
.serial{font-family:monospace;font-size:13px;color:#b04a00;direction:ltr;display:inline-block}
.meta{font-size:12px;color:#667;line-height:1.8}
.meta b{color:#334}
.note{font-size:11px;color:#888;margin-top:5px}
.empty{text-align:center;padding:40px 10px;color:#889}
footer{text-align:center;font-size:11px;color:#99a;padding:20px 10px 30px}
</style>
</head>
<body>
<header>
  <h1>حصر مركز خدمات مصر - الإسكندريه</h1>
  <div class="sub">قاعدة البيانات الكاملة — تعمل بدون إنترنت على الموبايل</div>
</header>
<div class="wrap">
  <input id="q" class="search" placeholder="ابحث بالاسم، السريال، المكان، أو أي كلمة...">
  <div class="chips" id="chips"></div>
  <div class="row">
    <select id="dept"><option value="">كل الإدارات</option></select>
    <select id="loc"><option value="">كل الأماكن</option></select>
  </div>
  <div class="bar"><span id="count"></span><button class="btn" id="csv">تصدير CSV</button></div>
  <div class="cards" id="list"></div>
</div>
<footer>البيانات مأخوذة من ملف الإكسل الأصلي — نسخة العرض على الموبايل</footer>
<script>
const DATA = __DATA__;
const sections = [["","الكل"],["devices","الأجهزة"],["furniture","المنقولات"],
                  ["electrical","الكهرباء"],["network","الشبكات"]];
let section = "";
const $ = id => document.getElementById(id);
const norm = s => (s||"").toString().toLowerCase().replace(/[أإآ]/g,"ا").replace(/ة/g,"ه")
                   .replace(/ى/g,"ي").replace(/[ـ\\u064b-\\u0652]/g,"").trim();

function fillSelect(id, field){
  const values = [...new Set(DATA.map(x=>x[field]).filter(Boolean))].sort();
  $(id).insertAdjacentHTML("beforeend", values.map(v=>`<option>${v}</option>`).join(""));
}
function chips(){
  $("chips").innerHTML = sections.map(([k,l])=>
    `<button class="chip ${k===section?'on':''}" data-k="${k}">${l}</button>`).join("");
  $("chips").querySelectorAll("button").forEach(b=>b.onclick=()=>{
    section=b.dataset.k; chips(); render();
  });
}
function filtered(){
  const q=norm($("q").value), d=$("dept").value, l=$("loc").value;
  return DATA.filter(x=>{
    if(section && x.section!==section) return false;
    if(d && x.department!==d) return false;
    if(l && x.location!==l) return false;
    if(q && !norm(x.search).includes(q)) return false;
    return true;
  });
}
function render(){
  const rows=filtered();
  $("count").textContent = `عدد النتائج: ${rows.length}`;
  $("list").innerHTML = rows.length ? rows.slice(0,600).map(x=>`
    <div class="card">
      <h3><span>${x.name}</span><span class="code">${x.code}</span></h3>
      <div class="meta">
        ${x.serial?`السريال: <span class="serial">${x.serial}</span><br>`:""}
        ${x.department?`الإدارة: <b>${x.department}</b><br>`:""}
        ${x.location?`المكان: <b>${x.location}</b><br>`:""}
        ${x.category?`التصنيف: ${x.category} &nbsp;|&nbsp; `:""}الكمية: <b>${x.qty}</b>
      </div>
      ${x.notes?`<div class="note">${x.notes}</div>`:""}
    </div>`).join("") : `<div class="empty">لا توجد نتائج مطابقة</div>`;
}
$("q").oninput=render; $("dept").onchange=render; $("loc").onchange=render;
$("csv").onclick=()=>{
  const rows=filtered();
  const head=["كود","القطعة","السريال","الإدارة","المكان","التصنيف","الكمية","ملاحظات"];
  const lines=[head,...rows.map(x=>[x.code,x.name,x.serial,x.department,x.location,x.category,x.qty,x.notes])]
    .map(r=>r.map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(","));
  const url=URL.createObjectURL(new Blob(["\\ufeff"+lines.join("\\n")],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a"); a.href=url; a.download="inventory.csv"; a.click();
};
fillSelect("dept","department"); fillSelect("loc","location"); chips(); render();
</script>
</body></html>"""


def main() -> None:
    conn = connect()
    rows = find_assets(conn, SearchFilters())
    data = [{
        "code": r["asset_code"], "name": r["name_ar"], "serial": r["serial_number"],
        "department": r["dept_ar"] or "", "location": r["loc_ar"] or "",
        "category": r["category_ar"] or "", "qty": r["quantity"],
        "notes": r["notes"], "section": r["section"],
        "search": " ".join(str(r[k] or "") for k in
                           ("asset_code", "name_ar", "name_en", "serial_number", "brand_model",
                            "notes")) + " " + (r["dept_ar"] or "") + " " + (r["loc_ar"] or ""),
    } for r in rows]
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    print(f"wrote {OUT} ({len(data)} assets, {OUT.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
