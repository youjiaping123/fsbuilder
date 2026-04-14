from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DATA = [
    ("Models", 91),
    ("Analysis Parsing", 83),
    ("Analysis Provider", 60),
    ("Analysis Service", 96),
    ("Application", 88),
    ("CLI", 93),
    ("Gen Renderers", 98),
    ("Gen Service", 78),
    ("WebUI API", 97),
    ("WebUI Server", 24),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def main() -> None:
    width = 1400
    height = 900
    margin_left = 280
    margin_right = 80
    margin_top = 90
    bar_gap = 18
    bar_height = 46
    chart_width = width - margin_left - margin_right
    max_value = 100

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = _font(34)
    label_font = _font(24)
    tick_font = _font(20)

    draw.text(
        (margin_left, 24),
        "Module-level Coverage from the Current Test Report",
        fill="#1f2937",
        font=title_font,
    )

    chart_top = margin_top
    chart_bottom = chart_top + len(DATA) * (bar_height + bar_gap) - bar_gap

    # grid and x-axis labels
    for tick in range(0, 101, 20):
        x = margin_left + int(chart_width * tick / max_value)
        draw.line((x, chart_top - 12, x, chart_bottom + 12), fill="#d1d5db", width=1)
        draw.text((x - 12, chart_bottom + 20), str(tick), fill="#4b5563", font=tick_font)

    draw.text((width // 2 - 60, height - 40), "Coverage (%)", fill="#374151", font=label_font)

    y = chart_top
    for label, value in DATA:
        draw.text((20, y + 8), label, fill="#111827", font=label_font)
        bar_len = int(chart_width * value / max_value)
        draw.rounded_rectangle(
            (margin_left, y, margin_left + bar_len, y + bar_height),
            radius=10,
            fill="#4C78A8",
            outline="#254B6E",
            width=2,
        )
        draw.text(
            (margin_left + bar_len + 12, y + 8),
            f"{value}%",
            fill="#111827",
            font=label_font,
        )
        y += bar_height + bar_gap

    output_dir = Path(__file__).parent
    image.save(output_dir / "coverage_chart_python.png")


if __name__ == "__main__":
    main()
