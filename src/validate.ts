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
