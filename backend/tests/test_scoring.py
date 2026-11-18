"""Offline tests for the baseball scoring state machine."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring import new_game, apply, current_batters

class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.g = new_game("league-1", "home-1", "away-1")
        self.g.update({"gameId": "game-1", "PK": "LEAGUE#league-1", "SK": "GAME#game-1", "createdAt": "test"})

    def test_start_and_runs(self):
        g = apply(self.g, "start")
        g = apply(g, "run")
        self.assertEqual(g["runs"]["away"], [1])
        self.assertEqual(g["runs"]["home"], [0])

    def test_three_outs_switch_sides(self):
        g = apply(self.g, "start")
        for _ in range(3):
            g = apply(g, "out")
        self.assertEqual((g["inning"], g["half"], g["outs"]), (1, "bottom", 0))
        for _ in range(3):
            g = apply(g, "out")
        self.assertEqual((g["inning"], g["half"], g["outs"]), (2, "top", 0))
        self.assertEqual(g["runs"]["away"], [0, 0])

    def test_batting_order_and_on_deck(self):
        g = apply(self.g, "setBattingOrder", {"side": "away", "playerIds": ["p1", "p2", "p3"]})
        self.assertEqual(current_batters(g), {"current": "p1", "onDeck": "p2"})
        g = apply(apply(g, "start"), "nextBatter")
        self.assertEqual(current_batters(g), {"current": "p2", "onDeck": "p3"})

    def test_undo(self):
        g = apply(apply(self.g, "start"), "run")
        g = apply(g, "undo")
        self.assertEqual(g["runs"]["away"], [0])
        self.assertEqual(g["status"], "live")
        self.assertEqual(g["revision"], 3)

    def test_reset_preserves_keys(self):
        g = apply(apply(self.g, "start"), "run")
        g = apply(g, "reset")
        self.assertEqual(g["PK"], self.g["PK"])
        self.assertEqual(g["SK"], self.g["SK"])
        self.assertEqual(g["runs"]["away"], [0])
        self.assertEqual(g["status"], "scheduled")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            new_game("league-1", "same", "same")
        with self.assertRaises(ValueError):
            apply(self.g, "run")
        with self.assertRaises(ValueError):
            apply(self.g, "undo")
        with self.assertRaises(ValueError):
            apply(self.g, "setBattingOrder", {"side": "away", "playerIds": ["p1", "p1"]})

if __name__ == "__main__":
    unittest.main()
