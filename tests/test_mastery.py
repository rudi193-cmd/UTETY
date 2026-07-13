#!/usr/bin/env python3
"""Tests for utety/core/mastery.py — on-device BKT inference."""
import unittest

from utety.core.mastery import BKTParams, mastered, predict_correct, update


class TestBKTParams(unittest.TestCase):
    def test_identifiability_caps_guess_and_slip(self):
        p = BKTParams(guess=0.9, slip=0.8)
        self.assertLess(p.guess, 0.5)
        self.assertLess(p.slip, 0.5)

    def test_probabilities_clamped(self):
        p = BKTParams(prior=1.7, learn=-0.2)
        self.assertEqual(p.prior, 1.0)
        self.assertEqual(p.learn, 0.0)


class TestInference(unittest.TestCase):
    def setUp(self):
        self.p = BKTParams(prior=0.3, learn=0.15, guess=0.2, slip=0.1)

    def test_correct_raises_mastery(self):
        after = update(self.p.prior, correct=True, params=self.p)
        self.assertGreater(after, self.p.prior)

    def test_incorrect_lowers_or_holds_mastery(self):
        after = update(self.p.prior, correct=False, params=self.p)
        # A wrong answer should not increase mastery.
        self.assertLessEqual(after, self.p.prior + 1e-9)

    def test_streak_of_correct_reaches_mastery_threshold(self):
        pk = self.p.prior
        for _ in range(20):
            pk = update(pk, correct=True, params=self.p)
        self.assertTrue(mastered(pk, threshold=0.95))

    def test_predict_correct_in_unit_interval(self):
        pc = predict_correct(0.5, self.p)
        self.assertGreaterEqual(pc, 0.0)
        self.assertLessEqual(pc, 1.0)

    def test_matches_hand_computed_posterior(self):
        # One correct observation, then learning step. Hand-computed:
        # cond = 0.3*0.9 / (0.3*0.9 + 0.7*0.2) = 0.27/0.41
        # p'   = cond*(1-0) + (1-cond)*0.15
        cond = 0.27 / 0.41
        expect = cond + (1 - cond) * 0.15
        got = update(0.3, correct=True, params=self.p)
        self.assertAlmostEqual(got, expect, places=10)


if __name__ == "__main__":
    unittest.main()
