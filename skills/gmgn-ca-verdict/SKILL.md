---
name: gmgn-ca-verdict
description: Contract due-diligence score — combines contract safety (honeypot, tax, open source, ownership renounce, LP burn/lock, liquidity, dev history), holder structure (top-10 concentration, dev holdings, bundled launch, sniper supply, insider wallets, bot share) and price action into one 0-100 composite where every deduction states its reason and no LLM scores anything. Missing data is never counted as good news. Use when the user pastes a contract address and asks 这个币怎么样, 安全吗, 能不能买, 尽调, 扫一下, is this a rug, is this safe, check this token, audit this contract, or wants an overall verdict on a token.
argument-hint: "--chain <sol|bsc|base|eth> --address <token_address> [--lang zh|en]"
metadata:
  cliHelp: "gmgn-cli token info --help && gmgn-cli token security --help"
---

**BEFORE RUNNING ANY COMMAND: Run `gmgn-cli config --check`. If exit code is 0, proceed normally. If exit code is 1, run `gmgn-cli config` and show output, then apply the key with `gmgn-cli config --apply <KEY>`. If unknown option, tell user to run `npm install -g gmgn-cli`.**

**IMPORTANT: Always use `gmgn-cli` via the script below. Do NOT use curl, WebFetch, or visit gmgn.ai.**

## Sub-commands

Three read-only CLI calls, then one composite score.

| Purpose | CLI command used |
|---------|------------------|
| Token basics, dev, pool, holder stats | `gmgn-cli token info --chain <chain> --address <address> --raw` |
| Honeypot, tax, open source, renounce, LP lock | `gmgn-cli token security --chain <chain> --address <address> --raw` |
| Candles for the price-action component | `gmgn-cli market kline --chain <chain> --address <address> --resolution 15m --raw` |

Only the first is required. If either of the other two fails, that component abstains and the
report says so.

## Supported Chains

`sol` / `bsc` / `base` / `eth` — whatever the CLI accepts. Address shape is validated before
the call: EVM needs `0x` + 40 hex, Solana needs base58 32-44. An unrecognised chain name falls
back to the EVM rule and refuses.

## Prerequisites

- `gmgn-cli` installed once: `npm install -g gmgn-cli`
- API key configured: `gmgn-cli config`
- Python 3.9+ — standard library only

The script never reads `GMGN_API_KEY` or `GMGN_PRIVATE_KEY`.

## Parameters

```bash
python3 ~/.claude/skills/gmgn-ca-verdict/verdict.py <ADDRESS> <CHAIN> [LANG]
```

| Position | Required | Description |
|----------|----------|-------------|
| `ADDRESS` | Yes | Token contract address |
| `CHAIN` | Yes | `sol` for base58; `bsc` for EVM `0x...` unless the user names another chain |
| `LANG` | No | `zh` or `en` — default `zh` |

## Usage Examples

```bash
python3 ~/.claude/skills/gmgn-ca-verdict/verdict.py 0xfa8f...7777 bsc
python3 ~/.claude/skills/gmgn-ca-verdict/verdict.py So1111...1112 sol en
```

Paste the complete stdout verbatim — every line, every section. Do **not** summarize away the
"not available" list; it is what tells the user which checks the score does not cover.

## Scenario → what you get

| The user asks | This skill returns |
|---------------|--------------------|
| 「这个币怎么样」 /「能不能买」 / "is this safe" | A 0-100 composite + a verdict band + every deduction with its reason |
| 「帮我扫一下这个 CA」 / "audit this contract" | Contract safety, holder structure and price action as three separate sub-scores |
| 「是不是貔貅」 / "is this a rug" | An explicit honeypot determination — or an explicit statement that the check was unavailable |

**It does not answer:** who is talking about it on X, or what the raw candles look like.

This is the right default for an unqualified 「看看这个币」. When the user then drills into one
dimension, hand off: chart only → `gmgn-kline-pattern`; deep chip structure (related wallets,
per-wallet cost basis) → `gmgn-holder-analysis`; narrative → `gmgn-x-narrative`.

## The rule that matters most

**Missing data is never good news.** On-chain data has gaps. The naive implementation reads an
absent field as `0`, so a check that never ran renders as "dev holds 0%" and "snipers cleared
0.00%" — inventing positive signals. That is worse than saying "unavailable": it makes an
unexamined token look clean. Measured: an unchecked token could score 100.

Three mechanisms enforce this:

1. Every positive signal is gated on the field actually being present.
2. A component whose checks all failed reports `known = 0`, **abstains from the composite**, and
   renders as "no data" instead of a number. Without this, empty input scored 89 — because
   "nothing deducted" is numerically identical to "nothing wrong".
3. If the honeypot check or open-source status is unavailable, the composite is **capped at 59**
   and the verdict names the missing check.

Never present a capped score as a passing grade.

## Scoring

Weights: contract `.34`, holder structure `.22`, price action `.15`. Only components that
actually resolved contribute; weights renormalize over those present, so a missing component
neither helps nor hurts.

| Condition | Result |
|-----------|--------|
| Honeypot confirmed | Contract score 0, composite capped at 8 |
| Honeypot or open-source status unavailable | Composite capped at 59 |
| No component resolved any check | Composite 0, verdict "cannot score" |

Bands: ≥75 worth a close look · ≥60 a small position is defensible · ≥45 watch only · ≥30 risky
· below that, avoid.

## Honeypot false positives on tokenized equities

Tokenized-stock / RWA tokens carry compliance transfer rules, so the honeypot simulator's sell
attempt fails and the token gets flagged. Measured on BSC:

| Token | `is_honeypot` | 24h sells | 24h sell volume | Holders |
|-------|---------------|-----------|-----------------|---------|
| SPYB (SPY) | `true` | 15,660 | $4.49M | 96,829 |
| QQQB (Invesqo QQQ) | `true` | 128,200 | $34.18M | 148,747 |

A token you cannot sell cannot settle 128,200 sell transactions. Both also report
`privileges: []`, `flags: []` and zero tax — a real honeypot needs a privileged mechanism to
block selling.

**The flag is downgraded to unknown, not cleared.** The trading data proves the token can be
sold; it does not prove the contract has no transfer restriction. The "key check unavailable →
cap at 59" path then applies, so the worst case is a genuine honeypot scoring 59 instead of 8,
rather than 90. The contradiction requires all of: ≥500 sells in 24h, ≥$100K sell volume,
sell/buy volume ratio between 0.3 and 3.0, no privileged functions, and no tax.

## Field Notes

CLI output does not use the same field names or shapes as GMGN's internal endpoints. Porting
naively fails silently.

- `security.is_open_source` / `is_renounced` / `is_honeypot` are **booleans**, not `0/1`, and
  missing is `null`. All three states must stay distinct — "not checked" is not "failed".
- **LP lock is not `lock_summary.lock_percent`.** That field is the string `"0"` even for a
  token whose LP is 95% burned. The real data is `lock_summary.lock_detail[]`, where each entry
  carries `percent`, `pool` and `is_blackhole`; `is_blackhole: true` means burned.
- `burn_status` is `""` in `token security` output — never `"burn"`.
- `token info` carries `stat.*` (concentration, dev holdings, bundler and sniper shares) for any
  address.
- `wallet_tags_stat.*` counters **cap at 1000** — report them as a floor, not a count.

## Notes

- All CLI calls use `--raw` for single-line JSON output.
- Rule-engine output — information aggregation only, not investment advice.
- Read-only: this skill runs only `token info`, `token security` and `market kline`. No signing,
  no private key, no trade commands.
- Binance Alpha catalyst and X narrative are separate concerns and are not part of this skill.
  Their absence does not lower the score.
