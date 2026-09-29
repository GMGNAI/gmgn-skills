import { Command } from "commander";
import { OpenApiClient, BuyWalletInfo, CreateTokenParams } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { confirmTrade, displayText, extraFeeTotal, nativeSymbol, sumDecimals, weiAnnotations } from "../confirm.js";
import { sanitizeMetadataField, validateMetadataUrl, MAX_DESCRIPTION_LEN, MAX_NAME_LEN } from "../sanitize.js";
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
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / robinhood")
    .requiredOption("--dex <dex>", "Launchpad: pump / bonk / bags (sol) / fourmeme / flap (bsc) / klik / clanker (base) / trench / pons (robinhood)")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--name <name>", "Token name")
    .requiredOption("--symbol <symbol>", "Token symbol")
    .requiredOption("--buy-amt <amount>", "Initial buy amount in native token (e.g. 0.01 SOL)")
    .option("--image <base64>", "Token logo as base64-encoded data (max 2MB decoded)")
    .option("--image-url <url>", "Token logo URL")
    .option("--description <text>", "Token description / project pitch")
    .option("--website <url>", "Website URL")
    .option("--twitter <url>", "Twitter link")
    .option("--telegram <url>", "Telegram link")
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", parseFloat)
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--fee <amount>", "Base gas / fee")
    .option("--priority-fee <sol>", "Priority fee in SOL (SOL only)")
    .option("--tip-fee <amount>", "Tip fee")
    .option("--gas-price <amount>", "Gas price in wei (EVM chains)")
    .option("--max-fee-per-gas <amount>", "Max fee per gas in wei (EVM only)")
    .option("--max-priority-fee-per-gas <amount>", "Max priority fee per gas in wei (EVM only)")
    .option("--anti-mev", "Enable anti-MEV protection (SOL only)")
    .option("--anti-mev-mode <mode>", "Anti-MEV mode: off / normal / secure (SOL only)")
    .option("--raised-token <symbol>", "Raise token symbol: pump→USDC; bonk→USD1; fourmeme→USDT/USD1; base/robinhood→native only; leave empty for native")
    .option("--dev-wallet-bps <n>", "Dev wallet fee in basis points (100 = 1%)", parseInt)
    .option("--dev-gas <amount>", "Dev gas amount")
    .option("--dev-priority <amount>", "Dev priority fee")
    .option("--dev-tip <amount>", "Dev tip fee")
    .option("--dev-max-fee-per-gas <amount>", "Dev tx feeCap in wei (EVM EIP-1559)")
    .option("--approve-vision <version>", "Approve vision version: v1 / v2 (default: v2)")
    .option("--source <source>", "Traffic source identifier")
    // Pump.fun specific
    .option("--is-mayhem", "Enable Mayhem mode (Pump.fun only)")
    .option("--is-cashback", "Enable Cashback (Pump.fun only)")
    .option("--is-buy-back", "Enable Agent Auto Buyback (Pump.fun only)")
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
    // CondMarket execution config + auto-sell (JSON)
    .option("--buy-trade-config <json>", "Buy-side trade config for CondMarket orders as JSON (TradeParam)")
    .option("--sell-trade-config <json>", "Sell-side trade config for auto-sell / pending_sell as JSON (TradeParam)")
    .option("--sell-configs <json>", "Auto-sell strategy list as JSON array (CookingSellConfig[])")
    .option("--yes", "Skip the interactive confirmation prompt (requires GMGN_ALLOW_AUTOMATED_TRADES=1)")
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
      // Validate/clean all free-text and link metadata before publishing. This
      // prevents the CLI from being used to mint tokens whose metadata carries a
      // prompt-injection payload aimed at other users' AI agents.
      const params: CreateTokenParams = {
        chain: opts.chain,
        dex: opts.dex,
        from_address: opts.from,
        name: sanitizeMetadataField(opts.name, "--name", MAX_NAME_LEN),
        symbol: sanitizeMetadataField(opts.symbol, "--symbol", MAX_NAME_LEN),
        buy_amt: opts.buyAmt,
      };
      if (opts.image) params.image = opts.image;
      if (opts.imageUrl) params.image_url = validateMetadataUrl(opts.imageUrl, "--image-url");
      if (opts.description) params.description = sanitizeMetadataField(opts.description, "--description", MAX_DESCRIPTION_LEN);
      if (opts.website) params.website = validateMetadataUrl(opts.website, "--website");
      if (opts.twitter) params.twitter = validateMetadataUrl(opts.twitter, "--twitter");
      if (opts.telegram) params.telegram = validateMetadataUrl(opts.telegram, "--telegram");
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.fee) params.fee = opts.fee;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.gasPrice) params.gas_price = opts.gasPrice;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.antiMevMode) params.anti_mev_mode = opts.antiMevMode;
      if (opts.raisedToken != null) params.raised_token = opts.raisedToken;
      if (opts.devWalletBps != null) params.dev_wallet_bps = opts.devWalletBps;
      if (opts.devGas) params.dev_gas = opts.devGas;
      if (opts.devPriority) params.dev_priority = opts.devPriority;
      if (opts.devTip) params.dev_tip = opts.devTip;
      if (opts.devMaxFeePerGas) params.dev_max_fee_per_gas = opts.devMaxFeePerGas;
      if (opts.approveVision) params.approve_vision = opts.approveVision;
      if (opts.source) params.source = opts.source;
      if (opts.isMayhem) params.is_mayhem = true;
      if (opts.isCashback) params.is_cashback = true;
      if (opts.isBuyBack) params.is_buy_back = true;
      if (opts.pumpFeeShareList) params.pump_fee_share_list = parseJsonOption(opts.pumpFeeShareList, "--pump-fee-share-list");
      if (opts.flapRateConf) params.flap_rate_conf = parseJsonOption(opts.flapRateConf, "--flap-rate-conf");
      if (opts.fourmemeRateConf) params.fourmeme_rate_conf = parseJsonOption(opts.fourmemeRateConf, "--fourmeme-rate-conf");
      if (opts.bagsFeeShareList) params.bags_fee_share_list = parseJsonOption(opts.bagsFeeShareList, "--bags-fee-share-list");
      if (opts.bonkModel) params.bonk_model = opts.bonkModel;
      if (opts.buyWallets) params.buy_wallets = parseJsonOption(opts.buyWallets, "--buy-wallets");
      if (opts.snipBuyWallets) params.snip_buy_wallets = parseJsonOption(opts.snipBuyWallets, "--snip-buy-wallets");
      if (opts.buyTradeConfig) params.buy_trade_config = parseJsonOption(opts.buyTradeConfig, "--buy-trade-config");
      if (opts.sellTradeConfig) params.sell_trade_config = parseJsonOption(opts.sellTradeConfig, "--sell-trade-config");
      if (opts.sellConfigs) params.sell_configs = parseJsonOption(opts.sellConfigs, "--sell-configs");
      confirmTrade({
        action: "Create token",
        params,
        keyFields: ["chain", "dex", "from_address", "name", "symbol", "buy_amt", "raised_token", "slippage", "auto_slippage", "is_anti_mev", "anti_mev_mode"],
        protections: params.chain === "sol"
          ? [{ fields: ["is_anti_mev", "anti_mev_mode"], text: "Anti-MEV protection not requested (is_anti_mev / anti_mev_mode not sent) — the launch buy can be sandwiched." }]
          : [],
        totals: cookingTotals(params),
        annotations: weiAnnotations(params, ["gas_price", "max_fee_per_gas", "max_priority_fee_per_gas", "dev_max_fee_per_gas"]),
      }, opts.yes);

      const client = new OpenApiClient(getConfig(true));
      const data = await client.createToken(params).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

function parseJsonOption<T>(raw: string, flag: string): T {
  try {
    return JSON.parse(raw) as T;
  } catch {
    console.error(`[gmgn-cli] ${flag} must be valid JSON`);
    process.exit(1);
  }
}

// Totals whose meaning only this command knows: the native-token spend across
// the dev buy, bundle wallets and snipe wallets, the extra fees, and where the
// creator fees go.
function cookingTotals(params: CreateTokenParams): string[] {
  const buyWallets = Array.isArray(params.buy_wallets) ? params.buy_wallets : [];
  const snipWallets = Array.isArray(params.snip_buy_wallets) ? params.snip_buy_wallets : [];
  const walletSum = (ws: BuyWalletInfo[]) => sumDecimals(ws.map((w) => String(w?.buy_amt)));
  const terms = [`${displayText(String(params.buy_amt))} (dev)`];
  const amounts = [String(params.buy_amt)];
  if (buyWallets.length) {
    terms.push(`${walletSum(buyWallets) ?? "?"} (${buyWallets.length} buy wallets)`);
    amounts.push(...buyWallets.map((w) => String(w?.buy_amt)));
  }
  if (snipWallets.length) {
    terms.push(`${walletSum(snipWallets) ?? "?"} (${snipWallets.length} snipe wallets)`);
    amounts.push(...snipWallets.map((w) => String(w?.buy_amt)));
  }
  const lines = [`Total buy spend: ${terms.join(" + ")} = ${sumDecimals(amounts) ?? "?"} ${nativeSymbol(params.chain)}`];

  const fees = extraFeeTotal(params.chain, params.tip_fee, params.priority_fee);
  if (fees) lines.push(fees);

  const shares = [params.pump_fee_share_list, params.bags_fee_share_list].flatMap((l) => (Array.isArray(l) ? l : []));
  if (shares.length) {
    const list = shares.map((s) => `${s?.provider}:${s?.username} ${Number(s?.basic_points) / 100}%`).join(", ");
    lines.push(`Creator fees routed to: ${displayText(list)}`);
  }
  return lines;
}
