import { Command } from "commander";
import { OpenApiClient, CreateTokenParams } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateChain } from "../validate.js";

export function registerCookingCommands(program: Command): void {
  const cooking = program.command("cooking").description("Token creation and launchpad commands");

  cooking
    .command("stats")
    .description("Get token creation statistics by launchpad (exist auth)")
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
    .option("--anti-mev", "Enable anti-MEV protection (SOL only)")
    .option("--anti-mev-mode <mode>", "Anti-MEV mode: normal / secure (SOL only)")
    .option("--raised-token <symbol>", "Raise token symbol: pump→USDC; bonk→USD1; fourmeme→USDT/USD1; leave empty for native")
    .option("--description <text>", "Token description / project pitch")
    .option("--dev-wallet-bps <n>", "Dev wallet fee in basis points (100 = 1%)", parseInt)
    .option("--max-fee-per-gas <amount>", "Max fee per gas in wei (EVM only)")
    .option("--max-priority-fee-per-gas <amount>", "Max priority fee per gas in wei (EVM only)")
    .option("--dev-gas <amount>", "Dev gas amount")
    .option("--dev-priority <amount>", "Dev priority fee")
    .option("--dev-tip <amount>", "Dev tip fee")
    .option("--approve-vision <version>", "Approve vision version: v1 / v2 (default: v2)")
    .option("--source <source>", "Traffic source identifier")
    // Pump.fun specific
    .option("--is-mayhem", "Enable Mayhem mode (Pump.fun only)")
    .option("--is-cashback", "Enable Cashback (Pump.fun only)")
    .option("--is-revoke-fee-auth", "Revoke fee authority (Pump.fun only)")
    .option("--is-agent", "Enable Agent mode (Pump.fun only)")
    .option("--agent-bps <n>", "Agent fee in basis points (Pump.fun only)", parseInt)
    .option("--pump-fee-share-list <json>", "Pump.fun fee share list as JSON array (Pump.fun only)")
    // Flap specific
    .option("--flap-rate-conf <json>", "Flap rate config as JSON object (Flap only)")
    // FourMeme specific
    .option("--fourmeme-rate-conf <json>", "FourMeme rate config as JSON object (FourMeme only)")
    // BAGS specific
    .option("--bags-fee-share-list <json>", "BAGS fee share list as JSON array (BAGS only)")
    // Bonk specific
    .option("--bonk-model <model>", "Bonk model identifier (bonk DEX only)")
    // Multi-wallet buy
    .option("--buy-wallets <json>", "Multi-wallet buy config as JSON array [{from_address, buy_amt}]")
    .option("--snip-buy-wallets <json>", "Snipe-buy wallet config as JSON array [{from_address, buy_amt}]")
    .option("--interval-seconds <n>", "Interval between multi-wallet buys in seconds", parseInt)
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
      if (opts.antiMevMode) params.anti_mev_mode = opts.antiMevMode;
      if (opts.raisedToken != null) params.raised_token = opts.raisedToken;
      if (opts.devWalletBps != null) params.dev_wallet_bps = opts.devWalletBps;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.devGas) params.dev_gas = opts.devGas;
      if (opts.devPriority) params.dev_priority = opts.devPriority;
      if (opts.devTip) params.dev_tip = opts.devTip;
      if (opts.approveVision) params.approve_vision = opts.approveVision;
      if (opts.source) params.source = opts.source;
      if (opts.isMayhem) params.is_mayhem = true;
      if (opts.isCashback) params.is_cashback = true;
      if (opts.isRevokeFeeAuth) params.is_revoke_fee_auth = true;
      if (opts.isAgent) params.is_agent = true;
      if (opts.agentBps != null) params.agent_bps = opts.agentBps;
      if (opts.pumpFeeShareList) params.pump_fee_share_list = JSON.parse(opts.pumpFeeShareList);
      if (opts.flapRateConf) params.flap_rate_conf = JSON.parse(opts.flapRateConf);
      if (opts.fourmemeRateConf) params.fourmeme_rate_conf = JSON.parse(opts.fourmemeRateConf);
      if (opts.bagsFeeShareList) params.bags_fee_share_list = JSON.parse(opts.bagsFeeShareList);
      if (opts.bonkModel) params.bonk_model = opts.bonkModel;
      if (opts.buyWallets) params.buy_wallets = JSON.parse(opts.buyWallets);
      if (opts.snipBuyWallets) params.snip_buy_wallets = JSON.parse(opts.snipBuyWallets);
      if (opts.intervalSeconds != null) params.interval_seconds = opts.intervalSeconds;
      const client = new OpenApiClient(getConfig(true));
      const data = await client.createToken(params).catch(exitOnError);
      printResult(data, opts.raw);
    });
}
