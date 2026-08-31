const VALID_CHAINS = new Set(["sol", "bsc", "base", "eth", "robinhood", "arc", "stable" /*, "monad" */]);
const SOL_ADDRESS_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const EVM_ADDRESS_RE = /^0x[0-9a-fA-F]{40}$/;
const POSITIVE_INT_RE = /^\d+$/;

export function validateChain(chain: string): void {
  if (!VALID_CHAINS.has(chain)) {
    console.error(
      `[gmgn-cli] Invalid chain: "${chain}". Must be one of: ${[...VALID_CHAINS].join(", ")}`
    );
    process.exit(1);
  }
}

const STRATEGY_V1_CHAINS = new Set(["sol", "bsc", "base", "eth", "robinhood"]);

export function validateStrategyV1Chain(chain: string): void {
  if (!STRATEGY_V1_CHAINS.has(chain)) {
    console.error(
      `[gmgn-cli] Invalid V1 strategy chain: "${chain}". Must be one of: ${[...STRATEGY_V1_CHAINS].join(", ")}. Use order strategy create-v2 for arc / stable.`
    );
    process.exit(1);
  }
}

export function validateAddress(address: string, chain: string, label: string): void {
  const isEvm = chain === "bsc" || chain === "base" || chain === "eth" || chain === "robinhood" || chain === "arc" || chain === "stable" /* || chain === "monad" */;
  const valid = isEvm ? EVM_ADDRESS_RE.test(address) : SOL_ADDRESS_RE.test(address);
  if (!valid) {
    console.error(
      `[gmgn-cli] Invalid ${label} address for chain "${chain}": "${address}"`
    );
    process.exit(1);
  }
}

export function validatePositiveInt(value: string, label: string): void {
  if (!POSITIVE_INT_RE.test(value) || BigInt(value) <= 0n) {
    console.error(
      `[gmgn-cli] Invalid ${label}: "${value}". Must be a positive integer.`
    );
    process.exit(1);
  }
}

// Chains that do not support condition orders / smart_trade strategies.
const NO_CONDITION_ORDER_CHAINS = new Set(["arc", "stable"]);

export function validateConditionOrdersSupported(chain: string, feature: string): void {
  if (NO_CONDITION_ORDER_CHAINS.has(chain)) {
    console.error(
      `[gmgn-cli] condition orders are not supported on chain "${chain}" (${feature}). Use a plain swap or limit_order instead.`
    );
    process.exit(1);
  }
}

export function validatePercent(value: number): void {
  if (value <= 0 || value > 100) {
    console.error(
      `[gmgn-cli] Invalid --percent: ${value}. Must be between 0 (exclusive) and 100 (inclusive).`
    );
    process.exit(1);
  }
}
