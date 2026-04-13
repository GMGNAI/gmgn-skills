import { Command } from "commander";
import { OpenApiClient } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateChain } from "../validate.js";

export function registerTrackCommands(program: Command): void {
  const track = program.command("track").description("On-chain tracking commands: follow-wallet trades, KOL trades, Smart Money trades");

  track
    .command("follow-wallet")
    .description("Get follow-wallet trade records")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .option("--wallet <address>", "Filter by wallet address")
    .option("--limit <n>", "Page size (1–100, default 10)", parseInt)
    .option("--side <side>", "Trade direction filter: buy / sell")
    .option("--filter <tag...>", "Filter conditions, repeatable")
    .option("--min-amount-usd <n>", "Minimum trade amount (USD)", parseFloat)
    .option("--max-amount-usd <n>", "Maximum trade amount (USD)", parseFloat)
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const extra: Record<string, string | number | string[]> = {};
      if (opts.wallet) extra["wallet_address"] = opts.wallet;
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.side) extra["side"] = opts.side;
      if (opts.filter?.length) extra["filters"] = opts.filter;
      if (opts.minAmountUsd != null) extra["min_amount_usd"] = opts.minAmountUsd;
      if (opts.maxAmountUsd != null) extra["max_amount_usd"] = opts.maxAmountUsd;
      const client = new OpenApiClient(getConfig());
      const data = await client.getFollowWallet(opts.chain, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  track
    .command("kol")
    .description("Get KOL trade records")
    .option("--chain <chain>", "Chain: sol / bsc / base")
    .option("--limit <n>", "Page size (1–200, default 100)", parseInt)
    .option("--side <side>", "Filter by trade direction: buy / sell (client-side filter)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (opts.chain) validateChain(opts.chain);
      const client = new OpenApiClient(getConfig());
      const data = await client.getKol(opts.chain, opts.limit).catch(exitOnError) as { list?: { side: string }[] };
      if (opts.side && data?.list) {
        data.list = data.list.filter((item) => item.side === opts.side);
      }
      printResult(data, opts.raw);
    });

  track
    .command("smartmoney")
    .description("Get Smart Money trade records")
    .option("--chain <chain>", "Chain: sol / bsc / base")
    .option("--limit <n>", "Page size (1–200, default 100)", parseInt)
    .option("--side <side>", "Filter by trade direction: buy / sell (client-side filter)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (opts.chain) validateChain(opts.chain);
      const client = new OpenApiClient(getConfig());
      const data = await client.getSmartMoney(opts.chain, opts.limit).catch(exitOnError) as { list?: { side: string }[] };
      if (opts.side && data?.list) {
        data.list = data.list.filter((item) => item.side === opts.side);
      }
      printResult(data, opts.raw);
    });
}
