"""Build a silent Arabic caption walkthrough video from the real UI screenshots.

Uses Qt to render correctly-shaped Arabic captions, then ffmpeg for H.264 output.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "screenshots"
OUT = ROOT / "videos" / "شرح_البرنامج.mp4"

SLIDES = [
    (None, "حصر مركز خدمات مصر - الإسكندريه\nبرنامج إدارة أصول المركز", "intro"),
    ("01_dashboard.png", "١ - لوحة التحكم: إجمالي القطع وأعدادها حسب الإدارة والمكان", "dashboard"),
    ("02_search.png", "٢ - البحث المتوسع: فلاتر القسم والإدارة والمكان والتصنيف", "search"),
    ("05_search_serial.png", "٣ - بحث سريع برقم السريال مع رقم القطعة والنتيجة الفورية", "serial"),
    ("06_asset_details.png", "٤ - فتح القطعة يعرض كل بياناتها وتاريخ حركاتها", "details"),
    ("03_import.png", "٥ - استيراد إكسل: اختر الملف، اعرض المعاينة، ثم احفظ", "import"),
    ("04_issues.png", "٦ - مراجعة البيانات: السريالات المكررة والكميات الناقصة", "review"),
    (None, "التصدير: إكسل بنفس الشكل الأصلي + تقرير PDF وطباعة\nالمستودع: github.com/hazemfeteha-lgtm/inventory-", "outro"),
]


def render_slide(image_path: Path | None, caption: str, target: Path, first: bool, last: bool) -> None:
    width, height = 1280, 720
    canvas = QImage(width, height, QImage.Format.Format_ARGB32)
    navy = QColor("#123a5a")
    canvas.fill(QColor("#0d2d47") if first or last else QColor("#eef3f8"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    if image_path and image_path.exists():
        shot = QImage(str(image_path))
        scaled = shot.scaled(width - 40, height - 150, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        painter.drawImage((width - scaled.width()) // 2, 16, scaled)

    banner = QColor("#2f6da3")
    painter.fillRect(0, height - 118, width, 118, banner)
    font = QFont("Noto Sans Arabic")
    font.setPointSize(19 if "\n" not in caption else 22)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(20, height - 118, width - 40, 118,
                     Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, caption)
    painter.end()
    canvas.save(str(target))


def main() -> None:
    app = QApplication(sys.argv)
    with tempfile.TemporaryDirectory(prefix="inv_slides_") as tmp:
        folder = Path(tmp)
        for i, (shot, caption, _) in enumerate(SLIDES, start=1):
            render_slide(SHOTS / shot if shot else None, caption,
                         folder / f"slide_{i:02d}.png", i == 1, i == len(SLIDES))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", "1/5", "-i", str(folder / "slide_%02d.png"),
            "-vf", "scale=1280:720,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-movflags", "+faststart", str(OUT),
        ]
        subprocess.run(cmd, check=True)
    print(OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
