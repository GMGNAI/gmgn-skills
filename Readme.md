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
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | Swap submission + order query | [SKILL.md](skills/gmgn-swap/SKILL.md) |

> For detailed CLI commands, parameters, and recommended values, see the [Wiki documentation](https://github.com/GMGNAI/gmgn-skills/wiki).

### Quick Start

Ready to install skills? [Jump to Installation →](#get-started)

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

## Get Started

Before installing, create your API Key at **https://gmgn.ai/ai**. The API key is used for:

1. Read data: tokens, trending lists, K-line, and featured on-chain metrics
2. Submit trades: market orders, limit orders, strategy orders, and more

---

## 1. Installation

Choose one of the following methods:

### 1.1 Via Agent (recommended)

Send this to your AI agent:

```bash
npx skills add GMGNAI/gmgn-skills
```

### 1.2 npm Global Install

```bash
npm install -g gmgn-cli@1.1.0
```

### 1.3 Local Development

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

## 2. Verify Connection

### Option 1: Via AI Agent

Send this prompt to your AI Agent:

```
Run this CLI command: GMGN_API_KEY=gmgn_solbscbaseethmonadtron npx gmgn-cli market trending --chain sol --interval 1h --limit 3
```

### Option 2: Via CLI

Test with the public API key — no registration required:

```bash
GMGN_API_KEY=gmgn_solbscbaseethmonadtron gmgn-cli market trending --chain sol --interval 1h --limit 3
```

If you see JSON output, the CLI is working. The public key supports all read-only commands (token / market / portfolio). The public key is for testing only — apply for your own API key to use any feature (see step 3).

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
3. Restart Cline — `/gmgn-token`, `/gmgn-market`, `/gmgn-portfolio`, `/gmgn-swap` will be available

#### Codex CLI

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

See [.codex/INSTALL.md](.codex/INSTALL.md) for full instructions.

#### OpenCode

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.opencode/gmgn-cli
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

## 7. CLI Reference

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
```

### Portfolio

```bash
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>
```

### Swap (requires private key)

```bash
# Submit swap
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
| token / market / portfolio | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL, USDC · bsc: BNB, USDC · base: ETH, USDC |

---

## 9. Security & Disclaimer

**About `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` is a **request-signing key** used to authenticate API calls to the GMGN OpenAPI service. It is not a blockchain wallet private key and does not directly control on-chain assets. If compromised, an attacker could forge authenticated API requests on your behalf — rotate it immediately via the GMGN dashboard if you suspect exposure.

**Best practices**

- Restrict config file permissions: `chmod 600 ~/.config/gmgn/.env`
- Never commit your `.env` file to version control — add it to `.gitignore`
- Do not share `GMGN_API_KEY` or `GMGN_PRIVATE_KEY` in logs, screenshots, or chat messages
- Use a pinned install (`npm install -g gmgn-cli@1.1.0`) rather than `npx gmgn-cli` to avoid executing unintended package updates alongside your credentials

**Disclaimer**

Use of this tool and any financial decisions made based on its output are entirely at your own risk. GMGN is not liable for any trading losses, errors, or unauthorized access resulting from improper credential management.

The npm package is published with provenance attestation, linking each release to a specific git commit and CI pipeline run. Verify with:
```bash
npm audit signatures gmgn-cli
```
