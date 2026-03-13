import { Command } from "commander";
import { OpenApiClient, SwapParams } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";

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
    .option("--min-output <amount>", "Minimum output amount")
    .option("--anti-mev", "Enable anti-MEV protection, default true")
    .option("--priority-fee <sol>", "Priority fee in SOL (≥ 0.00001, SOL only)")
    .option("--tip-fee <amount>", "Tip fee (SOL ≥ 0.00001 SOL / BSC ≥ 0.000001 BNB)")
    .option("--max-auto-fee <amount>", "Max auto fee cap")
    .option("--gas-price <gwei>", "Gas price in gwei (BSC ≥ 0.05 / BASE/ETH ≥ 0.01)")
    .option("--max-fee-per-gas <amount>", "EIP-1559 max fee per gas (Base)")
    .option("--max-priority-fee-per-gas <amount>", "EIP-1559 max priority fee per gas (Base)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      if (opts.percent == null && !opts.amount) {
        console.error("[gmgn-cli] Either --amount or --percent must be provided");
        process.exit(1);
      }
      const params: SwapParams = {
        chain: opts.chain,
        from_address: opts.from,
        input_token: opts.inputToken,
        output_token: opts.outputToken,
        input_amount: opts.percent != null ? (opts.amount ?? "0") : opts.amount,
      };
      if (opts.percent != null) params.input_amount_bps = String(Math.round(opts.percent * 100));
      if (opts.slippage != null) params.slippage = opts.slippage;
      if (opts.minOutput) params.min_output_amount = opts.minOutput;
      if (opts.antiMev) params.is_anti_mev = true;
      if (opts.priorityFee) params.priority_fee = opts.priorityFee;
      if (opts.tipFee) params.tip_fee = opts.tipFee;
      if (opts.maxAutoFee) params.max_auto_fee = opts.maxAutoFee;
      if (opts.gasPrice) params.gas_price = String(Math.round(parseFloat(opts.gasPrice) * 1e9));
      if (opts.maxFeePerGas) params.max_fee_per_gas = opts.maxFeePerGas;
      if (opts.maxPriorityFeePerGas) params.max_priority_fee_per_gas = opts.maxPriorityFeePerGas;

      const client = new OpenApiClient(getConfig(true));
      const data = await client.swap(params).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const order = program.command("order").description("Order management commands");

  order
    .command("get")
    .description("Query order status (requires private key)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / monad")
    .requiredOption("--order-id <id>", "Order ID")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const client = new OpenApiClient(getConfig(true));
      const data = await client.queryOrder(opts.orderId, opts.chain).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

