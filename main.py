#!/usr/bin/env python3
"""The World Today - 22 November 2026. One dense 1024x1024 news image.

v2: 42 stories (13 featured with drawn scene panels + 29 in brief),
day-in-numbers strip, region bar, certainty tags, explicit press time.

v2: 42 stories (13 featured with drawn scene panels + 29 in brief),
day-in-numbers strip, region bar, certainty tags, explicit press time.

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
    '9': [[(3, 0), (9, 0), (11, 2), (11, 6), (9, 8), (3, 8), (1, 6),
           (1, 2), (3, 0)],
          [(11, 8), (11, 13), (9, 15), (3, 15), (1, 13)]],
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
# v2 format (competitor study, Nov 21 final + Nov 22 dev top 5):
# fewer, bigger stories — 13 featured + 29 in brief = 42 total, 7 regions.
# Winners carry 31-43 stories with big featured cards, a day-in-numbers
# strip, a region bar, certainty tags, and an explicit press time.
# All figures verified against Reuters / AP / AFP / BBC / UN News / WHO /
# EU Commission on Monday 23 Nov 2026. COP31: collapsed Sun 22 Nov, no
# deal adopted. Cikande: 22 Nov figures 3 dead / 36 missing (Mon update
# 24 killed came later and is NOT the 22 Nov figure). GTA VI: $1.84bn was
# the Sensor Tower morning estimate of 19 Nov; Rockstar/Take-Two's
# official figure, 20 Nov, is $3.79bn day-one retail, 32.5m pre-sold.

# (kicker, headline lines, colour, body lines, scene key)
PANELS = [
    ("COP31 - ANTALYA", ("COP31", "COLLAPSES"), GOLD,
     ["NO DEAL. EU AND OTHERS REJECT THE FINAL TEXT,",
      "WHICH DROPS FOSSIL FUELS ENTIRELY. KURUM:",
      "'NO AGREEMENT, THESE DECISIONS HAVE NOT",
      "BEEN ADOPTED.' LONGEST COP EVER; FIRST WITH",
      "NO OVERARCHING DEAL SINCE COPENHAGEN 2009."], "cop31"),
    ("CIKANDE, INDONESIA", ("FIRE SEARCH", "3 DEAD,", "36 MISSING"), RED,
     ["SAT FIRE AT MILKITA CANDY",
      "FACTORY, CIKANDE. SUN SEARCH:",
      "3 DEAD, 36 MISSING, 15 SURVIVED,",
      "4 HURT. CAUSE NOT ANNOUNCED."], "cikande"),
    ("DYMER, UKRAINE", ("DRONE HITS", "FLAT, 14 MISSING"), BLUE,
     ["SUN MORNING: RUSSIAN DRONE",
      "HITS A 5-STOREY BLOCK NEAR",
      "KYIV. PART COLLAPSES, 3 DEAD",
      "FOUND, 9 EVACUATED, 14 MISSING",
      "AS RESCUERS DIG THROUGH RUBBLE."], "dymer"),
]

# (headline, detail, colour, certainty tag, date note) — featured 4..13
FEATURED = [
    ("MEXICO: 'EL CHAPO ISIDRO' HELD", "CARTEL BOSS HELD IN SINALOA; 11 KILLED IN RAID", RED, "CONFIRMED", "SAT RAID"),
    ("POLAND: 3 RUSSIAN KH-101 MISSILES", "PROSECUTORS CONFIRM; RUTTE VOWS DEFENCE", BLUE, "CONFIRMED", "FRI 20 NOV"),
    ("BAHRAIN: IRAN STRIKE WOUNDS 2", "SAT HIT ON CIVILIAN SITE; IRGC CLAIM", PURPLE, "REPORTED", "SUN UPDATE"),
    ("GAZA: AID TRUCK STRIKE KILLS 3", "WITNESSES: VEHICLE CARRIED FOOD IN GAZA CITY", PURPLE, "REPORTED", "22 NOV"),
    ("KRYVYI RIH: 2 KILLED, 83 HURT", "RUSSIAN MISSILE HITS HOMETOWN", BLUE, "CONFIRMED", "SAT 21 NOV"),
    ("EU-INDONESIA CEPA SIGNED", "10 YEARS OF TALKS; TARIFFS CUT 98.5%", GREEN, "OFFICIAL", "SAT 21 NOV"),
    ("SOUTH AFRICA: ANC FALLS TO 31%", "WORST LOCAL RESULT SINCE 1994", ORANGE, "OFFICIAL", "RESULTS 21 NOV"),
    ("NIGERIA BOAT: 24 DEAD", "FUNERAL BOAT CAPSIZES IN BAYELSA", ORANGE, "CONFIRMED", "FRI 20 NOV"),
    ("DRC EBOLA: 5,678 DEAD", "11,613 CASES AS OF 17 NOV, WHO REPORTS", ORANGE, "OFFICIAL", "WHO 20 NOV"),
    ("GTA VI: $3.79B DAY ONE", "RECORD LAUNCH, 32.5M PRE-SOLD", TEAL, "OFFICIAL", "20 NOV"),
]

# (headline, detail, colour, certainty tag, date note) — the rest 14..42
LIST = [
    ("KALININGRAD HIT BY DRONES", "UKRAINIAN DRONES STRIKE THE ENCLAVE", BLUE, "REPORTED", "22 NOV"),
    ("DENMARK EXPELS RUSSIAN ATTACHE", "7 DAYS TO LEAVE OVER ASSASSINATION PLOT", BLUE, "CONFIRMED", "22 NOV"),
    ("EU BUDGET: EUR 204B CUTS PLAN", "COSTA PROPOSES 3% BIG-TECH TAX", BLUE, "REPORTED", "22 NOV"),
    ("FRANCE PROTESTS, 6TH WEEKEND", "TENS OF THOUSANDS MARCH OVER COSTS", BLUE, "CONFIRMED", "22 NOV"),
    ("BELGIUM ATC STRIKE WARNING", "FLIGHT CANCELLATIONS FEARED", BLUE, "REPORTED", "22 NOV"),
    ("NORWAY VOIDS 3 OIL LICENCES", "COURT VOIDS CLIMATE-DISPUTED LICENCES", BLUE, "OFFICIAL", "22 NOV"),
    ("KENYA: EBOLA-FREE COUNTDOWN", "LAST PATIENT DISCHARGED; 42-DAY WATCH", ORANGE, "OFFICIAL", "11 NOV"),
    ("PERU QUAKE M6.7, 1 KILLED", "ANDES QUAKE DISPLACES 853; NO TSUNAMI", RED, "OFFICIAL", "FRI 21 NOV"),
    ("MALUKU QUAKE M7.2", "DEEP QUAKE OFF MALUKU; NO CASUALTIES", GREEN, "OFFICIAL", "SAT 21 NOV"),
    ("SOUTH KOREA MINISTER RESIGNS", "EDUCATION CHIEF QUITS OVER AI CHEATING", GREEN, "CONFIRMED", "22 NOV"),
    ("CHINA WARNS JAPAN ON TAIWAN", "BEIJING: CORRECT 'ERRONEOUS WORDS'", GREEN, "CONFIRMED", "22 NOV"),
    ("HORMUZ: 2 TANKERS HIT MINES", "TANKERS CATCH FIRE IN THE STRAIT", PURPLE, "REPORTED", "SUN 22 NOV"),
    ("ISRAEL COALITION TALKS", "EISENKOT INVITES NETANYAHU TO LEAD TALKS", PURPLE, "REPORTED", "22 NOV"),
    ("TRUMP: CREDIT-CARD CAP 10%", "PRESIDENT VOWS TO WORK WITH DEMOCRATS", RED, "CONFIRMED", "22 NOV"),
    ("TRUMP ORDERS CONTRACTORS", "CONTRACTORS MUST REPORT CONGRESS CONTACTS", RED, "CONFIRMED", "22 NOV"),
    ("FBI PROBES NCIC HACK", "APPARENT HACK OF CRIME DATABASE PROBED", RED, "REPORTED", "00:10 UTC"),
    ("SEATTLE ICE JET-BRIDGE ARREST", "MASKED AGENTS DETAIN 2 ON ALASKA FLIGHT", RED, "REPORTED", "22 NOV"),
    ("BOLSONARO IN ICU", "EX-PRESIDENT IN INTENSIVE CARE", RED, "CONFIRMED", "22 NOV"),
    ("US STOCKS IN CORRECTION", "AI AND CHIP SELL-OFF HITS DOW, S&P", RED, "REPORTED", "FRI SELL-OFF"),
    ("AMAZON IN $7.5B AI DEAL", "AMAZON SIGNS $7.5B AI DEAL WITH DECART", RED, "REPORTED", "22 NOV"),
    ("ANTHROPIC IPO ROW", "IPO SPARKS WALL ST ROW OVER DEAL CURBS", RED, "REPORTED", "22 NOV"),
    ("AUKUS: AUSTRALIA REBUKES CBO", "MARLES: 'THEY ARE WRONG' ON SUBS WARNING", TEAL, "CONFIRMED", "22 NOV"),
    ("UN 'KILLER ROBOTS' PLEDGE", "GENEVA TALKS END WITH PLEDGE OF NEW RULES", BLUE, "REPORTED", "22 NOV"),
    ("AIR NIUGINI LANDS SAFE", "ENGINE FIRE FORCES EMERGENCY LANDING", TEAL, "CONFIRMED", "22 NOV"),
    ("VERSTAPPEN WINS LAS VEGAS GP", "3RD VEGAS WIN, 75TH OF CAREER", TEAL, "OFFICIAL", "SAT NIGHT"),
    ("LIVERPOOL 4-0 MAN UTD", "POCHETTINO DEBUT ENDS IN ROUT; YORO OFF", TEAL, "CONFIRMED", "22 NOV"),
    ("BEPI COLOMBO REACHES MERCURY", "ESA PROBE ENTERS MERCURY ORBIT", TEAL, "OFFICIAL", "22 NOV"),
    ("EU RWANDA DEPORTATION HUBS", "EU MOVES ON RWANDA HUBS AND A DIGITAL TAX", BLUE, "REPORTED", "22 NOV"),
    ("SPARTA II STILL BURNING", "DRONE-HIT SHIP SMOULDERS, 16 EVACUATED", BLUE, "CONFIRMED", "SUN 22 NOV"),
]

# day-in-numbers strip: (big, label)
NUMBERS = [
    ("42", "STORIES"),
    ("7", "REGIONS"),
    ("3", "DEAD - CIKANDE"),
    ("14", "MISSING - DYMER"),
    ("83", "HURT - KRYVYI RIH"),
    ("$3.79B", "GTA VI DAY ONE"),
]

# region bar: (name, colour, count) — sums to 42
REGIONS = [
    ("EUROPE", BLUE, 11),
    ("AMERICAS", RED, 10),
    ("WORLD", GREY, 6),
    ("ASIA", GREEN, 5),
    ("MIDEAST", PURPLE, 4),
    ("AFRICA", ORANGE, 4),
    ("OCEANIA", TEAL, 2),
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
    (-107.4, 25.6, 4, RED),   # Sinaloa
    (22.0, 50.5, 5, BLUE),    # Poland
    (50.6, 26.2, 6, PURPLE),  # Bahrain
    (34.5, 31.5, 7, PURPLE),  # Gaza
    (33.4, 45.5, 8, BLUE),    # Kryvyi Rih
    (19.0, 56.5, 9, BLUE),    # Kaliningrad
    (11.0, 58.0, 10, BLUE),   # Copenhagen
    (6.3, 4.9, 11, ORANGE),   # Bayelsa
    (25.0, 0.0, 12, ORANGE),  # DRC
    (56.5, 26.5, 13, PURPLE), # Hormuz
]

# ---------------------------------------------------------------- layout
def f(v):
    return v * S

def header(cv):
    cv.fill_rect(0, 0, W, f(58), (10, 16, 28))
    text_stroke(cv, f(16), f(12), "THE WORLD TODAY", PAPER, scale=3.2, spacing=2.0)
    text_stroke(cv, f(648), f(10), "22 NOVEMBER 2026", GOLD, scale=2.6, spacing=2.0)
    text5(cv, f(648), f(40), "SUNDAY  -  42 STORIES  -  7 REGIONS", PAPER2,
          scale=2)
    cv.hline(0, f(58), W, GOLD, f(3))

def numbers_strip(cv):
    y0, h = 58, 38
    cv.fill_rect(0, f(y0), W, f(h), PANEL)
    cw = 992 / len(NUMBERS)
    for i, (big, lab) in enumerate(NUMBERS):
        x = 16 + i * cw
        bw = text_stroke_w(big, scale=1.6, spacing=1.5) / S
        text_stroke(cv, f(x + (cw - bw) / 2), f(y0 + 5), big, GOLD,
                    scale=1.6, spacing=1.5)
        lw = text5_w(lab, scale=2) / S
        text5(cv, f(x + (cw - lw) / 2), f(y0 + 26), lab, PAPER2, scale=2)
        if i:
            cv.fill_rect(f(x), f(y0 + 6), f(2), f(h - 12), LINE)

# ------------------------------------------------------- drawn scenes
# Simple geometric illustrations for the three lead panels.
def scene_cop31(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (24, 44, 66))
    cv.disc(x + w - int(w * 0.16), y + int(h * 0.26), int(h * 0.16), GOLD)
    for i, c in enumerate((GOLD, RED, BLUE, GREEN, PURPLE)):
        px = x + int(w * (0.10 + i * 0.16))
        cv.fill_rect(px, y + int(h * 0.30), 4, int(h * 0.55), PAPER2)
        cv.fill_rect(px + 4, y + int(h * 0.30), int(w * 0.10),
                     int(h * 0.18), c)
    cv.fill_rect(x + int(w * 0.36), y + int(h * 0.72), int(w * 0.28),
                 int(h * 0.28), PAPER)
    cv.fill_rect(x + int(w * 0.30), y + int(h * 0.86), int(w * 0.40),
                 int(h * 0.14), GOLD)
    for i in range(9):
        cv.disc(x + int(w * (0.08 + i * 0.10)), y + int(h * 0.94),
                3, GREY)

def scene_cikande(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (52, 18, 12))
    cv.fill_rect(x, y + int(h * 0.55), w, int(h * 0.45), (28, 14, 10))
    cv.fill_rect(x + int(w * 0.08), y + int(h * 0.62), int(w * 0.30),
                 int(h * 0.38), INK)
    cv.fill_rect(x + int(w * 0.42), y + int(h * 0.55), int(w * 0.34),
                 int(h * 0.45), INK)
    cv.fill_rect(x + int(w * 0.80), y + int(h * 0.42), int(w * 0.05),
                 int(h * 0.58), INK)
    cv.fill_rect(x + int(w * 0.88), y + int(h * 0.50), int(w * 0.05),
                 int(h * 0.50), INK)
    for fx, fh in ((0.22, 0.42), (0.55, 0.55), (0.72, 0.38)):
        bx = x + int(w * fx)
        by = y + int(h * 0.62)
        cv.fill_poly([(bx - int(w * 0.05), by), (bx, by - int(h * fh)),
                      (bx + int(w * 0.05), by)], ORANGE)
        cv.fill_poly([(bx - int(w * 0.025), by),
                      (bx, by - int(h * fh * 0.6)),
                      (bx + int(w * 0.025), by)], GOLD)
    for sx, sy, sr in ((0.82, 0.30, 9), (0.88, 0.20, 12), (0.93, 0.32, 8)):
        cv.disc(x + int(w * sx), y + int(h * sy), sr, GREY)

def scene_dymer(cv, x, y, w, h):
    cv.fill_rect(x, y, w, h, (14, 20, 40))
    for sx, sy in ((0.10, 0.15), (0.30, 0.08), (0.55, 0.18), (0.80, 0.10),
                   (0.92, 0.22), (0.45, 0.06)):
        cv.disc(x + int(w * sx), y + int(h * sy), 3, PAPER2)
    bx, bw = x + int(w * 0.14), int(w * 0.44)
    cv.fill_rect(bx, y + int(h * 0.30), bw, int(h * 0.70), (32, 42, 66))
    for r in range(4):
        for c in range(5):
            wx = bx + int(w * (0.03 + c * 0.085))
            wy = y + int(h * (0.36 + r * 0.15))
            cv.fill_rect(wx, wy, int(w * 0.05), int(h * 0.08),
                         GOLD if (r + c) % 3 else GREY)
    cx = bx + bw
    cv.fill_poly([(cx, y + int(h * 0.30)), (cx + int(w * 0.16),
                  y + int(h * 0.52)),
                  (cx + int(w * 0.10), y + int(h * 0.72)),
                  (cx + int(w * 0.22), y + int(h * 0.86)),
                  (cx + int(w * 0.30), y + h)], (20, 26, 42))
    cv.fill_rect(cx + int(w * 0.05), y + int(h * 0.88), int(w * 0.08),
                 int(h * 0.06), GREY)
    cv.fill_rect(cx + int(w * 0.16), y + int(h * 0.80), int(w * 0.07),
                 int(h * 0.06), GREY)
    dx, dy = x + int(w * 0.78), y + int(h * 0.16)
    cv.line(dx - 14, dy, dx + 14, dy, PAPER2, 3)
    cv.line(dx, dy - 14, dx, dy + 14, PAPER2, 3)
    cv.disc(dx, dy, 5, RED)
    cv.line(dx, dy + 10, bx + bw // 2, y + int(h * 0.34), GOLD, 2)

SCENES = {"cop31": scene_cop31, "cikande": scene_cikande,
          "dymer": scene_dymer}

def panel_cards(cv):
    cards = [(16, 324, 0), (350, 324, 1), (684, 324, 2)]
    y, h = 104, 168
    for x, w, i in cards:
        kicker, head, color, body, scene = PANELS[i]
        cv.fill_rect(f(x), f(y), f(w), f(h), PANEL)
        cv.rect(f(x), f(y), f(w), f(h), LINE, 2)
        SCENES[scene](cv, f(x) + 2, f(y) + 2, f(w) - 4, f(62))
        cv.fill_rect(f(x), f(y + 64), f(w), f(3), color)
        text5(cv, f(x + 10), f(y + 72), kicker, color, scale=2)
        text_stroke(cv, f(x + 10), f(y + 86), str(i + 1), GOLD, scale=2.0)
        hy = y + 84
        for ln in head:
            text_stroke(cv, f(x + 34), f(hy), ln, PAPER, scale=1.9,
                        spacing=1.5)
            hy += 17
        by = hy + 6
        for ln in body:
            text5(cv, f(x + 10), f(by), ln, PAPER2, scale=2)
            by += 9

def featured_grid(cv):
    text_stroke(cv, f(16), f(280), "TOP STORIES", PAPER, scale=1.8,
                spacing=1.5)
    text5(cv, f(16), f(298), "10 MORE, TAGGED BY CERTAINTY", GREY, scale=2)
    for row, y in enumerate((316, 394)):
        for col in range(5):
            idx = row * 5 + col
            headline, detail, color, tag, date = FEATURED[idx]
            x = 16 + col * 198
            w = 190
            cv.fill_rect(f(x), f(y), f(w), f(70), PANEL2)
            cv.fill_rect(f(x), f(y), f(w), f(3), color)
            cv.rect(f(x), f(y), f(w), f(70), LINE, 2)
            text5(cv, f(x + 8), f(y + 8), "%02d" % (idx + 4), color, scale=2)
            tw = text5_w(tag, scale=2)
            text5(cv, f(x + w - 8) - tw, f(y + 8), tag, GOLD, scale=2)
            hl = wrap5(headline, 19)[:2]
            hy = y + 20
            for ln in hl:
                text_stroke(cv, f(x + 8), f(hy), ln, PAPER, scale=1.3,
                            spacing=1.2)
                hy += 13
            dl = wrap5(detail + " - " + date, 28)[:2]
            dy = hy + 2
            for ln in dl:
                text5(cv, f(x + 8), f(dy), ln, PAPER2, scale=2)
                dy += 9

def world_map(cv):
    x0, y0, w, h = 16, 472, 992, 140
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

def region_bar(cv):
    y0, h = 620, 22
    cv.fill_rect(f(16), f(y0), f(992), f(h), PANEL)
    x = 16
    total = sum(c for _, _, c in REGIONS)
    for name, color, count in REGIONS:
        cv.fill_rect(f(x), f(y0 + 4), f(10), f(14), color)
        lab = "%s %d" % (name, count)
        text5(cv, f(x + 14), f(y0 + 6), lab, PAPER2, scale=2)
        x += 14 + text5_w(lab, scale=2) / S + 18

def story_list(cv):
    text_stroke(cv, f(16), f(650), "THE REST OF THE DAY", PAPER,
                scale=1.8, spacing=1.5)
    text5(cv, f(16), f(668), "29 MORE STORIES, ONE LINE EACH", GREY, scale=2)
    cols = [16, 350, 684]
    per_col = 10
    for ci, cx in enumerate(cols):
        cy = 686
        for si in range(per_col):
            idx = ci * per_col + si
            if idx >= len(LIST):
                break
            headline, detail, color, tag, date = LIST[idx]
            num = idx + 14  # stories 14..42
            num_s = "%02d " % num
            nw = text5_w(num_s, scale=2)
            text5(cv, f(cx), f(cy), num_s, color, scale=2)
            hl = wrap5(headline, 46)[:1]
            text5(cv, f(cx) + nw, f(cy), hl[0], PAPER, scale=2)
            cy += 9
            dl = wrap5(detail + " - " + date, 52)[:1]
            text5(cv, f(cx), f(cy), dl[0], GREY, scale=2)
            cy += 9
            tw = text5_w(tag, scale=2)
            text5(cv, f(cx + 324) - tw, f(cy - 18), tag, GOLD, scale=2)
            cy += 8

def date_check(cv):
    x0, y0, w, h = 16, 916, 992, 60
    cv.fill_rect(f(x0), f(y0), f(w), f(h), (24, 22, 10))
    cv.rect(f(x0), f(y0), f(w), f(h), GOLD, f(3))
    text5(cv, f(x0 + 10), f(y0 + 7),
          "DATE CHECK  -  ONLY 22 NOVEMBER  -  PRESS 14:00 UTC MON 23 NOV",
          GOLD, scale=2)
    lines = [
        "1 COP31 COLLAPSE * 2 CIKANDE SEARCH * 3 DYMER STRIKE * 6 BAHRAIN UPDATE *",
        "13 GTA VI IS THE OFFICIAL 20 NOV $3.79B * 29 FBI NCIC PROBE * 42 SPARTA II FIRE",
        "21 NOV EVENTS ARE DATED ON THEIR CARDS: PERU, MALUKU, KRYVYI RIH, MEXICO",
        "RAID, EU-INDONESIA DEAL, ANC RESULT. CIKANDE MON UPDATE (24 KILLED) NOT USED.",
    ]
    ly = y0 + 20
    for ln in lines:
        text5(cv, f(x0 + 10), f(ly), ln, PAPER2, scale=2)
        ly += 9

def footer(cv):
    lines = [
        "SOURCES: REUTERS - AP - AFP - BBC - UN NEWS - EUROPEAN COMMISSION - WHO -",
        "ECDC - FIA - ESPN - NEMA - BMKG - USGS. ALL TIMES UTC UNLESS NOTED.",
        "THE WORLD TODAY - SUNDAY 22 NOVEMBER 2026 - 42 STORIES - MAKE.FUN NEWS-IMAGE-20261122",
    ]
    ly = 984
    for ln in lines:
        tw = text5_w(ln, scale=2)
        text5(cv, f(512) - tw // 2, f(ly), ln, GREY, scale=2)
        ly += 9

def main():
    cv = Canvas()
    header(cv)
    numbers_strip(cv)
    panel_cards(cv)
    featured_grid(cv)
    world_map(cv)
    region_bar(cv)
    story_list(cv)
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
