import { Command } from "commander";
import { OpenApiClient } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateAddress, validateChain } from "../validate.js";

export function registerPortfolioCommands(program: Command): void {
  const portfolio = program.command("portfolio").description("Wallet portfolio commands");

  portfolio
    .command("holdings")
    .description("Get wallet token holdings")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--wallet <address>", "Wallet address")
    .option("--limit <n>", "Page size (default 20, max 50)", parseInt, 20)
    .option("--cursor <cursor>", "Pagination cursor")
    .option("--order-by <field>", "Sort field: usd_value / last_active_timestamp / realized_profit / unrealized_profit / total_profit / history_bought_cost / history_sold_income", "usd_value")
    .option("--direction <dir>", "Sort direction: asc / desc", "desc")
    .option("--interval <interval>", "Stats interval (default 24h)")
    .option("--sell-out", "Include sold-out positions")
    .option("--show-small", "Include small-value positions")
    .option("--hide-abnormal", "Hide abnormal positions")
    .option("--hide-airdrop", "Hide airdrop positions")
    .option("--hide-closed", "Hide closed positions")
    .option("--hide-open", "Hide open positions")
    .option("--tx30d", "Only show positions with trades in last 30 days")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.wallet, opts.chain, "--wallet");
      const extra: Record<string, string | number> = {};
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.cursor) extra["cursor"] = opts.cursor;
      if (opts.orderBy) extra["order_by"] = opts.orderBy;
      if (opts.direction) extra["direction"] = opts.direction;
      if (opts.interval) extra["interval"] = opts.interval;
      if (opts.sellOut) extra["sell_out"] = "true";
      if (opts.showSmall) extra["show_small"] = "true";
      if (opts.hideAbnormal) extra["hide_abnormal"] = "true";
      if (opts.hideAirdrop) extra["hide_airdrop"] = "true";
      if (opts.hideClosed) extra["hide_closed"] = "true";
      if (opts.hideOpen) extra["hide_open"] = "true";
      if (opts.tx30d) extra["tx30d"] = "true";

      const client = new OpenApiClient(getConfig());
      const data = await client.getWalletHoldings(opts.chain, opts.wallet, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  portfolio
    .command("activity")
    .description("Get wallet transaction activity")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--wallet <address>", "Wallet address")
    .option("--token <address>", "Filter by token contract address")
    .option("--limit <n>", "Page size", parseInt)
    .option("--cursor <cursor>", "Pagination cursor")
    .option("--type <type...>", "Activity type filter, repeatable: buy / sell / add / remove / transfer")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.wallet, opts.chain, "--wallet");
      if (opts.token) validateAddress(opts.token, opts.chain, "--token");
      const extra: Record<string, string | number | string[]> = {};
      if (opts.token) extra["token"] = opts.token;
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.cursor) extra["cursor"] = opts.cursor;
      if (opts.type?.length) extra["type"] = opts.type;

      const client = new OpenApiClient(getConfig());
      const data = await client.getWalletActivity(opts.chain, opts.wallet, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  portfolio
    .command("stats")
    .description("Get wallet trading statistics (supports multiple wallets)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--wallet <address...>", "Wallet address(es), repeatable")
    .option("--period <period>", "Stats period: 7d / 30d", "7d")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      for (const w of opts.wallet as string[]) validateAddress(w, opts.chain, "--wallet");
      const client = new OpenApiClient(getConfig());
      const data = await client.getWalletStats(opts.chain, opts.wallet, opts.period).catch(exitOnError);
      printResult(data, opts.raw);
    });

  portfolio
    .command("info")
    .description("Get wallets and main currency balances bound to the API Key")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const client = new OpenApiClient(getConfig());
      const data = await client.getUserInfo().catch(exitOnError);
      printResult(data, opts.raw);
    });

  portfolio
    .command("token-balance")
    .description("Get wallet token balance for a single token")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--wallet <address>", "Wallet address")
    .requiredOption("--token <address>", "Token contract address")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.wallet, opts.chain, "--wallet");
      validateAddress(opts.token, opts.chain, "--token");
      const client = new OpenApiClient(getConfig());
      const data = await client.getWalletTokenBalance(opts.chain, opts.wallet, opts.token).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

