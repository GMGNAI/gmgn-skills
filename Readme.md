# gmgn-cli

> 中文文档：[Readme.zh.md](Readme.zh.md)

GMGN OpenAPI command-line tool — market data, token info, wallet portfolio, and swap.

---

## Quick Start

### 0. Get an API Key

Apply at: **https://gmgn.ai/ai**

### 1. Configure

**Option A — Global config (recommended for AI skills / global install)**

Create `~/.config/gmgn/.env` once — works from any directory:

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here

# Required for swap / order:
GMGN_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n"
EOF
```

**Option B — Project `.env`**

```bash
cp .env.example .env
# Edit .env and fill in your values
```

Config lookup order: `~/.config/gmgn/.env` → project `.env` (project takes precedence).

### 2. Run

One-time run (no install required):

```bash
npx gmgn-cli <command> [options]
```

Global install:

```bash
npm install -g gmgn-cli
gmgn-cli <command> [options]
```

Local development:

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

---

## Commands

### Token

```bash
# Basic info + realtime price
npx gmgn-cli token info --chain sol --address <addr>

# Security metrics
npx gmgn-cli token security --chain sol --address <addr>

# Liquidity pool
npx gmgn-cli token pool --chain sol --address <addr>

# Top holders
npx gmgn-cli token holders --chain sol --address <addr>

# Top traders
npx gmgn-cli token traders --chain sol --address <addr>
```

### Market

```bash
# K-line data
npx gmgn-cli market kline \
  --chain sol \
  --address <addr> \
  --resolution 1m \
  --from 1700000000 \
  --to 1700003600

# Trending tokens (top by volume, last 1h, safe only)
npx gmgn-cli market trending \
  --chain sol \
  --interval 1h \
  --orderby volume --limit 20 \
  --filter not_risk --filter not_honeypot
```

Resolutions: `1m` / `5m` / `15m` / `1h` / `4h` / `1d`

### Portfolio

```bash
# Wallet holdings (defaults: limit=20, order-by=usd_value, direction=desc)
npx gmgn-cli portfolio holdings --chain sol --wallet <addr>

# Override defaults
npx gmgn-cli portfolio holdings --chain sol --wallet <addr> \
  --limit 50 --order-by unrealized_profit --direction asc

# Transaction activity
npx gmgn-cli portfolio activity --chain sol --wallet <addr>

# Trading stats
npx gmgn-cli portfolio stats --chain sol --wallet <addr>

# Token balance
npx gmgn-cli portfolio token-balance \
  --chain sol --wallet <addr> --token <token_addr>
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
  --slippage 0.01

# Sell 50% of a token (input_token must not be a currency)
npx gmgn-cli swap \
  --chain sol \
  --from <wallet-address> \
  --input-token <token-addr> \
  --output-token <sol-or-usdc-addr> \
  --percent 50

# Query order
npx gmgn-cli order get --chain sol --order-id <order-id>
```

---

## Typical Workflows

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
market trending (top 50, score-ranked)  →  AI selects top 5 by multi-factor analysis  →  user reviews  →  token info / token security  →  swap
```

---

## Output Format

Default: formatted JSON. Use `--raw` for single-line JSON (pipe-friendly):

```bash
npx gmgn-cli token info --chain sol --address <addr> --raw | jq '.price'
```

---

## Supported Chains

| Commands | Chains | Chain Currencies |
|----------|--------|-----------------|
| token / market / portfolio | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL, USDC · bsc: BNB, USDC · base: ETH, USDC |

---

## AI Skills

This project includes skills for AI coding assistants at `skills/` in the package root.

| Skill | Description |
|-------|-------------|
| `/gmgn-token` | Token info, security, pool, holders, traders |
| `/gmgn-market` | K-line market data |
| `/gmgn-portfolio` | Wallet holdings, activity, stats |
| `/gmgn-swap` | Swap submission + order query |

### Claude Code

Skills are automatically discovered when the package is installed as a plugin.

### Cursor

Skills are automatically discovered via the `.cursor-plugin/` configuration when the package is installed.

### Codex CLI

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.codex/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

See [.codex/INSTALL.md](.codex/INSTALL.md) for full instructions.

### OpenCode

```bash
git clone https://github.com/gmgn-ai/gmgn-skills ~/.opencode/gmgn-cli
mkdir -p ~/.agents/skills
ln -s ~/.opencode/gmgn-cli/skills ~/.agents/skills/gmgn-cli
```

See [.opencode/INSTALL.md](.opencode/INSTALL.md) for full instructions.

### Cline

Install this package and configure `skills/` as the skills directory in your Cline settings.

### Usage Examples

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

---

## Security & Disclaimer

- Never commit your `.env` file or private key to version control — add them to `.gitignore`
- Keep your `GMGN_API_KEY` and private key confidential; do not share them in logs, screenshots, or chat messages
- The private key used for swap/order must correspond to the wallet bound to your API Key
- **Use of this tool and any financial decisions made based on its output are entirely at your own risk. GMGN is not liable for any trading losses, errors, or unauthorized access resulting from improper credential management.**

---

## Detailed Docs

Full parameter reference: [docs/cli-usage.md](docs/cli-usage.md)
