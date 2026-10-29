# Fields and data limits

Two halves: **what `dev_score.py` emits** (read this to know which key carries which fact),
and **what the underlying API actually returns** (read this before trusting any field the
script does not already read for you).

## Script output

One JSON object on stdout, nothing else. Progress notes go to stderr and are not part of it.
Every string that originates from on-chain metadata (symbols, token addresses, counterparty
addresses, and the keys of `severity_by_token`) has already been sanitised and, if it carried
anything unusual, is wrapped in `「」`. Money is USD, times are Unix seconds, durations are
seconds, rates and shares are fractions of 1 (not percentages).

**Not scored** — `{"scored": false, "reason": ...}` plus whatever context was available:

| `reason` | Meaning |
|---|---|
| `index_empty` | The index returned nothing, twice, and `portfolio stats` could not separate an empty wallet from a degraded index. **No verdict is possible** — say the data is unavailable, never that he is clean. |
| `not_a_person` | Launch count and peak are both at factory scale — a launchpad or factory contract, not a launcher. |
| `peak_implausible` | Reported peak market cap above 50B USD: the data source is wrong, not the dev. |
| `never_launched` | Wallet is indexed and has traded, but has launched nothing. Not a dev. |

**Scored** — `{"scored": true, ...}`:

| Key | Carries |
|---|---|
| `chain`, `dev`, `as_of`, `mode` | what was analysed, and when |
| `score.total` / `.conduct` / `.power` / `.bonus` | the three numbers and the bonus actually added |
| `score.band` | `buyable` / `mixed` / `avoid` / `stay_away` — **this is the verdict** |
| `conduct_terms.*` | every term behind CONDUCT: `raw`, `dump_pen`, `abandon_pen`, `factory_pen`, `opaque_pen`, `mean_severity`, `median_severity`, and the thin-record shrink as `shrink_from` → `shrink_to` with `shrunk` and `shrink_weight` |
| `power_terms.*` | `peak`, `repeatable`, `flagship_alive`, `book_quality`, `book_weight`, `drawdown_term` |
| `dump_gate.tier` | `none` / `rare` / `often` / `often_unproven` / `sys`; `forced_by: "lp"` means a drained pool forced it, not the rate |
| `dump_gate.dumps` / `.coins_with_trades` / `.dump_rate` / `.flagship_dumped` | the gate's own numbers |
| `dump_gate.definition` / `.caps` / `.total_capped` | the thresholds used, and whether a ceiling actually bound the total |
| `launches.*` | `total`, `counter_total`, `on_curve`, `graduated`, `graduation_rate`, `sampled`, `tradeable`, `survival_rate`, `survival_den`, `stuck_rate`, `walkaway_rate`, `over_1m`, `median_drawdown_over_1m`, `career_days`, `career_days_is_floor` |
| `his_trades.*` | what he did with his own hands: `coins_with_trades`, `coins_with_pull_multiple`, `median_pull_multiple`, `median_first_sell_s`, **`fastest_first_sell_s`**, `self_snipe_rate`, `dumped_coins`, `sell_without_buy_coins`, `severity_by_token` |
| `liquidity.drained` / `.partial` / `.ignored_rows` / `.forces_gate` | pool pulls that cleared the guard, and how many rows the guard rejected |
| `flagship` | his best coin: the `coin` shape below plus `status`, `holds`, `balance`, `position_closed`, `dumped`, `age_days`, `age_from`, `exit_rows`, `exit_accounted_by`, `exit_unrecorded` |
| `top[]` | the biggest sampled coins, newest-peak first, each in the `coin` shape |
| `cross_wallet.*` | supply moved to another wallet: `moves`, `sold`, `pending`, `total_moves`, `verified`, `enabled` |
| `bundler.median` / `.hot[]` | share of supply bought in the creation block — disclose, never score |
| `coverage.*` | every limit on the numbers above: `pages_walked` vs `max_pages`, `trade_history_truncated`, `unresolved_coins`, `book_truncated`, `book_oldest_ts`, `book_bulk_from_ts`, `book_bulk_span_h`, `book_has_old_straggler`, `implausible_peaks`, `refetched` |

`coin` shape (used by `top[]`, `flagship`, `coverage.implausible_peaks`): `symbol`, `token`,
`peak_mc_usd`, `mc_usd`, `drawdown`, `holders`, `pool_usd`, `tradeable`, `age_days`,
`created_ts`, `bundler_rate`.

`move` shape (used throughout `cross_wallet`): `symbol`, `token`, `to`, `share_of_supply`,
`usd`, `seconds_after_open`, `before_open`, `same_as_funder`, `sold_usd`, `first_sell_s`,
`unchecked`.

`flagship.status` — one code, and what each one licenses you to say:

| `status` | Meaning |
|---|---|
| `unreadable` | `token info` gave nothing. Say the holding is unknown. |
| `holding` | Still holds his own bag. |
| `sold_own_bag` | Sold his own bag. |
| `closed_no_sell_row` | Position closed, but no `sell` row exists anywhere — closed is not the same as sold, and there is no evidence of a sale. |
| `untraded` | He never traded this coin. |
| `untraded_but_supply_moved` | He never traded it, but supply left to another wallet — the exit may be off this address. |
| `closed_exit_unrecorded` | Closed, and no row of any kind accounts for where the bag went. This is what `opaque_pen` is for. |
| `closed_exit_documented` | Closed, and burn / transfer / pull rows account for it. |

`flagship.holds` is tri-state: `true` / `false` only when the API said something, `null` when
it did not. On `null`, say nothing about the bag — do not read `not closed` as holding.

## API fields

Only these fields are confirmed against the live API. Anything else — degrade gracefully and say the number is missing.

**`portfolio created-tokens --chain <c> --wallet <dev>`**

| Field | Meaning |
|---|---|
| `inner_count` | coins still stuck on the bonding curve (never opened to market) |
| `open_count` | coins that graduated to an open market |
| `open_ratio` | graduation ratio as reported by the API |
| `creator_ath_info.ath_mc` / `.ath_token` / `.token_symbol` | his best coin ever, by peak market cap |
| `tokens[]` | **capped at ~101 rows, truncated `create_timestamp`-descending** — the rows you get are his NEWEST launches (measured live on two sol wallets; an ATH-descending order was assumed here for a while and is wrong). Usually shorter than the real book, so the launch count is `N = max(inner_count + open_count, len(tokens))` — the counters can also come back *smaller* than the array (measured live: 63 + 17 = 80 counters vs 95 array rows), and each source is only a floor on the truth. |
| `tokens[].token_address` / `.symbol` | identity |
| `tokens[].token_ath_mc` / `.market_cap` | peak vs current market cap. **`token_ath_mc` is not always real** — a coin with 28 holders and a $9.5K pool came back with a $21.4B peak. Read every peak through `t_ath()`, which zeroes a figure that no footprint of that coin could ever have supported. |
| `tokens[].is_open` / `.pool_liquidity` / `.liquidity_less_4k` | alive = `is_open` **and** `pool_liquidity >= 4000` |
| `tokens[].cto_flag` | community took over — the dev walked away |
| `tokens[].create_timestamp` | launch time (Unix seconds) |
| `tokens[].holders` / `.launchpad_platform` | context |
| `tokens[].bundler_rate` | share of supply bought in the creation block — the only cross-wallet signal that needs no link back to him; disclosed, never scored (see Data caveats below) |
| `tokens[].total_fee` / `.coin_creator_fee` | fee income |

**`portfolio activity --chain <c> --wallet <dev> --limit 20 --type buy --type sell [--cursor <next>]`**

**The server caps a page at 20 rows no matter what `--limit` says** — verified: `--limit 100` returns 20. So walk with the `--type` filter (`buy` / `sell` / `transferIn` / `transferOut` / `add` / `remove`, repeatable) rather than paging through transfers and fee claims to reach the trades. This skill makes two filtered walks: `buy,sell` for the dump analysis and `remove` for the liquidity-pull check.

| Field | Meaning |
|---|---|
| `activities[].token.address` | the coin traded — the join key back to `created-tokens` |
| `activities[].event_type` | `buy` / `sell` / `launch` / `claim_fee` / `burn` / `add` / `remove` |
| `activities[].cost_usd` (fallback `quote_amount`) | USD size of the leg |
| `activities[].timestamp` | Unix seconds |
| `next` | pagination cursor — pass as `--cursor` |

`remove` is a liquidity pull and is the single heaviest finding — which is exactly why it is guarded: a row must move a non-zero, non-negligible amount of **the token** before it counts (see dump-rate gate). Never treat `quote_amount` as a size: it is denominated in the *paired* token. `claim_fee` + `add` together mean fee income redeposited as liquidity — that is a **good** sign, not a dump, and must not be counted as selling.

**`token info --chain <c> --address <token>`** — note the flag is `--address`, not `--token`.

| Field | Meaning |
|---|---|
| `dev.creator_address` | resolve a token address to its dev — the entry point for token-address questions |
| `dev.creator_token_status` | `creator_hold` = still holding; anything containing `sell` = he sold his own bag; `creator_close` = position closed (check `creator_token_balance`, and do not assume a sale — it can be closed with no `sell` row anywhere in the activity feed) |
| `to_address` / `from_address` | counterparty on a `transfer_out` / `transfer_in` row — this is how a sibling wallet is found |
| `token.total_supply` | present on activity rows; `token_amount / total_supply` gives the share of supply moved |
| `common.fund_from_address` | from `portfolio stats` — the address that funded this wallet. Populated even when `common.fund_from` is empty; use `_address` |
| `dev.creator_token_balance` | how much of his own coin he still holds |
| `open_timestamp` vs `creation_timestamp` | market open vs contract creation — use `open_timestamp` for "how old is this really" |
| `image_dup_count` | how many other tokens reuse the same logo; >1 means it is not original art |


## Supported Chains

`sol` / `bsc` / `base` / `eth` / `arbitrum` / `hyperevm` / `robinhood` / `arc` / `stable` / `avalanche`

`robinhood` is a real chain hosting tokenized-stock tickers with the `longxyz` launchpad — do not assume a `0x…` address is on BSC/ETH. If `created-tokens` returns `inner_count=0, open_count=0`, probe the other chains before concluding the address is not a dev.

**How to probe, when the chain is unknown.** Narrow by address format first — a base58 address is `sol`
only (1 call); a `0x…` address is one of `bsc` / `base` / `eth` / `robinhood` / `arc` / `stable` (6 calls).
Then fire those `created-tokens` calls **sequentially with no sleep between them**: each call is a ~0.55s
round trip, so 6 chains resolve in ~3.3s, and the CLI's own pacing is already sufficient — adding a
defensive `sleep 3` per chain turns a 3s step into 21s and buys nothing.

**Do not parallelise the probe.** Measured: 7 concurrent `created-tokens` calls return in 0.67s but 2 of
them come back with empty stdout, and a second burst a few seconds later had *every* chain refused — the
limiter accumulates violations into a ban across runs, so a 20s saving costs a 45s+ ban and a retry
storm. Sequential is both faster end to end and the only safe shape.

**An address can be a dev on more than one chain.** Confirmed live: `0x85de…82e5` has 1 launch on `bsc`
and 2 on `robinhood`. Do not stop at the first chain that returns launches — finish the probe before
deciding anything. The scores are not comparable across chains and must never be averaged or merged.

**Analyse ONE chain, the one with the most TRADEABLE launches. Defer the rest until asked.** Two full
reports cost roughly twice the output length of one and the second is usually not what the user came for,
so pick one chain, run the analysis there, and stop. If the user asks about another chain, run it then.

Rank the candidate chains by **`open_count`** — coins that actually reached a tradeable pool — not by
total launches and **not by `ath_mc`. Both of those pick the wrong chain, in opposite directions:**

- **`ath_mc` selects on the axis with the least power over the answer.** TOTAL = CONDUCT + a POWER bonus that
  the dump rate gate caps *before* it is added, so a chain's peak market cap cannot change the buy/don't-buy
  call. A dev with a $1B coin and an 80% dump rate on chain A and three clean launches on chain B would
  be shown at his most impressive while every piece of evidence about whether he is buyable sits on B.
- **Total launch count is distorted by the inner pool.** `inner_count` coins never opened, so they carry
  no trades of his and contribute nothing to CONDUCT — they only pad the count. A chain with 20,000 stuck
  inner-pool launches and 2 open ones would outrank a chain with 30 open ones, while being the chain
  where CONDUCT is pure shrink and therefore has no information in it.

What actually governs the answer is `n_tr`, the number of his coins carrying his own trade rows — it is
the dump rate denominator and the breadth term in the thin-record shrink. But `created-tokens` returns nothing
that predicts it (checked live: `coin_creator_fee` is 0 and there is no per-token buy/sell field), so
`n_tr` costs a full activity walk and cannot be a selector. `open_count` is its cheapest honest proxy.
Use `ath_mc` only to break a tie in `open_count`.

**But a deferred chain must be disclosed, never hidden.** Launch count and best-ever market cap both come
back in the same `created-tokens` probe call, at zero extra cost, so every deferred chain gets one footer
line naming its launch count and its `creator_ath_info.ath_mc`. This is not optional: on `0x85de…82e5`
launch count picks `robinhood` (2 launches, best coin $1.02M) and defers `bsc` — which holds his one
$101.7M coin, a 100× larger achievement than anything on the chain that was analysed. Silently dropping
that would misrepresent the dev. When a deferred chain's `ath_mc` is **3× or more** than the analysed
chain's, say so in words on that footer line — the user has to know the bigger story is on the other
chain before deciding whether to ask for it.


## Prerequisites

- `gmgn-cli` installed globally — if missing: `npm install -g gmgn-cli`
- `GMGN_API_KEY` in `~/.config/gmgn/.env` (exist auth only — no private key needed)

## Rate limits

Plan-based leaky-bucket limiter: Free `5/5`, Plus `20/20`, Pro `50/50` (rate/capacity); sustained throughput ≈ `tier rate ÷ weight` req/s.

| Command | Route | Weight |
|---|---|---|
| `portfolio created-tokens` | `GET /v1/user/created_tokens` | 2 |
| `portfolio activity` | `GET /v1/user/wallet_activity` | 3 |
| `token info` | `GET /v1/token/info` | 1 |

One run costs 1× `created-tokens` + up to `MAX_PAGES`× `activity` (buy/sell walk) + up to 3× `activity` (remove walk) + up to `TOP_K`× `activity` (per-token completion, only if the walk truncated) + 1× `token info`. The activity walk is the expensive part, and pages are only 20 rows: a dev with 300 trades needs 15 pages at weight 3 = 45 weight, more than twice the bucket capacity. Three mechanisms, in the order they matter:

1. **`GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS=90000`** is exported to every `gmgn-cli` call. The CLI already retries a 429 by sleeping until the server's own `x-ratelimit-reset` header (+1s), but by default refuses to wait more than 5s, so a ~45s ban surfaces as an error. Raising the cap lets the CLI absorb the ban using the authoritative reset instant — never a guessed one, and never landing exactly on the boundary, which is what extends a ban by 5s each time.
2. **`MIN_GAP_S = 0.35` paces the calls** so the bucket does not empty in the first place, and the gap **doubles (up to 8s) on any limit signal and stays doubled for the rest of the run** — one hiccup slows the run instead of escalating into a ban. This self-tunes to whatever quota the key actually has.
3. The backoff in `dev_score.py`'s `run_cli` is only the last resort, for a ban already extended by earlier traffic.

Violations accumulate across runs, not just within one, so a ban inherited from a previous run can only be waited out — mechanism 1 is what does that. Never run two devs concurrently; the pacing is per-process.

**Two different rate-limit failures, and they need different waits.** An empty stdout with exit code 0 is the soft one — a few seconds clears it. An HTTP `429 RATE_LIMIT_BANNED` is the hard one, and its message carries the reset time; **retrying at or before that instant extends the ban by 5s each time**, so wait for the stated window *plus a margin* and never poll the boundary. `run_cli` in `dev_score.py` distinguishes the two and waits accordingly. With the pacing and the `TOP_K` bound in place a single dev completes without tripping the hard limit, but a ban carried in from earlier traffic still has to be waited out — so if the run opens with a wait line, that is inherited, not caused by this run.

**An empty stdout with exit code 0 means rate-limited, not "no data".** The script's `run_cli` already backs off and retries; if it still comes back empty, stop and tell the user when to retry rather than reporting zero trades — reporting zero trades on a rate limit would turn a dumper into an unproven-clean score, which is the worst failure this skill can have.

**When a request returns `429`, stop and tell the user exactly when they can retry.** Read `X-RateLimit-Reset` from the headers, or `reset_at` from the body, convert to local time, and state it plainly. Repeated requests during the cooldown extend the ban by 5s each, up to 5 minutes — never loop retries, and never time a retry to land exactly on the reset instant.

**Resume, don't restart.** If `token info` fails after the activity walk succeeded, report the score you already have and say the flagship holding is unavailable (`flagship.status: unreadable`); re-run only that call.


## Data caveats

- `len(tokens)` is normally a truncated view (~101 rows, `create_timestamp`-descending), but it can also exceed `inner_count + open_count`, so the launch count takes the max of the two. Rates whose denominator must come from one consistent source (graduation rate) stay on the counters. Rates over `tokens[]` alone (CTO rate, untradeable rate) are rates *within the sampled coins* and should be described that way.
- **The truncation is `create_timestamp`-descending, so the coins that decide the verdict are NOT guaranteed to be in the sample.** This bullet used to claim the opposite — that the cut only discards his *smallest* launches, so his representative coins are always present — and every POWER-side career claim was built on that guarantee. It is false. Measured live on a 17,752-launch sol wallet: the 101 rows covered a **six-hour** window of his newest launches, his real #2 (peak **$8.26M**, 4,130 holders, a $200K pool, still held by him) was absent, and two coins that peaked at **$8.2K** and **$6.6K** were present because they fell inside the window. The report printed "his second-best coin is 1/348 of his best — only one success so far" when the true ratio was 1/3.9 and he had cleared $1M at least twice.
  A >101-launch dev is still scoreable, because everything on the CONDUCT side is *his own conduct in the coins we can see* and a dump he committed inside the window is a dump. What is not scoreable is any **career-wide superlative**: "only succeeded once", "his #2 is 1/N of his #1", "never made a $1M coin", "he has only been doing this N days". All of those are gated on `book_trunc` / `career_floor` and must be stated as floors — *"of the launches we can read"* — or not stated. The API exposes no way to page past the cap, so the fix is wording, not more data.
- **`creator_token_status` has a third value that is neither hold nor sell: `creator_close`.** Confirmed live (robinhood/PONS): status `creator_close`, `creator_token_balance` 0, and the entire activity feed contains no `sell` and no `transferOut` — he bought 68M of his own supply, burned 10.7M, and the remaining ~5.7% of supply is simply gone from the wallet with no traceable route. Report the closed position and the untraceable exit as two separate facts; do not resolve it into "he sold", which would invent a row that is not there.
- A dev holding his own coin (`creator_token_status: creator_hold`) is a positive; a dev who never traded his own coin at all is neutral, not clean — it can also mean he sells from another wallet. The cross-wallet check is what decides which: when a supply move is confirmed the script reports `flagship.status: untraded_but_supply_moved`, and "he never sold a share" must not be said.
- **A truncated activity walk understates risk, never overstates it.** Missing rows can only remove coins from the dump count, so a partial scan makes a dumper look cleaner. Three things keep that from biasing the score: rows are newest-first so the walk exits losslessly once it passes his earliest launch; any coin launched at/after the oldest row seen is already complete by construction; and any coin that could still be missing trades is resolved individually with `--token`, biggest first, capped at `TOP_K`. Only coins past that cap are reported as unresolved — and they are his smallest, which is the right place to be blind.
- The per-token completion pass re-fetches rows the global walk already had, so rows are de-duplicated on `(token, event_type, timestamp, amount, tx_hash)` before any rate is computed. Without that, a coin's buy/sell totals would be double-counted and its pull multiple would stay correct while its size doubled.
- **Cross-wallet exits are detected, within a stated limit.** The script walks `--type transferOut`, keeps only transfers of coins *he created* that move ≥1% of total supply to a non-burn address, then verifies each of the largest `SIB_MAX_CHECK` by querying the recipient's own buy/sell rows for that coin. Two outcomes, and they must never be conflated: a recipient that **has sold** is a confirmed cross-wallet dump, and its USD is folded into that coin's `sell` total so pull multiple and 1st-sell delay measure the *dev* rather than the wallet — otherwise concealment scores better than selling openly. A recipient that has **not sold** is unsold overhang: report it as pending sell pressure, never as a dump, because it has not happened.
- `portfolio stats` → `common.fund_from_address` is fetched only when a supply move exists. If the recipient of the supply is also the address that funded the dev, that is one operator with two wallets — state it plainly, it is the strongest sibling-wallet evidence available on-chain.
- **A recipient with no sells is not proof of a sibling wallet.** It can equally be a lock contract, a CEX deposit address, or a pool. That is why the unsold case is reported as "supply left his wallet" with the alternative stated, never as "he has a second wallet" — only a recipient that actually *sold* is called a cross-wallet dump, and only the funder match is called one operator.
- The residual blind spot is now narrow but real: a dev who runs a **fully independent** second wallet — funded from elsewhere, launching its own coins — cannot be linked on-chain by this method. Do not claim a dev is clean on one wallet's records alone; say which transfers were verified.
- **`tokens[]` truncation is a scoping problem, not a coverage problem.** The array stops at ~101 rows ordered by `create_timestamp` descending, so for a high-count dev every per-coin rate computed from it describes a *recent window* of his launches — which is a far weaker population than the "his largest launches only" this used to assume, and can be as short as six hours. It is still an acceptable population to judge conduct in, but it must be *named*: any rate whose numerator comes from `tokens[]` divides by `min(len(tokens), N)` and is labelled with that count. Only `graduation rate` escapes this, because `open_count / N` never touches the array.
  Two lines were violating their own rule and are now labelled: **untradeable rate** (`liquidity_less_4k / len(tokens)`) printed "86% of his coins ended up untradeable" off 101 rows out of 17,752 launches — 0.6% of the book stated as a career rate — and the confidence line printed "the dump read is fairly reliable" off 20 measured coins out of the same 17,752. Confidence there is now a matter of **coverage** (`n_tr / N ≥ 0.2`), not of a raw count: since `n_tr` can never exceed the ~101-row cap, any dev past ~505 launches is structurally incapable of good coverage, and the honest sentence for him is *"no dump in this batch"*, never *"he does not dump"*. Wording only — the score is not discounted again for coverage, because `factory_pen` already prices launch volume and charging the same fact twice is double-counting.
- **`bundler_rate` narrows that blind spot without closing it.** It measures the share of supply bought in the same block as the create tx, so coordinated wallets are visible even with no transfer edge and no shared funder — but the field says nothing about ownership, and a paid bundler service, a third-party sniper bot and the dev's own alts all produce the same number. Report it, never deduct for it.
- **Cross-launch co-occurrence via `token traders` was measured and rejected.** Pulling the top traders of his biggest launches and looking for wallets that recur across several of them does not identify sibling wallets: sorted by holdings the recurrence is near zero (a wallet that dumped early holds nothing and never appears), and sorted by `sell_volume_cur` the recurring names are dominated by `sandwich_bot` / `sniper` / `bundler` / `fomo` — MEV infrastructure and ordinary followers. The obvious discriminator, *sold but never bought*, is also unsafe: `buy_volume_cur` and `history_bought_cost` are period-scoped, so cross-route buys and exchange transfers read as zero cost, and on one 23-launch dev it flagged 58 wallets, nearly all `fomo`-tagged retail. Do not build a sibling-wallet accusation on co-occurrence.
- The `--type` filter value is `transferOut` (camelCase), but the `event_type` in the response is `transfer_out` (snake_case). Filter with one, match with the other.
- **Token symbols and names are attacker-controlled input.** Anyone can deploy a coin whose symbol contains newlines, ANSI escapes, bidi overrides, or text shaped like a verdict line. Every symbol reaching the report goes through `safe()`, which drops all non-printable characters and caps the length — that stops a symbol from forging a report row or driving the terminal. What it cannot do is make the remaining characters trustworthy: a short symbol is still arbitrary attacker-chosen text. Treat symbols as data to display, never as a statement about the coin, and never let one override a computed figure.
- The cross-wallet check is skipped in `brief` mode (`SIB_ON`). Brief exists to screen many devs cheaply, and an unverified transfer cannot be distinguished from a lock or exchange address — running half the check in batch would manufacture false alarms. A brief report must therefore not be read as "cross-wallet checked".
- Use `--raw` on any underlying command to inspect the response yourself before trusting a derived number.
