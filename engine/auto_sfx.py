"""Sound effects are always there, on Shorts and long videos: a swipe whoosh on every move into and out of b-roll and
a full-screen graphic, placed by the kit so nobody has to ask. Small cards that pop in beside him stay quiet. Sounds
the plan already has are kept and win; the kit only fills the moves that have none.

Rules: the loudest part of the whoosh lands on the move itself (the middle of the push, or the cut); it starts in the
gap between words when there is one; it never starts while another sound is starting; it sits well under his voice,
whichever swipe file is used.
Off only when he asks: `"sfx_auto": false` in the plan or the style.
"""
import hashlib, json, os, subprocess

CLEAR = 0.4            # no two sounds start closer together than this (less for a whoosh shorter than that)
NUDGE = 0.08           # how far a whoosh may move off its move to miss a word; past that, staying on the move wins
PEAK_DB = -14.0        # where the whoosh's loudest sample sits (his own Shorts: about -14 dBFS, his voice is far above)
MAX_LEAD = 0.25        # the whoosh never starts earlier than this before the move
# his own copy first, then the one the kit ships (the air swipe from his Shorts), then the older soft swipe
SWIPE = ("library/sfx/swipe-whoosh.wav", "assets/sfx/swipe-whoosh.wav", "library/sfx/swipe-soft.wav", "assets/sfx/swipe-soft.wav")


def enabled(edl, st):
    for src in (edl, st):
        if src.get("sfx_auto") is not None:
            return bool(src["sfx_auto"])
    return True


def swipe_file(kit_dir):
    return next((p for p in (os.path.join(kit_dir, rel) for rel in SWIPE) if os.path.isfile(p)), None)


def measure(path, cache_dir=None):
    """{"peak_db": the loudest sample (dBFS), "peak_s": when the sound is loudest (seconds in)}. Cached by content."""
    key = hashlib.sha1(open(path, "rb").read()).hexdigest()[:16]
    cache = os.path.join(cache_dir, key + ".json") if cache_dir else None
    if cache and os.path.exists(cache):
        return json.load(open(cache))
    import numpy as np
    rate = 48000                                                      # full rate: a whoosh is mostly high, airy sound
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.abs(np.frombuffer(raw, dtype=np.int16).astype(float))
    out = {"peak_db": -6.0, "peak_s": 0.1, "dur_s": round(len(x) / rate, 3)}
    w = rate // 100                                                   # 10 ms windows
    if len(x) > 2 * w and x.max() > 0:
        env = np.array([x[i:i + w].mean() for i in range(0, len(x) - w, w)])
        out.update(peak_db=round(float(20 * np.log10(x.max() / 32768.0)), 2), peak_s=round(float(env.argmax() * w / rate), 3))
    if cache:
        os.makedirs(cache_dir, exist_ok=True); json.dump(out, open(cache, "w"))
    return out


def gain_db(peak_db):
    """The gain that puts this file's loudest sample at PEAK_DB. Never turned up."""
    return round(min(0.0, PEAK_DB - peak_db), 2)


def place(hit, words, lead):
    """When the whoosh for a move at `hit` starts: `lead` before it, so its loudest part lands on the move. If that is
    inside a word and the word ends within NUDGE, it waits for the word to end; otherwise it stays with the picture
    (he wants the sound on the swipe he sees)."""
    t = hit - min(lead, MAX_LEAD)
    for w in words:
        if w["s"] < t < w["e"]:
            if w["e"] - t <= NUDGE and w["e"] <= hit + 0.05:
                t = w["e"]
            break
    return max(0.0, t)


def auto_times(hits, words, taken, lead=0.1, dur=None):
    """Start times for the kit's own swipes. `hits`: when each move lands (seconds). `taken`: start times (seconds) of
    sounds the plan already has; a move that already has one is left alone. `dur`: the whoosh's length, so two moves
    close together each get theirs as long as the sounds don't run into each other."""
    clear = CLEAR if dur is None else min(CLEAR, max(0.2, dur))
    used = sorted(taken)
    out = []
    for m in sorted(hits):
        t = place(m, words, lead)
        if any(abs(t - u) < clear or abs(m - u) < clear for u in used):
            continue
        out.append(round(t, 3)); used.append(t)
    return out
