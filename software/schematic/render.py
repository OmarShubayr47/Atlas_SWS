"""Draw a template result to SVG: the circuit, a title, and a caption.

The caption carries the computed values, every assumption and every note,
so the drawing on its own tells the whole story — including what was NOT
given by the user. It uses schemdraw's own SVG backend, so matplotlib is not
needed; one drawing takes a few milliseconds on the Pi 5 (measured 4 ms for
a divider).

The SVG is black lines on a transparent background: right for paper or any
other viewer. The projected viewer inverts it (light lines on black).

Layout: title on top, circuit on the left, caption in a column on its right —
landscape, like the 16:9 projector, so the circuit is drawn as large as
possible. Font: schemdraw sizes text with Arial metrics; Liberation Sans is
metric-compatible with Arial (and installed on the Pi), so the computed
drawing size matches what Chromium renders and no caption is clipped. A
viewer without it falls back to its default sans (Arial on Windows).
"""
import textwrap

import schemdraw
import schemdraw.elements as elm

schemdraw.use("svg")

FONT = "Liberation Sans"
CAPTION_CHARS = 52
TITLE_SIZE = 20
TEXT_SIZE = 13
LINE_STEP = 0.62      # caption line spacing, in drawing units
GUTTER = 1.5          # space between circuit and caption, in drawing units


def caption_lines(result) -> list[str]:
    lines = [f"{label}: {text}" for label, text in result.derived]
    lines.append("")
    for text in result.assumptions:
        lines += textwrap.wrap("Assumed: " + text, CAPTION_CHARS)
    for text in result.notes:
        lines += textwrap.wrap("Note: " + text, CAPTION_CHARS)
    return lines


def render(template, result, title: str) -> bytes:
    with schemdraw.Drawing(show=False) as d:
        d.config(unit=3, fontsize=15, font=FONT)
        template.draw(d, result)
        box = d.get_bbox()
        elm.Label().at((box.xmin, box.ymax + 1.2)).label(
            title, halign="left", fontsize=TITLE_SIZE)
        x, y = box.xmax + GUTTER, box.ymax
        for line in caption_lines(result):
            if line:
                elm.Label().at((x, y)).label(line, halign="left", fontsize=TEXT_SIZE)
            y -= LINE_STEP
    svg = d.get_imagedata("svg")
    return svg if isinstance(svg, bytes) else svg.encode("utf-8")
