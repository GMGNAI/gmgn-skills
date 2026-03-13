import { Command } from "commander";
import { OpenApiClient } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";

export function registerMarketCommands(program: Command): void {
  const market = program.command("market").description("Market data commands");

  market
    .command("kline")
    .description("Get token K-line (candlestick) data")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .requiredOption("--resolution <resolution>", "Candlestick resolution: 1m / 5m / 15m / 1h / 4h / 1d")
    .requiredOption("--from <timestamp>", "Start time (Unix seconds)", parseInt)
    .requiredOption("--to <timestamp>", "End time (Unix seconds)", parseInt)
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const client = new OpenApiClient(getConfig());
      const data = await client
        .getTokenKline(opts.chain, opts.address, opts.resolution, opts.from * 1000, opts.to * 1000)
        .catch(exitOnError);
      printResult(data, opts.raw);
    });

  market
    .command("trending")
    .description("Get trending token swap data")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--interval <interval>", "Time interval: 1h / 3h / 6h / 24h")
    .option("--limit <n>", "Number of results (default 100, max 100)", parseInt)
    .option("--orderby <field>", "Sort field: score / volume / swaps / liquidity / marketcap / holders / price / change / ...")
    .option("--direction <dir>", "Sort direction: asc / desc")
    .option("--filter <tag...>", "Filter tags, repeatable: has_social / not_risk / not_honeypot / verified / locked / renounced / ...")
    .option("--platform <name...>", "Platform filter, repeatable: pump / moonshot / ...")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const extra: Record<string, string | number | string[]> = {};
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.orderby) extra["order_by"] = opts.orderby;
      if (opts.direction) extra["direction"] = opts.direction;
      if (opts.filter?.length) extra["filters"] = opts.filter;
      if (opts.platform?.length) extra["platforms"] = opts.platform;

      const client = new OpenApiClient(getConfig());
      const data = await client.getTrendingSwaps(opts.chain, opts.interval, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

