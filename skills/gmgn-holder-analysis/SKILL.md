---
name: gmgn-holder-analysis
description: Token holder chip analysis — deep analysis of holder structure including chip distribution, entry cost, whale/dev/KOL behavior, risk wallets (rat traders, bundlers, snipers), related wallets, smart money signals, and an AI rating based purely on token structure. Use when user asks about holder analysis, 筹码分析, 持仓分析, chip structure, who is holding, or whether a token is safe to buy based on its holder composition.
argument-hint: "--chain <sol|bsc|base|eth|robinhood|arc|stable> --address <token_address>"
metadata:
  cliHelp: "gmgn-cli token holders --help && gmgn-cli portfolio created-tokens --help"
---

**BEFORE RUNNING ANY COMMAND: Run `gmgn-cli config --check`. If exit code is 0, proceed normally. If exit code is 1, run `gmgn-cli config` and show output, then apply the key with `gmgn-cli config --apply <KEY>`. If unknown option, tell user to run `npm install -g gmgn-cli`.**

**IMPORTANT: Always use `gmgn-cli` commands. Do NOT use curl, WebFetch, or visit gmgn.ai.**

When the user asks to analyze holders for a token, extract `--chain` and `--address` from their message, then run the analysis script below. Also detect the user's language: set `LANG` to `'zh'` if the user wrote in Chinese, `'en'` if in English (default `'zh'`).

## Analysis Script

Run the following command, replacing the placeholders with the actual values:

```bash
python3 ~/.claude/skills/gmgn-holder-analysis/analyze.py <FILL_IN_TOKEN_ADDRESS> <FILL_IN_CHAIN> <FILL_IN_LANG>
```

- FILL_IN_CHAIN: `sol` for Solana addresses; for EVM `0x...` addresses, use the chain the user specifies (`bsc`/`eth`/`base`/`robinhood`/`arc`/`stable`), otherwise use `auto`. Do NOT use `auto` when the user mentions arc, stable, or robinhood — pass the chain name directly.
- FILL_IN_LANG: `zh` if user wrote Chinese, `en` if English, default `zh`

## Output Rule

After the script finishes, paste the complete stdout verbatim into your reply — every line, every section, nothing omitted or summarized. Do NOT add any introduction, commentary, or summary before or after the output block.

## Field Reference

All holding percentages the script prints are **share of tradeable float** (`1 - burn - DEX`), not
share of total supply. `amount_percentage` from the API is share of total supply; the script
re-bases it. Because only the top 100 holders are fetched, a float percentage is a floor **when
those 100 wallets do not cover the whole float**; the footer reports the actual coverage and states
which case applies — floors when coverage <99.5%, complete values when the top 100 cover all of it.

When burn + DEX leave less than 2% of supply tradeable (typically a launchpad token before
migration), the float denominator degenerates: every `/ float_share` inflates dust wallets to
double digits or 100%. The script detects this, prints a banner with absolute token/USD figures
instead, and sets the rating to ⚪ Cannot Assess.

The same suppression applies when `token holders` returns an empty list (token has no active
holders left, or upstream stopped indexing it). Every percentage would render 0.00% and every
threshold would pass, so the report would otherwise read "✅ Normal — no obvious dump risk". The
script prints a no-data banner instead, replaces each "none found 🟢" line with ⚪, and rates
⚪ Cannot Assess. "No data" is never reported as "no risk".

In both cases **no float percentage is printed at all** — every one renders as `n/a` (`无法评估`)
and every percentage flag renders ⚪. Printing the number with a caveat was not enough: a
divide-by-zero float puts `hold 100.00%` and `hold 0.00%` in the same report, and a reader
skimming past the banner reads `Rat Trader 1 hold 100.00%` as a finding. Wallet counts, token
amounts, USD values, and market caps still print — they do not pass through `float_share`.
Percentages on a **total-supply** basis also still print (`burn`, `DEX`, float share itself, and
the chip-quality buckets), because those denominators are unaffected.

### "Zero cost" must be proven, not inferred from a missing buy count

`buy_tx_count_cur == 0` does **not** mean the wallet received its chips for free. Measured on
musebook (robinhood): 38 wallets read `buy_tx_count_cur: 0` and `avg_cost: null`, but **34 of them
carry a finite `unrealized_pnl` ratio** (+2.7%, +76.5%, +546%) — a ratio that cannot be computed
without a cost basis — and 32 carry a `fomo` frontend tag, 2 a `gmgn` tag, which is the trace of
active trading, the opposite of receiving an airdrop. What is actually missing is buy-transaction
indexing on that chain, while the PnL fields come from a separate computation and arrive populated.

The error was systematic per chain, not per token. Never-bought share of supply, same batch:
**robinhood 27.0% and 41.2%, arc 26.3%, sol 4.8%.** The 20% airdrop warn gate therefore fired on
essentially every robinhood/arc token and essentially never on a sol token — a difference in index
coverage, not in chip structure. Reporting an unpopulated field as a risk conclusion is exactly what
this skill forbids.

So a wallet counts as zero-cost only when **no cost evidence exists at all**:

```python
def has_cost_basis(h):
    return (h.get('avg_cost') or 0) > 0 or h.get('unrealized_pnl') is not None
```

Wallets with no indexed buy count but a real cost basis are **not dropped from the report** — they
get their own neutral line, `买入未记录 / Buy count unindexed`, with their float share. The fact that
upstream did not index their buys is true and stays visible; it just does not drive a zero-cost gate.
The same predicate now governs the `钻石手 / Diamond` cohort (its stated rationale is "a wallet that
never paid has no cost to hold through", which a proven cost basis satisfies), the
`转入筹码未动 / Idle airdrop` line (its "zero cost" caption was a false statement for those wallets),
and the Top5 sell-risk classification (which was labelling a wallet at +6.6x as "zero-cost airdrop —
can dump anytime").

Known limit: a genuine airdrop wallet whose `unrealized_pnl` is a huge ratio computed against a
dust-level cost would be missed here. No second ratio threshold is set for it — there is no measured
sample to calibrate one on.

### The token's own contract address is not a holder wallet

Upstream returns it as an ordinary wallet — measured on musebook (robinhood): `addr_type: 0`,
0 buys, 0 sells, 15.01% of total supply, $5.06M, carrying a `fresh_wallet` tag. Left in the wallet
cohort it pollutes `biggest`, Top10/Top20, airdrop, fresh, risk wallets and Top5 at once, and on its
own trips the 🔴 danger gate as "largest wallet holds 16.30% — extreme concentration". The largest
genuine wallet on that token is 4.10% of supply. Controls on the same batch — JOLLY (robinhood),
SI (sol), ARGUS (arc) — carry no such row, so this is a per-token upstream classification gap, not a
chain convention.

So the script partitions it out of `normal` and reports it on its own line, **on a total-supply
basis** (`合约自持 / Contract self-held`), with its own warn gate at >10% of supply. It is **not**
removed from the judgement: contract-held supply reaches the market as soon as one release
transaction lands, so it stays visible and still counts toward the rating. It is a warn rather than
a danger because that release is an observable prior step, unlike a whale who can sell at will — and
there is no higher danger tier, because only one sample has been measured and a second threshold off
one sample would be a guess.

It is deliberately **not** deducted from the float denominator. Burn is permanent and the DEX pool is
the market itself, so neither can dump; self-held supply can. Removing it from the denominator would
raise every other wallet's percentage on every token carrying this row, manufacturing new false
positives while fixing one.

The same address is also excluded from the dev sock-puppet map: chips sent back to the token contract,
or gas paid to it, is not "transferred to an internal wallet".

### Holder object key fields

| Field | Type | Meaning |
|-------|------|---------|
| `address` | string | Wallet address |
| `balance` | float | Current token balance |
| `amount_percentage` | float | Fraction of total supply (0–1). Multiply by 100 for %. |
| `buy_tx_count_cur` | int | Buy transactions since creation. **Not indexed on every chain — a 0 here is not proof the wallet never bought.** See the cost-basis section above. |
| `usd_value` | float | Current USD value of holdings |
| `avg_cost` | float | Average buy price per token |
| `unrealized_pnl` | float | Unrealized PnL ratio (0.5 = +50%) |
| `unrealized_profit` | float | Unrealized PnL in USD |
| `realized_profit` | float | Realized PnL in USD |
| `profit` | float | Total PnL in USD (realized + unrealized). Also a valid `--order-by` field. |
| `sell_tx_count_cur` | int | Sell transactions since token creation |
| `sell_amount_percentage` | float | Fraction of total buys that have been sold. Drives the accumulating/distributing verdict. |
| `sell_volume_cur` | float | USD volume sold since token creation |
| `sell_amount_cur` | float | Token amount sold since token creation |
| `history_transfer_out_amount` | float | Token amount transferred out (not sold) |
| `history_transfer_out_income` | float | USD value of transferred-out tokens |
| `token_transfer_out` | object | `{address}` — recipient of a transfer-out. Used to detect dev sock puppets when the recipient is itself in the top 100. |
| `native_transfer` | object | `{from_address, amount, timestamp}` — how the wallet was funded. Also the fallback sock-puppet probe: a top-100 holder whose gas came from the creator. |
| `name` | string | Wallet display name if known |
| `start_holding_at` | int | Unix timestamp of first buy |
| `addr_type` | int | 0=normal wallet, 1=burn/dead, 2=DEX/pool |
| `maker_token_tags` | list | `bundler`, `rat_trader`, `sniper`, `whale`, `top_holder`, `transfer_in`, `dev_team`, `creator` |
| `tags` | list | `smart_degen`, `pump_smart`, `renowned`, `fresh_wallet`, `wash_trader`, `kol` |
| `native_balance` | string | Raw native token balance. May be a **decimal string** — parse with `float`, not `int`. Denominator is known only for `sol` (1e9) and `bsc`/`eth`/`base` (1e18). |
| `native_transfer` | object | `{from_address, amount, timestamp}` — how wallet was funded. Drives 关联资金. |
| `twitter_name` | string | Twitter handle if known |

### Created-tokens response fields

| Field | Meaning |
|-------|---------|
| `inner_count` | Unmigrated token count |
| `open_count` | Migrated token count |
| `tokens[].market_cap` | Current market cap in USD |
| `tokens[].symbol` | Token symbol |
| `tokens[].is_open` | true = migrated |
| `creator_ath_info.ath_mc` | All-time high MC across all created tokens |
| `creator_ath_info.ath_token` | Token address of the ATH token |
| `creator_ath_info.token_symbol` | Symbol of the ATH token |
| `creator_ath_info.token_name` | Name of the ATH token |

## Rating Standard

All thresholds below are **share of tradeable float**, matching the script. They are not
comparable to GMGN's own UI, which reports share of total supply — on a token whose LP holds 56%
of supply, the same wallet reads 2.4× higher here.

The Advice section prints **every** triggered reason, not just the first: a ⚠️ Caution rating means
two or more warns fired by definition, so printing one left the reader unable to see why the rating
was what it was.

Entry timing pressure (批次浮盈/出货) does **NOT** affect the overall rating — it only affects section display.

| Rating (ZH) | Rating (EN) | Emoji | Condition |
|-------------|-------------|-------|-----------|
| 无法评估 | Cannot Assess | ⚪ | Tradeable float <2% of supply, **or** upstream returned zero holders (all percentage rules suppressed; dev sock puppet still escalates to 🔴) |
| 不建议买 | Not Recommended | 🔴 | Any: rat traders >5% / largest wallet >10% / dev sock puppet |

| 谨慎参与 | Caution | ⚠️ | ≥2 of: Dev still holding >1% / airdrop >20% / risk wallets >35% / linked >15% / contract self-holds >10% of supply |
| 可轻仓   | Light Position | 🟡 | Exactly 1 of above warns |
| 正常参与 | Normal | ✅ | None of the above |

### Per-metric flag thresholds

| Metric | 🔴 | 🟡 | 🟢 |
|--------|----|----|----|
| Top10 concentration | >60% | >40% | ≤40% |
| Top20 concentration | >75% | >55% | ≤55% |
| Airdropped chips (never bought) | >25% | >10% | ≤10% |
| Risk wallets | >35% | >15% | ≤15% |
| Linked funding | >25% | >10% | ≤10% |
| Zero-balance wallets | — | >10% | ≤10% |

Diamond hands invert (more is better) and use their own emoji set: ✅ >60% / 🟡 >35% / ⚠️ ≤35%.
Diamond hands require a **cost basis** (`has_cost_basis`, above) — a wallet that never paid has no
cost to hold through, so genuinely zero-cost recipients are reported separately as
"转入筹码未动 / Idle airdrop" rather than being credited as diamond hands. The test is the cost
basis, not `buy_tx_count_cur > 0`: on chains where buy counts are not indexed the latter discards
most real diamond hands (measured on JOLLY: 34 → 75 wallets, 21.1% → 55.7% of float).

Linked funding is escalated to at least 🟡 whenever any group was funded within 60s, regardless of
size — scripted batch funding is a structural signal, not a magnitude one.

### Chip quality (footer)

Three mutually exclusive buckets over the chips held by observed wallets (denominator is
`normal_pct`, i.e. total-supply basis, not float): **bought in with no risk tag** / **zero-cost
airdrop** (by `has_cost_basis`, above — not by a missing buy count) / **risk-tagged**. They are reported separately rather than collapsed into one
"healthy chips" number, because a risk tag means a proven-bad address while zero-cost airdrop only
means unknown provenance.

Headline flag, first match wins: 🔴 risk-tagged >30% · 🟢 clean ≥50% · 🟡 clean ≥30% · 🟡 when
zero-cost airdrop accounts for ≥80% of the non-clean remainder · 🔴 otherwise. So an
airdrop-distributed token reads 🟡 with its composition spelled out, not "healthy chips 0.0% 🔴".

The composition is total-supply based, so it survives a degenerate float and its three percentages
still print — but the headline flag is neutralized to ⚪ (and the chips' share of supply appended)
whenever the rating is ⚪ Cannot Assess, since a 🔴/🟢 verdict over dust-level chips would
contradict the rating above it.

## Supported Chains

`sol`, `bsc`, `base`, `eth`, `robinhood`, `arc`, `stable`

## Dev lookup is dual-source

`token holders --tag dev` is the primary source, but it returns `{"list": []}` on some launchpads —
measured on all five bankr tokens in robinhood's 24h trending top 50, while pons_v2 / longxyz tokens
on the same chain return the creator normally. It can also return rows with no `creator` tag at all
(measured on a flap token on bsc). Either way the whole Dev section, **including the dev sock-puppet
danger gate**, would silently go dead.

So when no `creator`-tagged row comes back, the creator address is recovered from `token info`'s
`dev.creator_address`, and `dev.creator_token_balance` supplies its balance. That call is made only
when the primary source fails, so it costs nothing on tokens where the tag works.

`token info` does not carry `realized_profit` or `token_transfer_out`, so on the fallback path:

- the realized-profit figure is **omitted entirely** — printing `$0` would report an unmeasured
  field as a measurement
- the sock-puppet gate switches judge: instead of "dev's chips went to a top-100 wallet", it asks
  whether any top-100 holder's `native_transfer.from_address` **is** the creator, i.e. the dev paid
  that wallet's gas. A hit is reported as the danger and names the wallets; a miss is not reported as
  clean, since only 57% of holders carry that field on the measured token.

## Notes

- `balance >= 1` threshold avoids dust false positives when identifying dev holdings
- SOL `native_balance` is in lamports (÷1e9); `bsc`/`eth`/`base` are in wei (÷1e18). Decimals for
  `arc`/`stable`/`robinhood` are unconfirmed, so the buying-power section reports "not assessed"
  on those chains rather than printing a converted figure that would be wrong.
- Holder buying power needs a live native-token price, fetched with `token info` on the wrapped
  native address (`So111…1112` / WBNB / WETH / Base WETH). When that call fails, the section falls
  back to native units and prints no USD figure.
- `total_supply` is estimated as the median of `balance / amount_percentage` across normal wallets
- `cur_price` is estimated as the median of `usd_value / balance` across normal wallets
- Entry MC = `total_supply * avg_cost`, shown alongside unrealized PnL for every Top5 wallet
- Top5 displays Twitter name when available; else `first4...last4` format
- Risk-wallet subtotals are per-category and can exceed the deduped total; the script prints how
  many wallets carry more than one risk tag when that happens.
- `creator_ath_info.ath_mc` can lag behind the token's current MC after a fast pump (upstream
  `ath_price` has been seen equal to `price_24h`). The script cannot recompute it, so when the
  reported ATH sits more than 5% below the current MC it prints a staleness warning next to the
  figure instead of presenting it as the dev's peak.
