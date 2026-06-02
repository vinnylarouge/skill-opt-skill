#!/usr/bin/env python3
"""Build docs/one-man-show.gif — a reproducible render of the one-man-show explainer.

Same loop graph as docs/one-man-show.html (identical coordinates + palette), rendered as an
autoplaying GIF for inline display on GitHub. The story: a "factory line" where SkillOpt's four
roles are all staffed at once (a team, in *space*), then the flip to "one-man-with-hats" where a
single agent walks the same loop one node at a time (a skill, in *time*), then back.

Stdlib + Pillow only.  Usage:  python3 docs/build_one_man_show.py
"""
from PIL import Image, ImageDraw, ImageFont
import math, os

# ---- palette (matches one-man-show.html) -------------------------------------
PAPER  = (250, 249, 246)
INK    = (17, 17, 17)
SOFT   = (90, 90, 85)
BLUE   = (0, 80, 255)      # structure / staffed / a team in space
ORANGE = (243, 128, 32)    # the active hat / the agent moving in time
HAIR   = (210, 209, 206)
ACTIVE_FILL = (255, 244, 236)

# ---- canvas ------------------------------------------------------------------
W, H   = 560, 472          # logical units
DY     = 44                # graph sits below the title band
S      = 2                 # supersample factor while drawing
FINAL  = 1.35              # downscale target (final width ~= 756px)

MONO = "/System/Library/Fonts/Menlo.ttc"
def font(sz, bold=False):
    return ImageFont.truetype(MONO, int(sz * S), index=1 if bold else 0)

F_TITLE = font(15, bold=True)
F_NODE  = font(11, bold=True)
F_SUB   = font(8.5)
F_EDGE  = font(8.5)
F_CAP   = font(10)
F_HAT   = font(8.5, bold=True)
F_HATSUB= font(7)

def t(v):           # scale a logical coord to render space
    return v * S
def ty(v):          # graph y -> render y (with title band offset)
    return (v + DY) * S

# ---- graph definition (coords identical to the SVG) --------------------------
# rect nodes: (x, y, w, h, [lines], owner_hat)
RECTS = {
    "setup":   (235, 16, 90, 34,  ["setup"],                  "optimizer"),
    "rollout": (52, 86, 138, 46,  ["rollout", "frozen sub-agent"], "target"),
    "score":   (370, 86, 138, 46, ["score", "judge"],         "gate"),
    "reflect": (222, 152, 116, 38,["reflect"],                "optimizer"),
    "edit":    (230, 205, 100, 35,["edit"],                   "optimizer"),
    "ship":    (396, 266, 134, 35,["v+1  accept"],            None),
    "memory":  (24, 200, 96, 40,  ["memory", "rejected-edits"], "memory"),
}
GATE_C = (280, 283); GATE_HW, GATE_HH = 56, 27
GATE_PTS = [(280, 256), (336, 283), (280, 310), (224, 283)]
GATE_OWNER = "gate"

# straight edges: (id, p0, p1)
STRAIGHT = [
    ("e-su-ro",  (256, 50), (152, 86)),
    ("e-su-sc",  (304, 50), (408, 86)),
    ("e-ro-re",  (150, 132),(252, 153)),
    ("e-sc-re",  (410, 132),(308, 153)),
    ("e-re-ed",  (280, 190),(280, 205)),
    ("e-ed-ga",  (280, 240),(280, 255)),
    ("e-accept", (336, 283),(396, 283)),
]
# cubic bezier edges: (id, p0, c1, c2, p3, faint)
CURVES = [
    ("e-reject", (224, 283), (168, 289), (122, 262), (112, 240), False),
    ("e-retry",  (72, 200),  (72, 166),  (150, 150), (222, 166), False),
    ("e-loop",   (464, 266), (470, 150), (360, 30),  (327, 29),  True),
]
EDGE_LABELS = [
    ("fan-out ||", 280, 70, False),
    ("accept",     368, 276, False),
    ("reject",     158, 251, False),
    ("retry",      150, 138, False),
    ("next iter",  430, 120, True),
]

HATS = [  # (role, title, sub)
    ("target",    "TARGET",    "frozen"),
    ("optimizer", "OPTIMIZER", "reflect+edit"),
    ("gate",      "GATE",      "held-out"),
    ("memory",    "MEMORY",    "rejected-edits"),
]

# which hat owns each phase + the agent's walk
OWNER = {"setup": "optimizer", "rollout": "target", "score": "gate",
         "reflect": "optimizer", "edit": "optimizer", "gate": "gate",
         "memory": "memory", "ship": None}
PATH = ["setup", "rollout", "score", "reflect", "edit", "gate", "memory",
        "reflect", "edit", "gate", "ship"]
def leaving_edge(cur, nxt):
    if cur == "gate" and nxt == "memory": return "e-reject"
    if cur == "gate" and nxt == "ship":   return "e-accept"
    if cur == "memory" and nxt == "reflect": return "e-retry"
    if cur == "ship": return "e-loop"
    return None

# ---- drawing helpers ---------------------------------------------------------
def bezier(p0, c1, c2, p3, n=40):
    pts = []
    for k in range(n + 1):
        u = k / n; v = 1 - u
        x = v*v*v*p0[0] + 3*v*v*u*c1[0] + 3*v*u*u*c2[0] + u*u*u*p3[0]
        y = v*v*v*p0[1] + 3*v*v*u*c1[1] + 3*v*u*u*c2[1] + u*u*u*p3[1]
        pts.append((x, y))
    return pts

def arrowhead(d, tip, frm, color, size=7):
    ang = math.atan2(tip[1]-frm[1], tip[0]-frm[0])
    sx, sy = size*S, size*S*0.62
    bx, by = t(tip[0]) - sx*math.cos(ang), ty(tip[1]) - sx*math.sin(ang)
    left  = (bx - sy*math.sin(ang), by + sy*math.cos(ang))
    right = (bx + sy*math.sin(ang), by - sy*math.cos(ang))
    d.polygon([(t(tip[0]), ty(tip[1])), left, right], fill=color)

def draw_edge_straight(d, p0, p1, color, width, pulse=False):
    d.line([(t(p0[0]), ty(p0[1])), (t(p1[0]), ty(p1[1]))], fill=color, width=int(width*S))
    arrowhead(d, p1, p0, color)

def draw_edge_curve(d, pts, color, width, faint=False):
    if faint:  # dashed
        for k in range(0, len(pts)-1, 2):
            a, b = pts[k], pts[k+1]
            d.line([(t(a[0]), ty(a[1])), (t(b[0]), ty(b[1]))], fill=color, width=int(width*S))
    else:
        d.line([(t(x), ty(y)) for x, y in pts], fill=color, width=int(width*S), joint="curve")
    arrowhead(d, pts[-1], pts[-2], color)

def draw_text_center(d, s, x, y, fnt, color):
    d.text((t(x), ty(y)), s, font=fnt, fill=color, anchor="mm")

def rrect(d, box, radius, outline, width, fill):
    x0, y0, x1, y1 = box
    d.rounded_rectangle([t(x0), ty(y0), t(x1), ty(y1)], radius=radius*S,
                        outline=outline, width=int(width*S), fill=fill)

# ---- frame renderer ----------------------------------------------------------
def render(mode, active=None):
    """mode='factory' lights the whole team; mode='solo' walks one node (active)."""
    img = Image.new("RGB", (W*S, H*S), PAPER)
    d = ImageDraw.Draw(img)

    # title band
    d.text((W/2*S, 22*S), "skill-opt   orchestration  <->  skill", font=F_TITLE, fill=INK, anchor="mm")

    # graph frame
    d.rectangle([t(8), ty(8), t(W-8), ty(322)], outline=HAIR, width=int(1.4*S))

    # ---- edges ----
    for eid, p0, c1, c2, p3, faint in CURVES:
        pulse = (mode == "solo" and eid == active_edge)
        col = ORANGE if pulse else (HAIR if faint else INK)
        pts = bezier(p0, c1, c2, p3)
        draw_edge_curve(d, pts, col, 2.4 if pulse else (1.4), faint=faint and not pulse)
    for eid, p0, p1 in STRAIGHT:
        pulse = (mode == "solo" and eid == active_edge)
        col = ORANGE if pulse else INK
        # base edges are semi-transparent ink; emulate with soft gray when not pulsing
        if not pulse: col = (120, 120, 118)
        draw_edge_straight(d, p0, p1, col, 2.4 if pulse else 1.4, pulse)

    # edge labels
    for s, x, y, faint in EDGE_LABELS:
        draw_text_center(d, s, x, y, F_EDGE, HAIR if faint else SOFT)

    # ---- nodes ----
    def node_style(name):
        if mode == "solo":
            if name == active: return (ORANGE, 2.6, ACTIVE_FILL)
            return (INK, 1.6, PAPER)
        else:  # factory: team staffed
            if name == "ship": return (INK, 1.6, PAPER)
            return (BLUE, 2.2, PAPER)

    for name, (x, y, w, h, lines, _owner) in RECTS.items():
        oc, ow, fill = node_style(name)
        rrect(d, (x, y, x+w, y+h), 3, oc, ow, fill)
        if len(lines) == 1:
            draw_text_center(d, lines[0], x+w/2, y+h/2, F_NODE, INK)
        else:
            draw_text_center(d, lines[0], x+w/2, y+h/2 - 8, F_NODE, INK)
            draw_text_center(d, lines[1], x+w/2, y+h/2 + 9, F_SUB, SOFT)

    # gate diamond
    oc, ow, fill = node_style("gate")
    d.polygon([(t(px), ty(py)) for px, py in GATE_PTS], outline=oc, width=int(ow*S), fill=fill)
    draw_text_center(d, "gate?", GATE_C[0], GATE_C[1], F_NODE, INK)

    # ---- caption ----
    if mode == "factory":
        cap = "factory line  -  Target . Optimizer . Gate . Memory staffed at once: a team, in space."
        ccol = BLUE
    else:
        role = OWNER.get(active)
        cap = "one-man-with-hats  -  one agent wears the %s hat, then swaps: a skill, in time." % (
            (role or "-").upper())
        ccol = ORANGE
    d.text((W/2*S, ty(338)), cap, font=F_CAP, fill=ccol, anchor="mm")

    # ---- hat rail ----
    n = len(HATS); gap = 8; chip_w = (W - 16 - gap*(n-1)) / n; chip_h = 30; y0 = 382
    for k, (role, title, sub) in enumerate(HATS):
        x0 = 8 + k*(chip_w + gap)
        if mode == "factory":
            oc, tc = BLUE, BLUE
        elif active and OWNER.get(active) == role:
            oc, tc = ORANGE, ORANGE
        else:
            oc, tc = HAIR, SOFT
        d.rounded_rectangle([t(x0), ty(y0), t(x0+chip_w), ty(y0+chip_h)], radius=3*S,
                            outline=oc, width=int(1.6*S), fill=PAPER)
        draw_text_center(d, title, x0+chip_w/2, y0+11, F_HAT, tc)
        draw_text_center(d, sub,   x0+chip_w/2, y0+22, F_HATSUB, SOFT)

    # downscale for crisp antialiased output
    fw, fh = int(W*FINAL), int(H*FINAL)
    return img.resize((fw, fh), Image.LANCZOS)

# ---- build the frame sequence ------------------------------------------------
active_edge = None  # module-level, set per solo step

def build():
    global active_edge
    frames, durations = [], []

    # open on the factory line
    active_edge = None
    frames.append(render("factory")); durations.append(1700)

    # walk the loop as one actor
    step_ms = {"gate": 1000, "memory": 950, "ship": 1350}
    for idx, cur in enumerate(PATH):
        nxt = PATH[(idx+1) % len(PATH)]
        active_edge = leaving_edge(cur, nxt)
        frames.append(render("solo", active=cur))
        durations.append(step_ms.get(cur, 760))

    # settle back to the factory line (closes the loop)
    active_edge = None
    frames.append(render("factory")); durations.append(1700)

    out = os.path.join(os.path.dirname(__file__), "one-man-show.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:],
                   duration=durations, loop=0, optimize=True, disposal=2)
    kb = os.path.getsize(out) / 1024
    print(f"wrote {out}  ({len(frames)} frames, {kb:.0f} KB)")

if __name__ == "__main__":
    build()
