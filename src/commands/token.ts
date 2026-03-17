import { Command } from "commander";
import { OpenApiClient } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateAddress, validateChain } from "../validate.js";

export function registerTokenCommands(program: Command): void {
  const token = program.command("token").description("Token information commands");

  token
    .command("info")
    .description("Get token basic information and realtime price")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
      const client = new OpenApiClient(getConfig());
      const data = await client.getTokenInfo(opts.chain, opts.address).catch(exitOnError);
      printResult(data, opts.raw);
    });

  token
    .command("security")
    .description("Get token security metrics")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
      const client = new OpenApiClient(getConfig());
      const data = await client.getTokenSecurity(opts.chain, opts.address).catch(exitOnError);
      printResult(data, opts.raw);
    });

  token
    .command("pool")
    .description("Get token liquidity pool information")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
      const client = new OpenApiClient(getConfig());
      const data = await client.getTokenPoolInfo(opts.chain, opts.address).catch(exitOnError);
      printResult(data, opts.raw);
    });

  token
    .command("holders")
    .description("Get top token holders")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .option("--limit <n>", "Number of results (default 20, max 100)", parseInt)
    .option("--order-by <field>", "Sort field: amount_percentage / profit / unrealized_profit / buy_volume_cur / sell_volume_cur", "amount_percentage")
    .option("--direction <dir>", "Sort direction: asc / desc", "desc")
    .option("--tag <tag>", "Wallet tag filter: renowned / smart_degen", "renowned")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
      const extra: Record<string, string | number> = {};
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.orderBy) extra["order_by"] = opts.orderBy;
      if (opts.direction) extra["direction"] = opts.direction;
      if (opts.tag) extra["tag"] = opts.tag;
      const client = new OpenApiClient(getConfig());
      const data = await client.getTokenTopHolders(opts.chain, opts.address, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  token
    .command("traders")
    .description("Get top token traders")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .option("--limit <n>", "Number of results (default 20, max 100)", parseInt)
    .option("--order-by <field>", "Sort field: amount_percentage / profit / unrealized_profit / buy_volume_cur / sell_volume_cur", "amount_percentage")
    .option("--direction <dir>", "Sort direction: asc / desc", "desc")
    .option("--tag <tag>", "Wallet tag filter: renowned / smart_degen", "renowned")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
      const extra: Record<string, string | number> = {};
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.orderBy) extra["order_by"] = opts.orderBy;
      if (opts.direction) extra["direction"] = opts.direction;
      if (opts.tag) extra["tag"] = opts.tag;
      const client = new OpenApiClient(getConfig());
      const data = await client.getTokenTopTraders(opts.chain, opts.address, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

