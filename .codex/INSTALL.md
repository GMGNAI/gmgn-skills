# Installing gmgn-cli Skills for Codex

Enable GMGN skills in Codex via native skill discovery. Just clone and symlink.

## Prerequisites

- Git
- GMGN API Key from [gmgn.ai/settings/api](https://gmgn.ai/ai)

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/gmgn-ai/gmgn-skills ~/.codex/gmgn-cli
   ```

2. **Create the skills symlink:**

   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/gmgn-cli/skills ~/.agents/skills/gmgn-cli
   ```

   **Windows (PowerShell):**

   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\gmgn-cli" "$env:USERPROFILE\.codex\gmgn-cli\skills"
   ```

3. **Configure credentials:**

   ```bash
   cp ~/.codex/gmgn-cli/.env.example ~/.codex/gmgn-cli/.env
   # Edit .env and set GMGN_API_KEY
   ```

4. **Restart Codex** to discover the skills.

## Verify

```bash
ls -la ~/.agents/skills/gmgn-cli
```

You should see four skill directories: `gmgn-token`, `gmgn-market`, `gmgn-portfolio`, `gmgn-swap`.

## Available Skills

| Skill | When to Use |
|-------|-------------|
| `gmgn-token` | Token info, security, pool, top holders, top traders |
| `gmgn-market` | K-line / candlestick market data |
| `gmgn-portfolio` | Wallet holdings, activity, trading stats, token balance |
| `gmgn-swap` | Swap execution + order status query (requires private key) |

## Updating

```bash
cd ~/.codex/gmgn-cli && git pull
```

## Uninstalling

```bash
rm ~/.agents/skills/gmgn-cli
rm -rf ~/.codex/gmgn-cli   # optional
```
