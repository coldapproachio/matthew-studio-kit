"""One theme per video. A theme is one set of colours (page, type, one accent and a second colour) that every graphic in
that video uses: HyperFrames library pieces, saved graphics and anything drawn for it. So a video never looks like
three different designs pasted together, and the theme changes from video to video.

Which theme a video gets: the plan's "theme" (set at draft, his to change: "make this one the green theme"), else the
theme pinned in his preferences ("theme": one name, he always wants it), else none (an older plan keeps its look).
Draft picks the next theme in turn from his list (preferences "themes", else every theme in themes/), so two videos
in a row never share one.

How it reaches a graphic: HyperFrames library pieces read shared colour names (--fg, --bg, --surface, --brand,
--accent, --accent-2, --muted, --border). The kit sets those as the page's defaults, so a piece that has its own real
colours (a ChatGPT window, an iMessage thread) keeps them. Annotation families that carry their own colour names
(the hand-drawn hw- pieces, mk-, yt-) are set outright. A piece's colour-type variables default to the accent.
"""
import glob, json, os

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = (os.path.join(KIT, "my-styles", "themes"), os.path.join(KIT, "themes"))   # his own first, then the kit's
STATE = os.path.join(KIT, ".cache", "theme-turn.json")
ROLES = ("bg", "surface", "fg", "muted", "border", "accent", "accent2", "over", "ink")

# shared names library pieces expect from the page -> theme role (a piece's own value wins)
SHARED = {"--bg": "bg", "--surface": "surface", "--fg": "fg", "--muted": "muted", "--border": "border",
          "--brand": "accent", "--accent": "accent", "--accent-2": "accent2"}
# annotation families with their own names -> theme role (set outright; they are drawings, not real app screens)
FAMILY = {"--hw-ink": "over", "--hw-ink-dark": "ink", "--hw-accent": "accent", "--hw-accent-warm": "accent",
          "--hw-mark-color": "accent", "--hw-arrow-color": "accent", "--hw-co-accent": "accent", "--ca-ink": "accent",
          "--mk-accent": "accent", "--mk-accent-dark": "accent", "--mk-ink": "ink", "--mk-ink-dark": "over",
          "--yt-prism-r": "accent", "--yt-prism-b": "accent2", "--yt-cyan": "accent2"}


def names():
    seen = {}
    for d in DIRS:
        for p in sorted(glob.glob(os.path.join(d, "*.json"))):
            n = os.path.basename(p)[:-5]
            if n not in seen:
                try: seen[n] = float(json.load(open(p)).get("turn", 99))
                except (OSError, ValueError, TypeError): seen[n] = 99.0
    return sorted(seen, key=lambda n: (seen[n], n))   # the order they are taken in (a theme's "turn"), his red first


def load(name):
    """The theme's colours, or None when there is no such theme."""
    for d in DIRS:
        p = os.path.join(d, f"{name}.json")
        if os.path.isfile(p):
            t = json.load(open(p))
            return dict(t, name=name) if all(k in t for k in ROLES) else None
    return None


def for_video(edl, prefs):
    """The theme this video uses, or None (an older plan with no theme keeps its look)."""
    name = edl.get("theme") or (prefs or {}).get("theme")
    return load(name) if name else None


def next_in_turn(prefs=None):
    """The theme the next new video gets: his pinned theme if he has one, else the next in his list, in turn."""
    prefs = prefs or {}
    if prefs.get("theme") and load(prefs["theme"]):
        return prefs["theme"]
    order = [n for n in (prefs.get("themes") or names()) if load(n)]
    if not order:
        return None
    try: last = json.load(open(STATE)).get("last")
    except (OSError, ValueError): last = None
    pick = order[(order.index(last) + 1) % len(order)] if last in order else order[0]
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"last": pick}, open(STATE, "w"))
    return pick


def css(t):
    """The theme as a stylesheet for one graphic: shared names as page defaults, family names set outright."""
    shared = "".join(f"{k}:{t[r]};" for k, r in SHARED.items())
    family = "".join(f"{k}:{t[r]} !important;" for k, r in FAMILY.items())
    return f"html{{{shared}}}\n:root,[data-composition-id]{{{family}}}"


def colour_vars(declared, given, t):
    """Values for a piece's own colour-type variables the plan left alone: the accent (a background-ish one: the page)."""
    out = {}
    for v in declared or []:
        vid = str(v.get("id") or v.get("name") or "")
        if v.get("type") == "color" and vid and vid not in (given or {}):
            low = vid.lower()
            out[vid] = t["bg"] if ("bg" in low or "background" in low) else t["fg"] if ("ink" in low or "text" in low) else t["accent"]
    return out
