# gmgn-cli

> 中文文档：[Readme.zh.md](Readme.zh.md)

GMGN AI skills for on-chain operations — token research, market data, wallet analysis, and swap.

---

## Skills

| Skill | Description | Reference |
|-------|-------------|-----------|
| [`/gmgn-token`](skills/gmgn-token/SKILL.md) | Token info, security, pool, holders, traders | [SKILL.md](skills/gmgn-token/SKILL.md) |
| [`/gmgn-market`](skills/gmgn-market/SKILL.md) | K-line market data, trending tokens | [SKILL.md](skills/gmgn-market/SKILL.md) |
| [`/gmgn-portfolio`](skills/gmgn-portfolio/SKILL.md) | Wallet holdings, activity, stats | [SKILL.md](skills/gmgn-portfolio/SKILL.md) |
| [`/gmgn-swap`](skills/gmgn-swap/SKILL.md) | Swap submission + order query | [SKILL.md](skills/gmgn-swap/SKILL.md) |

---

## Usage Examples

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

## Setup

### 0. Prepare

Before applying for an API Key, get two things ready:

**Generate an Ed25519 key pair**

Download and run the [Binance Asymmetric Key Generator](https://github.com/binance/asymmetric-key-generator/releases). You will need the **public key** when filling out the API Key application, and the **private key** in your `.env` later (for swap / order).

**Get your public egress IP** (for the IP whitelist)

```bash
curl ip.me
```

Or visit **https://ip.me** in your browser.

### 1. Get an API Key

Apply at **https://gmgn.ai/ai** — enter the public key and your IP address from the step above.

### 2. Configure

**Option A — Global config (recommended)**

Create `~/.config/gmgn/.env` once — works from any directory:

```bash
mkdir -p ~/.config/gmgn
cat > ~/.config/gmgn/.env << 'EOF'
GMGN_API_KEY=your_api_key_here

# Required for swap / order (private key from step 0):
GMGN_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n<base64>\n-----END PRIVATE KEY-----\n"
EOF
```

**Option B — Project `.env`**

```bash
cp .env.example .env
# Edit .env and fill in your values
```

Config lookup order: `~/.config/gmgn/.env` → project `.env` (project takes precedence).

### 3. CLI Install

Install a pinned version to avoid pulling untrusted updates at runtime:

```bash
npm install -g gmgn-cli@1.0.1
```

Local development:

```bash
npm install
npm run build
node dist/index.js <command> [options]
```

### 4. Connect to Your AI Tool

#### Claude Code

Skills are automatically discovered when the package is installed as a plugin.

#### Cursor

Skills are automatically discovered via the `.cursor-plugin/` configuration.

1. Complete steps 1–3 above
2. Configure credentials in `~/.config/gmgn/.env`
3. Restart Cursor — skills will be available in Agent mode via `/gmgn-*` commands

#### Cline

1. Complete steps 1–3 above
2. In Cline settings → **Skills directory**: point to the installed package's `skills/` folder:
   ```bash
   echo "$(npm root -g)/gmgn-skills/skills"
   ```
3. Configure credentials in `~/.config/gmgn/.env`
4. Restart Cline — `/gmgn-token`, `/gmgn-market`, `/gmgn-portfolio`, `/gmgn-swap` will be available

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
market trending (top 50)  →  AI selects top 5 by multi-factor analysis  →  user reviews  →  token info / token security  →  swap
```

---

## CLI Reference

Full parameter reference: [docs/cli-usage.md](docs/cli-usage.md)

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
  --slippage 0.01

# Query order
npx gmgn-cli order get --chain sol --order-id <order-id>
```

---

## Supported Chains

| Commands | Chains | Chain Currencies |
|----------|--------|-----------------|
| token / market / portfolio | `sol` / `bsc` / `base` | — |
| swap / order | `sol` / `bsc` / `base` | sol: SOL, USDC · bsc: BNB, USDC · base: ETH, USDC |

---

## Output Format

Default: formatted JSON. Use `--raw` for single-line JSON (pipe-friendly):

```bash
npx gmgn-cli token info --chain sol --address <addr> --raw | jq '.price'
```

---

## Security & Disclaimer

**About `GMGN_PRIVATE_KEY`**

`GMGN_PRIVATE_KEY` is a **request-signing key** used to authenticate API calls to the GMGN OpenAPI service. It is not a blockchain wallet private key and does not directly control on-chain assets. If compromised, an attacker could forge authenticated API requests on your behalf — rotate it immediately via the GMGN dashboard if you suspect exposure.

**Best practices**

- Restrict config file permissions: `chmod 600 ~/.config/gmgn/.env`
- Never commit your `.env` file to version control — add it to `.gitignore`
- Do not share `GMGN_API_KEY` or `GMGN_PRIVATE_KEY` in logs, screenshots, or chat messages
- Use a pinned install (`npm install -g gmgn-cli@1.0.1`) rather than `npx gmgn-cli` to avoid executing unintended package updates alongside your credentials

**Disclaimer**

Use of this tool and any financial decisions made based on its output are entirely at your own risk. GMGN is not liable for any trading losses, errors, or unauthorized access resulting from improper credential management.

The npm package is published with provenance attestation, linking each release to a specific git commit and CI pipeline run. Verify with:
```bash
npm audit signatures gmgn-cli
```
