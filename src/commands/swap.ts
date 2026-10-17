import { Command } from "commander";
import { OpenApiClient, SwapParams, MultiSwapParams, StrategyCreateParams, StrategyCancelParams, WRITE_ROUTES } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { ANTI_MEV_PROTECTION, confirmTrade, EXPIRY_PROTECTION, MIN_OUTPUT_PROTECTION, SLIPPAGE_PROTECTION, weiAnnotations } from "../confirm.js";
import { gweiToWei, nonNegativeInt, nonNegativeNumber, parseJsonOption, validateAddress, validateChain, validateConditionOrdersSupported, validatePercent, validatePositiveInt, validateV1SmartTradeSupported } from "../validate.js";

export function registerSwapCommands(program: Command): void {
  program
    .command("swap")
    .description("Submit a token swap")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .option("--amount <amount>", "Input raw amount (smallest unit)")
    .option("--percent <pct>", "Input amount as a percentage, e.g. 50 = 50%, 1 = 1%; only valid when input_token is NOT a currency", nonNegativeNumber("--percent"))
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", nonNegativeNumber("--slippage"))
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--min-output <amount>", "Minimum output amount")
    .option("--anti-mev", "Enable anti-MEV protection, default true")
    .option("--priority-fee <sol>", "Priority fee in SOL (≥ 0.00001, SOL only)")
    .option("--tip-fee <amount>", "Tip fee (SOL ≥ 0.00001 SOL / BSC ≥ 0.000001 BNB)")
    .option("--gas-price <gwei>", "Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01); mutually exclusive with --gas-level")
    .option("--gas-level <level>", "Gas price tier (eth only): low / average / high; mutually exclusive with --gas-price")
    .option("--auto-fee", "Auto fee mode (eth only); delegates fee selection to trading bot for condition_orders strategy")
    .option("--max-fee-per-gas <amount>", "EIP-1559 max fee per gas (BSC / BASE / ETH)")
    .option("--max-priority-fee-per-gas <amount>", "EIP-1559 max priority fee per gas (BSC / BASE / ETH)")
    .option("--condition-orders <json>", 'JSON array of take-profit/stop-loss conditions, e.g. \'[{"order_type":"profit_stop","side":"sell","price_scale":"150","sell_ratio":"100"}]\'; trace types: \'[{"order_type":"profit_stop_trace","side":"sell","price_scale":"150","sell_ratio":"100","drawdown_rate":"50"}]\'; not supported on arc / stable')
    .option("--sell-ratio-type <type>", "Sell ratio base: buy_amount (default) / hold_amount; only used with --condition-orders")
    .option("--yes", "Skip the interactive confirmation prompt (requires GMGN_ALLOW_AUTOMATED_TRADES=1)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (opts.percent == null && !opts.amount) {
        console.error("[gmgn-cli] Either --amount or --percent must be provided");
        process.exit(1);
      }
      validateChain(opts.chain);
      validateAddress(opts.from, opts.chain, "--from");
      validateAddress(opts.inputToken, opts.chain, "--input-token");
      validateAddress(opts.outputToken, opts.chain, "--output-token");
      if (opts.amount) validatePositiveInt(opts.amount, "--amount");
      if (opts.percent != null) validatePercent(opts.percent);
      const params: SwapParams = {
        chain: opts.chain,
        from_address: opts.chain === "sol" ? opts.from : opts.from.toLowerCase(),
        input_token: opts.inputToken,
        output_token: opts.outputToken,
        input_amount: opts.percent != null ? (opts.amount ?? "0") : opts.amount,
      };
      if (opts.percent != null) params.input_amount_bps = String(Math.round(opts.percent * 100));
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.minOutput) params.min_output_amount = opts.minOutput;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.autoFee) params.auto_fee = true;
      if (opts.gasPrice) params.gas_price = gweiToWei(opts.gasPrice, "--gas-price");
      if (opts.gasLevel) params.gas_level = opts.gasLevel;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.conditionOrders) {
        validateConditionOrdersSupported(opts.chain, "swap");
        params.condition_orders = parseJsonOption(opts.conditionOrders, "--condition-orders");
      }
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;

      const client = new OpenApiClient(getConfig(true));
      confirmTrade({
        action: "Swap",
        route: WRITE_ROUTES.swap,
        params,
        keyFields: ["chain", "from_address", "input_token", "output_token", "input_amount_bps", "input_amount", "slippage", "auto_slippage", "min_output_amount", "is_anti_mev"],
        protections: [MIN_OUTPUT_PROTECTION, SLIPPAGE_PROTECTION],
        annotations: {
          ...weiAnnotations(params, ["gas_price"]),
          ...(params.input_amount_bps
            ? { input_amount_bps: `${Number(params.input_amount_bps) / 100}% of balance`, input_amount: "ignored — amount is set by input_amount_bps" }
            : { input_amount: "smallest unit" }),
        },
      }, opts.yes);

      const data = await client.swap(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  program
    .command("multi-swap")
    .description("Submit token swaps across multiple wallets concurrently (up to 100 wallets)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .requiredOption("--accounts <addresses>", "Comma-separated wallet addresses (all must be bound to the API Key)")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .option("--input-amount <json>", 'JSON map of wallet→amount (smallest unit), e.g. \'{"addr1":"1000000","addr2":"2000000"}\'')
    .option("--input-amount-bps <json>", 'JSON map of wallet→percent in bps (1–10000, e.g. 5000=50%), e.g. \'{"addr1":"5000"}\'')
    .option("--output-amount <json>", "JSON map of wallet→target output amount")
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", nonNegativeNumber("--slippage"))
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--anti-mev", "Enable anti-MEV protection")
    .option("--priority-fee <sol>", "Priority fee in SOL (SOL only, ≥ 0.00001)")
    .option("--tip-fee <amount>", "Tip fee (SOL ≥ 0.00001 / BSC ≥ 0.000001 BNB)")
    .option("--gas-price <gwei>", "Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01); mutually exclusive with --gas-level")
    .option("--gas-level <level>", "Gas price tier (eth only): low / average / high; mutually exclusive with --gas-price")
    .option("--auto-fee", "Auto fee mode (eth only); delegates fee selection to trading bot for condition_orders strategy")
    .option("--max-fee-per-gas <amount>", "EIP-1559 max fee per gas (BSC / BASE / ETH)")
    .option("--max-priority-fee-per-gas <amount>", "EIP-1559 max priority fee per gas (BSC / BASE / ETH)")
    .option("--condition-orders <json>", "JSON array of take-profit/stop-loss conditions attached to each successful wallet's swap; not supported on arc / stable")
    .option("--sell-ratio-type <type>", "Sell ratio base: buy_amount (default) / hold_amount; only used with --condition-orders")
    .option("--yes", "Skip the interactive confirmation prompt (requires GMGN_ALLOW_AUTOMATED_TRADES=1)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (!opts.inputAmount && !opts.inputAmountBps && !opts.outputAmount) {
        console.error("[gmgn-cli] At least one of --input-amount, --input-amount-bps, or --output-amount must be provided");
        process.exit(1);
      }
      validateChain(opts.chain);
      const accounts = (opts.accounts as string).split(",").map((a: string) => a.trim()).filter(Boolean);
      if (accounts.length === 0 || accounts.length > 100) {
        console.error("[gmgn-cli] --accounts must be 1–100 comma-separated wallet addresses");
        process.exit(1);
      }
      accounts.forEach((a: string) => validateAddress(a, opts.chain, "--accounts"));
      validateAddress(opts.inputToken, opts.chain, "--input-token");
      validateAddress(opts.outputToken, opts.chain, "--output-token");
      const params: MultiSwapParams = {
        chain: opts.chain,
        accounts: opts.chain === "sol" ? accounts : accounts.map((a: string) => a.toLowerCase()),
        input_token: opts.inputToken,
        output_token: opts.outputToken,
      };
      if (opts.inputAmount) {
        params.input_amount = parseJsonOption(opts.inputAmount, "--input-amount");
      }
      if (opts.inputAmountBps) {
        params.input_amount_bps = parseJsonOption(opts.inputAmountBps, "--input-amount-bps");
      }
      if (opts.outputAmount) {
        params.output_amount = parseJsonOption(opts.outputAmount, "--output-amount");
      }
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.autoFee) params.auto_fee = true;
      if (opts.gasPrice) params.gas_price = gweiToWei(opts.gasPrice, "--gas-price");
      if (opts.gasLevel) params.gas_level = opts.gasLevel;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.conditionOrders) {
        validateConditionOrdersSupported(opts.chain, "multi_swap");
        params.condition_orders = parseJsonOption(opts.conditionOrders, "--condition-orders");
      }
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;

      const client = new OpenApiClient(getConfig(true));
      confirmTrade({
        action: "Multi-wallet swap",
        route: WRITE_ROUTES.multiSwap,
        params,
        keyFields: ["chain", "accounts", "input_token", "output_token", "input_amount", "input_amount_bps", "output_amount", "slippage", "auto_slippage", "is_anti_mev"],
        protections: [SLIPPAGE_PROTECTION, ANTI_MEV_PROTECTION],
        totals: [`Wallets: ${params.accounts.length}`],
        feeLabel: "Extra fees per wallet transaction",
        annotations: {
          ...weiAnnotations(params, ["gas_price"]),
          ...perWalletAnnotations("input_amount", params.input_amount, () => "smallest unit"),
          ...perWalletAnnotations("input_amount_bps", params.input_amount_bps, (v) => `${Number(v) / 100}% of balance`),
        },
      }, opts.yes);

      const data = await client.multiSwap(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const order = program.command("order").description("Order management commands");

  order
    .command("quote")
    .description("Get a swap quote without submitting a transaction (exist auth — GMGN_API_KEY only, no private key needed)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .requiredOption("--amount <amount>", "Input amount (smallest unit)")
    .requiredOption("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", parseFloat)
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.from, opts.chain, "--from");
      validateAddress(opts.inputToken, opts.chain, "--input-token");
      validateAddress(opts.outputToken, opts.chain, "--output-token");
      validatePositiveInt(opts.amount, "--amount");
      const client = new OpenApiClient(getConfig(true));
      const data = await client
        .quoteOrder(opts.chain, opts.from, opts.inputToken, opts.outputToken, opts.amount, opts.slippage)
        .catch(exitOnError);
      printResult(data, opts.raw);
    });

  order
    .command("get")
    .description("Query order status (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .requiredOption("--order-id <id>", "Order ID")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const client = new OpenApiClient(getConfig(true));
      const data = await client.queryOrder(opts.orderId, opts.chain).catch(exitOnError);
      printResult(data, opts.raw);
    });

  program
    .command("gas-price")
    .description("Query recommended gas price tiers for any chain (exist auth — API Key only; eth / bsc / base / sol / robinhood / arc / stable)")
    .requiredOption("--chain <chain>", "Chain: eth / bsc / base / sol / robinhood / arc / stable")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const client = new OpenApiClient(getConfig(false));
      const data = await client.getGasPrice(opts.chain).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const strategy = order.command("strategy").description("Limit/strategy order management");

  strategy
    .command("create")
    .description("Create a limit/strategy order (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--base-token <address>", "Base token contract address")
    .requiredOption("--quote-token <address>", "Quote token contract address")
    .requiredOption("--order-type <type>", "Order type: limit_order / smart_trade (arbitrum / hyperevm / arc / stable support limit_order only in V1)")
    .requiredOption("--sub-order-type <type>", "Sub-order type: buy_low / buy_high / stop_loss / take_profit (limit_order); mix_trade (smart_trade with condition_orders)")
    .option("--check-price <price>", "Trigger check price (required for limit_order; omit for smart_trade)")
    .option("--open-price <price>", "Open price of the position")
    .option("--amount-in <amount>", "Input amount (smallest unit)")
    .option("--amount-in-percent <pct>", "Input amount as a percentage (e.g. 50 = 50%)")
    .option("--limit-price-mode <mode>", "Price mode: exact / slippage (default: slippage)")
    .option("--expire-in <seconds>", "Order expiry in seconds", nonNegativeInt("--expire-in"))
    .option("--sell-ratio-type <type>", "Sell ratio basis: buy_amount (default) / hold_amount")
    .option("--quote-investment <amount>", "Quote token investment amount (smart_trade)")
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", nonNegativeNumber("--slippage"))
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--priority-fee <sol>", "Priority fee in SOL (required for SOL chain)")
    .option("--tip-fee <amount>", "Tip fee (required for SOL chain)")
    .option("--auto-fee", "Auto fee mode (eth only); delegates fee selection to trading bot")
    .option("--gas-price <gwei>", "Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01 gwei); mutually exclusive with --gas-level")
    .option("--gas-level <level>", "Gas price tier (eth only): low / average / high; mutually exclusive with --gas-price")
    .option("--max-fee-per-gas <amount>", "EIP-1559 max fee per gas (BSC / BASE / ETH)")
    .option("--max-priority-fee-per-gas <amount>", "EIP-1559 max priority fee per gas (BSC / BASE / ETH)")
    .option("--anti-mev", "Enable anti-MEV protection")
    .option("--condition-orders <json>", "JSON array of condition sub-orders for smart_trade (must include a buy_low entry + TP/SL entries); V1 smart_trade is not supported on arbitrum / hyperevm / arc / stable")
    .option("--sell-param <json>", "JSON object of sell-side trade params used when a TP/SL condition fires (required for smart_trade)")
    .option("--buy-param <json>", "JSON object of buy-side trade params override for smart_trade")
    .option("--yes", "Skip the interactive confirmation prompt (requires GMGN_ALLOW_AUTOMATED_TRADES=1)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (!opts.amountIn && !opts.amountInPercent) {
        console.error("[gmgn-cli] Either --amount-in or --amount-in-percent must be provided");
        process.exit(1);
      }
      if (!opts.slippage && !opts.autoSlippage) {
        console.error("[gmgn-cli] Either --slippage or --auto-slippage must be provided");
        process.exit(1);
      }
      validateChain(opts.chain);
      validateAddress(opts.from, opts.chain, "--from");
      validateAddress(opts.baseToken, opts.chain, "--base-token");
      validateAddress(opts.quoteToken, opts.chain, "--quote-token");
      if (opts.orderType === "smart_trade") {
        validateV1SmartTradeSupported(opts.chain);
      }
      const params: StrategyCreateParams = {
        chain: opts.chain,
        from_address: opts.from,
        base_token: opts.baseToken,
        quote_token: opts.quoteToken,
        order_type: opts.orderType,
        sub_order_type: opts.subOrderType,
      };
      if (opts.checkPrice) params.check_price = opts.checkPrice;
      if (opts.openPrice) params.open_price = opts.openPrice;
      if (opts.amountIn) params.amount_in = opts.amountIn;
      if (opts.amountInPercent) params.amount_in_percent = opts.amountInPercent;
      if (opts.limitPriceMode) params.limit_price_mode = opts.limitPriceMode;
      if (opts.expireIn != null) params.expire_in = opts.expireIn;
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;
      if (opts.quoteInvestment) params.quote_investment = opts.quoteInvestment;
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.autoFee) params.auto_fee = true;
      if (opts.gasPrice) params.gas_price = gweiToWei(opts.gasPrice, "--gas-price");
      if (opts.gasLevel) params.gas_level = opts.gasLevel;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.conditionOrders) {
        params.condition_orders = parseJsonOption(opts.conditionOrders, "--condition-orders");
      }
      if (opts.sellParam) {
        params.sell_param = parseJsonOption(opts.sellParam, "--sell-param");
      }
      if (opts.buyParam) {
        params.buy_param = parseJsonOption(opts.buyParam, "--buy-param");
      }
      const client = new OpenApiClient(getConfig(true));
      confirmTrade({
        action: "Create strategy order",
        route: WRITE_ROUTES.strategyCreate,
        params,
        keyFields: ["chain", "from_address", "base_token", "quote_token", "order_type", "sub_order_type", "amount_in", "amount_in_percent", "quote_investment", "open_price", "limit_price_mode", "expire_in", "slippage", "auto_slippage", "is_anti_mev"],
        protections: [SLIPPAGE_PROTECTION, ANTI_MEV_PROTECTION, EXPIRY_PROTECTION],
        feeLabel: "Extra fees when the order executes",
        annotations: {
          ...weiAnnotations(params, ["gas_price"]),
          ...(params.amount_in_percent ? { amount_in_percent: `${params.amount_in_percent}% of balance` } : {}),
          ...(params.expire_in != null ? { expire_in: "seconds" } : {}),
        },
      }, opts.yes);

      const data = await client.createStrategyOrder(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  strategy
    .command("list")
    .description("List strategy orders (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .option("--type <type>", "open (default) / history")
    .option("--from <address>", "Filter by wallet address")
    .requiredOption("--group-tag <tag>", "Filter by group: LimitOrder / STMix")
    .option("--base-token <address>", "Filter by token address")
    .option("--page-token <token>", "Pagination cursor from previous response")
    .option("--limit <n>", "Results per page", parseInt)
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const extra: Record<string, string | number> = {};
      if (opts.type) extra["type"] = opts.type;
      if (opts.from) extra["from_address"] = opts.from;
      if (opts.groupTag) extra["group_tag"] = opts.groupTag;
      if (opts.baseToken) extra["base_token"] = opts.baseToken;
      if (opts.pageToken) extra["page_token"] = opts.pageToken;
      if (opts.limit != null) extra["limit"] = opts.limit;
      const client = new OpenApiClient(getConfig(true));
      const data = await client.getStrategyOrders(opts.chain, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  strategy
    .command("cancel")
    .description("Cancel a strategy order (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / arbitrum / hyperevm / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--order-id <id>", "Order ID to cancel")
    .option("--order-type <type>", "Order type: limit_order / smart_trade")
    .option("--close-sell-model <model>", "Sell model when closing")
    .option("--yes", "Skip the interactive confirmation prompt (requires GMGN_ALLOW_AUTOMATED_TRADES=1)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.from, opts.chain, "--from");
      const params: StrategyCancelParams = {
        chain: opts.chain,
        from_address: opts.from,
        order_id: opts.orderId,
      };
      if (opts.orderType) params.order_type = opts.orderType;
      if (opts.closeSellModel) params.close_sell_model = opts.closeSellModel;
      const client = new OpenApiClient(getConfig(true));
      confirmTrade({
        action: "Cancel strategy order",
        route: WRITE_ROUTES.strategyCancel,
        params,
        keyFields: ["chain", "from_address", "order_id", "order_type"],
      }, opts.yes);

      const data = await client.cancelStrategyOrder(params).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

// "input_amount.<wallet>" → hint, for the per-wallet maps of multi-swap.
function perWalletAnnotations(field: string, map: Record<string, string> | undefined, hint: (v: string) => string): Record<string, string> {
  const out: Record<string, string> = {};
  if (map == null || typeof map !== "object") return out;
  for (const [wallet, v] of Object.entries(map)) {
    if (/^\w+$/.test(wallet)) out[`${field}.${wallet}`] = hint(String(v));
  }
  return out;
}
