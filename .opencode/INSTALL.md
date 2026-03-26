# Installing gmgn-cli Skills for OpenCode

Enable GMGN skills in OpenCode via native skill discovery. Just clone and symlink.

## Prerequisites

- Git
- GMGN API Key from [gmgn.ai/settings/api](https://gmgn.ai/ai)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/GMGNAI/gmgn-skills ~/.opencode/gmgn-cli
   ```

2. **Register the plugin:**

   ```bash
   mkdir -p ~/.opencode/plugins
   ln -s ~/.opencode/gmgn-cli ~/.opencode/plugins/gmgn-cli
   ```

3. **Link the skills:**

   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.opencode/gmgn-cli/skills ~/.agents/skills/gmgn-cli
   ```

4. **Configure credentials:**

   ```bash
   cp ~/.opencode/gmgn-cli/.env.example ~/.opencode/gmgn-cli/.env
   # Edit .env and set GMGN_API_KEY
   ```

5. **Restart OpenCode** to discover the skills.

## Verify

After restarting, ask OpenCode: *"What GMGN skills are available?"* — it should list the four skills.

## Available Skills

| Skill | When to Use |
|-------|-------------|
| `gmgn-token` | Token info, security, pool, top holders, top traders |
| `gmgn-market` | K-line / candlestick market data |
| `gmgn-portfolio` | Wallet holdings, activity, trading stats, token balance |
| `gmgn-swap` | Swap execution + order status query (requires private key) |

## Updating

```bash
cd ~/.opencode/gmgn-cli && git pull
```

## Uninstalling

```bash
rm ~/.agents/skills/gmgn-cli
rm ~/.opencode/plugins/gmgn-cli
rm -rf ~/.opencode/gmgn-cli   # optional
```
