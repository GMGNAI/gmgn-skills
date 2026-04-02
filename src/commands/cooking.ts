import { Command } from "commander";
import { OpenApiClient, CreateTokenParams } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateChain } from "../validate.js";

export function registerCookingCommands(program: Command): void {
  const cooking = program.command("cooking").description("Token creation and launchpad commands");

  cooking
    .command("stats")
    .description("Get token creation statistics by launchpad (normal auth)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const client = new OpenApiClient(getConfig());
      const data = await client.getCookingStatistics().catch(exitOnError);
      printResult(data, opts.raw);
    });

  cooking
    .command("create")
    .description("Create a token on a launchpad platform (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / ton")
    .requiredOption("--dex <dex>", "Launchpad: pump / raydium / pancakeswap / flap / fourmeme / bonk / bags / ...")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--name <name>", "Token name")
    .requiredOption("--symbol <symbol>", "Token symbol")
    .requiredOption("--buy-amt <amount>", "Initial buy amount in native token (e.g. 0.01 SOL)")
    .option("--image <base64>", "Token logo as base64-encoded data (max 2MB decoded)")
    .option("--image-url <url>", "Token logo URL")
    .option("--website <url>", "Website URL")
    .option("--twitter <url>", "Twitter link")
    .option("--telegram <url>", "Telegram link")
    .option("--slippage <n>", "Slippage tolerance (e.g. 0.01 = 1%)", parseFloat)
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--priority-fee <sol>", "Priority fee in SOL (SOL only)")
    .option("--tip-fee <amount>", "Tip fee")
    .option("--gas-price <amount>", "Gas price in wei (EVM chains)")
    .option("--anti-mev", "Enable anti-MEV protection")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (!opts.image && !opts.imageUrl) {
        console.error("[gmgn-cli] Either --image or --image-url must be provided");
        process.exit(1);
      }
      if (!opts.slippage && !opts.autoSlippage) {
        console.error("[gmgn-cli] Either --slippage or --auto-slippage must be provided");
        process.exit(1);
      }
      validateChain(opts.chain);
      const params: CreateTokenParams = {
        chain: opts.chain,
        dex: opts.dex,
        from_address: opts.from,
        name: opts.name,
        symbol: opts.symbol,
        buy_amt: opts.buyAmt,
      };
      if (opts.image) params.image = opts.image;
      if (opts.imageUrl) params.image_url = opts.imageUrl;
      if (opts.website) params.website = opts.website;
      if (opts.twitter) params.twitter = opts.twitter;
      if (opts.telegram) params.telegram = opts.telegram;
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.gasPrice) params.gas_price = opts.gasPrice;
      if (opts.antiMev) params.is_anti_mev = true;
      const client = new OpenApiClient(getConfig(true));
      const data = await client.createToken(params).catch(exitOnError);
      printResult(data, opts.raw);
    });
}
