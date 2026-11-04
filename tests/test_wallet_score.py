"""Offline regression tests for the executable wallet-score documentation.

Run with: python -m unittest discover -s tests -v
Only the gmgn-cli process boundary is stubbed; the actual embedded script runs.
"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1] / "skills/gmgn-wallet-score/SKILL.md"


def run_score(stats, language="en"):
    source = SKILL.read_text(encoding="utf-8").split("python3 << 'PYEOF'\n", 1)[1].split("\nPYEOF", 1)[0]
    values = {"CHAIN": "robinhood", "WALLET_ADDRESS": "fixture-wallet",
              "LANG": language, "LATENCY": "3.0", "SLIPPAGE": "0.05",
              "GAS": "0.2", "SAMPLE": "200"}
    for key, value in values.items():
        source = source.replace("<FILL_IN_" + key + ">", value)
    calls = []

    def cli(args, **kwargs):
        calls.append(args)
        if args[:3] == ["gmgn-cli", "portfolio", "stats"]:
            data = stats
        elif args[:3] == ["gmgn-cli", "portfolio", "activity"]:
            data = {"activities": []}
        else:
            raise AssertionError("Unexpected CLI call: " + repr(args))
        return subprocess.CompletedProcess(args, 0, json.dumps(data), "")

    output = io.StringIO()
    namespace = {}
    with patch("subprocess.run", side_effect=cli), contextlib.redirect_stdout(output):
        exec(compile(source, str(SKILL), "exec"), namespace)
    assert len(calls) == 2
    return namespace, output.getvalue()


def stats_fixture(profit=300, cost=3000):
    return {"buy": 30, "sell": 30, "realized_profit": profit,
            "bought_cost": cost, "realized_profit_pnl": profit / cost if cost else None,
            "pnl_stat": {"token_num": 30, "winrate": 0.6,
                         "avg_holding_period": 86400, "pnl_0x_2x_num": 18,
                         "pnl_nd5_0x_num": 10, "pnl_lt_nd5_num": 2},
            "common": {"created_token_count": 0}}


class WalletScoreTests(unittest.TestCase):
    def test_missing_roi_and_zero_cost_are_unknown_not_a_copy_gain(self):
        stats = stats_fixture(profit=-300, cost=0)
        stats["buy"] = 0
        stats.pop("realized_profit_pnl")
        result, output = run_score(stats)
        self.assertIsNone(result["w"]["roi"])
        self.assertIsNone(result["bt"])
        self.assertIsNone(result["track_disp"])
        self.assertIn("ROI unknown", output)
        self.assertIn("copy estimate not measurable for this window", output)
        self.assertNotIn("Genuine track record and high copy-tradeability", output)

    def test_nonfinite_roi_is_unknown(self):
        for roi in ("nan", "inf", "-inf"):
            with self.subTest(roi=roi):
                stats = stats_fixture()
                stats["realized_profit_pnl"] = roi
                result, output = run_score(stats)
                self.assertIsNone(result["w"]["roi"])
                self.assertIsNone(result["track_disp"])
                self.assertIn("ROI unknown", output)

    def test_nonfinite_cost_cannot_produce_copy_estimate(self):
        for cost in ("nan", "inf", "-inf"):
            with self.subTest(cost=cost):
                stats = stats_fixture()
                stats["bought_cost"] = cost
                result, output = run_score(stats)
                self.assertIsNone(result["bt"])
                self.assertIn("copy estimate not measurable for this window", output)

    def test_unusable_cost_never_uses_reported_roi_as_a_denominator(self):
        for profit in (-300, 300):
            for cost in (None, 0, -1, "bad"):
                with self.subTest(profit=profit, cost=cost):
                    stats = stats_fixture(profit=profit)
                    stats["bought_cost"] = cost
                    result, output = run_score(stats)
                    self.assertIsNone(result["bt"])
                    self.assertIn("no copy-return conclusion", output)

    def test_unknown_roi_variants_do_not_score_roi(self):
        for roi in (None, "", "bad"):
            with self.subTest(roi=roi):
                stats = stats_fixture()
                stats["realized_profit_pnl"] = roi
                result, output = run_score(stats)
                self.assertIsNone(result["track_facs"]["roi"])
                self.assertIsNone(result["track_disp"])
                self.assertIn("ROI unknown", output)
                # An independently available positive cost still supports the estimate.
                self.assertIsNotNone(result["bt"])

    def test_zero_roi_with_positive_cost_keeps_execution_drag(self):
        result, output = run_score(stats_fixture(profit=0))
        self.assertEqual(result["w"]["roi"], 0)
        self.assertIsNotNone(result["track_disp"])
        self.assertEqual(result["bt"]["wallet_pct"], 0)
        self.assertAlmostEqual(result["bt"]["copy_7d"], -346.5)
        self.assertIn("ROI +0.0%", output)

    def test_valid_nonzero_estimates_preserve_existing_formula(self):
        for profit in (-300, 300, 15000, -3000):
            with self.subTest(profit=profit):
                result, output = run_score(stats_fixture(profit=profit))
                wallet_pct = max(-0.9, min(3.0, profit / 3000))
                copy_pct = wallet_pct - 3 * 0.015 * 0.3 - 2 * 0.05 - 0.2 / 100
                self.assertEqual(result["bt"]["copy_7d"], round(profit * copy_pct / wallet_pct, 1))
                self.assertNotIn("not measurable", output)

    def test_documented_aliases_are_still_supported(self):
        stats = stats_fixture()
        stats["total_cost"] = stats.pop("bought_cost")
        stats["pnl"] = stats.pop("realized_profit_pnl")
        result, _ = run_score(stats)
        self.assertEqual(result["w"]["roi"], 0.1)
        self.assertIsNotNone(result["bt"])

    def test_unknown_data_renders_in_chinese_mode_too(self):
        result, output = run_score(stats_fixture(cost=0), language="zh")
        self.assertIsNone(result["bt"])
        self.assertIn("copy estimate not measurable for this window", output)


if __name__ == "__main__":
    unittest.main()
