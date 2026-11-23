#!/usr/bin/env python3
"""The World Today - 22 November 2026. One dense 1024x1024 news image.

Pure Python standard library. Deterministic: no network, no clock, no
randomness. Renders at 2048x2048 (2x supersampling, all geometry computed
in device space) and averages down to 1024x1024. Writes entry.png to
$MAKEFUN_OUTPUT_DIR or /output. Run: python3 main.py
"""

import os
import struct
import zlib

S = 2                      # supersample factor
W, H = 1024 * S, 1024 * S  # device canvas

# ---------------------------------------------------------------- palette
INK    = (13, 20, 34)     # page background, deep navy
PANEL  = (22, 33, 54)     # card background
PANEL2 = (27, 40, 66)     # lighter card
PAPER  = (245, 239, 224)   # paper white
PAPER2 = (214, 222, 232)   # muted paper
GOLD   = (232, 184, 75)    # masthead accent / date-check
RED    = (224, 82, 70)     # breaking / Americas
BLUE   = (96, 165, 224)    # Europe
GREEN  = (88, 196, 120)    # Asia-Pacific
ORANGE = (240, 150, 60)    # Africa
PURPLE = (178, 132, 224)   # Middle East
TEAL   = (72, 200, 190)    # Oceania / sport
GREY   = (120, 134, 152)   # secondary text
LINE   = (58, 74, 100)     # hairlines
MAPSEA = (16, 28, 48)      # map sea
MAPLAND = (52, 84, 96)     # map land
MAPLINE = (120, 160, 170)  # map outline

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.px = bytearray(W * H * 3)
        self.fill_rect(0, 0, W, H, INK)

    def set(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x, y, w, h = int(x), int(y), int(w), int(h)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        for yy in range(y0, y1):
            base = (yy * W + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c, t=2):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def hline(self, x, y, w, c, t=2):
        self.fill_rect(x, y, w, t, c)

    def disc(self, cx, cy, r, c):
        cx, cy, r = int(cx), int(cy), int(r)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    self.set(cx + dx, cy + dy, c)

    def line(self, x0, y0, x1, y1, c, w=2):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = x1 - x0, y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        r = max(1, w // 2)
        for i in range(steps + 1):
            t = i / steps
            self.disc(int(round(x0 + dx * t)), int(round(y0 + dy * t)), r, c)

    def poly(self, pts, c, close=True):
        n = len(pts)
        for i in range(n - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c, 2)
        if close and n > 2:
            self.line(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], c, 2)

    def fill_poly(self, pts, c):
        # scanline fill, device space
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(H, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                for x in range(max(0, int(xs[j])), min(W, int(xs[j + 1]) + 1)):
                    self.set(x, y, c)

    def downsample_png(self):
        out = bytearray(W // S * H // S * 3)
        ow, oh = W // S, H // S
        for y in range(oh):
            for x in range(ow):
                r = g = b = 0
                for dy in range(S):
                    for dx in range(S):
                        i = ((y * S + dy) * W + x * S + dx) * 3
                        r += self.px[i]
                        g += self.px[i + 1]
                        b += self.px[i + 2]
                o = (y * ow + x) * 3
                out[o], out[o + 1], out[o + 2] = r // 4, g // 4, b // 4
        raw = b"".join(b"\x00" + bytes(out[y * ow * 3:(y + 1) * ow * 3])
                       for y in range(oh))
        comp = zlib.compress(raw, 9)

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data +
                    struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        png = (b"\x89PNG\r\n\x1a\n" +
               chunk(b"IHDR", struct.pack(">IIBBBBB", ow, oh, 8, 2, 0, 0, 0)) +
               chunk(b"IDAT", comp) + chunk(b"IEND", b""))
        return png


# ------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows, 5 bits, bit 4 = leftmost pixel. Caps only.
FONT5 = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ' ': (0, 0, 0, 0, 0, 0, 0),
    '.': (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ',': (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    ':': (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ';': (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    '-': (0, 0, 0, 0x0E, 0, 0, 0),
    '/': (0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    '%': (0x19, 0x1A, 0x02, 0x04, 0x08, 0x0B, 0x13),
    '$': (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    '+': (0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0),
    '=': (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '?': (0x0E, 0x11, 0x01, 0x06, 0x04, 0, 0x04),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0, 0x04),
    '*': (0, 0x15, 0x0E, 0x1F, 0x0E, 0x15, 0),
    '#': (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    '@': (0x0E, 0x11, 0x17, 0x15, 0x16, 0x10, 0x0E),
    '_': (0, 0, 0, 0, 0, 0, 0x1F),
    '<': (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    '>': (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
}

def text5(cv, x, y, s, color, scale=2, spacing=1):
    """Draw caps text at device coords. scale 2 => 5x7 final pixels."""
    cx = int(x)
    y = int(y)
    for ch in s.upper():
        g = FONT5.get(ch, FONT5[' '])
        for row in range(7):
            bits = g[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    cv.fill_rect(cx + col * scale, y + row * scale,
                                 scale, scale, color)
        cx += (5 + spacing) * scale
    return cx

def text5_w(s, scale=2, spacing=1):
    return len(s) * (5 + spacing) * scale - spacing * scale

def wrap5(s, max_chars):
    words = s.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if len(t) <= max_chars:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ------------------------------------------- 12x16 stroke display font
# Grid 12 wide x 16 tall. Each glyph: list of polylines, points (x, y).
STROKE = {
    'A': [[(1, 15), (6, 0), (11, 15)], [(3.5, 10), (8.5, 10)]],
    'B': [[(1, 0), (1, 15)], [(1, 0), (8, 0), (10, 2), (10, 6), (8, 8), (1, 8)],
          [(1, 8), (8, 8), (10, 10), (10, 13), (8, 15), (1, 15)]],
    'C': [[(10, 2), (8, 0), (3, 0), (1, 2), (1, 13), (3, 15), (8, 15), (10, 13)]],
    'D': [[(1, 0), (1, 15)], [(1, 0), (7, 0), (10, 3), (10, 12), (7, 15), (1, 15)]],
    'E': [[(10, 0), (1, 0), (1, 15), (10, 15)], [(1, 7), (8, 7)]],
    'F': [[(10, 0), (1, 0), (1, 15)], [(1, 7), (8, 7)]],
    'G': [[(10, 2), (8, 0), (3, 0), (1, 2), (1, 13), (3, 15), (8, 15), (10, 13),
           (10, 8), (6, 8)]],
    'H': [[(1, 0), (1, 15)], [(11, 0), (11, 15)], [(1, 8), (11, 8)]],
    'I': [[(3, 0), (9, 0)], [(6, 0), (6, 15)], [(3, 15), (9, 15)]],
    'J': [[(4, 0), (10, 0)], [(8, 0), (8, 13), (6, 15), (3, 15), (1, 13)]],
    'K': [[(1, 0), (1, 15)], [(10, 0), (1, 8)], [(3, 6), (10, 15)]],
    'L': [[(1, 0), (1, 15), (10, 15)]],
    'M': [[(1, 15), (1, 0), (6, 9), (11, 0), (11, 15)]],
    'N': [[(1, 15), (1, 0), (11, 15), (11, 0)]],
    'O': [[(3, 0), (9, 0), (11, 2), (11, 13), (9, 15), (3, 15), (1, 13),
           (1, 2), (3, 0)]],
    'P': [[(1, 15), (1, 0), (8, 0), (10, 2), (10, 6), (8, 8), (1, 8)]],
    'Q': [[(3, 0), (9, 0), (11, 2), (11, 13), (9, 15), (3, 15), (1, 13),
           (1, 2), (3, 0)], [(8, 10), (11, 15)]],
    'R': [[(1, 15), (1, 0), (8, 0), (10, 2), (10, 6), (8, 8), (1, 8)],
          [(4, 8), (11, 15)]],
    'S': [[(10, 2), (8, 0), (3, 0), (1, 2), (1, 6), (3, 8), (9, 8), (11, 10),
           (11, 13), (9, 15), (3, 15), (1, 13)]],
    'T': [[(1, 0), (11, 0)], [(6, 0), (6, 15)]],
    'U': [[(1, 0), (1, 13), (3, 15), (9, 15), (11, 13), (11, 0)]],
    'V': [[(1, 0), (6, 15), (11, 0)]],
    'W': [[(1, 0), (3, 15), (6, 6), (9, 15), (11, 0)]],
    'X': [[(1, 0), (11, 15)], [(11, 0), (1, 15)]],
    'Y': [[(1, 0), (6, 8), (11, 0)], [(6, 8), (6, 15)]],
    'Z': [[(1, 0), (11, 0), (1, 15), (11, 15)]],
    '0': [[(3, 0), (9, 0), (11, 2), (11, 13), (9, 15), (3, 15), (1, 13),
           (1, 2), (3, 0)], [(3, 3), (9, 12)]],
    '1': [[(4, 2), (7, 0), (7, 15)], [(4, 15), (10, 15)]],
    '2': [[(1, 2), (3, 0), (9, 0), (11, 2), (11, 6), (9, 8), (1, 15), (11, 15)]],
    '3': [[(1, 0), (9, 0), (11, 2), (11, 6), (9, 8), (1, 8)],
          [(9, 8), (11, 10), (11, 13), (9, 15), (1, 15)]],
    '4': [[(9, 0), (9, 15)], [(1, 10), (11, 10)], [(9, 0), (1, 10)]],
    '5': [[(10, 0), (1, 0), (1, 7), (9, 7), (11, 9), (11, 13), (9, 15),
           (3, 15), (1, 13)]],
    '6': [[(10, 2), (8, 0), (3, 0), (1, 2), (1, 13), (3, 15), (9, 15),
           (11, 13), (11, 9), (9, 7), (3, 7), (1, 9)]],
    '7': [[(1, 0), (11, 0), (5, 15)]],
    '8': [[(3, 0), (9, 0), (11, 2), (11, 6), (9, 8), (3, 8), (1, 6),
           (1, 2), (3, 0)],
          [(3, 8), (9, 8), (11, 10), (11, 13), (9, 15), (3, 15), (1, 13),
           (1, 10), (3, 8)]],
    '9': [[(1, 13), (1, 6), (3, 7), (9, 7), (11, 9), (11, 13), (9, 15),
           (3, 15), (1, 13)],
          [(1, 6), (1, 2), (3, 0), (9, 0), (11, 2), (11, 6)]],
    ' ': [],
    '.': [[(5, 14), (7, 14), (7, 15), (5, 15)]],
    '-': [[(2, 8), (10, 8)]],
    ':': [[(5, 4), (7, 4), (7, 6), (5, 6)], [(5, 10), (7, 10), (7, 12), (5, 12)]],
    '/': [[(10, 15), (2, 0)]],
    '(': [[(8, 0), (4, 4), (4, 11), (8, 15)]],
    ')': [[(4, 0), (8, 4), (8, 11), (4, 15)]],
    '%': [[(2, 0), (5, 0), (5, 4), (2, 4), (2, 0)],
          [(10, 15), (2, 0)],
          [(7, 11), (10, 11), (10, 15), (7, 15), (7, 11)]],
    '$': [[(6, 0), (6, 15)], [(10, 2), (8, 0), (3, 0), (1, 2), (1, 6),
           (3, 8), (9, 8), (11, 10), (11, 13), (9, 15), (3, 15), (1, 13)]],
    ',': [[(5, 13), (7, 13), (7, 15), (4, 15)]],
}

def text_stroke(cv, x, y, s, color, scale=2.0, spacing=2.0):
    """Display text in device coords. scale: device px per grid unit.
    A scale of 2.0 on the 2048 canvas = 12x16 final glyphs."""
    cx = int(x)
    y = int(y)
    wdt = max(2, int(round(scale * 0.9)))
    for ch in s.upper():
        for stroke in STROKE.get(ch, []):
            for a, b in zip(stroke, stroke[1:]):
                cv.line(int(round(cx + a[0] * scale)),
                        int(round(y + a[1] * scale)),
                        int(round(cx + b[0] * scale)),
                        int(round(y + b[1] * scale)), color, wdt)
        cx += int(round((12 + spacing) * scale))
    return cx

def text_stroke_w(s, scale=2.0, spacing=2.0):
    return int(round(len(s) * (12 + spacing) * scale))

# ------------------------------------------------------------------ data
# 54 stories. Headline + one detail line. Dates are shown on the card
# whenever the event is not 22 November itself. All figures verified
# against Reuters / AP / AFP / BBC / UN News / WHO / EU Commission
# on Monday 23 Nov 2026. COP31: collapsed Sun 22 Nov, no deal adopted.
# Cikande: 22 Nov figures 3 dead / 36 missing (Mon update 24 killed
# came later and is NOT the 22 Nov figure). GTA VI: $1.84bn was the
# Sensor Tower morning estimate of 19 Nov; Rockstar/Take-Two's
# official figure, 20 Nov, is $3.79bn day-one retail, 32.5m pre-sold.

LEADS = [
    ("COP31 - ANTALYA", ("COP31", "COLLAPSES"), GOLD,
     ["NO DEAL. EU AND OTHERS REJECT THE FINAL TEXT,",
      "WHICH DROPS FOSSIL FUELS ENTIRELY. KURUM:",
      "'NO AGREEMENT, THESE DECISIONS HAVE NOT",
      "BEEN ADOPTED.' LONGEST COP EVER; FIRST WITH",
      "NO OVERARCHING DEAL SINCE COPENHAGEN 2009."]),
    ("CIKANDE, INDONESIA", ("FIRE SEARCH", "3 DEAD,", "36 MISSING"), RED,
     ["SAT FIRE AT MILKITA CANDY",
      "FACTORY, CIKANDE. SUN SEARCH:",
      "3 DEAD, 36 MISSING, 15 SURVIVED,",
      "4 HURT. CAUSE NOT ANNOUNCED."]),
    ("DYMER, UKRAINE", ("DRONE HITS", "FLAT, 14 MISSING"), BLUE,
     ["SUN MORNING: RUSSIAN DRONE",
      "HITS A 5-STOREY BLOCK NEAR",
      "KYIV. PART COLLAPSES, 3 DEAD",
      "FOUND, 9 EVACUATED, 14 MISSING",
      "AS RESCUERS DIG THROUGH RUBBLE."]),
]

# (headline, detail, region colour, date note or "")
STORIES = [
    ("MEXICO: 'EL CHAPO ISIDRO' HELD", "CARTEL BOSS HELD IN SINALOA; 11 KILLED IN RAID", RED, "SAT RAID"),
    ("POLAND: 3 RUSSIAN KH-101 MISSILES", "PROSECUTORS CONFIRM SUN; RUTTE: NATO WILL DEFEND", BLUE, "FRI 20 NOV"),
    ("BAHRAIN: IRAN STRIKE WOUNDS 2", "SAT HIT ON CIVILIAN SITE; IRGC CLAIMS US PATRIOTS", PURPLE, "SUN UPDATE"),
    ("GAZA: AID TRUCK STRIKE KILLS 3", "WITNESSES: VEHICLE CARRIED FOOD IN GAZA CITY", PURPLE, "22 NOV"),
    ("KRYVYI RIH: 2 KILLED, 83 HURT", "RUSSIAN MISSILE HITS ZELENSKYY'S HOMETOWN", BLUE, "SAT 21 NOV"),
    ("KALININGRAD HIT BY DRONES", "UKRAINIAN DRONES STRIKE THE ENCLAVE, FIRST TIME", BLUE, "REPORTED"),
    ("DENMARK EXPELS RUSSIAN ATTACHE", "7 DAYS TO LEAVE OVER ALLEGED ASSASSINATION PLOT", BLUE, "22 NOV"),
    ("EU-INDONESIA CEPA SIGNED", "10 YEARS OF TALKS; TARIFFS CUT ON 98.5% OF GOODS", GREEN, "SAT 21 NOV"),
    ("EU BUDGET: EUR 204B CUTS PLAN", "COSTA PROPOSES 3% BIG-TECH TAX; EUR 100B FOR KYIV", BLUE, "22 NOV"),
    ("FRANCE PROTESTS, 6TH WEEKEND", "TENS OF THOUSANDS MARCH OVER COSTS, POLICE POWERS", BLUE, "22 NOV"),
    ("BELGIUM ATC STRIKE WARNING", "FLIGHT CANCELLATIONS FEARED AS CONTROLLERS STRIKE", BLUE, "22 NOV"),
    ("TRAFALGAR TREE FELLED", "LONDON'S CHRISTMAS TREE CUT DOWN IN NORWAY", BLUE, "22 NOV"),
    ("NORWAY VOIDS 3 OIL LICENCES", "SUPREME COURT RULES CLIMATE-DISPUTED LICENCES INVALID", BLUE, "22 NOV"),
    ("SOUTH AFRICA: ANC FALLS TO 31%", "WORST LOCAL RESULT SINCE 1994; DA LEADS IN CITIES", ORANGE, "RESULTS 21 NOV"),
    ("NIGERIA BOAT: 24 DEAD", "FUNERAL BOAT CAPSIZES IN BAYELSA; SEARCH GOES ON", ORANGE, "FRI 20 NOV"),
    ("DRC EBOLA: 5,678 DEAD", "11,613 CASES AS OF 17 NOV, WHO REPORTS; STILL SPREADING", ORANGE, "WHO 20 NOV"),
    ("KENYA: EBOLA-FREE COUNTDOWN", "LAST PATIENT DISCHARGED; 42-DAY WATCH BEGINS", ORANGE, "11 NOV"),
    ("HAITI-EL SALVADOR PRISON DEAL", "HAITI TO BUILD 3 PRISONS WITH SALVADORAN HELP", RED, "22 NOV"),
    ("KENYA-SAUDI: 293,600 JOBS", "KENYA SECURES SAUDI JOB OPENINGS FOR ITS WORKERS", ORANGE, "22 NOV"),
    ("GHANA HERITAGE BANKNOTES", "NEW SERIES HONOURS NKRUMAH, KOFI ANNAN, TRADERS", ORANGE, "22 NOV"),
    ("PERU QUAKE M6.7, 1 KILLED", "ANDES QUAKE DISPLACES 853; NO TSUNAMI THREAT", RED, "FRI 21 NOV"),
    ("MALUKU QUAKE M7.2", "DEEP QUAKE OFF SW MALUKU; NO TSUNAMI, NO CASUALTIES", GREEN, "SAT 21 NOV"),
    ("SOUTH KOREA MINISTER RESIGNS", "EDUCATION CHIEF QUITS OVER AI CHEATING SCANDAL", GREEN, "22 NOV"),
    ("CHINA WARNS JAPAN ON TAIWAN", "BEIJING: CORRECT 'ERRONEOUS WORDS' AFTER TAKAICHI", GREEN, "22 NOV"),
    ("HORMUZ SWIM: PUGH CROSSES", "BRITON SWIMS WAR-HIT STRAIT FOR THE ENVIRONMENT", PURPLE, "22 NOV"),
    ("HORMUZ: 2 TANKERS HIT MINES", "TANKERS CATCH FIRE IN THE STRAIT, IRGC REPORTS", PURPLE, "SUN 22 NOV"),
    ("ISRAEL COALITION TALKS", "EISENKOT INVITES NETANYAHU TO FORM NEW GOVERNMENT", PURPLE, "22 NOV"),
    ("TRUMP: CREDIT-CARD CAP 10%", "PRESIDENT VOWS TO WORK WITH DEMOCRATS ON THE CAP", RED, "22 NOV"),
    ("TRUMP ORDERS CONTRACTORS", "FEDERAL CONTRACTORS MUST REPORT CONGRESS CONTACTS", RED, "22 NOV"),
    ("FBI PROBES NCIC HACK", "FBI INVESTIGATES APPARENT HACK OF CRIME DATABASE", RED, "00:10 UTC"),
    ("SEATTLE ICE JET-BRIDGE ARREST", "MASKED AGENTS DETAIN 2 ON ALASKA FLIGHT; PORT FURIOUS", RED, "22 NOV"),
    ("BOLSONARO IN ICU", "EX-PRESIDENT IN INTENSIVE CARE, BOWEL OBSTRUCTION", RED, "22 NOV"),
    ("US STOCKS IN CORRECTION", "AI AND CHIP SELL-OFF PUSHES DOW, S&P INTO CORRECTION", RED, "FRI SELL-OFF"),
    ("AMAZON IN $7.5B AI DEAL", "AMAZON SIGNS $7.5B AI DEAL WITH DECART", RED, "22 NOV"),
    ("ANTHROPIC IPO ROW", "IPO SPARKS WALL ST ROW OVER UNUSUAL DEAL CURBS", RED, "22 NOV"),
    ("GTA VI: $3.79B DAY ONE", "ROCKSTAR OFFICIAL: RECORD LAUNCH, 32.5M PRE-SOLD", TEAL, "20 NOV"),
    ("RIEMANN PROOF CLAIMED", "MATHEMATICIAN CLAIMS PROOF WITH CLAUDE'S HELP - CLAIM", TEAL, "CLAIM ONLY"),
    ("SBF: 82-MIN PRISON INTERVIEW", "EX-FTX CHIEF SPEAKS FROM BROOKLYN PRISON, 14-YEAR-OLD HOST", TEAL, "22 NOV"),
    ("AUKUS: AUSTRALIA REBUKES CBO", "MARLES: 'THEY ARE WRONG' ON SUBMARINE WARNING", TEAL, "22 NOV"),
    ("UN 'KILLER ROBOTS' PLEDGE", "GENEVA TALKS END WITH PLEDGE OF NEW RULES IN 2 YEARS", BLUE, "22 NOV"),
    ("AIR NIUGINI LANDS SAFE", "ENGINE FIRE FORCES EMERGENCY LANDING; ALL 146 SAFE", TEAL, "22 NOV"),
    ("SHENZHEN SUMMIT NUCLEAR PACT", "CHINA-RUSSIA NUCLEAR DECLARATION AT SHENZHEN TALKS", GREEN, "22 NOV"),
    ("VERSTAPPEN WINS LAS VEGAS GP", "3RD VEGAS WIN, 75TH OF CAREER; NORRIS 2ND, PIASTRI 3RD", TEAL, "SAT NIGHT"),
    ("LIVERPOOL 4-0 MAN UTD", "POCHETTINO DEBUT ENDS IN ROUT; YORO OFF AFTER 8 MIN", TEAL, "22 NOV"),
    ("KANSAS CITY WIN NWSL TITLE", "CURRENT TAKE THE NWSL CHAMPIONSHIP", TEAL, "22 NOV"),
    ("WEMBANYAMA 50 PTS, SPURS WIN", "SPURS STAR SCORES 50 IN VICTORY", TEAL, "22 NOV"),
    ("BEPI COLOMBO REACHES MERCURY", "ESA PROBE ENTERS MERCURY ORBIT", TEAL, "22 NOV"),
    ("NASA: TINY ASTEROID MINI-MOON", "SMALL ASTEROID CAPTURED AS EARTH'S TEMPORARY MOON", TEAL, "22 NOV"),
    ("UFO FOOTAGE DECLASSIFIED", "US RELEASES MORE UFO FOOTAGE FILMED IN MIDDLE EAST", RED, "22 NOV"),
    ("EU RWANDA DEPORTATION HUBS", "EU MOVES ON RWANDA HUBS AND A DIGITAL TAX", BLUE, "22 NOV"),
    ("SPARTA II STILL BURNING", "DRONE-HIT CARGO SHIP SMOULDERS; 16 CREW EVACUATED", BLUE, "SUN 22 NOV"),
]

# ------------------------------------------------------------------- map
# Coarse continent outlines in (lon, lat). Recognisable at small size.
CONTINENTS = [
    [(-168, 66), (-150, 70), (-135, 69), (-125, 71), (-110, 68), (-95, 69),
     (-85, 66), (-82, 60), (-77, 62), (-70, 58), (-65, 60), (-60, 55),
     (-55, 52), (-60, 47), (-65, 44), (-70, 42), (-75, 38), (-80, 32),
     (-81, 26), (-85, 29), (-90, 21), (-95, 19), (-97, 16), (-92, 15),
     (-86, 12), (-83, 9), (-79, 9), (-82, 14), (-87, 15), (-90, 14),
     (-94, 17), (-97, 22), (-105, 20), (-110, 24), (-115, 28), (-120, 34),
     (-125, 40), (-125, 48), (-130, 55), (-140, 60), (-155, 58), (-165, 60)],
    [(-80, 9), (-77, 4), (-80, -3), (-81, -6), (-77, -12), (-72, -18),
     (-70, -23), (-70, -30), (-72, -37), (-73, -44), (-74, -50), (-70, -54),
     (-66, -55), (-65, -48), (-62, -40), (-57, -35), (-52, -32), (-48, -28),
     (-41, -23), (-39, -17), (-35, -9), (-35, -6), (-40, -3), (-44, -2),
     (-50, 0), (-53, 4), (-58, 6), (-62, 9), (-68, 11), (-72, 12), (-77, 8)],
    [(-17, 15), (-17, 21), (-15, 27), (-10, 31), (-5, 35), (0, 36),
     (10, 37), (11, 34), (15, 32), (20, 32), (25, 32), (30, 31), (32, 31),
     (35, 28), (34, 27), (37, 22), (39, 18), (40, 15), (43, 11), (48, 11),
     (51, 10), (46, 5), (42, 0), (40, -5), (40, -10), (39, -15), (36, -18),
     (33, -22), (32, -26), (28, -32), (20, -35), (17, -32), (15, -27),
     (12, -18), (13, -12), (12, -6), (9, -1), (9, 4), (-8, 4), (-13, 8),
     (-17, 12)],
    [(-10, 36), (-9, 38), (-9, 43), (-2, 44), (-1, 46), (-4, 48), (-2, 49),
     (0, 50), (2, 51), (5, 53), (8, 55), (8, 57), (10, 59), (5, 60), (5, 62),
     (10, 64), (12, 66), (18, 69), (25, 71), (30, 70), (35, 68), (40, 68),
     (45, 68), (50, 69), (55, 68), (60, 69), (65, 68), (70, 72), (75, 72),
     (80, 73), (90, 75), (100, 76), (110, 74), (120, 73), (130, 72),
     (140, 72), (150, 70), (158, 69), (162, 66), (170, 66), (178, 65),
     (178, 62), (170, 60), (162, 58), (158, 52), (150, 59), (142, 55),
     (140, 50), (135, 45), (130, 42), (127, 40), (122, 38), (120, 32),
     (122, 28), (118, 25), (112, 22), (108, 18), (105, 10), (103, 8),
     (100, 6), (98, 10), (95, 15), (92, 20), (90, 22), (88, 22), (85, 19),
     (82, 16), (80, 13), (77, 8), (75, 12), (72, 20), (68, 23), (66, 25),
     (62, 25), (58, 25), (56, 26), (54, 26), (52, 25), (50, 29), (48, 30),
     (44, 29), (40, 30), (36, 36), (33, 36), (30, 36), (27, 37), (23, 36),
     (20, 40), (18, 40), (15, 44), (12, 44), (8, 44), (3, 42), (0, 40),
     (-2, 37), (-6, 36), (-9, 37)],
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (0, 53), (1, 51)],
    [(130, 31), (132, 33), (135, 34), (137, 35), (139, 37), (141, 39),
     (141, 42), (143, 44), (141, 45), (140, 42), (138, 38), (136, 36),
     (133, 34)],
    [(113, -22), (114, -30), (115, -33), (118, -35), (124, -33), (129, -32),
     (132, -32), (135, -35), (138, -35), (140, -38), (145, -38), (150, -37),
     (153, -32), (153, -27), (150, -22), (146, -19), (142, -15), (142, -11),
     (136, -12), (132, -12), (130, -13), (126, -14), (122, -17), (118, -20)],
    [(167, -45), (170, -42), (173, -40), (175, -38), (177, -38), (174, -41),
     (171, -44)],
    [(95, 5), (98, 3), (100, -2), (103, -3), (106, -6), (110, -7),
     (114, -8), (118, -9), (120, -10), (119, -5), (117, 0), (115, 3),
     (112, 5), (108, 6), (105, 5), (102, 2), (98, 5)],
    [(109, 1), (111, 3), (114, 4), (117, 6), (118, 2), (117, -2),
     (114, -4), (111, -3)],
    [(131, -1), (136, -2), (141, -3), (146, -6), (150, -8), (147, -9),
     (143, -8), (138, -7), (134, -4)],
    [(44, -16), (47, -15), (50, -16), (49, -20), (45, -25), (43, -22),
     (44, -16)],
]

# (lon, lat, lead number, colour) - pins on the map
PINS = [
    (30.7, 36.9, 1, GOLD),    # COP31 Antalya
    (106.3, -6.3, 2, RED),    # Cikande
    (30.3, 50.8, 3, BLUE),    # Dymer
    (-107.4, 25.6, 5, RED),   # Sinaloa
    (22.0, 50.5, 6, BLUE),    # Poland
    (50.6, 26.2, 7, PURPLE),  # Bahrain
    (34.5, 31.5, 8, PURPLE),  # Gaza
    (33.4, 45.5, 9, BLUE),    # Kryvyi Rih
    (19.0, 56.5, 10, BLUE),   # Kaliningrad
    (11.0, 58.0, 11, BLUE),   # Copenhagen
    (6.3, 4.9, 15, ORANGE),   # Bayelsa
    (25.0, 0.0, 16, ORANGE),  # DRC
    (-75.2, -11.5, 21, RED),  # Peru
    (127.0, 37.5, 23, GREEN), # Seoul
]

# (hour UTC, label, above_line?) - timeline strip
TIMELINE = [
    (0.2, "00:10 FBI HACK", True),
    (3.9, "03:56 CIKANDE", False),
    (5.4, "05:26 DRAFT", True),
    (7.0, "DYMER", False),
    (12.0, "SPARTA II", True),
    (16.5, "16:30 LIVERPOOL", False),
    (19.5, "COP31 FALLS", True),
]

# ---------------------------------------------------------------- layout
def f(v):
    return v * S

def header(cv):
    cv.fill_rect(0, 0, W, f(66), (10, 16, 28))
    text_stroke(cv, f(16), f(14), "THE WORLD TODAY", PAPER, scale=3.4, spacing=2.0)
    text_stroke(cv, f(700), f(12), "22 NOVEMBER 2026", GOLD, scale=2.6, spacing=2.0)
    text5(cv, f(700), f(42), "SUNDAY  -  54 STORIES  -  6 CONTINENTS", PAPER2,
          scale=2)
    cv.hline(0, f(66), W, GOLD, f(3))

def lead_cards(cv):
    cards = [(16, 440, 0), (468, 260, 1), (740, 268, 2)]
    y, h = 76, 132
    for x, w, i in cards:
        kicker, head, color, body = LEADS[i]
        cv.fill_rect(f(x), f(y), f(w), f(h), PANEL)
        cv.fill_rect(f(x), f(y), f(w), f(4), color)
        cv.rect(f(x), f(y), f(w), f(h), LINE, 2)
        text5(cv, f(x + 10), f(y + 10), kicker, color, scale=2)
        text_stroke(cv, f(x + 10), f(y + 24), str(i + 1), GOLD, scale=2.0)
        hy = y + 22
        for ln in head:
            text_stroke(cv, f(x + 34), f(hy), ln, PAPER, scale=1.9, spacing=1.5)
            hy += 17
        by = hy + 6
        for ln in body:
            text5(cv, f(x + 10), f(by), ln, PAPER2, scale=2)
            by += 9

def world_map(cv):
    x0, y0, w, h = 16, 216, 992, 136
    cv.fill_rect(f(x0), f(y0), f(w), f(h), MAPSEA)
    cv.rect(f(x0), f(y0), f(w), f(h), LINE, 2)
    text5(cv, f(x0 + 8), f(y0 + 6), "THE WORLD  -  WHERE IT HAPPENED", GOLD, scale=2)

    def proj(lon, lat):
        px = x0 + (lon + 180.0) / 360.0 * w
        py = y0 + 8 + (85.0 - lat) / 145.0 * (h - 14)
        return int(round(f(px))), int(round(f(py)))

    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        cv.fill_poly(pts, MAPLAND)
        cv.poly(pts, MAPLINE, close=True)
    for lon, lat, num, color in PINS:
        px, py = proj(lon, lat)
        cv.disc(px, py, f(6), color)
        num_s = str(num)
        tw = text5_w(num_s, scale=2)
        text5(cv, px - tw // 2, py - f(3), num_s, INK, scale=2)

def timeline(cv):
    y0, h = 360, 40
    x0, x1 = 30, 994
    text5(cv, f(16), f(y0), "UTC TIMELINE", GOLD, scale=2)
    ly = y0 + 22
    cv.hline(f(x0), f(ly), f(x1 - x0), LINE, f(2))
    for hr in (0, 24):
        tx = x0 + (x1 - x0) * hr / 24.0
        cv.fill_rect(f(tx) - 1, f(ly - 3), f(2), f(6), GREY)
        lab = "%02d:00" % hr
        text5(cv, f(tx) - text5_w(lab, scale=2) // 2, f(ly + 6), lab, GREY, scale=2)
    for hr, lab, above in TIMELINE:
        tx = x0 + (x1 - x0) * hr / 24.0
        cv.disc(f(tx), f(ly), f(4), GOLD)
        tw = text5_w(lab, scale=2)
        lx = max(f(16), min(f(tx) - tw // 2, f(1008) - tw))
        ty = f(ly - 10) if above else f(ly + 6)
        text5(cv, lx, ty, lab, PAPER2, scale=2)

def story_grid(cv):
    y0 = 434
    text_stroke(cv, f(16), f(408), "THE DAY IN BRIEF", PAPER, scale=2.0, spacing=1.5)
    key = [("EUROPE", BLUE), ("ASIA", GREEN), ("AFRICA", ORANGE),
           ("AMERICAS", RED), ("MIDEAST", PURPLE), ("SPORT", TEAL)]
    kx = 560
    for name, color in key:
        cv.fill_rect(f(kx), f(412), f(10), f(10), color)
        kx += 12
        kx = text5(cv, f(kx), f(413), name, PAPER2, scale=2)
        kx += 14
    cols = [16, 267, 518, 769]
    col_w = 239
    per_col = 13
    for ci, cx in enumerate(cols):
        cy = y0
        for si in range(per_col):
            idx = ci * per_col + si
            if idx >= len(STORIES):
                break
            headline, detail, color, date = STORIES[idx]
            num = idx + 4  # stories 4..54, leads are 1..3
            full = detail + " - " + date
            h_lines = wrap5(headline, 38)[:2]
            d_lines = wrap5(full, 38)[:max(1, 3 - len(h_lines))]
            # first line: coloured number, then headline
            num_s = "%02d " % num
            nw = text5_w(num_s, scale=2)
            text5(cv, f(cx), f(cy), num_s, color, scale=2)
            text5(cv, f(cx) + nw, f(cy), h_lines[0], PAPER, scale=2)
            cy += 9
            for ln in h_lines[1:]:
                text5(cv, f(cx), f(cy), ln, PAPER, scale=2)
                cy += 9
            for ln in d_lines:
                text5(cv, f(cx), f(cy), ln, GREY, scale=2)
                cy += 9
            cy += 6

def date_check(cv):
    x0, y0, w, h = 16, 884, 992, 78
    cv.fill_rect(f(x0), f(y0), f(w), f(h), (24, 22, 10))
    cv.rect(f(x0), f(y0), f(w), f(h), GOLD, f(3))
    text5(cv, f(x0 + 10), f(y0 + 8), "DATE CHECK  -  ONLY 22 NOVEMBER", GOLD, scale=2)
    lines = [
        "COP31 COLLAPSE * DYMER STRIKE * SPARTA II FIRE * CIKANDE SEARCH *",
        "BAHRAIN UPDATE * FBI NCIC PROBE * DENMARK EXPULSION * FRANCE PROTESTS *",
        "KOREA MINISTER RESIGNS * HORMUZ TANKERS * EU BUDGET PLAN * UFO FILES",
        "21 NOV EVENTS ARE DATED ON THEIR CARDS: PERU, MALUKU, KRYVYI RIH, MEXICO",
        "RAID, EU-INDONESIA DEAL. GTA VI FIGURE IS THE OFFICIAL 20 NOV $3.79B.",
    ]
    ly = y0 + 22
    for ln in lines:
        text5(cv, f(x0 + 10), f(ly), ln, PAPER2, scale=2)
        ly += 9

def footer(cv):
    lines = [
        "SOURCES: REUTERS - AP - AFP - BBC - UN NEWS - EUROPEAN COMMISSION - WHO -",
        "ECDC - FIA - ESPN - NEMA - BMKG - USGS. ALL TIMES UTC UNLESS NOTED.",
        "THE WORLD TODAY - SUNDAY 22 NOVEMBER 2026 - MAKE.FUN NEWS-IMAGE-20261122",
    ]
    ly = 972
    for ln in lines:
        tw = text5_w(ln, scale=2)
        text5(cv, f(512) - tw // 2, f(ly), ln, GREY, scale=2)
        ly += 9

def main():
    cv = Canvas()
    header(cv)
    lead_cards(cv)
    world_map(cv)
    timeline(cv)
    story_grid(cv)
    date_check(cv)
    footer(cv)
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    png = cv.downsample_png()
    with open(os.path.join(out, "entry.png"), "wb") as fh:
        fh.write(png)
    print("wrote %s/entry.png %d bytes" % (out, len(png)))

if __name__ == "__main__":
    main()
