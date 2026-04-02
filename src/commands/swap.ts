import { Command } from "commander";
import { OpenApiClient, SwapParams, StrategyCreateParams, StrategyCancelParams } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateAddress, validateChain, validatePercent, validatePositiveInt } from "../validate.js";

export function registerSwapCommands(program: Command): void {
  program
    .command("swap")
    .description("Submit a token swap")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth ")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .option("--amount <amount>", "Input raw amount (smallest unit)")
    .option("--percent <pct>", "Input amount as a percentage, e.g. 50 = 50%, 1 = 1%; only valid when input_token is NOT a currency", parseFloat)
    .option("--slippage <n>", "Slippage tolerance (e.g. 0.01 = 1%)", parseFloat)
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--min-output <amount>", "Minimum output amount")
    .option("--anti-mev", "Enable anti-MEV protection, default true")
    .option("--priority-fee <sol>", "Priority fee in SOL (≥ 0.00001, SOL only)")
    .option("--tip-fee <amount>", "Tip fee (SOL ≥ 0.00001 SOL / BSC ≥ 0.000001 BNB)")
    .option("--max-auto-fee <amount>", "Max auto fee cap")
    .option("--gas-price <gwei>", "Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01)")
    .option("--max-fee-per-gas <amount>", "EIP-1559 max fee per gas (Base)")
    .option("--max-priority-fee-per-gas <amount>", "EIP-1559 max priority fee per gas (Base)")
    .option("--condition-orders <json>", 'JSON array of take-profit/stop-loss conditions, e.g. \'[{"order_type":"profit_stop","side":"sell","price_scale":"150","sell_ratio":"100"}]\'')
    .option("--sell-ratio-type <type>", "Sell ratio base: buy_amount (default) / hold_amount; only used with --condition-orders")
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
        from_address: opts.from,
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
      if (opts.maxAutoFee) params.max_auto_fee = opts.maxAutoFee;
      if (opts.gasPrice) params.gas_price = String(Math.round(parseFloat(opts.gasPrice) * 1e9));
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;
      if (opts.conditionOrders) {
        try {
          params.condition_orders = JSON.parse(opts.conditionOrders);
        } catch {
          console.error("[gmgn-cli] --condition-orders must be valid JSON");
          process.exit(1);
        }
      }
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;

      const client = new OpenApiClient(getConfig(true));
      const data = await client.swap(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const order = program.command("order").description("Order management commands");

  order
    .command("quote")
    .description("Get a swap quote without submitting a transaction")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--input-token <address>", "Input token contract address")
    .requiredOption("--output-token <address>", "Output token contract address")
    .requiredOption("--amount <amount>", "Input amount (smallest unit)")
    .requiredOption("--slippage <n>", "Slippage tolerance (e.g. 0.01 = 1%)", parseFloat)
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.from, opts.chain, "--from");
      validateAddress(opts.inputToken, opts.chain, "--input-token");
      validateAddress(opts.outputToken, opts.chain, "--output-token");
      validatePositiveInt(opts.amount, "--amount");
      const client = new OpenApiClient(getConfig());
      const data = await client
        .quoteOrder(opts.chain, opts.from, opts.inputToken, opts.outputToken, opts.amount, opts.slippage)
        .catch(exitOnError);
      printResult(data, opts.raw);
    });

  order
    .command("get")
    .description("Query order status (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / monad")
    .requiredOption("--order-id <id>", "Order ID")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const client = new OpenApiClient(getConfig(true));
      const data = await client.queryOrder(opts.orderId, opts.chain).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const strategy = order.command("strategy").description("Limit/strategy order management");

  strategy
    .command("create")
    .description("Create a limit/strategy order (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--from <address>", "Wallet address (must match API Key binding)")
    .requiredOption("--base-token <address>", "Base token contract address")
    .requiredOption("--quote-token <address>", "Quote token contract address")
    .requiredOption("--order-type <type>", "Order type: limit_order")
    .requiredOption("--sub-order-type <type>", "Sub-order type: buy_low / buy_high / stop_loss / take_profit")
    .requiredOption("--check-price <price>", "Trigger check price")
    .option("--open-price <price>", "Open/entry price")
    .option("--amount-in <amount>", "Input amount (smallest unit)")
    .option("--amount-in-percent <pct>", "Input amount as a percentage (e.g. 50 = 50%)")
    .option("--limit-price-mode <mode>", "Price mode: exact / slippage (default: slippage)")
    .option("--expire-in <seconds>", "Order expiry in seconds", parseInt)
    .option("--sell-ratio-type <type>", "Sell ratio basis: buy_amount (default) / hold_amount")
    .option("--slippage <n>", "Slippage tolerance (e.g. 0.01 = 1%)", parseFloat)
    .option("--auto-slippage", "Enable automatic slippage")
    .option("--priority-fee <sol>", "Priority fee in SOL (required for SOL chain)")
    .option("--tip-fee <amount>", "Tip fee (required for SOL chain)")
    .option("--gas-price <gwei>", "Gas price in gwei (required for BSC; ≥ 0.05 gwei / BASE/ETH ≥ 0.01 gwei)")
    .option("--anti-mev", "Enable anti-MEV protection")
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
      const params: StrategyCreateParams = {
        chain: opts.chain,
        from_address: opts.from,
        base_token: opts.baseToken,
        quote_token: opts.quoteToken,
        order_type: opts.orderType,
        sub_order_type: opts.subOrderType,
        check_price: opts.checkPrice,
      };
      if (opts.openPrice) params.open_price = opts.openPrice;
      if (opts.amountIn) params.amount_in = opts.amountIn;
      if (opts.amountInPercent) params.amount_in_percent = opts.amountInPercent;
      if (opts.limitPriceMode) params.limit_price_mode = opts.limitPriceMode;
      if (opts.expireIn != null) params.expire_in = opts.expireIn;
      if (opts.sellRatioType) params.sell_ratio_type = opts.sellRatioType;
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.autoSlippage) params.auto_slippage = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.gasPrice) params.gas_price = String(Math.round(parseFloat(opts.gasPrice) * 1e9));
      if (opts.antiMev) params.is_anti_mev = true;
      const client = new OpenApiClient(getConfig(true));
      const data = await client.createStrategyOrder(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  strategy
    .command("list")
    .description("List strategy orders (normal auth)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
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
      const client = new OpenApiClient(getConfig());
      const data = await client.getStrategyOrders(opts.chain, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  strategy
    .command("cancel")
    .description("Cancel a strategy order (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
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
