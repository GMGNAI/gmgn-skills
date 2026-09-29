const VALID_CHAINS = new Set(["sol", "bsc", "base", "eth", "arbitrum", "hyperevm", "robinhood", "arc", "stable" /*, "monad" */]);
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

export function validateAddress(address: string, chain: string, label: string): void {
  const isEvm = chain === "bsc" || chain === "base" || chain === "eth" || chain === "arbitrum" || chain === "hyperevm" || chain === "robinhood" || chain === "arc" || chain === "stable" /* || chain === "monad" */;
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

// Chains that do not support condition orders attached to market swaps.
const NO_CONDITION_ORDER_CHAINS = new Set(["arc", "stable"]);

// V1 smart_trade is unavailable on the newer EVM chains. They support the V2
// strategy endpoint instead; the CLI currently exposes only the V1 command.
const NO_V1_SMART_TRADE_CHAINS = new Set(["arbitrum", "hyperevm", "arc", "stable"]);

export function validateConditionOrdersSupported(chain: string, feature: string): void {
  if (NO_CONDITION_ORDER_CHAINS.has(chain)) {
    console.error(
      `[gmgn-cli] condition orders are not supported on chain "${chain}" (${feature}). Use a plain swap or limit_order instead.`
    );
    process.exit(1);
  }
}

export function validateV1SmartTradeSupported(chain: string): void {
  if (NO_V1_SMART_TRADE_CHAINS.has(chain)) {
    console.error(
      `[gmgn-cli] V1 smart_trade is not supported on chain "${chain}". Use a plain limit_order, or call the OpenAPI V2 strategy endpoint for TP/SL orders.`
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

// ---- `market search` input validation ----
//
// Search is deliberately more permissive about chains than the other commands:
// the endpoint accepts the literal "all" plus any chain the platform currently has
// enabled — including ones the core commands don't support yet (tron / monad /
// megaeth / xlayer / hyperevm). A stale local allowlist would reject valid
// searches, so shape-check only and let the server be the authority.
const SEARCH_CHAIN_RE = /^[a-z][a-z0-9_]{1,19}$/;

export function validateSearchChain(chain: string): void {
  if (chain !== "all" && !SEARCH_CHAIN_RE.test(chain)) {
    console.error(
      `[gmgn-cli] Invalid --chain: "${chain}". Use "all" or a chain identifier such as sol / eth / bsc / base / tron.`
    );
    process.exit(1);
  }
}

// Zero-width, bidi-override and C0/C1 control characters can make one token's name
// render identically to another's, so strip them before measuring length and send
// the cleaned string upstream. Length is counted in code points, not UTF-16 units,
// so emoji-heavy ticker names are not over-counted.
const INVISIBLE_CHARS_RE =
  /[\u0000-\u001F\u007F-\u009F\u00AD\u034F\u061C\u180E\u200B-\u200F\u202A-\u202E\u2060-\u2064\u2066-\u206F\uFEFF\uFFF9-\uFFFB]/g;

export function normalizeSearchQuery(raw: string): string {
  const cleaned = raw.replace(INVISIBLE_CHARS_RE, "").trim();
  const length = [...cleaned].length;
  if (length < 1 || length > 100) {
    console.error(
      `[gmgn-cli] Invalid --query: must be 1-100 characters after removing invisible characters (got ${length}).`
    );
    process.exit(1);
  }
  return cleaned;
}

// ---- Option parsers for fund-moving commands ----
//
// A malformed number must not reach a signed body: parseFloat("abc") is NaN and
// JSON.stringify turns NaN / Infinity into null, which silently drops the value.

/** Commander parser for a finite, non-negative number, e.g. --slippage. */
export function nonNegativeNumber(flag: string): (raw: string) => number {
  return (raw) => {
    const n = Number(raw);
    if (raw.trim() === "" || !Number.isFinite(n) || n < 0) {
      console.error(`[gmgn-cli] Invalid ${flag}: "${raw}". Must be a non-negative number.`);
      process.exit(1);
    }
    return n;
  };
}

/** Commander parser for a non-negative integer, e.g. --expire-in. */
export function nonNegativeInt(flag: string): (raw: string) => number {
  return (raw) => {
    if (!POSITIVE_INT_RE.test(raw) || !Number.isSafeInteger(Number(raw))) {
      console.error(`[gmgn-cli] Invalid ${flag}: "${raw}". Must be a non-negative integer.`);
      process.exit(1);
    }
    return Number(raw);
  };
}

/** Parse a JSON option value, exiting with a clear message when it is malformed. */
export function parseJsonOption<T>(raw: string, flag: string): T {
  try {
    return JSON.parse(raw) as T;
  } catch {
    console.error(`[gmgn-cli] ${flag} must be valid JSON`);
    process.exit(1);
  }
}

/** Exact gwei → wei conversion for --gas-price, e.g. "0.05" → "50000000". */
export function gweiToWei(raw: string, flag: string): string {
  const m = /^(\d+)(?:\.(\d{1,9}))?$/.exec(raw.trim());
  if (!m) {
    console.error(`[gmgn-cli] Invalid ${flag}: "${raw}". Must be a gwei amount with at most 9 decimals.`);
    process.exit(1);
  }
  return BigInt(m[1] + (m[2] ?? "").padEnd(9, "0")).toString();
}
