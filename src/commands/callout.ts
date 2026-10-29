import { Command } from "commander";
import { OpenApiClient, type CalloutGlobalExtra, type CalloutRecordExtra } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateCalloutChains, validateCalloutLimit, validateNonNegativeDecimal } from "../validate.js";

const CALLOUT_CHAIN_HELP =
  "sol / bsc / eth / base / megaeth / hyperevm / tron / monad / xlayer / robinhood / arbitrum / arc / stable / avalanche";

export function registerCalloutCommands(program: Command): void {
  const callout = program.command("callout").description("Call-out (喊单) read commands: one wallet's call-out history, global call-out feed");

  callout
    .command("record")
    .description("Get the call-out history on one wallet over the last 30 days, newest first")
    .requiredOption("--chain <chain>", `Chain: ${CALLOUT_CHAIN_HELP}`)
    .requiredOption("--wallet <address>", "Call-out wallet address")
    .option("--token <address>", "Only call-outs on this token")
    .option("--limit <n>", "Page size (0–50, 0 = server default)", parseInt)
    .option("--page-token <token>", "next_page_token from the previous page (valid 24h)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const [chain] = validateCalloutChains([opts.chain]);
      const extra: CalloutRecordExtra = {};
      if (opts.token) extra.call_token = opts.token;
      if (opts.limit != null) {
        validateCalloutLimit(opts.limit);
        extra.limit = opts.limit;
      }
      if (opts.pageToken) extra.page_token = opts.pageToken;
      const client = new OpenApiClient(getConfig());
      const data = await client.getCalloutRecord(chain, opts.wallet, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  callout
    .command("global")
    .description("Get the global call-out feed across one or more chains, newest first")
    .requiredOption("--chain <chain...>", `Chains, repeatable (1–20): ${CALLOUT_CHAIN_HELP}`)
    .option("--limit <n>", "Page size (0–50, 0 = server default); filtered pages may return more", parseInt)
    .option("--page-token <token>", "next_page_token from the previous page (valid 24h)")
    .option("--only-kol", "Only call-outs from KOL wallets")
    .option("--only-declaration", "Only paid declarations")
    .option("--only-safe", "Only tokens whose security state is safe")
    .option("--min-holding-usd <usd>", "Minimum current holding of the caller in USD (inclusive)")
    .option("--max-holding-usd <usd>", "Maximum current holding of the caller in USD (inclusive)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const chains = validateCalloutChains(opts.chain);
      const extra: CalloutGlobalExtra = {};
      if (opts.limit != null) {
        validateCalloutLimit(opts.limit);
        extra.limit = opts.limit;
      }
      if (opts.pageToken) extra.page_token = opts.pageToken;
      if (opts.onlyKol) extra.only_kol = true;
      if (opts.onlyDeclaration) extra.only_declaration = true;
      if (opts.onlySafe) extra.only_safe = true;
      if (opts.minHoldingUsd != null) {
        validateNonNegativeDecimal(opts.minHoldingUsd, "--min-holding-usd");
        extra.min_holding_usd = opts.minHoldingUsd;
      }
      if (opts.maxHoldingUsd != null) {
        validateNonNegativeDecimal(opts.maxHoldingUsd, "--max-holding-usd");
        extra.max_holding_usd = opts.maxHoldingUsd;
      }
      if (extra.min_holding_usd != null && extra.max_holding_usd != null
          && Number(extra.min_holding_usd) > Number(extra.max_holding_usd)) {
        console.error("[gmgn-cli] Invalid holding range: --min-holding-usd is greater than --max-holding-usd.");
        process.exit(1);
      }
      const client = new OpenApiClient(getConfig());
      const data = await client.getCalloutGlobal(chains, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });
}
