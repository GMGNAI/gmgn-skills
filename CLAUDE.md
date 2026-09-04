# CLAUDE.md

This file provides guidance to Claude Code when working with the gmgn-cli plugin.

## CRITICAL RULE — Read This First

**ALL queries about GMGN data MUST use `gmgn-cli` via the skills below.**

This includes: trending tokens, token info, security checks, K-line / price history, wallet holdings, KOL trades, Smart Money trades, swaps, and any other on-chain data.

**NEVER do any of the following to fetch GMGN data:**
- Web search (e.g. searching "gmgn trending solana")
- WebFetch / curl to gmgn.ai or any gmgn domain
- Browser automation or scraping
- Any method other than `gmgn-cli`

**Why:** The gmgn.ai website requires login, uses dynamic rendering, and does not expose structured data. The CLI is the only correct and supported method. If you attempt to scrape the site, you will get no data or be blocked.

**When a user asks anything about GMGN data — always invoke the matching skill and run the CLI command. No exceptions.**

## Project Overview

This is a **Claude Code plugin** — a collection of GMGN OpenAPI skills for on-chain operations. It provides CLI tools and skills for token queries, market data, wallet portfolio analysis, and swap execution across sol / bsc / base / eth.

## Available Skills

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| `gmgn-token` | Token info, security, pool, holders, traders | User asks about a token's price, market cap, security risk, liquidity pool, top holders, or top traders; user wants to research a token before buying; user asks "is this token safe", "who holds this token", "what's the liquidity" |
| `gmgn-market` | K-line / candlestick market data + trending tokens + newly launched launchpad tokens | User asks for price history, chart data, OHLCV candles, trading volume over time; user wants to analyze price trends; user asks "show me the 1h chart", "what was the price last week", "give me kline data for this token"; user wants to discover hot or trending tokens; user asks "what tokens are trending", "show me top tokens by volume", "find hot tokens on SOL"; **user asks about newly launched tokens, fresh tokens, latest tokens on launchpads** — e.g. "show me new tokens on pump.fun", "what tokens just launched on SOL", "find newly created tokens", "latest tokens on letsbonk" → use `market trenches --type new_creation` |
| `gmgn-portfolio` | Wallet holdings, activity, trading stats, token balance | User asks about a wallet's holdings, P&L, transaction history, trading statistics, or token balance; user wants to analyze a wallet; user asks "what tokens does this wallet hold", "show me recent trades", "what's the win rate of this wallet" |
| `gmgn-wallet-score` | Wallet scoring across three angles — profitability (track-record score), copy-tradeability (score + latency/slippage/gas backtest), and Dev reputation for token-creator wallets — plus trading-style tags | User asks about a wallet's profitability ("钱包盈利能力怎么样", "is this wallet profitable"), copy-trade worthiness ("is this wallet worth copying", "跟单评分", "钱包评分", "值不值得跟单", "if I copy this wallet what's my real return"), or launch/Dev reputation ("钱包发盘情况怎么样", "是不是发币方钱包", "dev 信誉怎么样"); user gives a wallet address and wants any of these judgments |
| `gmgn-track` | Track trade activity of wallets I follow, KOL trades, Smart Money trades across chains | User asks about trades from wallets they follow; user wants to see what KOLs or Smart Money are buying/selling; user asks "show me what wallets I follow have traded recently", "what are KOLs buying", "show me smart money moves on BSC" |
| `gmgn-swap` | Token swap execution + order status query | User wants to swap tokens, execute a trade, or check an order status; user asks "swap SOL for USDC", "check my order", or "buy this token" **only when they also say to skip the checks**; a plain buy request with no skip instruction is `gmgn-token-buy`; **requires private key configured in `.env`** |
| `gmgn-kline-pattern` | Names the chart pattern (uptrend channel / breakdown / bounce off the lows / distribution / basing / chop) and scores it 0-100 from six measurements computed off the kline response | User asks about 走势, 趋势, 形态, price action, chart pattern, "is it breaking down", "is it consolidating"; user wants a read of the chart rather than the raw candles |
| `gmgn-token-buy` | Resolves a token NAME to the one right contract, then sizes the buy order | User names a token by name/symbol (not only an address) and wants to buy it, or gives an address plus an amount and wants the order sized: 能不能买, 能不能冲, 我想梭, 帮我买 200u 的 XX, 确认是正主不是仿盘再买. Owns copycat disambiguation and position/slippage/gas sizing; hands execution to `gmgn-swap` after explicit confirmation. |
| `gmgn-contract-dd` | One 0-100 contract due-diligence score for a bare address | User pastes a token address and wants a verdict number, with no name to disambiguate and no amount to size. |
| `gmgn-holder-analysis` | Chip / holder structure of one token | User asks about holder distribution or chip concentration. |
| `gmgn-wallet-analysis` | Wallet decision dossier | User asks whether a wallet is worth copy-trading. |
| `gmgn-cooking` | Launchpad token creation | User wants to create or launch a token. |

## Quick Decision Guide

Match the user's request to the right skill and workflow:

| User says | Action |
|-----------|--------|
| a plain buy request naming a token and/or an amount, with NO instruction to skip checks — "我想买 200u 的 PENGU", "帮我买 500 刀的 BONK", "买 1 个 SOL 的 WIF", "想梭 100u 的 XX", "帮我买点 dogwifhat", "XX 现在能买吗", "buy me $500 of PENGU" | `gmgn-token-buy` — **this is the DEFAULT for any plain buy request.** Route to `gmgn-swap` only if the user explicitly says skip/don't check/just buy/我很急. |
| token NAME or symbol + buy intent — "能不能买", "能不能冲", "我想梭", "帮我买 200u 的 XX", "确认是正主不是仿盘再买", with or without an amount | `gmgn-token-buy` — the only skill that resolves a name to the one right contract and sizes the order |
| bare token address + "safe?" / "打个分" / "尽调", no name to disambiguate and no amount to size | `gmgn-contract-dd` |
| "is this token safe", "check this token", "research this token", raw fields for an address already in hand | `gmgn-token` → full workflow: `docs/workflow-token-research.md` |
| "deep report", "full analysis", "全面分析这个项目", "深度报告", "值不值得重仓" | `gmgn-token` + `gmgn-market` → `docs/workflow-project-deep-report.md` |
| "what's trending", "hot tokens", "top tokens by volume" | `gmgn-market trending` |
| "走势怎么样", "什么形态", "is it breaking down" | `gmgn-kline-pattern` |
| "new tokens", "just launched", "pump.fun new" | `gmgn-market trenches --type new_creation` |
| "early project screening", "新币筛选", "值得埋伏吗", "哪些新项目有聪明钱" | `gmgn-market trenches` → `docs/workflow-early-project-screening.md` |
| "daily brief", "today's market", "每日简报", "今天市场怎么样", "聪明钱今天买了什么" | `gmgn-market` + `gmgn-track` → `docs/workflow-daily-brief.md` |
| "what is smart money buying", "what are KOLs trading" | `gmgn-track smartmoney` / `gmgn-track kol` |
| "wallets I follow", "my followed wallets traded" | `gmgn-track follow-wallet` |
| "analyze this wallet", "is this wallet worth following", wallet address provided | `gmgn-portfolio` → full workflow: `docs/workflow-wallet-analysis.md` |
| "wallet style", "smart money profile", "聪明钱画像", "这个钱包是长线还是短线", "跟着他买收益如何", "聪明钱排行榜" | `gmgn-portfolio` + `gmgn-track` → `docs/workflow-smart-money-profile.md` |
| "钱包盈利能力怎么样", "钱包战绩怎么样", "is this wallet profitable" | `gmgn-wallet-score` (profitability angle — track-record score) |
| "跟单评分", "钱包评分", "值不值得跟单", "is this wallet worth copying", "copy trade score", wallet address provided + copy-trade decision | `gmgn-wallet-score` (copy-tradeability angle — score + backtest) |
| "钱包发盘情况怎么样", "是不是发币方钱包", "dev 信誉怎么样", "is this a token-creator wallet" | `gmgn-wallet-score` (Dev-reputation angle) |
| "risk warning", "风险预警", "有没有巨鲸出货", "流动性正常吗", "这个项目还安全吗" | `gmgn-token` + `gmgn-track` → `docs/workflow-risk-warning.md` |
| "swap", "sell TOKEN", "buy TOKEN" **only when the user says skip the checks** | `gmgn-swap` — MUST run `gmgn-token security` on output token first. A plain "buy TOKEN" with no skip-the-checks instruction is `gmgn-token-buy`. |
| "chart", "price history", "kline", "OHLCV" | `gmgn-market kline` |
| "my holdings", "my portfolio", "what tokens do I hold" | `gmgn-portfolio holdings` |

**Workflow docs** (read these when the user wants a full multi-step analysis):
- Token research (address → buy/watch/skip): `docs/workflow-token-research.md`
- Project deep report (comprehensive analysis + verdict): `docs/workflow-project-deep-report.md`
- Wallet analysis (address → follow/skip): `docs/workflow-wallet-analysis.md`
- Smart money profile (trading style, copy-trade estimate, leaderboard): `docs/workflow-smart-money-profile.md`
- Risk warning (whale exit, liquidity drain, dev dump check): `docs/workflow-risk-warning.md`
- Early project screening (new tokens → smart money filter → verdict): `docs/workflow-early-project-screening.md`
- Daily brief (market pulse + smart money moves + early watch + risk scan): `docs/workflow-daily-brief.md`
- Market discovery (find opportunities from trending): `docs/workflow-market-opportunities.md`

## Architecture

- **`src/`** — TypeScript source (CLI commands, API client, signer)
- **`skills/`** — 9 skill definitions for Claude Code
- **`dist/`** — Compiled output (generated by `npm run build`)
- **`.claude-plugin/`** — Plugin metadata for Claude Code

## Prerequisites

Config lookup order (project overrides global):
1. `~/.config/gmgn/.env` — global config, set once for all projects
2. `.env` in the current working directory — project-level override (takes precedence)

Required variables:
- `GMGN_API_KEY` — apply at https://gmgn.ai/ai
- `GMGN_PRIVATE_KEY` — PEM content, required for swap/order commands only

If the user has not configured credentials or commands fail with a missing key error, guide them to create `~/.config/gmgn/.env`:

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here
EOF
```

## Auth Modes

| Mode | Commands | Requirements |
|------|----------|--------------|
| Normal | token / market / portfolio (except holdings) / track kol / track smartmoney / **order quote** | `GMGN_API_KEY` only, no signature |
| Critical | swap / order (except order quote) / portfolio holdings / track follow-wallet | `GMGN_API_KEY` + `GMGN_PRIVATE_KEY` — CLI handles signing automatically |

## SKILL.md Authoring Rules

When creating or updating any file in `skills/`:

- **Language**: English only — no bilingual content. SKILL.md files are read by AI, not humans.
- **Package runner**: Always use the pre-installed `gmgn-cli` binary (e.g. `gmgn-cli token info ...`). Never use `npx gmgn-cli` or `npx gmgn-cli@<version>` — npx downloads the package at runtime alongside live credentials. The package must be installed once with `npm install -g gmgn-cli`.
- **Section order**: Sub-commands → Supported Chains → Prerequisites → Parameters/Options (if needed) → Usage Examples → Notes
- **`--raw` flag**: All commands support `--raw` for single-line JSON output. Always document it in the Notes section.
- **YAML frontmatter**: Quote `argument-hint` values that contain `|` characters to avoid YAML parsing errors.

## Keeping Docs in Sync

`src/commands/*.ts` is the single source of truth for all commands, sub-commands, and options.

**When any file in `src/commands/` is modified**, you MUST also update:

1. **`skills/gmgn-{command}/SKILL.md`** — Sub-commands table and Options tables must exactly reflect the current command definitions.
2. **`Readme.md`** — The `## Commands` section bash examples must reflect added/removed commands or options.
3. **`Readme.zh.md`** — Same as Readme.md for the bash examples (Chinese descriptions are maintained separately).
