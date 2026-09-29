/**
 * confirm.ts — code-enforced human-in-the-loop gate for financial writes.
 *
 * Commands that move real funds (swap, multi-swap, token creation, strategy
 * order creation / cancellation) must not execute on the say-so of an AI agent
 * alone. A hijacked agent — e.g. one that read a prompt-injection payload out of
 * token metadata — can emit any command line it wants, so a plain `--yes` flag is
 * not a real barrier: the injected instructions can just tell the agent to pass
 * `--yes`.
 *
 * This gate enforces confirmation in CODE, not in a SKILL.md instruction:
 *
 *   1. Interactive terminal (default): we read a typed "yes" directly from the
 *      controlling TTY (/dev/tty), NOT from stdin. An autonomous agent driving the
 *      CLI over a pipe cannot answer this prompt, and no text in the agent's
 *      context can satisfy it — a real human must be present at the keyboard.
 *
 *   2. Intentional automation: to run headless, the operator must BOTH pass
 *      `--yes` AND set the environment variable GMGN_ALLOW_AUTOMATED_TRADES=1 in
 *      their own shell, out of band. Requiring the env var (which the CLI never
 *      sets and an injected instruction should not know to set) plus the flag makes
 *      autonomous execution a deliberate, two-factor human decision.
 *
 * A confirmation is only meaningful if the human sees what will actually be
 * signed. So the summary is NOT hand-written per command: it is derived from the
 * exact request body, flattened to every leaf field, and printed in four sections
 * (key fields, risky fields with a plain-language consequence, protections that
 * are NOT set, and everything else). Section 4 is by definition "every leaf the
 * first three did not print", so a newly added parameter shows up automatically.
 *
 * Once confirmed, the canonical-JSON sha256 of that body is recorded. The API
 * client refuses to sign a fund-moving request whose body digest was not
 * confirmed (see consumeConfirmation), which catches both a new command that
 * forgot to call confirmTrade and a body mutated after confirmation.
 *
 * If neither confirmation path is satisfied, the trade is refused before any
 * signature is made.
 */

import { createHash } from "node:crypto";
import { openSync, readSync, closeSync, existsSync } from "node:fs";

const AUTOMATION_ENV = "GMGN_ALLOW_AUTOMATED_TRADES";

// Strings longer than this are folded to <string, size, sha256> so a 2MB base64
// image does not scroll the rest of the summary off screen. Risky fields are
// never folded.
const FOLD_THRESHOLD = 256;

export interface UnsetProtection {
  fields: string[]; // printed when NONE of these top-level fields is in the body
  text: string; // what the user is exposed to because of it
}

export interface TradeSummary {
  action: string; // e.g. "Swap", "Create token", "Create strategy order"
  params: object; // the exact object that will be signed and sent
  keyFields: string[]; // top-level fields shown first, in this order
  protections?: UnsetProtection[];
  totals?: string[]; // derived totals whose units only the command knows
  annotations?: Record<string, string>; // leaf path → unit hint, e.g. "0.05 gwei"
}

interface RiskRule {
  field: string;
  consequence: string;
}

// Fields that make the transaction do something beyond the headline trade. A
// leaf is claimed by the rule for the OUTERMOST matching path segment, so
// `sell_param.tip_fee` is shown under sell_param with its full path.
const RISK_RULES: RiskRule[] = [
  { field: "tip_fee", consequence: "Extra tip paid from your wallet on top of the trade (native token)." },
  { field: "priority_fee", consequence: "Extra priority fee paid from your wallet (SOL)." },
  { field: "fee", consequence: "Base fee / gas paid from your wallet." },
  { field: "gas_price", consequence: "Gas price you pay per unit of gas (wei)." },
  { field: "gas_level", consequence: "Gas price tier — higher tiers cost more." },
  { field: "auto_fee", consequence: "Fee selection is delegated to the trading bot; no cap is set here." },
  { field: "max_fee_per_gas", consequence: "Upper bound on the gas price you may pay." },
  { field: "max_priority_fee_per_gas", consequence: "Upper bound on the priority fee you may pay." },
  { field: "dev_gas", consequence: "Fee paid for the dev (creator) buy transaction." },
  { field: "dev_priority", consequence: "Priority fee paid for the dev (creator) buy transaction." },
  { field: "dev_tip", consequence: "Tip paid for the dev (creator) buy transaction." },
  { field: "dev_max_fee_per_gas", consequence: "Gas cap for the dev (creator) buy transaction." },
  { field: "check_price", consequence: "Trigger price — the order executes automatically once the market reaches it." },
  { field: "condition_orders", consequence: "Attaches automatic take-profit / stop-loss orders that SELL your position when triggered, without asking again." },
  { field: "sell_ratio_type", consequence: "Base used to size the automatic sells (buy amount vs. current holding)." },
  { field: "sell_param", consequence: "Trade params used when an automatic sell condition fires." },
  { field: "buy_param", consequence: "Trade params used for the buy leg of the strategy." },
  { field: "close_sell_model", consequence: "How the position is closed when the order is cancelled — may sell your tokens." },
  { field: "buy_wallets", consequence: "Additional wallets that buy at launch — each spends its buy_amt." },
  { field: "snip_buy_wallets", consequence: "Snipe wallets that buy right after launch — each spends its buy_amt." },
  { field: "buy_trade_config", consequence: "Execution params (fees / slippage) for the snipe and bundle buys." },
  { field: "sell_trade_config", consequence: "Execution params (fees / slippage) for the automatic sells." },
  { field: "sell_configs", consequence: "Auto-sell strategies created right after launch — they sell from the listed wallets automatically." },
  { field: "is_buy_back", consequence: "Agent auto-buyback — spends funds buying the token back automatically." },
  { field: "dev_wallet_bps", consequence: "Dev wallet fee share in basis points (100 = 1%)." },
  { field: "pump_fee_share_list", consequence: "Creator-fee split — these accounts receive the listed basis points of creator fees." },
  { field: "bags_fee_share_list", consequence: "Creator-fee split — these accounts receive the listed basis points of creator fees." },
  { field: "flap_rate_conf", consequence: "Token tax and fee routing baked into the token — rates and recipient addresses." },
  { field: "fourmeme_rate_conf", consequence: "Token fee routing baked into the token — rates and recipient address." },
];

const RISK_FIELDS = new Set(RISK_RULES.map((r) => r.field));

const confirmedDigests = new Set<string>();

/**
 * Enforce human confirmation for a financial write. Prints a summary derived
 * from the request body, then either reads an interactive "yes" from the TTY or
 * verifies the explicit automation opt-in. Aborts the process if confirmation is
 * not obtained; on success records the body digest for consumeConfirmation.
 */
export function confirmTrade(summary: TradeSummary, assumeYes: boolean): void {
  // Render from the JSON round-trip, i.e. exactly what JSON.stringify will put on
  // the wire (undefined dropped, NaN → null).
  const payload = JSON.parse(JSON.stringify(summary.params)) as Record<string, unknown>;
  printSummary(summary, payload);

  const automationOptIn = process.env[AUTOMATION_ENV] === "1";

  if (assumeYes) {
    if (automationOptIn) {
      console.error(
        `[gmgn-cli] Proceeding non-interactively (--yes + ${AUTOMATION_ENV}=1).`
      );
      confirmedDigests.add(payloadDigest(payload));
      return;
    }
    // --yes alone is deliberately NOT enough: an injected agent can pass it.
    abort(
      `--yes was supplied but ${AUTOMATION_ENV}=1 is not set in the environment. ` +
        `Non-interactive trade execution is disabled by default. If you truly intend ` +
        `to allow automated trades, set ${AUTOMATION_ENV}=1 in your own shell first.`
    );
  }

  const answer = readFromTty(
    `\nType "yes" to confirm this ${summary.action.toLowerCase()}, anything else to cancel: `
  );

  if (answer == null) {
    abort(
      `No interactive terminal available to confirm this ${summary.action.toLowerCase()}. ` +
        `Refusing to execute a financial transaction without human confirmation. ` +
        `For intentional automation, set ${AUTOMATION_ENV}=1 and pass --yes.`
    );
  }

  if (answer.trim().toLowerCase() !== "yes") {
    abort("Confirmation not received. Transaction cancelled.");
  }

  confirmedDigests.add(payloadDigest(payload));
}

/**
 * Check that a serialized request body is exactly one the user confirmed, and
 * consume that confirmation so it authorizes a single signature.
 */
export function consumeConfirmation(body: string): boolean {
  const digest = payloadDigest(JSON.parse(body));
  return confirmedDigests.delete(digest);
}

export function payloadDigest(payload: unknown): string {
  return createHash("sha256").update(canonicalJson(payload)).digest("hex");
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(canonicalJson).join(",")}]`;
  }
  if (value !== null && typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const entries = Object.keys(obj)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${canonicalJson(obj[k])}`);
    return `{${entries.join(",")}}`;
  }
  return JSON.stringify(value);
}

interface Leaf {
  path: string;
  segments: string[]; // object keys along the path, array indices dropped
  value: unknown; // primitive, or an empty array / object
}

function flatten(value: unknown, path = "", segments: string[] = [], out: Leaf[] = []): Leaf[] {
  if (Array.isArray(value)) {
    if (value.length === 0) out.push({ path, segments, value });
    value.forEach((item, i) => flatten(item, `${path}[${i}]`, segments, out));
  } else if (value !== null && typeof value === "object") {
    const keys = Object.keys(value);
    if (keys.length === 0) out.push({ path, segments, value });
    for (const k of keys) {
      const key = /^[A-Za-z0-9_]+$/.test(k) ? k : `[${escapeText(JSON.stringify(k))}]`;
      const childPath = path === "" ? key : key.startsWith("[") ? `${path}${key}` : `${path}.${key}`;
      flatten((value as Record<string, unknown>)[k], childPath, [...segments, k], out);
    }
  } else {
    out.push({ path, segments, value });
  }
  return out;
}

function printSummary(summary: TradeSummary, payload: Record<string, unknown>): void {
  const header = `⚠️  ${summary.action} — confirmation required`;
  console.error(`\n${header}`);
  console.error("-".repeat(header.length));
  console.error("  Every field below is part of the request that will be signed.");

  const leaves = flatten(payload);
  const printed = new Set<Leaf>();
  const line = (leaf: Leaf, fold: boolean, indent = "    ") => {
    const note = summary.annotations?.[leaf.path];
    console.error(`${indent}${leaf.path} = ${renderValue(leaf.value, fold)}${note ? `  (${note})` : ""}`);
    printed.add(leaf);
  };

  // ① Key fields, in the order the command lists them.
  console.error("\n  ① Key fields");
  for (const field of summary.keyFields) {
    for (const leaf of leaves) {
      if (leaf.segments[0] === field) line(leaf, true);
    }
  }
  for (const total of summary.totals ?? []) {
    console.error(`    ${total}`);
  }

  // ② Risky fields, grouped by rule, each with its consequence. Never folded.
  const keySet = new Set(summary.keyFields);
  const byRule = new Map<string, Leaf[]>();
  for (const leaf of leaves) {
    if (printed.has(leaf) || keySet.has(leaf.segments[0])) continue;
    const field = leaf.segments.find((s) => RISK_FIELDS.has(s));
    if (field == null) continue;
    byRule.set(field, [...(byRule.get(field) ?? []), leaf]);
  }
  console.error("\n  ② ⚠️  What else this transaction will do");
  if (byRule.size === 0) console.error("    (nothing beyond the key fields)");
  for (const rule of RISK_RULES) {
    const group = byRule.get(rule.field);
    if (!group) continue;
    console.error(`    ${rule.field} — ${rule.consequence}`);
    for (const leaf of group) line(leaf, false, "      ");
  }

  // ③ Protections that are NOT set — removing a field is an attack too.
  const missing = (summary.protections ?? []).filter((p) => p.fields.every((f) => !(f in payload)));
  console.error("\n  ③ ⚠️  Protections NOT set");
  if (missing.length === 0) console.error("    (none)");
  for (const p of missing) {
    console.error(`    - ${p.text}`);
  }

  // ④ Everything the first three sections did not print.
  const rest = leaves.filter((leaf) => !printed.has(leaf));
  console.error("\n  ④ All other fields");
  if (rest.length === 0) console.error("    (none)");
  for (const leaf of rest) line(leaf, true);
}

function renderValue(value: unknown, fold: boolean): string {
  if (Array.isArray(value)) return "[]";
  if (value !== null && typeof value === "object") return "{}";
  if (typeof value !== "string") return String(value);
  const bytes = Buffer.byteLength(value, "utf8");
  if (fold && value.length > FOLD_THRESHOLD) {
    const sha = createHash("sha256").update(value).digest("hex").slice(0, 12);
    return `<string, ${formatBytes(bytes)}, sha256 ${sha}…>`;
  }
  return escapeText(JSON.stringify(value));
}

// JSON.stringify escapes C0 controls but not C1 controls, bidi overrides or
// zero-width characters, any of which can hide or reorder what the human reads.
function escapeText(s: string): string {
  return s.replace(
    /[\u0080-\u009f\u200b-\u200f\u2028-\u202e\u2060-\u2064\u2066-\u2069\ufeff]/g,
    (ch) => `\\u${ch.charCodeAt(0).toString(16).padStart(4, "0")}`
  );
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

const NATIVE_SYMBOLS: Record<string, string> = {
  sol: "SOL",
  bsc: "BNB",
  base: "ETH",
  eth: "ETH",
  arbitrum: "ETH",
  hyperevm: "HYPE",
};

export function nativeSymbol(chain: string): string {
  return NATIVE_SYMBOLS[chain] ?? "native token";
}

/**
 * Exact decimal sum of amount strings. Returns null if any value is not a plain
 * non-negative decimal, so a malformed amount is never silently summed as 0.
 */
export function sumDecimals(values: string[]): string | null {
  if (!values.every((v) => /^\d+(\.\d+)?$/.test(v))) return null;
  const scale = Math.max(0, ...values.map((v) => (v.split(".")[1] ?? "").length));
  const total = values.reduce((acc, v) => {
    const [int, frac = ""] = v.split(".");
    return acc + BigInt(int + frac.padEnd(scale, "0"));
  }, 0n);
  const digits = total.toString().padStart(scale + 1, "0");
  if (scale === 0) return digits;
  const frac = digits.slice(-scale).replace(/0+$/, "");
  return frac ? `${digits.slice(0, -scale)}.${frac}` : digits.slice(0, -scale);
}

/**
 * "Extra fees: tip 5 SOL + priority 0.1 SOL = 5.1 SOL" for the tip / priority
 * fees in a body, or null when neither is set.
 */
export function extraFeeTotal(chain: string, tipFee?: string, priorityFee?: string, label = "Extra fees"): string | null {
  const parts: Array<[string, string]> = [];
  if (tipFee) parts.push(["tip", tipFee]);
  if (priorityFee) parts.push(["priority", priorityFee]);
  if (parts.length === 0) return null;
  const unit = nativeSymbol(chain);
  const terms = parts.map(([name, v]) => `${name} ${displayText(v)} ${unit}`).join(" + ");
  const total = sumDecimals(parts.map(([, v]) => v));
  return `${label}: ${terms}${parts.length > 1 ? ` = ${total ?? "?"} ${unit}` : ""}`;
}

/** Render a wei amount string as gwei for display, e.g. "50000000" → "0.05 gwei". */
function weiToGwei(wei: string): string | null {
  if (!/^\d+$/.test(wei)) return null;
  const padded = wei.padStart(10, "0");
  const int = padded.slice(0, -9).replace(/^0+(?=\d)/, "");
  const frac = padded.slice(-9).replace(/0+$/, "");
  return `${frac ? `${int}.${frac}` : int} gwei`;
}

/**
 * Unit hints for fields that are sent in wei, e.g. { gas_price: "wei = 0.05 gwei" }
 * (--gas-price on swap / strategy is typed in gwei and converted before sending).
 */
export function weiAnnotations<T extends object>(params: T, keys: Array<keyof T & string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of keys) {
    const v = params[k];
    const gwei = typeof v === "string" ? weiToGwei(v) : null;
    if (gwei) out[k] = `wei = ${gwei}`;
  }
  return out;
}

/** Quote-free, escaped rendering of untrusted text for the confirmation block. */
export function displayText(s: string): string {
  return escapeText(JSON.stringify(s)).slice(1, -1);
}

/**
 * Read a single line from the controlling terminal (/dev/tty), bypassing stdin so
 * a piped/automated caller cannot supply the answer. Returns null if no TTY is
 * available (e.g. headless CI, agent driving the CLI over a pipe).
 */
function readFromTty(prompt: string): string | null {
  const ttyPath = process.platform === "win32" ? "CONIN$" : "/dev/tty";
  if (process.platform !== "win32" && !existsSync(ttyPath)) {
    return null;
  }

  let fd: number;
  try {
    fd = openSync(ttyPath, "r");
  } catch {
    return null;
  }

  try {
    process.stderr.write(prompt);
    const buf = Buffer.alloc(1);
    let line = "";
    while (true) {
      let bytes = 0;
      try {
        bytes = readSync(fd, buf, 0, 1, null);
      } catch {
        return null;
      }
      if (bytes === 0) break; // EOF
      const ch = buf.toString("utf8", 0, 1);
      if (ch === "\n") break;
      if (ch === "\r") continue;
      line += ch;
    }
    return line;
  } finally {
    closeSync(fd);
  }
}

function abort(msg: string): never {
  console.error(`[gmgn-cli] ${msg}`);
  process.exit(1);
}
