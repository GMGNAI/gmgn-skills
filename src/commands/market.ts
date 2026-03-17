import { Command } from "commander";
import { OpenApiClient } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateAddress, validateChain } from "../validate.js";

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
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
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
    .option("--order-by <field>", "Sort field: default / volume / swaps / marketcap / holder_count / price / change1h / ... (see docs for full list)")
    .option("--direction <dir>", "Sort direction: asc / desc")
    .option("--filter <tag...>", "Filter tags, repeatable. sol: renounced / frozen / has_social / not_wash_trading / ... evm: not_honeypot / verified / renounced / locked / ... (see docs for full list)")
    .option("--platform <name...>", "Platform filter, repeatable. sol: Pump.fun / letsbonk / moonshot_app / ... bsc: fourmeme / flap / clanker / ... base: clanker / flaunch / zora / ... (see docs for full list)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const extra: Record<string, string | number | string[]> = {};
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.orderBy) extra["order_by"] = opts.orderBy;
      if (opts.direction) extra["direction"] = opts.direction;
      if (opts.filter?.length) extra["filters"] = opts.filter;
      if (opts.platform?.length) extra["platforms"] = opts.platform;

      const client = new OpenApiClient(getConfig());
      const data = await client.getTrendingSwaps(opts.chain, opts.interval, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

