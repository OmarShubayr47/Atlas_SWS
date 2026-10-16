"""Projector test pattern: native resolution, overscan, and focus in one image.

Why: the projector's EDID *prefers* 1920x1080, and it even accepts 4K — but
input modes say what the scaler ACCEPTS, not what the panel HAS. Budget
projectors routinely take 1080p and scale it down onto a smaller panel. For a
touch interface that matters twice: effective resolution sets how small a
button can be, and any overscan (edges cropped) breaks touch-to-pixel mapping.

The image, exactly 1920x1080, drawn pixel-for-pixel:

    top-left     1-px checkerboard          the hardest pattern to reproduce
    top-right    1-px vertical lines        tests horizontal resolution
    bottom-left  1-px horizontal lines      tests vertical resolution
    bottom-right line-period bars 1,2,3,4,6,8 px, labelled
    frame        1-px white border + corner arrows: overscan check

How to read it (walk up close to the image):
    native 1080p, in focus  1-px areas look like fine, EVEN texture/grey;
                            the 4 and 8 px bars are crisp stripes
    downscaled panel        1-px areas show BEAT BANDS / waves / moire —
                            coarse regular stripes much larger than a pixel
    out of focus            everything soft, 4 px bars smeared too — fix focus
                            first; blur hides the evidence
    overscan                any edge of the white border missing = cropped

Usage:
    python tests/projector_pattern.py [seconds]             resolution/focus
    python tests/projector_pattern.py --overscan [seconds]  measure edge crop
    python tests/projector_pattern.py --flip [seconds]      rotated 180 deg

--flip exists because focus on this projector varies with height (soft at
the top). Rotating the pattern moves each test region into the other half, so
every region can be judged in the sharp zone rather than confusing a focus
gradient with a resolution limit.

--overscan draws coloured bands, each 10 px wide, stepping inward from the
image edge. The outermost colour still visible on a side tells you how many
pixels that side is cropped by: outermost visible = band 3 means ~30 px lost
on that edge. The legend in the centre maps colour to pixels.
"""
import os
import pathlib
import signal
import sys
import time

import numpy as np

W, H = 1920, 1080
OUT = pathlib.Path(__file__).resolve().parent.parent / "scratch" / "projector_pattern.png"


def build() -> np.ndarray:
    img = np.zeros((H, W, 3), dtype=np.uint8)
    hw, hh = W // 2, H // 2
    y, x = np.mgrid[0:H, 0:W]

    tl = ((x + y) % 2 == 0)
    tr = (x % 2 == 0)
    bl = (y % 2 == 0)
    img[:hh, :hw][tl[:hh, :hw]] = 255
    img[:hh, hw:][tr[:hh, hw:]] = 255
    img[hh:, :hw][bl[hh:, :hw]] = 255

    # bottom-right: vertical bars of increasing period, each in its own band
    periods = [1, 2, 3, 4, 6, 8]
    band = (H - hh) // len(periods)
    for i, p in enumerate(periods):
        y0, y1 = hh + i * band + 6, hh + (i + 1) * band - 6
        cols = ((np.arange(hw, W) - hw) // p) % 2 == 0
        img[y0:y1, hw:][:, cols] = 255

    # 1-px white frame at the absolute edge + a grey divider cross
    img[0, :] = img[-1, :] = 255
    img[:, 0] = img[:, -1] = 255
    img[hh - 1:hh + 1, :] = 128
    img[:, hw - 1:hw + 1] = 128
    return img


BAND_PX = 10
BAND_COLOURS = [  # distinct, nameable colours
    ("white", (255, 255, 255)), ("red", (255, 0, 0)), ("green", (0, 200, 0)),
    ("blue", (40, 80, 255)), ("yellow", (255, 230, 0)), ("magenta", (255, 0, 255)),
    ("cyan", (0, 230, 230)), ("orange", (255, 130, 0)), ("grey", (140, 140, 140)),
    ("pink", (255, 150, 190)), ("lime", (170, 255, 0)), ("purple", (140, 60, 200)),
]


def build_overscan() -> np.ndarray:
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for k, (_, rgb) in enumerate(BAND_COLOURS):
        a, b = k * BAND_PX, (k + 1) * BAND_PX
        img[a:b, a:W - a] = rgb          # top
        img[H - b:H - a, a:W - a] = rgb  # bottom
        img[a:H - a, a:b] = rgb          # left
        img[a:H - a, W - b:W - a] = rgb  # right
    return img


def main() -> int:
    overscan = "--overscan" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    seconds = float(args[0]) if args else 180.0
    img = build_overscan() if overscan else build()
    OUT.parent.mkdir(exist_ok=True)

    os.environ.setdefault("SDL_VIDEODRIVER", "wayland")
    import pygame  # after SDL env is set

    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN | pygame.NOFRAME)
    pygame.mouse.set_visible(False)
    surf = pygame.surfarray.make_surface(img.swapaxes(0, 1))

    font = pygame.font.Font(None, 34)
    if overscan:
        big = pygame.font.Font(None, 44)
        x0, y0 = W // 2 - 330, H // 2 - 290
        surf.blit(big.render("OVERSCAN: outermost colour visible on each edge?",
                             True, (255, 255, 255)), (x0 - 120, y0 - 60))
        for k, (name, rgb) in enumerate(BAND_COLOURS):
            t = big.render(f"band {k}: {name:<8} = pixels {k * BAND_PX}-{(k + 1) * BAND_PX - 1}"
                           " from edge", True, rgb)
            surf.blit(t, (x0, y0 + k * 44))
        out = OUT.with_name("projector_overscan.png")
        pygame.image.save(surf, str(out))
        return _show(pygame, screen, surf, seconds, out)
    labels = [(f"{p} px", (W // 2 + 8, H // 2 + i * ((H // 2) // 6) + 10))
              for i, p in enumerate([1, 2, 3, 4, 6, 8])]
    for text, pos in labels:
        t = font.render(text, True, (255, 60, 60), (0, 0, 0))
        surf.blit(t, pos)
    for text, pos in [("1px checker", (12, 12)), ("1px vertical", (W // 2 + 12, 12)),
                      ("1px horizontal", (12, H // 2 + 12))]:
        surf.blit(font.render(text, True, (255, 60, 60), (0, 0, 0)), pos)

    if "--flip" in sys.argv:
        surf = pygame.transform.rotate(surf, 180)

    # Save exactly what is displayed, labels included, for the grim comparison.
    pygame.image.save(surf, str(OUT))
    return _show(pygame, screen, surf, seconds, OUT)


def _show(pygame, screen, surf, seconds: float, saved) -> int:
    screen.blit(surf, (0, 0))
    pygame.display.flip()
    print(f"pattern up at {screen.get_size()} for {seconds:.0f}s (saved {saved})",
          flush=True)

    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    signal.signal(signal.SIGINT, lambda *_: stop.update(now=True))
    end = time.monotonic() + seconds
    while not stop["now"] and time.monotonic() < end:
        for ev in pygame.event.get():
            if ev.type in (pygame.QUIT, pygame.KEYDOWN):
                stop["now"] = True
        screen.blit(surf, (0, 0))
        pygame.display.flip()
        time.sleep(0.1)
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
