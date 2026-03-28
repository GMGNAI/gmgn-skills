<div align="center">

<img src="static/gmgnagentskills.png" alt="GMGN Agent Skills" />

[![X](https://img.shields.io/badge/Follow-%40gmgnai-black?logo=x&logoColor=white)](https://x.com/gmgnai) [![Telegram](https://img.shields.io/badge/Telegram-gmgnagentapi-2CA5E0?logo=telegram&logoColor=white)](https://t.me/gmgnagentapi) [![Discord](https://img.shields.io/badge/Discord-gmgnai-5865F2?logo=discord&logoColor=white)](https://discord.gg/gmgnai)

English | [简体中文](Readme.zh.md)

</div>

## GMGN Agent Skills

With GMGN Agent Skills, you can use AI agents to query real-time trending token rankings across multiple chains, token fundamentals, social media signals, live trading activity, new tokens in Trenches, top holders, top traders, smart money positions, KOL holdings, insider wallets, bundled wallet exposure, and other professional on-chain analytics. It also supports market orders, limit orders, advanced take-profit/stop-loss strategy orders, and wallet management — including real-time holdings, recent P&L, and transaction history — all through natural language.

---

## Skills

| Skill | Description | Reference |
|-------|-------------|-----------|
| [`/gmgn-token`](skills/gmgn-token/SKILL.md) | Token info, security, pool, holders, traders | [SKILL.md](skills/gmgn-token/SKILL.md) |
| [`/gmgn-market`](skills/gmgn-market/SKILL.md) | K-line market data, trending tokens | [SKILL.md](skills/gmgn-market/SKILL.md) |
| [`/gmgn-portfolio`](skills/gmgn-portfolio/SKILL.md) | Wallet holdings, activity, stats | [SKILL.md](skills/gmgn-portfolio/SKILL.md) |
| [`/gmgn-track`](skills/gmgn-track/SKILL.md) | Follow-wallet trades, KOL trades, Smart Money trades | [SKILL.md](skills/gmgn-track/SKILL.md) |
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | Swap submission + order query | [SKILL.md](skills/gmgn-swap/SKILL.md) |

> For detailed CLI commands, parameters, and recommended values, see the [Wiki documentation](https://github.com/GMGNAI/gmgn-skills/wiki).

### Quick Start

> **Note for AI assistants:** If you are an AI Agent helping the user install or configure gmgn-cli, jump directly to [Quick Start (AI Agent)](#quick-start-ai-agent) — it contains all the steps you need to complete, including how to guide the user through API key generation. If the user asks to upgrade, jump to [Upgrade (AI Agent)](#upgrade-ai-agent).

Ready to install? [Jump to Installation →](#1-installation)

Already installed? [Upgrade Skills and CLI →](#9-upgrade-skills-and-cli)

> **Tip:** If your AI agent tries to open or scrape the gmgn.ai website instead of using the CLI, add this to your prompt: `Use gmgn-cli commands. Do not call gmgn.ai web endpoints directly.`

---

## Quick Start (AI Agent)

> The following steps are for AI Agents. Some steps require the user to complete actions in a browser.

**Step 1 — Install CLI and Skills**

```bash
npx skills add GMGNAI/gmgn-skills
```

**Step 2 — Verify with public key (no registration needed)**

```bash
GMGN_API_KEY=gmgn_solbscbaseethmonadtron gmgn-cli market trending --chain sol --interval 1h --limit 3
```

If JSON output appears, the CLI is working.

**Step 3 — Guide user to get their own API key**

Tell the user: "To use your own API key, go to **https://gmgn.ai/ai** and apply. You will need an Ed25519 public key. I can generate a key pair for you — just say the word."

When the user asks, run:

```bash
openssl genpkey -algorithm ed25519 -out /tmp/gmgn_private.pem 2>/dev/null && \
  openssl pkey -in /tmp/gmgn_private.pem -pubout 2>/dev/null
```

Show the **public key** to the user with the following instructions:

> This is your Ed25519 public key. Please complete these two steps:
> 1. Go to **https://gmgn.ai/ai**, paste the public key above into the API Key creation form, and submit.
> 2. Once created, copy the **API Key** shown on the page and send it back to me — I'll handle Step 4 configuration for you.

Wait for the user to reply with their API Key before continuing to Step 4.

**Step 4 — Configure credentials**

After the user receives their API key, write it to the global config:

```bash
mkdir -p ~/.config/gmgn
# Write API key (replace with the actual key the user provides)
echo 'GMGN_API_KEY=<user_api_key>' > ~/.config/gmgn/.env
chmod 600 ~/.config/gmgn/.env
```

If the user also needs swap capability, append the private key:

```bash
# Append private key (use the PEM content from Step 3)
echo 'GMGN_PRIVATE_KEY="<pem_content>"' >> ~/.config/gmgn/.env
```

**Step 5 — Verify**

```bash
gmgn-cli market trending --chain sol --interval 1h --limit 3
```

If output appears without error, setup is complete.

---

## Upgrade (AI Agent)

> Run this command to upgrade both the CLI and Skills to the latest version.

```bash
npx skills add GMGNAI/gmgn-skills
```

Check the installed version after upgrading:

```bash
gmgn-cli --version
```

> For the full upgrade reference, see [Section 9 — Upgrade Skills and CLI](#9-upgrade-skills-and-cli).

---

## Demo Cases

### Trending Token Rankings

Send this prompt to your AI Agent:

```
Fetch Solana 1h trending, filter for pump.fun tokens created within 6h, sort by volume descending.
```

![Trending Token Rankings](static/market-rank-1h-Pumpfun-en.png)

### Real-Time Token Trading Analysis

Send this prompt to your AI Agent:

```
Check the first token's K-line, analyze entry timing, plot price + volume chart, and provide social media links and smart money/KOL trading analysis.
```

![Token Analysis 1](static/market-tokenanalysis-en01.png)
![Token Analysis 2](static/market-tokenanalysis-en02.png)

---

## 1. Installation

> **Prerequisites:** Before installing, create your API Key at **https://gmgn.ai/ai** (see [Section 3](#3-get-your-own-api-key) for the full setup guide).

Choose one of the following methods:

### 1.1 Via Agent (recommended)

Send this to your AI agent:

```bash
npx skills add GMGNAI/gmgn-skills
```

### 1.2 npm Global Install

```bash
npm install -g gmgn-cli
```

### 1.3 Local Development

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

## 2. Verify Connection

Test with the public API key — no registration required:

```bash
GMGN_API_KEY=gmgn_solbscbaseethmonadtron gmgn-cli market trending --chain sol --interval 1h --limit 3
```

If you see JSON output, the CLI is working. The public key supports all read-only commands (token / market / portfolio) and is for testing only — apply for your own API key to use any feature (see step 3).

## 3. Get Your Own API Key

The public key in step 2 is for testing only. Apply for your own API key at **https://gmgn.ai/ai** — required for all actual use (read-only and swap). You will need:

### 3.1 Generate an Ed25519 Key Pair

**Option 1 — Ask your AI agent (recommended)**

Send this prompt to your agent:

```
Generate an Ed25519 key pair for me using OpenSSL and show me:
1. The public key (I need to fill it in the GMGN API Key application form)
2. The private key in PEM format (I need to set it as GMGN_PRIVATE_KEY in my .env)
```

**Option 2 — Binance Key Generator**

Download and run the [Binance Asymmetric Key Generator](https://github.com/binance/asymmetric-key-generator/releases).

Enter the **public key** in the application form.

### 3.2 Get Your Public Egress IP

For the IP whitelist (required when enabling swap capability on your API key):

```bash
curl ip.me
```

## 4. Configure Your API Key

### Option 1: Global config (recommended)

Create `~/.config/gmgn/.env` once — works from any directory:

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here

# Required for swap / order only:
GMGN_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n"
EOF
```

### Option 2: Project `.env`

```bash
cp .env.example .env
# Edit .env and fill in your values
```

Config lookup order: `~/.config/gmgn/.env` → project `.env` (project takes precedence).

## 5. Try in AI Clients

#### OpenClaw

Send the following prompt directly to test the query capabilities:

```
Show me the trending tokens on Solana in the last 1 hour.
```

#### Claude Code

Skills are automatically discovered when the package is installed as a plugin.

#### Cursor

Skills are automatically discovered via the `.cursor-plugin/` configuration.

1. Complete the installation and configuration steps above
2. Restart Cursor — skills will be available in Agent mode via `/gmgn-*` commands

#### Cline

1. Complete the installation and configuration steps above
2. In Cline settings → **Skills directory**: point to the installed package's `skills/` folder:
   ```bash
   echo "$(npm root -g)/gmgn-skills/skills"
   ```
3. Restart Cline — `/gmgn-token`, `/gmgn-market`, `/gmgn-portfolio`, `/gmgn-track`, `/gmgn-swap` will be available

#### Codex CLI

```bash
git clone https://github.com/GMGNAI/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

See [.codex/INSTALL.md](.codex/INSTALL.md) for full instructions.

#### OpenCode

```bash
git clone https://github.com/GMGNAI/gmgn-skills ~/.opencode/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.opencode/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

See [.opencode/INSTALL.md](.opencode/INSTALL.md) for full instructions.

---

## 6. Usage

### Examples

Natural language prompts you can send to any AI assistant with gmgn-cli skills installed:

```
buy 0.1 SOL of <token_address>
sell 50% of <token_address> on BSC
check order status <order_id>
is <token_address> safe to buy on solana?
show top holders of <token_address>
show my wallet holdings on SOL
query token details for 0x1234...
show trading stats for wallet <wallet_address> on BSC
```

### Typical Workflows

**Research a token:**
```
token info  →  token security  →  token pool  →  token holders
```

**Analyze a wallet:**
```
portfolio holdings  →  portfolio stats  →  portfolio activity
```

**Execute a trade:**
```
token info (confirm token)  →  portfolio token-balance (check funds)  →  swap  →  order get (poll status)
```

**Discover trading opportunities via trending:**
```
market trending (top 50)  →  AI selects top 5 by multi-factor analysis  →  user reviews  →  token info / token security  →  swap
```

---

## 7. Workflow Docs

Step-by-step guides for common analysis tasks:

| Workflow | When to use |
|----------|-------------|
| [workflow-token-research.md](docs/workflow-token-research.md) | Pre-buy token due diligence (address → buy/watch/skip) |
| [workflow-project-deep-report.md](docs/workflow-project-deep-report.md) | Comprehensive project analysis with scored dimensions and full written report |
| [workflow-wallet-analysis.md](docs/workflow-wallet-analysis.md) | Wallet quality assessment (address → follow/skip) |
| [workflow-smart-money-profile.md](docs/workflow-smart-money-profile.md) | Trading style analysis, copy-trade ROI estimate, smart money leaderboard |
| [workflow-risk-warning.md](docs/workflow-risk-warning.md) | Active risk monitoring for held positions (whale exit, liquidity, dev dump) |
| [workflow-early-project-screening.md](docs/workflow-early-project-screening.md) | Screen newly launched launchpad tokens for smart money entry |
| [workflow-daily-brief.md](docs/workflow-daily-brief.md) | Daily market overview: trending + smart money moves + early watch + risk scan |
| [workflow-market-opportunities.md](docs/workflow-market-opportunities.md) | Discover trading opportunities from trending data |
| [workflow-token-due-diligence.md](docs/workflow-token-due-diligence.md) | 4-step token due diligence checklist |

## 8. CLI Reference

Full parameter reference: [docs/cli-usage.md](docs/cli-usage.md). All commands support `--raw` for single-line JSON output (pipe-friendly, e.g. `| jq '.price'`).

### Token

```bash
npx gmgn-cli token info --chain sol --address <addr>
```

### Market

```bash
npx gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --order-by volume --limit 20 \
  --filter not_risk --filter not_honeypot

npx gmgn-cli market trenches \
  --chain sol \
  --type new_creation --type near_completion --type completed \
  --launchpad-platform Pump.fun --launchpad-platform pump_mayhem --launchpad-platform letsbonk \
  --limit 80
```

### Portfolio

```bash
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>
```

### Track

```bash
# Follow-wallet trade records (requires GMGN_PRIVATE_KEY)
npx gmgn-cli track follow-wallet --chain sol
npx gmgn-cli track follow-wallet --chain sol --wallet <wallet_address> --side buy

# KOL trade records
npx gmgn-cli track kol --limit 100 --raw
npx gmgn-cli track kol --chain sol --side buy --limit 50 --raw

# Smart Money trade records
npx gmgn-cli track smartmoney --limit 100 --raw
npx gmgn-cli track smartmoney --chain sol --side sell --limit 50 --raw
```

### Swap (requires private key)

```bash
# Submit swap with fixed slippage
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --slippage 0.01

# Submit swap with automatic slippage
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <input-token-addr> \
  --output-token <output-token-addr> \
  --amount 1000000 \
  --auto-slippage

# Query order
npx gmgn-cli order get --chain sol --order-id <order-id>
```

## 8. Supported Chains

| Commands | Chains | Chain Currencies |
|----------|--------|-----------------|
| token / market / portfolio / track | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL, USDC · bsc: BNB, USDC · base: ETH, USDC |

---

## 9. Upgrade Skills and CLI

```bash
# Upgrade CLI and Skills
npx skills add GMGNAI/gmgn-skills

# Check current version
gmgn-cli --version
```

> **Via AI Agent:** Tell your agent — "Upgrade gmgn-cli and the skills to the latest version." See also [Upgrade (AI Agent)](#upgrade-ai-agent).

---

## 10. Security & Disclaimer (Read Before Use)

This tool can be invoked by an AI Agent to submit real on-chain transactions automatically. It carries inherent risks including model hallucination, uncontrolled execution, and prompt injection. Once authorized, the AI Agent will submit transactions on behalf of your linked wallet address — **on-chain transactions are irreversible once confirmed** and may result in financial loss. Use with caution.

**About `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` is a **request-signing key** used to authenticate API calls to the GMGN OpenAPI service. It is not a blockchain wallet private key and does not directly control on-chain assets. If compromised, an attacker could forge authenticated API requests on your behalf — rotate it immediately via the GMGN dashboard if you suspect exposure.

**Best practices**

- Restrict config file permissions: `chmod 600 ~/.config/gmgn/.env`
- Never commit your `.env` file to version control — add it to `.gitignore`
- Do not share `GMGN_API_KEY` or `GMGN_PRIVATE_KEY` in logs, screenshots, or chat messages
- Before every swap, carefully review the trade summary presented by the AI (chain, wallet, token addresses, amount) and confirm only when it matches your intent
- Test with small amounts first before executing larger trades
- Always use the latest version of gmgn-cli (`npm install -g gmgn-cli`). To check your current version: `gmgn-cli --version`

**Disclaimer**

Use of this tool and any financial decisions made based on its output are entirely at your own risk. GMGN is not liable for any trading losses, errors, or unauthorized access resulting from model hallucination, prompt injection, improper credential management, or user confirmation errors. By using this tool, you acknowledge that you have fully understood the above risks and voluntarily accept all responsibility.

The npm package is published with provenance attestation, linking each release to a specific git commit and CI pipeline run. Verify with:
```bash
npm audit signatures gmgn-cli
```
