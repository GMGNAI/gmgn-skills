# Discover Trading Opportunities via Trending — Workflow

Use this workflow to surface high-potential tokens from trending data.

## Step 1 — Fetch trending data

Fetch a broad pool with safe filters:

```bash
gmgn-cli market trending \
  --chain <chain> --interval 1h \
  --order-by volume --limit 50 \
  --filter not_honeypot --filter has_social --raw
```

## Step 2 — AI multi-factor analysis

Analyze each record in the response using the following signals (apply judgment, not rigid rules):

| Signal | Field(s) | Weight | Notes |
|--------|----------|--------|-------|
| Smart money interest | `smart_degen_count`, `renowned_count` | High | Key conviction indicator |
| Bluechip ownership | `bluechip_owner_percentage` | Medium | Quality of holder base |
| Real trading activity | `volume`, `swaps` | Medium | Distinguishes genuine interest from wash trading |
| Price momentum | `change1h`, `change5m` | Medium | Prefer positive, non-parabolic moves |
| Pool safety | `liquidity` | Medium | Low liquidity = high slippage risk |
| Token maturity | `creation_timestamp` | Low | Avoid tokens less than ~1h old unless other signals are very strong |

Select the **top 5** tokens with the best composite profile. Prefer tokens that perform well across multiple signals rather than excelling in just one.

## Step 3 — Present top 5 to user

Present results as a concise table, then give a one-line rationale for each pick:

```
Top 5 Trending Tokens — SOL / 1h

# | Symbol | Address (short) | Smart Degens | Volume | 1h Chg | Reasoning
1 | ...     | ...             | ...          | ...    | ...    | Smart money accumulating + high volume
2 | ...
...
```

## Step 4 — Follow-up actions

For each token, offer:
- **Deep dive**: run full token research workflow — see [workflow-token-research.md](workflow-token-research.md)
- **Swap**: execute directly if the user is satisfied with the trending data alone
