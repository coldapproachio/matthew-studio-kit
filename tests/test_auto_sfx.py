"""2.3.9: sound effects are always there (the kit adds swipes on b-roll and graphic moves), b-roll is the default,
and captions over a full-screen graphic stay readable."""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
import auto_sfx as ax

import swipe as sw

FPS = 30
WORDS = [{"w": "a", "s": 4.6, "e": 5.05}, {"w": "b", "s": 5.33, "e": 5.9}, {"w": "c", "s": 6.0, "e": 7.03},
         {"w": "d", "s": 7.35, "e": 9.9}, {"w": "e", "s": 9.95, "e": 12.0}]
TL = {"width": 1080, "height": 1920,
      "broll": [{"start": 161, "frames": 54}],                                                     # 5.37 s to 7.17 s
      "blocks": [{"start": 215, "frames": 79, "show": "cutaway", "solid": True},                   # 7.17 s to 9.80 s, full screen
                 {"start": 400, "frames": 60, "show": "overlay"}]}                                 # a small card beside him


class AutoSfxTests(unittest.TestCase):
    def test_full_screen_changes_swipe_and_small_cards_do_not(self):
        moves = sw.plan(sw.scenes(TL), FPS, 900)
        self.assertEqual([(m["into"], m["out"]) for m in moves], [("broll0", "base"), ("blk0", "broll0"), ("base", "blk0")])
        self.assertTrue(all(m["frames"] == 4 for m in moves))          # each one a 4-frame push
        self.assertTrue(moves[1]["early"])                              # back to back: the graphic pushes the b-roll out

    def test_a_see_through_graphic_is_not_a_move(self):
        tl = dict(TL, broll=[], blocks=[{"start": 215, "frames": 79, "show": "cutaway", "solid": False}])
        self.assertEqual(sw.scenes(tl), [])

    def test_one_whoosh_per_move_and_plan_sounds_win(self):
        hits = [5.43, 7.1, 9.73]
        self.assertEqual(len(ax.auto_times(hits, WORDS, [], 0.16, 0.27)), 3)
        self.assertEqual(len(ax.auto_times(hits, WORDS, [5.3, 7.0], 0.16, 0.27)), 1)   # only the move the plan left silent

    def test_no_swipe_at_the_very_start_or_end(self):
        tl = dict(TL, broll=[{"start": 0, "frames": 60}], blocks=[])
        self.assertEqual(sw.plan(sw.scenes(tl), FPS, 63), [])

    def test_it_is_on_unless_he_asks_for_none(self):
        self.assertTrue(ax.enabled({}, {}))
        self.assertFalse(ax.enabled({"sfx_auto": False}, {}))
        self.assertFalse(ax.enabled({}, {"sfx_auto": False}))
        self.assertTrue(ax.enabled({"sfx_auto": True}, {"sfx_auto": False}))   # the plan's word wins

    def test_the_kit_ships_his_approved_sounds(self):
        for f in ("swipe-whoosh.wav", "swipe-soft.wav", "ui-pop.wav", "ui-tick.wav"):
            self.assertTrue((ROOT / "assets" / "sfx" / f).is_file(), f)
        self.assertTrue(os.path.basename(ax.swipe_file(str(ROOT))).startswith("swipe-"))

    def test_docs_make_broll_and_sound_the_default(self):
        agents = (ROOT / "AGENTS.md").read_text()
        self.assertIn("B-roll on most videos", agents)
        self.assertIn("Sound effects always", agents)
        self.assertNotIn("B-roll only when he asks", agents)
        self.assertNotIn("B-roll only when he asks", (ROOT / "styles" / "default" / "STYLE.md").read_text())
        self.assertIn("on Shorts and long videos", agents)
        self.assertIn("2.4.0", (ROOT / "CHANGELOG.md").read_text())

    def test_captions_over_a_full_screen_graphic_get_a_halo(self):
        src = (ROOT / "engine" / "render_hf.py").read_text()
        self.assertIn(".ongfx .w", src)
        self.assertIn('b.get("show") == "cutaway"', src)


if __name__ == "__main__":
    unittest.main()
