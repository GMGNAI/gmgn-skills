"""Offline regressions for issue #237; no network or wallet access."""
import importlib.util
import contextlib
import io
import json
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'analysis', ROOT / 'skills/gmgn-wallet-analysis/analyze.py')
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def fixture():
    return {'stats_7d': {
        'buy': 30, 'sell': 30, 'realized_profit': 900,
        'bought_cost': 6000, 'realized_profit_pnl': 0.15,
        'pnl_stat': {'token_num': 30, 'winrate': 0.6,
                     'pnl_lt_nd5_num': 2, 'pnl_0x_2x_num': 18},
        'common': {'created_token_count': 1}}}


def run_score(stats, language='en'):
    skill = ROOT / 'skills/gmgn-wallet-score/SKILL.md'
    source = skill.read_text(encoding='utf-8').split("python3 << 'PYEOF'\n", 1)[1].split('\nPYEOF', 1)[0]
    for key, value in {'CHAIN': 'robinhood', 'WALLET_ADDRESS': 'fixture-wallet',
                       'LANG': language, 'LATENCY': '3', 'SLIPPAGE': '0.05',
                       'GAS': '0.2', 'SAMPLE': '200'}.items():
        source = source.replace('<FILL_IN_' + key + '>', value)
    calls = []

    def cli(args, **kwargs):
        calls.append(args[2])
        if args[2] == 'stats':
            data = stats
        elif args[2] == 'activity':
            data = {'activities': []}
        else:
            raise AssertionError('Unexpected CLI call')
        return subprocess.CompletedProcess(args, 0, json.dumps(data), '')

    output, ns = io.StringIO(), {}
    with patch('subprocess.run', side_effect=cli), contextlib.redirect_stdout(output):
        exec(compile(source, str(skill), 'exec'), ns)
    return ns, output.getvalue(), calls


class TokenCountTest(unittest.TestCase):
    def setUp(self):
        analysis.load_lang('en')

    def test_invalid_counts_stay_unknown_in_both_skills(self):
        for value in (None, '', 'bad', 'nan', 'inf', '-inf', -1, 2.5, True, False):
            with self.subTest(value=value):
                data = fixture()
                data['stats_7d']['pnl_stat']['token_num'] = value
                m = analysis.compute(data, 3, None)
                self.assertFalse(m['token_count_known'])
                self.assertFalse(m['is_dev'])
                self.assertIsNone(m['lt50_share'])
                self.assertIsNone(m['implied_winners'])
                self.assertIsNone(m['unsettled'])
                self.assertFalse(m['pcr_represents_record'])
                self.assertIn('token count unavailable', analysis.report(
                    'FIXTURE', 'sol', m, analysis.gates(m), [], False))
                score, text, calls = run_score(data['stats_7d'])
                self.assertIsNone(score['token_num'])
                self.assertIsNone(score['track_disp'])
                self.assertFalse(score['is_dev_wallet'])
                self.assertEqual(calls, ['stats', 'activity'])
                self.assertNotIn('Tokens traded 0', text)

    def test_known_zero_is_not_unknown_or_a_denominator(self):
        data = fixture()
        data['stats_7d']['pnl_stat']['token_num'] = 0
        m = analysis.compute(data, 3, None)
        self.assertTrue(m['token_count_known'])
        self.assertFalse(m['is_dev'])
        self.assertIsNone(m['lt50_share'])
        text = analysis.report('FIXTURE', 'sol', m, analysis.gates(m), [], False)
        self.assertIn('only 0 tokens', text)
        self.assertNotIn('200.0%', text)
        score, text, _ = run_score(data['stats_7d'])
        self.assertEqual(score['token_num'], 0)
        self.assertIsNone(score['big_loss'])
        self.assertIsNone(score['track_disp'])
        self.assertIn('Tokens traded 0', text)

    def test_valid_numeric_string_retains_ratios(self):
        data = fixture()
        data['stats_7d']['pnl_stat']['token_num'] = '30'
        m = analysis.compute(data, 3, None)
        self.assertTrue(m['token_count_known'])
        self.assertFalse(m['is_dev'])
        self.assertAlmostEqual(m['lt50_share'], 2 / 30)
        score, _, _ = run_score(data['stats_7d'])
        self.assertEqual(score['token_num'], 30)
        self.assertIsNotNone(score['track_disp'])

    def test_inconsistent_loss_count_is_not_over_one_hundred_percent(self):
        data = fixture()
        data['stats_7d']['pnl_stat']['pnl_lt_nd5_num'] = 60
        m = analysis.compute(data, 3, None)
        self.assertIsNone(m['lt50_share'])
        self.assertIsNone(analysis.gates(m)['G4'][0])
        self.assertNotIn('200.0%', analysis.report(
            'FIXTURE', 'sol', m, analysis.gates(m), [], False))
        score, _, _ = run_score(data['stats_7d'])
        self.assertIsNone(score['big_loss'])
        self.assertIsNone(score['track_disp'])

    def test_measured_launcher_veto_is_preserved(self):
        data = fixture()
        data['stats_7d']['common']['created_token_count'] = 16
        m = analysis.compute(data, 3, None)
        self.assertTrue(m['is_dev'])
        self.assertFalse(analysis.gates(m)['G1'][0])
        self.assertIn('launcher', analysis.verdict(m, analysis.gates(m))[1])

    def test_independent_self_launch_veto_survives_unknown_count(self):
        data = fixture()
        del data['stats_7d']['pnl_stat']['token_num']
        m = analysis.compute(data, 3, None)
        m.update(self_lo=0.8, self_hi=0.8, self_own_usd=800,
                 self_own_n=3, self_own_top=['FIXTURE'])
        gates = analysis.gates(m)
        self.assertFalse(gates['G1'][0])
        self.assertIn('most of its profit', analysis.verdict(m, gates)[1])

    def test_unknown_count_renders_in_chinese(self):
        data = fixture()
        del data['stats_7d']['pnl_stat']['token_num']
        analysis.load_lang('zh')
        m = analysis.compute(data, 3, None)
        self.assertIn('token count unavailable', analysis.report(
            'FIXTURE', 'sol', m, analysis.gates(m), [], False))
        score, text, _ = run_score(data['stats_7d'], language='zh')
        self.assertIsNone(score['track_disp'])
        self.assertIn('token count unavailable', text)

    def test_score_missing_count_does_not_scan_or_discount_as_launcher(self):
        stats = fixture()['stats_7d']
        del stats['pnl_stat']['token_num']
        m, text, calls = run_score(stats)
        self.assertFalse(m['is_dev_wallet'])
        self.assertEqual(calls, ['stats', 'activity'])
        self.assertIsNone(m['track_disp'])
        self.assertIsNone(m['big_loss'])
        self.assertIn('token count unavailable', text)
        self.assertNotIn('Tokens traded 0', text)

    def test_missing_count_is_not_a_launcher_or_loss_ratio(self):
        data = fixture()
        del data['stats_7d']['pnl_stat']['token_num']
        m = analysis.compute(data, 3, None)
        self.assertFalse(m['is_dev'])
        self.assertIsNone(m['lt50_share'])
        gates = analysis.gates(m)
        self.assertIsNone(gates['G1'][0])
        report = analysis.report('FIXTURE', 'sol', m, gates, [], False)
        self.assertIn('token count unavailable', report)
        for invented in ('200.0%', 'traded 0', 'only 0 tokens',
                         'of 0 coins', 'launcher trading its own tokens',
                         'a wash-trading flag we cannot check'):
            self.assertNotIn(invented, report)


if __name__ == '__main__':
    unittest.main()
