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
 *   1. Interactive terminal (default): the confirmation block is written to, and
 *      a typed "yes" is read from, the controlling TTY (/dev/tty) — NOT
 *      stdout/stderr/stdin. An autonomous agent driving the CLI over a pipe
 *      cannot answer this prompt or filter what the human reads, and no text in
 *      the agent's context can satisfy it — a real human must be present.
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
 * are NOT in effect, and everything else). Section 4 is by definition "every leaf
 * the first three did not print", so a newly added parameter shows up
 * automatically.
 *
 * Once confirmed, the sha256 of the canonical {method, path, query, body} is
 * recorded. The API client refuses to sign ANY non-GET request whose digest was
 * not confirmed (see consumeConfirmation), which catches a new command or route
 * that forgot to call confirmTrade, a body or query mutated after confirmation,
 * and a confirmation replayed against a different route.
 *
 * If neither confirmation path is satisfied, the trade is refused before any
 * signature is made.
 */

import { createHash } from "node:crypto";
import { openSync, readSync, writeSync, closeSync, existsSync } from "node:fs";

const AUTOMATION_ENV = "GMGN_ALLOW_AUTOMATED_TRADES";

// Blob fields (e.g. a base64 --image) longer than this are folded to
// <string, size, sha256> so they do not scroll the rest of the summary away.
// Only fields a command declares in blobFields are ever folded.
const FOLD_THRESHOLD = 256;

export type Body = Record<string, unknown>;

export interface Protection {
  text: string; // printed when the protection is not in effect
  isSet: (body: Body) => boolean; // judged on the values actually being sent
}

export interface TradeSummary {
  action: string; // e.g. "Swap", "Create token", "Create strategy order"
  route: string; // API path the body is POSTed to; bound into the digest
  params: object; // the exact object that will be signed and sent
  keyFields: string[]; // top-level fields shown first, in this order
  blobFields?: string[]; // top-level fields that may be folded (e.g. image)
  protections?: Protection[];
  totals?: string[]; // derived totals whose meaning only the command knows
  feeLabel?: string; // label for the top-level tip / priority fee total
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

// ---- Protections shared by several commands ----

export const SLIPPAGE_PROTECTION: Protection = {
  text: "No slippage limit — neither a positive slippage nor auto_slippage is sent, so the server default applies.",
  isSet: (b) => b.auto_slippage === true || (typeof b.slippage === "number" && b.slippage > 0),
};

export const MIN_OUTPUT_PROTECTION: Protection = {
  text: "No minimum-received floor (min_output_amount missing or 0) — only slippage bounds what you get back.",
  isSet: (b) => typeof b.min_output_amount === "string" && /^\d+$/.test(b.min_output_amount) && /[1-9]/.test(b.min_output_amount),
};

export const EXPIRY_PROTECTION: Protection = {
  text: "No expiry (expire_in missing or 0) — the order stays live for the server-default lifetime.",
  isSet: (b) => typeof b.expire_in === "number" && b.expire_in > 0,
};

const ANTI_MEV_CHAINS = new Set(["sol", "bsc", "eth"]);

// For commands whose anti-MEV default is not documented as on: warn only where
// the flag is supported, and say what actually happens.
export const ANTI_MEV_PROTECTION: Protection = {
  text: "Anti-MEV protection not requested (is_anti_mev not sent) — the server default applies.",
  isSet: (b) => b.is_anti_mev === true || !ANTI_MEV_CHAINS.has(String(b.chain)),
};

const confirmedDigests = new Set<string>();

/**
 * Enforce human confirmation for a financial write. Shows a summary derived
 * from the request body, then either reads an interactive "yes" from the TTY or
 * verifies the explicit automation opt-in. Aborts the process if confirmation is
 * not obtained; on success records the request digest for consumeConfirmation.
 */
export function confirmTrade(summary: TradeSummary, assumeYes: boolean): void {
  // Render from the JSON round-trip, i.e. exactly what JSON.stringify will put on
  // the wire (undefined dropped, NaN → null).
  const payload = JSON.parse(JSON.stringify(summary.params)) as Body;
  const block = renderSummary(summary, payload).join("\n") + "\n";
  // Queries on fund-moving routes are always empty today; the client binds the
  // real query into its digest, so a future query parameter fails closed here.
  const digest = requestDigest("POST", summary.route, {}, payload);

  if (assumeYes) {
    process.stderr.write(block);
    if (process.env[AUTOMATION_ENV] === "1") {
      console.error(
        `[gmgn-cli] Proceeding non-interactively (--yes + ${AUTOMATION_ENV}=1).`
      );
      confirmedDigests.add(digest);
      return;
    }
    // --yes alone is deliberately NOT enough: an injected agent can pass it.
    abort(
      `--yes was supplied but ${AUTOMATION_ENV}=1 is not set in the environment. ` +
        `Non-interactive trade execution is disabled by default. If you truly intend ` +
        `to allow automated trades, set ${AUTOMATION_ENV}=1 in your own shell first.`
    );
  }

  const tty = openTty();
  if (tty == null) {
    process.stderr.write(block);
    abort(
      `No interactive terminal available to confirm this ${summary.action.toLowerCase()}. ` +
        `Refusing to execute a financial transaction without human confirmation. ` +
        `For intentional automation, set ${AUTOMATION_ENV}=1 and pass --yes.`
    );
  }

  let answer: string | null;
  try {
    // Written to the terminal itself, so whoever launched the process cannot
    // filter or rewrite what the human reads before typing "yes".
    tty.write(block);
    tty.write(`\nType "yes" to confirm this ${summary.action.toLowerCase()}, anything else to cancel: `);
    answer = tty.readLine();
  } finally {
    tty.close();
  }

  if (answer == null || answer.trim().toLowerCase() !== "yes") {
    abort("Confirmation not received. Transaction cancelled.");
  }

  confirmedDigests.add(digest);
}

/**
 * Check that a request about to be signed is exactly one the user confirmed, and
 * consume that confirmation so it authorizes a single signature.
 */
export function consumeConfirmation(method: string, path: string, query: unknown, body: string): boolean {
  const digest = requestDigest(method, path, query, body === "" ? null : JSON.parse(body));
  return confirmedDigests.delete(digest);
}

function requestDigest(method: string, path: string, query: unknown, body: unknown): string {
  return createHash("sha256").update(canonicalJson({ method, path, query, body })).digest("hex");
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
      const childPath = /^\w+$/.test(k)
        ? (path ? `${path}.${k}` : k)
        : `${path}[${escapeText(JSON.stringify(k))}]`;
      flatten((value as Record<string, unknown>)[k], childPath, [...segments, k], out);
    }
  } else {
    out.push({ path, segments, value });
  }
  return out;
}

function renderSummary(summary: TradeSummary, payload: Body): string[] {
  const header = `⚠️  ${summary.action} — confirmation required`;
  const out = [`\n${header}`, "-".repeat(header.length), "  Every field below is part of the request that will be signed."];

  const leaves = flatten(payload);
  const blobs = new Set(summary.blobFields ?? []);
  const printed = new Set<Leaf>();
  const line = (leaf: Leaf, indent = "    ") => {
    const note = summary.annotations?.[leaf.path];
    const value = renderValue(leaf.value, blobs.has(leaf.segments[0]));
    out.push(`${indent}${leaf.path} = ${value}${note ? `  (${displayText(note)})` : ""}`);
    printed.add(leaf);
  };

  // ① Key fields, in the order the command lists them, then derived totals.
  out.push("", "  ① Key fields");
  for (const field of summary.keyFields) {
    for (const leaf of leaves) {
      if (leaf.segments[0] === field) line(leaf);
    }
  }
  for (const total of [...(summary.totals ?? []), ...feeTotals(leaves, String(payload.chain), summary.feeLabel)]) {
    out.push(`    ${total}`);
  }

  // ② Risky fields, grouped by rule, each with its consequence. Never folded.
  const byRule = new Map<string, Leaf[]>();
  for (const leaf of leaves) {
    if (printed.has(leaf)) continue;
    const field = leaf.segments.find((s) => RISK_FIELDS.has(s));
    if (field == null) continue;
    const group = byRule.get(field);
    if (group) group.push(leaf);
    else byRule.set(field, [leaf]);
  }
  out.push("", "  ② ⚠️  What else this transaction will do");
  if (byRule.size === 0) out.push("    (nothing beyond the key fields)");
  for (const rule of RISK_RULES) {
    const group = byRule.get(rule.field);
    if (!group) continue;
    out.push(`    ${rule.field} — ${rule.consequence}`);
    for (const leaf of group) line(leaf, "      ");
  }

  // ③ Protections NOT in effect — removing or zeroing a field is an attack too.
  const missing = (summary.protections ?? []).filter((p) => !p.isSet(payload));
  out.push("", "  ③ ⚠️  Protections NOT in effect");
  if (missing.length === 0) out.push("    (none)");
  for (const p of missing) out.push(`    - ${p.text}`);

  // ④ Everything the first three sections did not print.
  const rest = leaves.filter((leaf) => !printed.has(leaf));
  out.push("", "  ④ All other fields");
  if (rest.length === 0) out.push("    (none)");
  for (const leaf of rest) line(leaf);

  return out;
}

// "Extra fees: tip 5 SOL + priority 0.1 SOL = 5.1 SOL", one line per object that
// carries tip_fee / priority_fee — the top level and every nested trade config
// (sell_param, buy_trade_config, ...), since each pays for its own transaction.
function feeTotals(leaves: Leaf[], chain: string, topLabel = "Extra fees"): string[] {
  const groups = new Map<string, Array<[string, string]>>();
  for (const leaf of leaves) {
    const name = leaf.segments[leaf.segments.length - 1];
    if (name !== "tip_fee" && name !== "priority_fee") continue;
    const container = leaf.path.slice(0, -(name.length + 1));
    const group = groups.get(container) ?? [];
    group.push([name === "tip_fee" ? "tip" : "priority", String(leaf.value)]);
    groups.set(container, group);
  }
  const unit = nativeSymbol(chain);
  return [...groups].map(([container, parts]) => {
    const terms = parts.map(([name, v]) => `${name} ${displayText(v)} ${unit}`).join(" + ");
    const total = parts.length > 1 ? ` = ${sumDecimals(parts.map(([, v]) => v)) ?? "?"} ${unit}` : "";
    return `${container ? `Extra fees in ${container}` : topLabel}: ${terms}${total}`;
  });
}

function renderValue(value: unknown, foldable: boolean): string {
  if (Array.isArray(value)) return "[]";
  if (value !== null && typeof value === "object") return "{}";
  if (typeof value !== "string") return String(value);
  if (foldable && value.length > FOLD_THRESHOLD) {
    const sha = createHash("sha256").update(value).digest("hex").slice(0, 12);
    return `<string, ${formatBytes(Buffer.byteLength(value, "utf8"))}, sha256 ${sha}…>`;
  }
  return escapeText(JSON.stringify(value));
}

// Anything that is not a plainly visible character is shown as an escape:
// control / format / unassigned / private-use (\p{C}), separators other than the
// ASCII space (\p{Z}), combining marks (\p{M}), default-ignorable code points
// (soft hyphen, Hangul fillers, variation selectors, tag characters...) and the
// blank braille pattern. Any of these can make one value look like another.
const UNSAFE_CHARS_RE = /[\p{C}\p{Z}\p{M}\p{Default_Ignorable_Code_Point}\u2800]/gu;

function escapeText(s: string): string {
  return s.replace(UNSAFE_CHARS_RE, (ch) => {
    if (ch === " ") return ch;
    const cp = ch.codePointAt(0)!;
    return cp > 0xffff ? `\\u{${cp.toString(16)}}` : `\\u${cp.toString(16).padStart(4, "0")}`;
  });
}

/** Quote-free, escaped rendering of untrusted text for the confirmation block. */
export function displayText(s: string): string {
  return escapeText(JSON.stringify(s).slice(1, -1));
}

function formatBytes(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

// Only chains whose gas token the docs name; the rest are labelled by chain.
const NATIVE_SYMBOLS: Record<string, string> = {
  sol: "SOL",
  bsc: "BNB",
  base: "ETH",
  eth: "ETH",
  arbitrum: "ETH",
  hyperevm: "HYPE",
};

export function nativeSymbol(chain: string): string {
  return NATIVE_SYMBOLS[chain] ?? `${chain} native token`;
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

interface Tty {
  write(s: string): void;
  readLine(): string | null;
  close(): void;
}

/**
 * Open the controlling terminal (/dev/tty, or CONIN$/CONOUT$ on Windows),
 * bypassing stdio so a piped/automated caller can neither supply the answer nor
 * alter the text shown. Returns null if no TTY is available (e.g. headless CI,
 * agent driving the CLI over a pipe).
 */
function openTty(): Tty | null {
  const win = process.platform === "win32";
  if (!win && !existsSync("/dev/tty")) return null;

  let inFd: number | undefined;
  let outFd: number;
  try {
    inFd = openSync(win ? "CONIN$" : "/dev/tty", "r");
    outFd = openSync(win ? "CONOUT$" : "/dev/tty", "w");
  } catch {
    if (inFd !== undefined) closeSync(inFd);
    return null;
  }
  const fdIn = inFd;

  return {
    write: (s) => {
      writeSync(outFd, s);
    },
    readLine: () => {
      const buf = Buffer.alloc(1);
      let line = "";
      while (true) {
        let bytes = 0;
        try {
          bytes = readSync(fdIn, buf, 0, 1, null);
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
    },
    close: () => {
      closeSync(fdIn);
      closeSync(outFd);
    },
  };
}

function abort(msg: string): never {
  console.error(`[gmgn-cli] ${msg}`);
  process.exit(1);
}
