---
name: gmgn-kline-pattern
description: Price-action pattern reading — classifies a token's candles into a named pattern (uptrend channel, breakdown, distribution at highs, basing, wide chop, consolidation) and scores it 0-100 from EMA structure, 20-bar least-squares slope, ATR volatility, drawdown from the range high, volume ratio and volume/price divergence. Every point added or deducted states its reason; no LLM scores anything. Use when the user asks about K 线, K线形态, 走势, 趋势, 形态, price action, chart pattern, whether a chart looks strong or weak, is it breaking down, is it consolidating, or wants a technical read of a token's chart.
argument-hint: "--chain <sol|bsc|base|eth> --address <token_address> [--resolution 15m] [--lang zh|en]"
metadata:
  cliHelp: "gmgn-cli market kline --help"
---

**BEFORE RUNNING ANY COMMAND: Run `gmgn-cli config --check`. If exit code is 0, proceed normally. If exit code is 1, run `gmgn-cli config` and show output, then apply the key with `gmgn-cli config --apply <KEY>`. If unknown option, tell user to run `npm install -g gmgn-cli`.**

**IMPORTANT: Always use `gmgn-cli` via the script below. Do NOT use curl, WebFetch, or visit gmgn.ai.**

## Sub-commands

The skill wraps one read-only CLI call and adds the pattern classification on top.

| Purpose | CLI command used |
|---------|------------------|
| Fetch candles | `gmgn-cli market kline --chain <chain> --address <address> --resolution <res> --raw` |

`gmgn-market` returns the raw candles; this skill answers **what pattern that is**. Use both
together only if the user wants the underlying data as well.

## Supported Chains

`sol` / `bsc` / `base` / `eth` — whatever `gmgn-cli market kline` accepts. Address shape is
validated before the call: EVM chains need `0x` + 40 hex, Solana needs base58 of length 32-44.
An unrecognised chain name falls back to the EVM rule and refuses rather than accepting both.

## Prerequisites

- `gmgn-cli` installed once: `npm install -g gmgn-cli`
- API key configured: `gmgn-cli config`
- Python 3.9+ — the script uses only the standard library

The script never reads `GMGN_API_KEY` or `GMGN_PRIVATE_KEY`. Authentication, rate limiting and
output sanitization are all handled by the CLI.

## Parameters

```bash
python3 ~/.claude/skills/gmgn-kline-pattern/pattern.py <ADDRESS> <CHAIN> [RESOLUTION] [LANG]
```

| Position | Required | Description |
|----------|----------|-------------|
| `ADDRESS` | Yes | Token contract address |
| `CHAIN` | Yes | `sol` for base58 addresses; `bsc` for EVM `0x...` unless the user names another chain |
| `RESOLUTION` | No | `1s 1m 5m 15m 30m 1h 4h 12h 1d` — default `15m` |
| `LANG` | No | `zh` if the user wrote Chinese, `en` if English — default `zh` |

## Usage Examples

```bash
# Default 15m read
python3 ~/.claude/skills/gmgn-kline-pattern/pattern.py 0xfa8f...7777 bsc

# 1h candles, English output
python3 ~/.claude/skills/gmgn-kline-pattern/pattern.py So1111...1112 sol 1h en
```

Paste the complete stdout verbatim into your reply — every line, nothing omitted or
summarized. Do not add commentary before or after the output block.

## Scenario → what you get

| The user asks | This skill returns |
|---------------|--------------------|
| 「这个币的走势怎么样」 / "how does the chart look" | A named pattern + a 0-100 score + the six measurements behind it |
| 「现在是什么形态」 / "is it breaking down" | The pattern name and why that classification won |
| 「能追吗」 / "is it overbought" | Consecutive-bar and volume-ratio context — the score never answers "should I buy" |

**It does not answer:** is the contract safe, who holds it, is anyone talking about it.

Use a different skill when the user wants **raw candle data** (`gmgn-market`), an **overall
verdict** (`gmgn-ca-verdict`, which already contains this skill's logic as one component), or
**social buzz** (`gmgn-x-narrative`).

## Scoring

Starts at 50 and moves only on evidence.

| Adjustment | Condition | Δ |
|------------|-----------|---|
| EMA structure | EMA9 above EMA21 / below | +12 / −12 |
| 20-bar slope | > +15% / > +2% / < −15% / < −2% | +15 / +6 / −15 / −6 |
| Volume spike | latest bar > 3× average, closing green / red | +8 / −10 |
| Volume drought | latest bar < 30% of average | −5 |
| Drawdown from range high | > 60% / > 30% / < 5% | −15 / −6 / +8 |
| Volume-price divergence | new price high on volume < 70% of the prior window | −10 |

Volatility (ATR), consecutive green/red bars and the EMA cross are reported as context and do
**not** move the score — they change how a position should be sized, not whether the pattern
is strong.

## Pattern Classification

Evaluated in order; the first match wins.

| Pattern | Condition |
|---------|-----------|
| Vertical run-up | slope > 25% and drawdown < 12% |
| Uptrend channel | slope > 8% and drawdown < 25% |
| Breakdown | drawdown > 55% and slope < −10% |
| Distribution at highs | drawdown > 35% and abs(slope) < 8% |
| Slow bleed | slope < −20% |
| Basing at lows | abs(slope) < 5%, ATR < 5%, up-from-low < 20% |
| Wide chop | abs(slope) < 8% and ATR > 8% |
| Bullish / Bearish consolidation | everything else, by EMA direction |

Slope is a least-squares fit over the last 20 closes divided by the window mean, so it reads as
"this stretch moved N% overall", not as a raw price gradient.

## Notes

- All CLI calls use `--raw` for single-line JSON output.
- The pattern is a description of what already happened. It does not predict price and is not
  investment advice — say so if the user reads it as a signal.
- Fewer than 8 usable candles → the script says so and returns a neutral 50 rather than
  inventing a pattern out of noise.
- The official `time` field is in milliseconds and `volume` is USD turnover (`amount` is the
  token count); the script handles both.
- These are price candles. Market-cap candles are not exposed by the CLI, so a market-cap read
  is not available here.
- Read-only: this skill runs only `market kline`. No signing, no private key, no trade commands.
