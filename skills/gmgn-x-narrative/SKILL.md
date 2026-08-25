---
name: gmgn-x-narrative
description: X (Twitter) narrative and chatter for a token — measures whether anyone is actually talking about a contract, using the project's own X account, the X handles bound to its top holders, a KOL / Smart Money pool built from the CLI, and public search engines. Every mention needs hard evidence (the CA, a cashtag, or the name plus on-chain context words); upstream shill counts are never trusted. Use when the user asks 有人聊吗, 叙事, 热度, 声量, 推特, KOL 提了吗, social buzz, is anyone talking about this, narrative check, or wants the social side of a token rather than its chart or contract.
argument-hint: "--chain <sol|bsc|base|eth> --address <token_address> [--lang zh|en] [--kol 24] [--budget 45]"
metadata:
  cliHelp: "gmgn-cli token holders --help && gmgn-cli track kol --help"
---

**BEFORE RUNNING ANY COMMAND: Run `gmgn-cli config --check`. If exit code is 0, proceed normally. If exit code is 1, run `gmgn-cli config` and show output, then apply the key with `gmgn-cli config --apply <KEY>`. If unknown option, tell user to run `npm install -g gmgn-cli`.**

**IMPORTANT: Always use `gmgn-cli` via the script below. Do NOT use curl, WebFetch, or visit gmgn.ai.**

## Sub-commands

Four read-only CLI calls supply the handle lists; the post content itself comes from X's public
embed endpoint and from search engines, neither of which is a GMGN domain.

| Purpose | CLI command used |
|---------|------------------|
| Token symbol, name, project X account | `gmgn-cli token info --chain <chain> --address <address> --raw` |
| X handles bound to top holders | `gmgn-cli token holders --chain <chain> --address <address> --limit 100 --raw` |
| KOL pool | `gmgn-cli track kol --chain <chain> --limit 100 --raw` |
| Smart Money pool | `gmgn-cli track smartmoney --chain <chain> --limit 100 --raw` |

Handles bound to holders rank **above** the global KOL pool: someone holding this token is more
likely to be talking about it than someone who merely made money historically.

## Supported Chains

`sol` / `bsc` / `base` / `eth` — whatever the CLI accepts. Address shape is validated before the
call; an unrecognised chain name falls back to the EVM rule and refuses.

## Prerequisites

- `gmgn-cli` installed once: `npm install -g gmgn-cli`
- API key configured: `gmgn-cli config`
- Python 3.9+ — standard library only
- Outbound network access to `syndication.twitter.com` and a search engine

The script never reads `GMGN_API_KEY` or `GMGN_PRIVATE_KEY`.

## Parameters

```bash
python3 ~/.claude/skills/gmgn-x-narrative/narrative.py <ADDRESS> <CHAIN> [LANG] [--kol=N] [--budget=S] [--quiet]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `ADDRESS` | Yes | Token contract address |
| `CHAIN` | Yes | `sol` for base58; `bsc` for EVM `0x...` unless the user names another chain |
| `LANG` | No | `zh` or `en` — default `zh` |
| `--kol=N` | No | Timelines to warm per source — default 24 |
| `--budget=S` | No | Seconds allowed for timeline warming — default 45 |
| `--quiet` | No | Suppress the progress log on stderr |

**This skill is slower than the others.** Each X timeline takes 1-2.5 seconds and X rate-limits
by IP, so warming runs against a time budget rather than to completion. Tell the user it may
take up to a minute. Lowering `--budget` makes it faster; coverage drops and the report says so.

## Usage Examples

```bash
python3 ~/.claude/skills/gmgn-x-narrative/narrative.py 0xfa8f...7777 bsc
python3 ~/.claude/skills/gmgn-x-narrative/narrative.py So1111...1112 sol en --kol=12 --budget=25
```

Paste the complete stdout verbatim. Do **not** omit the coverage line or the closing note —
they are what make the score interpretable.

## Scenario → what you get

| The user asks | This skill returns |
|---------------|--------------------|
| 「有人在聊这个币吗」 / "is anyone talking about this" | A 0-100 narrative score, the mentions found, and how many timelines were actually covered |
| 「叙事是什么」 / "what is the narrative" | Narrative classification from the post texts, plus Web2 sources linked from them |
| 「KOL 提了吗」 / "have any KOLs mentioned it" | Which KOLs mentioned it inside the 24-hour window, with engagement |
| 「项目方还在运营吗」 / "is the team active" | Project account follower count and 7-day posting cadence |

**It does not answer:** anything about the contract, the holders, or the chart. Use
`gmgn-ca-verdict` for a verdict, `gmgn-kline-pattern` for the chart, `gmgn-track` for which
wallets are trading it right now.

Do **not** run this as part of a routine 「看看这个币」 — it is the slowest skill in the set. Run
it when the user specifically asks about social or narrative.

## The one thing you must not misread

**X is effectively closed to crawlers. Zero search results do not mean nobody is talking.**
This skill scores only the evidence it obtained and **never deducts for a miss**. A low score
with low coverage means "not observed", not "no interest".

Never restate a low score as "nobody cares about this token". Say what the report says: how
many timelines were covered and what was found in them.

## Two hard rules in the scoring

1. **Only mentions inside a 24-hour window are scored.** Older ones are archived and shown
   separately, never counted.
2. **Every mention needs hard evidence** — the CA, a cashtag, or the name plus on-chain context
   words. A name-only match from a timeline is reported but not scored; name collisions are
   common among memecoins. Upstream shill counts and plaza mention totals are never trusted:
   those are second-hand conclusions.

## Notes

- All CLI calls use `--raw` for single-line JSON output.
- Post content comes from `syndication.twitter.com`, X's public embed endpoint — no login and no
  X API key required. It is not a contractual API: X can change or withdraw it, in which case
  this skill degrades to search-engine results only.
- Search coverage is uneven. Bing was measured returning zero results; Brave and DuckDuckGo
  carry it.
- Outbound links found in posts have their titles fetched through `safefetch.py`, which resolves
  DNS and refuses private addresses on every redirect hop. Those URLs come from posts and are
  entirely untrusted input.
- Scoring text is generated in Chinese and translated through `i18n.py`. In `en` mode the output
  is checked for residual CJK and a missing translation prints a warning to stderr naming the
  untranslated string.
- Caches live under `~/.cache/gmgn-x-narrative/`, never in the install directory.
- Read-only: this skill runs only `token info`, `token holders`, `track kol` and
  `track smartmoney`. No signing, no private key, no trade commands.
