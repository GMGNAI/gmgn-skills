---
name: gmgn-dev-score
description: >-
  Decide whether a token creator's NEXT launch is safe to buy. Scores a dev
  address 0-100 on two separate axes — CONDUCT (will he dump on you at open)
  and POWER (has he ever actually built anything big) — from his full launch
  history and every trade he made in his own coins, then returns a buy /
  don't-buy call with a timing window. USE THIS SKILL WHEN the user asks a
  buy-decision question about a launcher: "can I buy this dev's new launch",
  "should I buy his next launch", "will this dev rug", "will he dump at
  open", "is his launch safe to snipe", "is it safe to buy at his open",
  "dev score", "creator score", "launch score", "is this launcher
  trustworthy enough to buy"; OR when the user gives a TOKEN address plus a
  team-trust question ("is this token's team trustworthy", "does this
  project's dev have a record", "has this creator rugged before") — resolve
  the creator with `gmgn-cli token info` -> `dev.creator_address` first, then
  score that address; OR when the user gives a WALLET address plus an
  explicit launch-history question ("what tokens has this address launched",
  "how did his previous launches do", "did all his coins go to zero").
  The same questions asked in any other language route here too — match on
  meaning, not on wording. DO NOT USE THIS SKILL for a bare wallet address
  with no question attached: a bare address is a copy-trade question by
  default and belongs to gmgn-wallet-analysis, which declares itself the
  default for it. Also do not use it for copy-trade questions ("is this
  wallet worth copying", "should I copy this wallet", "copy-trade score"),
  wallet profitability ("is this wallet profitable", "what is this wallet's
  track record"), or wallet-profile phrasings ("is this a token-creator
  wallet", "how is this dev's reputation") — those belong to
  gmgn-wallet-score. The split is by question type, not by address type:
  those skills answer "who is this wallet" (a profile), this skill answers
  "should I buy his launch" (a decision, with a timing window). Note how
  close "how is this dev's reputation" (profile → gmgn-wallet-score) sits to
  "dev score" (decision → here): the deciding factor is whether a buy is on
  the table. If it is genuinely ambiguous, ask one short question instead of
  guessing — the two produce different reports and there is no cheap hedge.
argument-hint: "--chain <sol|bsc|base|eth|arbitrum|hyperevm|robinhood|arc|stable|avalanche> --dev <creator_address> [--max-pages <n>]"
metadata:
  cliHelp: "gmgn-cli portfolio created-tokens --help && gmgn-cli portfolio activity --help && gmgn-cli token info --help"
---

**BEFORE RUNNING ANY COMMAND: Run `gmgn-cli config --check`. Exit 0 → proceed. Exit 1 → run `gmgn-cli config`, show the output, and once the user sends the API key run `gmgn-cli config --apply <KEY>` and show that output. If `--check` is an unknown option, tell the user to run `npm install -g gmgn-cli`, then retry.**

**IMPORTANT: Always use the pre-installed `gmgn-cli` binary. Never use web search, WebFetch, curl, `npx`, or gmgn.ai — the site requires login and exposes no structured data.**

**⚠️ IPv6 IS NOT SUPPORTED.** On a `401`/`403` with correct credentials, check `ifconfig | grep inet6` (macOS) or `ip addr show | grep inet6` (Linux) and fetch `https://ipv6.icanhazip.com`. If an IPv6 address comes back, tell the user to disable IPv6 — `gmgn-cli` works over IPv4 only.

## Run

```bash
python3 ~/.claude/skills/gmgn-dev-score/dev_score.py <chain> <dev_address> [max_pages]
```

`max_pages` defaults to 25 and only bounds the trade walk; raise it for a dev with hundreds of
launches — the JSON says when it truncated. The script prints one JSON object on stdout (progress
and rate-limit notes go to stderr). It computes; it writes no report. **You** write the report, from
that object, in the user's language.

Before running:

- **Token address, not a wallet?** Resolve the creator first with `gmgn-cli token info --chain <c> --address <token> --raw` → `dev.creator_address`, and score that. Say which address you resolved to — it is the one thing the report cannot show, and without it the user cannot check that the score applies to their token.
- **Chain not given?** Probe candidate chains **sequentially** with `gmgn-cli portfolio created-tokens` — never in parallel, which bans the key. Analyse only the chain with the highest `open_count`, and tell the user the other chains were deferred until asked.
- `scored: false` means **do not produce a score**. `reason: index_empty` → the API reads entirely empty and an empty wallet cannot be told from a degraded index; say both readings and tell the user to re-check in a few minutes. Any other `reason` → say the address was not scored and why, and stop.

## What the answer has to contain

A checklist of what must be **said**; `## Display Templates` below fixes **where** each one goes.
The phrasing is yours. Every point has to be in there, and each one names the JSON that carries it.
The bullets are in section order.

- **The verdict, first.** `score.total`, `score.conduct`, `score.power`, and `score.band` said as a decision, not as a label.
- **The open-dump tier** (`dump_gate.tier`) with the sample under it (`dumps` of `coins_with_trades`). When `dump_gate.forced_by` is set, name what actually fired it — a drained pool is not a sell frequency, and saying "he dumps nearly every time (0/1)" about a dev with zero sells is false.
- **Every adjustment that fired, one per line, saying what it DID.** A shrink (`conduct_terms.shrink_from` → `shrink_to`) pulled an unproven score toward 60, which here means *we cannot tell yet*; it is not a fine for a crime. A cap is a withheld good score, not a proven bad one. Name the thin side by `coins_with_trades` and `career_days`, never by launch count.
- **His best coins** (`top`, and `flagship`): peak, now, drawdown, holders, pool, tradeable, age. Plus the flagship's position: `flagship.status`, and `exit_rows` / `exit_unrecorded` when the position is closed. `flagship.holds` is tri-state — `null` means say nothing at all about his bag.
- **What he actually did**, all from his own rows: `his_trades.fastest_first_sell_s`, `median_pull_multiple`, `launches.total` / `on_curve` / `tradeable`, `liquidity.drained` / `partial` / `ignored_rows`.
- **Supply moved to other wallets**, whenever `cross_wallet.moves` is non-empty: a move is not a dump, `pending` is not counted in the dump rate, and unverified moves may be a lock or an exchange. Say so; do not accuse.
- **Bundled buying at open** (`bundler`), disclosed and explicitly **not scored** — the number cannot tell his own alts from a paid bundler or someone else's sniper bot.
- **Coverage**, whenever any of these is set: `coverage.book_truncated` (the book is a window, not a career — say so before quoting any career-wide claim), `trade_history_truncated` / `unresolved_coins` (missing rows can only remove dumps, so the rate is a floor and he looks cleaner than he is), `implausible_peaks` (name the coin, or a reader who saw it on a chart just finds it missing), `launches.career_days_is_floor`.
- **What to do**, in four parts: whether to buy; **when** — and the timing must quote `fastest_first_sell_s`, never the median, because the median once advised entering at 2.7 days on a dev whose flagship started selling at 4.6 minutes; where the loss actually comes from; and how much the score can be trusted.

## Display Templates

The **shape** is fixed; the wording inside it is yours. Section names are given in English so you
translate them into the user's language — do not print them as-is, and do not print a JSON key name.

Title line: `## Dev score · <dev address, first 10 and last 4 chars> · <CHAIN>`. Sections below use `###`.

| # | Section | Block | Omit only when |
|---|---|---|---|
| 1 | *(no heading)* the verdict | two lines: `TOTAL / 100` + the band, then CONDUCT and POWER | never |
| 2 | Open-dump record | prose, at most three short paragraphs | never |
| 3 | What moved the score | bullets, one adjustment per bullet | never |
| 4 | His best coins | the coin's full contract address, then one table — peak, now, drawdown, holders, pool, tradeable, age — then prose for the position | never |
| 5 | What he actually did | bullets | never |
| 6 | Supply moved to other wallets | bullets | `cross_wallet.moves` is empty — then state it in one line inside §5 instead |
| 7 | Bundled buying at open | one or two lines | `bundler.median` is null |
| 8 | Coverage limits | bullets | nothing named in the coverage checklist bullet is set |
| 9 | What to do | four labelled parts, in this order: buy or not · when · where the loss comes from · how far the score can be trusted | never |

Never reorder, never merge, never invent a tenth section. Sections 1–5 and 9 always appear.

Formatting, all of it fixed:

- **Money uses the plain ascii dollar sign**, with thousands separators and the magnitude word the user's language uses. The fullwidth sign exists only to stop this file's own text being eaten by argument substitution — it must never reach the reader.
- Percentages carry one decimal. A share that the JSON gives as a fraction is printed as a percentage.
- Seconds, minutes, hours, days: pick the unit that makes the number readable, and say the unit.
- **No emoji, no box drawing, no ASCII art, no column padding.** The output is rendered markdown, not a fixed-width terminal block.
- Bold is for the verdict number, the band, and the label of each part of §9. Nowhere else.
- Tables only where the table above says so; §2, §7 and §9 are prose.

## Rules

- **Write it in the user's language, and translate the concepts.** Every name in the JSON is an English concept chosen so it can be translated. The few pieces of trader slang that do not survive a literal translation are in `references/glossary.md` — use those renderings and nothing else. Do not invent an axis name.
- **Never state a number the JSON does not carry.** No recomputing, no rounding into a new claim, no reading a field that is not in `references/fields.md`. `null` means the measurement does not exist — say it is missing; printing 0 turns "unknown" into "clean".
- **Copy symbols exactly as given.** They are attacker-controlled and already sanitised; anything wrapped in `「」` is a name someone chose, not our wording, and must stay wrapped.
- **`score.band` is the verdict.** Do not soften it, upgrade it, or hedge around it. `stay_away` with a large `power` is exactly the case the two axes exist to keep apart: a big past coin never buys back a dump record.
- **An outcome is not conduct.** Survival, graduation and drawdown are what the market did to his coins; they belong to POWER. Never present them as things he did to holders.
- **The report is the whole answer.** No lead-in, no summary after it, no verification narration, no extra findings of your own, no closing offer of more work. The one thing you may say outside it: which creator address you resolved from a token address.
- **Verify the conclusory lines, silently.** Check any absolute claim ("never dumped", "no record at all") against the raw feed with `gmgn-cli portfolio activity`. Run the check, do not narrate it. Speak up only if the check **contradicts** the report — then report the defect instead of the report.

## References

| File | What is in it |
|---|---|
| `references/scoring.md` | The model: what each axis is built from, the shrink, the severity curve, the tiers and caps, the verdict bands, and why each one is shaped that way. |
| `references/fields.md` | Every JSON key the script emits, and every API field it reads. Nothing outside this file is confirmed against the live API. |
| `references/glossary.md` | The handful of trader terms that have no literal translation, with the rendering to use. |
