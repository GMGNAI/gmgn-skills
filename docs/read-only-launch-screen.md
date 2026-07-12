# Read-only new-launch screen

`scripts/scan-new-launches.ps1` is a PowerShell research workflow for screening newly created Solana launchpad tokens. It is intentionally **read-only**: it calls only `market trenches`, `token info`, `token security`, and `token holders`. It never calls `swap`, `multi-swap`, `order`, or `cooking`.

The script is a screening aid, not investment advice or a trade signal. A passing token is labelled `research_watchlist_only`; the script does not submit or prepare transactions.

## Prerequisites

Build the local CLI from the repository root:

```powershell
npm ci
npm run build
```

For read-only testing, use GMGN's documented public demo key with `-UseDemoKey`. For personal use, set `GMGN_API_KEY` in the shell or configured GMGN environment instead. Do not store private keys in the script.

## Run

```powershell
# Strict live screen; prints JSON to stdout
.\scripts\scan-new-launches.ps1 -Mode strict -UseDemoKey

# Inspect a specific Solana token through the second-stage checks
.\scripts\scan-new-launches.ps1 -Mode strict -UseDemoKey `
  -InspectAddress <solana_token_address>

# Optionally preserve a point-in-time JSON artifact locally
.\scripts\scan-new-launches.ps1 -Mode strict -UseDemoKey `
  -OutputPath .\launch-screen.json
```

## What it checks

Stage one fetches `market trenches --type new_creation --filter-preset safe`, then records a reason for every rejection. The strict profile requires:

| Signal | Threshold |
|---|---:|
| Liquidity | at least $25,000 |
| Holders | at least 100 |
| Smart-money wallets | at least 5 |
| Dev-team holding | at most 5% |
| Top-10 concentration | at most 25% |
| Rat-trader / bundler trade rate | at most 10% |
| Creator token count | at most 100 |

The `exploratory` profile has lower thresholds solely to observe newer and thinner markets. It still does not issue a buy recommendation.

Stage two only runs for stage-one survivors, or for the explicit `-InspectAddress`. It checks mint and freeze authority, taxes, and holder distribution. Liquidity-pool accounts are excluded from non-pool holder concentration calculations; risk tags such as `bundler`, `rat_trader`, and `sandwich_bot` in the top holders cause a monitor/reject disposition.

## Output and benchmark

The JSON output includes:

- all first-stage results and rejection reasons;
- second-stage findings and a `research_watchlist_only` or `reject_or_monitor_only` disposition;
- a `benchmark` section with every CLI command, response size, exit code, and end-to-end duration in milliseconds.

Timing includes local Node CLI startup and the GMGN API request. Market data changes quickly, so any result is a point-in-time research snapshot.
