import { Command } from "commander";
import { OpenApiClient, SwapParams, MultiSwapParams, StrategyCreateParams, StrategyCreateV2Params, StrategyCancelParams } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { confirmTrade } from "../confirm.js";
import { validateAddress, validateChain, validateConditionOrdersSupported, validatePercent, validatePositiveInt, validateStrategyV1Chain } from "../validate.js";

export function registerSwapCommands(program: Command): void {
  program
    .command("swap")
    .description("Submit a token swap")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .option("--amount <amount>", "Input raw amount (smallest unit)")
    .option("--percent <pct>", "Input amount as a percentage, e.g. 50 = 50%, 1 = 1%; only valid when input_token is NOT a currency", parseFloat)
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", parseFloat)
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
      if (opts.gasPrice) params.gas_price = String(Math.round(parseFloat(opts.gasPrice) * 1e9));
      if (opts.gasLevel) params.gas_level = opts.gasLevel;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.conditionOrders) {
        validateConditionOrdersSupported(opts.chain, "swap");
        try {
          params.condition_orders = JSON.parse(opts.conditionOrders);
        } catch {
          console.error("[gmgn-cli] --condition-orders must be valid JSON");
          process.exit(1);
        }
      }
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;

      confirmTrade({
        action: "Swap",
        lines: [
          `Chain:        ${params.chain}`,
          `Wallet:       ${params.from_address}`,
          `Input token:  ${params.input_token}`,
          `Output token: ${params.output_token}`,
          opts.percent != null
            ? `Amount:       ${opts.percent}% of balance`
            : `Amount:       ${params.input_amount} (smallest unit)`,
          `Slippage:     ${opts.autoSlippage ? "auto" : (params.slippage ?? "default")}`,
        ],
      }, opts.yes);

      const client = new OpenApiClient(getConfig(true));
      const data = await client.swap(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  program
    .command("multi-swap")
    .description("Submit token swaps across multiple wallets concurrently (up to 100 wallets)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .requiredOption("--accounts <addresses>", "Comma-separated wallet addresses (all must be bound to the API Key)")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .option("--input-amount <json>", 'JSON map of wallet→amount (smallest unit), e.g. \'{"addr1":"1000000","addr2":"2000000"}\'')
    .option("--input-amount-bps <json>", 'JSON map of wallet→percent in bps (1–10000, e.g. 5000=50%), e.g. \'{"addr1":"5000"}\'')
    .option("--output-amount <json>", "JSON map of wallet→target output amount")
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", parseFloat)
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
      const params: MultiSwapParams = {
        chain: opts.chain,
        accounts: opts.chain === "sol" ? accounts : accounts.map((a: string) => a.toLowerCase()),
        input_token: opts.inputToken,
        output_token: opts.outputToken,
      };
      if (opts.inputAmount) {
        try { params.input_amount = JSON.parse(opts.inputAmount); }
        catch { console.error("[gmgn-cli] --input-amount must be valid JSON"); process.exit(1); }
      }
      if (opts.inputAmountBps) {
        try { params.input_amount_bps = JSON.parse(opts.inputAmountBps); }
        catch { console.error("[gmgn-cli] --input-amount-bps must be valid JSON"); process.exit(1); }
      }
      if (opts.outputAmount) {
        try { params.output_amount = JSON.parse(opts.outputAmount); }
        catch { console.error("[gmgn-cli] --output-amount must be valid JSON"); process.exit(1); }
      }
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.autoFee) params.auto_fee = true;
      if (opts.gasPrice) params.gas_price = String(Math.round(parseFloat(opts.gasPrice) * 1e9));
      if (opts.gasLevel) params.gas_level = opts.gasLevel;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.conditionOrders) {
        validateConditionOrdersSupported(opts.chain, "multi_swap");
        try { params.condition_orders = JSON.parse(opts.conditionOrders); }
        catch { console.error("[gmgn-cli] --condition-orders must be valid JSON"); process.exit(1); }
      }
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;

      confirmTrade({
        action: "Multi-wallet swap",
        lines: [
          `Chain:        ${params.chain}`,
          `Wallets:      ${params.accounts.length} (${params.accounts.join(", ")})`,
          `Input token:  ${params.input_token}`,
          `Output token: ${params.output_token}`,
          `Slippage:     ${opts.autoSlippage ? "auto" : (params.slippage ?? "default")}`,
        ],
      }, opts.yes);

      const client = new OpenApiClient(getConfig(true));
      const data = await client.multiSwap(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const order = program.command("order").description("Order management commands");

  order
    .command("quote")
    .description("Get a swap quote without submitting a transaction (exist auth — GMGN_API_KEY only, no private key needed)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
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
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
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
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--base-token <address>", "Base token contract address")
    .requiredOption("--quote-token <address>", "Quote token contract address")
    .requiredOption("--order-type <type>", "Order type: limit_order / smart_trade")
    .requiredOption("--sub-order-type <type>", "Sub-order type: buy_low / buy_high / stop_loss / take_profit (limit_order); mix_trade (smart_trade with condition_orders)")
    .option("--check-price <price>", "Trigger check price (required for limit_order; omit for smart_trade)")
    .option("--open-price <price>", "Open price of the position")
    .option("--amount-in <amount>", "Input amount (smallest unit)")
    .option("--amount-in-percent <pct>", "Input amount as a percentage (e.g. 50 = 50%)")
    .option("--limit-price-mode <mode>", "Price mode: exact / slippage (default: slippage)")
    .option("--expire-in <seconds>", "Order expiry in seconds", parseInt)
    .option("--sell-ratio-type <type>", "Sell ratio basis: buy_amount (default) / hold_amount")
    .option("--quote-investment <amount>", "Quote token investment amount (smart_trade)")
    .option("--slippage <n>", "Slippage tolerance (e.g. 30 = 30%)", parseFloat)
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--priority-fee <sol>", "Priority fee in SOL (required for SOL chain)")
    .option("--tip-fee <amount>", "Tip fee (required for SOL chain)")
    .option("--auto-fee", "Auto fee mode (eth only); delegates fee selection to trading bot")
    .option("--gas-price <gwei>", "Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01 gwei); mutually exclusive with --gas-level")
    .option("--gas-level <level>", "Gas price tier (eth only): low / average / high; mutually exclusive with --gas-price")
    .option("--max-fee-per-gas <amount>", "EIP-1559 max fee per gas (BSC / BASE / ETH)")
    .option("--max-priority-fee-per-gas <amount>", "EIP-1559 max priority fee per gas (BSC / BASE / ETH)")
    .option("--anti-mev", "Enable anti-MEV protection")
    .option("--condition-orders <json>", "JSON array of condition sub-orders for smart_trade (must include a buy_low entry + TP/SL entries); smart_trade not supported on arc / stable")
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
      validateStrategyV1Chain(opts.chain);
      if (opts.orderType === "smart_trade") {
        validateConditionOrdersSupported(opts.chain, "strategy create (smart_trade)");
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
      if (opts.gasPrice) params.gas_price = String(Math.round(parseFloat(opts.gasPrice) * 1e9));
      if (opts.gasLevel) params.gas_level = opts.gasLevel;
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.conditionOrders) {
        try { params.condition_orders = JSON.parse(opts.conditionOrders); }
        catch { console.error("[gmgn-cli] --condition-orders must be valid JSON"); process.exit(1); }
      }
      if (opts.sellParam) {
        try { params.sell_param = JSON.parse(opts.sellParam); }
        catch { console.error("[gmgn-cli] --sell-param must be valid JSON"); process.exit(1); }
      }
      if (opts.buyParam) {
        try { params.buy_param = JSON.parse(opts.buyParam); }
        catch { console.error("[gmgn-cli] --buy-param must be valid JSON"); process.exit(1); }
      }
      confirmTrade({
        action: "Create strategy order",
        lines: [
          `Chain:       ${params.chain}`,
          `Wallet:      ${params.from_address}`,
          `Base token:  ${params.base_token}`,
          `Quote token: ${params.quote_token}`,
          `Order type:  ${params.order_type} / ${params.sub_order_type}`,
          `Amount:      ${params.amount_in ?? `${params.amount_in_percent}%`}`,
        ],
      }, opts.yes);

      const client = new OpenApiClient(getConfig(true));
      const data = await client.createStrategyOrder(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  registerStrategyCreateV2(strategy);

  strategy
    .command("list")
    .description("List strategy orders (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .option("--type <type>", "open (default) / history")
    .option("--from <address>", "Filter by wallet address")
    .option("--group-tag <tag>", "Filter by group: LimitOrder / STMix")
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
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--order-id <id>", "Order ID to cancel")
    .option("--order-type <type>", "Order type: limit_order / smart_trade")
    .option("--close-sell-model <model>", "Sell model when closing")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const params: StrategyCancelParams = {
        chain: opts.chain,
        from_address: opts.from,
        order_id: opts.orderId,
      };
      if (opts.orderType) params.order_type = opts.orderType;
      if (opts.closeSellModel) params.close_sell_model = opts.closeSellModel;
      const client = new OpenApiClient(getConfig(true));
      const data = await client.cancelStrategyOrder(params).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

function registerStrategyCreateV2(strategy: Command): void {
  strategy
    .command("create-v2")
    .description("Create a V2 smart-trade strategy order (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--base-token <address>", "Base token contract address")
    .requiredOption("--quote-token <address>", "Quote token contract address")
    .requiredOption("--buy-type <type>", "Entry type: market / limit / position")
    .requiredOption("--condition-orders <json>", "JSON array of take-profit/stop-loss condition orders")
    .requiredOption("--sell-param <json>", "JSON object of sell-side trade parameters")
    .option("--quote-investment <amount>", "Quote investment in smallest units (market / limit)")
    .option("--buy-order <json>", "JSON object describing the entry order (required for limit)")
    .option("--buy-param <json>", "JSON object of buy-side trade parameters (market / limit)")
    .option("--open-amount <amount>", "Existing position amount in smallest units (required for position)")
    .option("--open-price <price>", "Existing position entry price (required for position)")
    .option("--cost-price <price>", "Optional position cost price")
    .option("--sell-ratio-type <type>", "Sell ratio basis: buy_amount / hold_amount")
    .option("--limit-price-mode <mode>", "Limit price mode: exact / slippage")
    .option("--expire-in <seconds>", "Order expiry in seconds", parseInt)
    .option("--yes", "Skip the interactive confirmation prompt (requires GMGN_ALLOW_AUTOMATED_TRADES=1)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.from, opts.chain, "--from");
      validateAddress(opts.baseToken, opts.chain, "--base-token");
      validateAddress(opts.quoteToken, opts.chain, "--quote-token");
      if (!["market", "limit", "position"].includes(opts.buyType)) {
        console.error("[gmgn-cli] --buy-type must be market, limit, or position");
        process.exit(1);
      }
      if ((opts.buyType === "market" || opts.buyType === "limit") && !opts.quoteInvestment) {
        console.error("[gmgn-cli] --quote-investment is required for market and limit entries");
        process.exit(1);
      }
      if (opts.buyType === "limit" && !opts.buyOrder) {
        console.error("[gmgn-cli] --buy-order is required for limit entries");
        process.exit(1);
      }
      if (opts.buyType === "position" && (!opts.openAmount || !opts.openPrice)) {
        console.error("[gmgn-cli] --open-amount and --open-price are required for position entries");
        process.exit(1);
      }
      const params: StrategyCreateV2Params = {
        chain: opts.chain,
        from_address: opts.from,
        base_token: opts.baseToken,
        quote_token: opts.quoteToken,
        sub_order_type: "mix_trade",
        buy_type: opts.buyType,
        condition_orders: parseJsonOption(opts.conditionOrders, "--condition-orders", true),
        sell_param: parseJsonOption(opts.sellParam, "--sell-param", false),
      };
      if (opts.quoteInvestment) params.quote_investment = opts.quoteInvestment;
      if (opts.buyOrder) params.buy_order = parseJsonOption(opts.buyOrder, "--buy-order", false);
      if (opts.buyParam) params.buy_param = parseJsonOption(opts.buyParam, "--buy-param", false);
      if (opts.openAmount) params.open_amount = opts.openAmount;
      if (opts.openPrice) params.open_price = opts.openPrice;
      if (opts.costPrice) params.cost_price = opts.costPrice;
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;
      if (opts.limitPriceMode) params.limit_price_mode = opts.limitPriceMode;
      if (opts.expireIn != null) params.expire_in = opts.expireIn;
      confirmTrade({
        action: "Create V2 strategy order",
        lines: [
          `Chain:       ${params.chain}`,
          `Wallet:      ${params.from_address}`,
          `Base token:  ${params.base_token}`,
          `Quote token: ${params.quote_token}`,
          `Entry type:  ${params.buy_type}`,
          `Amount:      ${params.quote_investment ?? params.open_amount}`,
        ],
      }, opts.yes);
      const client = new OpenApiClient(getConfig(true));
      const data = await client.createStrategyOrderV2(params).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

function parseJsonOption(value: string, label: string, expectArray: true): Record<string, unknown>[];
function parseJsonOption(value: string, label: string, expectArray: false): Record<string, unknown>;
function parseJsonOption(value: string, label: string, expectArray: boolean): Record<string, unknown> | Record<string, unknown>[] {
  try {
    const parsed: unknown = JSON.parse(value);
    const valid = expectArray
      ? Array.isArray(parsed) && parsed.every((item) => item !== null && typeof item === "object" && !Array.isArray(item))
      : parsed !== null && typeof parsed === "object" && !Array.isArray(parsed);
    if (!valid) throw new Error("wrong JSON shape");
    return parsed as Record<string, unknown> | Record<string, unknown>[];
  } catch {
    console.error(`[gmgn-cli] ${label} must be valid JSON ${expectArray ? "array" : "object"}`);
    process.exit(1);
  }
}
