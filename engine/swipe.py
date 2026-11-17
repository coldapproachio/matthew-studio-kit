"""Full-screen changes swipe in and out, like his own Shorts: b-roll pushes in from the left while what was on screen
slides out to the right, and it leaves the same way. A full-screen graphic slides in over him and off again (the
renderer keeps his picture still under it, because a graphic can be see-through). The kit plans every move here so
nobody has to build it by hand in Studio.

What counts as a full-screen change: every b-roll clip, and a graphic that fills the frame with a solid picture (a
real cutaway). A top-panel graphic changes the frame too, so it gets the sound but no push. Everything he stays visible
behind is not a move at all and comes in quietly: a small card beside him (an overlay, or a boxed block on a long
video), and a full-frame graphic that is see-through (cards floating over his face), unless the plan says
`"swipe": true` on it.

Off only when he asks: `"swipe": false` in the plan or the style (hard cuts, the sound stays), or on one b-roll clip
or block.
"""
import re

PUSH_S = 0.133      # how long the push takes (4 frames at 30 fps), as in his reference
MIN_PUSHES = 3      # a scene shorter than this many pushes is cut in and out instead
FULL_AREA = 0.6     # a boxed block on a long video counts as full screen from this share of the frame
EASE = lambda p: p * p * (3 - 2 * p)   # ease in and out


def enabled(edl, st):
    for src in (edl, st):
        if src.get("swipe") is not None:
            return bool(src["swipe"])
    return True


def push_frames(fps):
    return max(2, int(round(PUSH_S * fps)))


def fills_frame(block, W, H):
    show = str(block.get("show") or "").lower()
    if show == "cutaway": return True
    if show in ("overlay", "panel"): return False
    box = block.get("box")
    return not box or box[2] * box[3] >= FULL_AREA * W * H


_CLEAR = re.compile(r"^\s*(transparent|none|inherit|initial|unset)\b|(rgba|hsla)\([^)]*,\s*0(\.0+)?\s*\)", re.I)
_BG = re.compile(r"(?<![-\w])background(?:-color)?\s*:\s*([^;}]+)", re.I)


def solid_cover(html_text, w, h):
    """True when a graphic paints the whole frame (a background on its page or root, or on a layer that covers it), so
    nothing of him shows through. Not sure means False: it is then treated like today, a quiet cut."""
    def solid(decl):
        m = _BG.search(decl)
        return bool(m) and not _CLEAR.search(m.group(1))
    def covers(decl):
        return bool(re.search(r"inset\s*:\s*0(?![.\d])", decl)
                    or (re.search(rf"(?<![-\w])width\s*:\s*(100%|100vw|{w}px)", decl) and re.search(rf"(?<![-\w])height\s*:\s*(100%|100vh|{h}px)", decl)))
    root = re.search(r'<[^>]*\bid="([^"]+)"[^>]*data-composition-id|<[^>]*data-composition-id[^>]*\bid="([^"]+)"', html_text)
    rid = next((g for g in (root.groups() if root else ()) if g), "root")
    page = re.compile(rf"(html|body|:root|#{re.escape(rid)}|\[data-composition-id[^\]]*\])")
    css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", html_text, flags=re.S | re.I))
    for names, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if solid(decl) and (covers(decl) or any(page.fullmatch(x.strip()) for x in names.split(","))):
            return True
    return any(solid(st) and covers(st) for st in re.findall(r'style="([^"]*)"', html_text))


def scenes(tl, lens=None, pushes=True):
    """Everything that changes the whole picture, in time order: {id, start, end, push}. `lens`: how long each block
    really shows (frames). `push`: it slides in and out (full-frame b-roll and full-screen graphics)."""
    W, H = tl["width"], tl["height"]
    out = []
    for i, b in enumerate(tl.get("broll") or []):
        out.append({"id": f"broll{i}", "start": b["start"], "end": b["start"] + b["frames"],
                    "push": pushes and b.get("layout", "full") == "full" and b.get("swipe", True)})
    for i, b in enumerate(tl.get("blocks") or []):
        n = lens[i] if lens else b["frames"]
        if fills_frame(b, W, H):
            if b.get("swipe") is True or (b.get("solid", True) and b.get("swipe") is not False):
                out.append({"id": f"blk{i}", "start": b["start"], "end": b["start"] + n, "push": pushes})
            elif b.get("solid", True):   # he asked for no swipe on this one: a cut, the sound stays
                out.append({"id": f"blk{i}", "start": b["start"], "end": b["start"] + n, "push": False})
        elif str(b.get("show") or "").lower() == "panel":
            out.append({"id": f"blk{i}", "start": b["start"], "end": b["start"] + n, "push": False})
    return sorted(out, key=lambda s: (s["start"], s["end"]))


def plan(sc, fps, total):
    """The moves, in time order. Each: {at, frames, hit, into, out}.
    frames > 0: a push over [at, at + frames): `into` slides in from the left as `out` slides off to the right ("base" is
    his camera). frames == 0: a plain cut at `at` (a panel, a clip too short to push). `hit`: the frame the swipe sound
    is aimed at (the middle of a push, or the cut). A scene that follows another without a gap pushes the first one out:
    its clip starts `frames` early (the renderer does that), so his face never flashes between the two."""
    n = push_frames(fps)
    long_enough = lambda s: s["push"] and s["end"] - s["start"] >= MIN_PUSHES * n
    near = lambda a, b: abs(a - b) <= 1
    moves = []
    for k, s in enumerate(sc):
        prev = next((p for p in sc[:k] if near(p["end"], s["start"])), None)
        nxt = next((q for q in sc[k + 1:] if near(q["start"], s["end"])), None)
        if s["start"] >= 2 * n:                              # a video that opens on it just opens on it
            if long_enough(s) and prev is None:
                moves.append({"at": s["start"], "frames": n, "into": s["id"], "out": "base"})
            elif long_enough(s) and long_enough(prev) and s["start"] - n > prev["start"] + n:
                moves.append({"at": s["start"] - n, "frames": n, "into": s["id"], "out": prev["id"], "early": True})
            else:
                moves.append({"at": s["start"], "frames": 0, "into": s["id"], "out": prev["id"] if prev else "base"})
        if nxt is None and s["end"] <= total - 2 * n:        # the next scene's own move covers a back-to-back change
            if long_enough(s):
                moves.append({"at": s["end"] - n, "frames": n, "into": "base", "out": s["id"]})
            else:
                moves.append({"at": s["end"], "frames": 0, "into": "base", "out": s["id"]})
    for m in moves:
        m["hit"] = m["at"] + m["frames"] / 2
    return sorted(moves, key=lambda m: m["at"])


def steps(move, W):
    """Per-frame x positions for a push: [(frame, x of the incoming picture, x of the outgoing one)]. The first frame
    already shows movement and the frame after the last is fully in, so no frame is wasted."""
    n = move["frames"]
    out = []
    for k in range(n):
        p = EASE((k + 1) / (n + 1))
        out.append((move["at"] + k, round(-W * (1 - p), 2), round(W * p, 2)))
    return out
