import { Command } from "commander";
import { OpenApiClient, TokenSignalGroup } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateAddress, validateChain } from "../validate.js";

// Parse token age string. If a unit suffix is present (s/m), use it as-is.
// Bare numbers (no unit) are treated as minutes with a warning.
function parseDuration(value: string): string {
  if (/^\d+(\.\d+)?[sm]$/.test(value)) return value;
  if (/^\d+(\.\d+)?$/.test(value)) {
    console.warn(
      `[gmgn-cli] Warning: no unit specified for duration "${value}" — treating as minutes (${value}m). Use a suffix to be explicit: ${value}s for seconds or ${value}m for minutes.`
    );
    return `${value}m`;
  }
  console.error(
    `[gmgn-cli] Invalid duration "${value}". Use seconds (e.g. 30s) or minutes (e.g. 0.5m / 1m / 5m).`
  );
  process.exit(1);
}

export function registerMarketCommands(program: Command): void {
  const market = program.command("market").description("Market data commands");

  market
    .command("kline")
    .description("Get token K-line (candlestick) data")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--address <address>", "Token contract address")
    .requiredOption("--resolution <resolution>", "Candlestick resolution: 1m / 5m / 15m / 1h / 4h / 1d")
    .option("--from <timestamp>", "Start time (Unix seconds)", parseInt)
    .option("--to <timestamp>", "End time (Unix seconds)", parseInt)
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      validateAddress(opts.address, opts.chain, "--address");
      const client = new OpenApiClient(getConfig());
      const data = await client
        .getTokenKline(
          opts.chain,
          opts.address,
          opts.resolution,
          opts.from != null ? opts.from * 1000 : undefined,
          opts.to != null ? opts.to * 1000 : undefined
        )
        .catch(exitOnError);
      printResult(data, opts.raw);
    });

  market
    .command("trending")
    .description("Get trending token swap data")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .requiredOption("--interval <interval>", "Time interval: 1m / 5m / 1h / 6h / 24h")
    .option("--limit <n>", "Number of results (default 100, max 100)", parseInt)
    .option("--order-by <field>", "Sort field: default / volume / swaps / marketcap / holder_count / price / change1h / ... (see docs for full list)")
    .option("--direction <dir>", "Sort direction: asc / desc")
    .option("--filter <tag...>", "Filter tags, repeatable. sol: renounced / frozen / has_social / not_wash_trading / ... evm: not_honeypot / verified / renounced / locked / ... (see docs for full list)")
    .option("--platform <name...>", "Platform filter, repeatable. sol: Pump.fun / letsbonk / moonshot_app / ... bsc: fourmeme / flap / clanker / ... base: clanker / flaunch / zora / ... (see docs for full list)")
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      validateChain(opts.chain);
      const extra: Record<string, string | number | string[]> = {};
      if (opts.limit != null) extra["limit"] = opts.limit;
      if (opts.orderBy) extra["order_by"] = opts.orderBy;
      if (opts.direction) extra["direction"] = opts.direction;
      if (opts.filter?.length) extra["filters"] = opts.filter;
      if (opts.platform?.length) extra["platforms"] = opts.platform;

      const client = new OpenApiClient(getConfig());
      const data = await client.getTrendingSwaps(opts.chain, opts.interval, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });

  const trenchesCmd = market
    .command("trenches")
    .description("Get Trenches token data (new creation, near completion, completed)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base")
    .option("--type <type...>", "Categories to query, repeatable: new_creation / near_completion / completed (default: all three)")
    .option("--launchpad-platform <platform...>", "Launchpad platform filter, repeatable (default: all platforms for the chain)")
    .option("--limit <n>", "Max results per category, max 80 (default: 80)", parseInt)
    .option("--filter-preset <preset>", "Apply a named filter preset: safe / smart-money / strict")
    .option("--sort-by <field>", "Client-side sort per category: smart_degen_count / renowned_count / volume_24h / volume_1h / swaps_24h / swaps_1h / rug_ratio / holder_count / usd_market_cap / created_timestamp")
    .option("--direction <dir>", "Sort direction: asc / desc (default: desc; asc for rug_ratio)")
    .option("--raw", "Output raw JSON");

  // Dynamically register all server-side filter flags
  for (const def of TRENCHES_FILTER_FIELDS) {
    const flag = def.api.replace(/_/g, '-');
    if (def.type === "int") {
      trenchesCmd.option(`--${flag} <${def.type}>`, def.desc, parseInt);
    } else if (def.type === "float") {
      trenchesCmd.option(`--${flag} <${def.type}>`, def.desc, parseFloat);
    } else if (def.type === "duration") {
      trenchesCmd.option(`--${flag} <duration>`, def.desc, parseDuration);
    } else {
      trenchesCmd.option(`--${flag} <value>`, def.desc);
    }
  }

  trenchesCmd.action(async (opts) => {
    validateChain(opts.chain);
    const client = new OpenApiClient(getConfig());

    // Build server-side filter object
    const filters: Record<string, number | string> = {};

    // Apply preset values first
    if (opts.filterPreset != null) {
      const preset = TRENCHES_FILTER_PRESETS[opts.filterPreset as string];
      if (!preset) {
        console.error(`Unknown --filter-preset "${opts.filterPreset}". Valid options: ${Object.keys(TRENCHES_FILTER_PRESETS).join(", ")}`);
        process.exit(1);
      }
      Object.assign(filters, preset);
    }

    // Apply individual filter flags (override preset values)
    const optsMap = opts as Record<string, unknown>;
    for (const def of TRENCHES_FILTER_FIELDS) {
      const key = apiFieldToCliKey(def.api);
      const val = optsMap[key];
      if (val != null) filters[def.api] = val as number | string;
    }

    const data = await client
      .getTrenches(opts.chain, opts.type, opts.launchpadPlatform, opts.limit, Object.keys(filters).length ? filters : undefined)
      .catch(exitOnError);

    const result = opts.sortBy
      ? sortTrenchesResult(data as Record<string, unknown>, opts.sortBy as string, (opts.direction as string) ?? "")
      : data;
    printResult(result, opts.raw);
  });

  market
    .command("signal")
    .description("Query token signals (price spikes, smart money buys, large buys, etc.) — max 50 results per group")
    .requiredOption("--chain <chain>", "Chain: sol / bsc")
    .option("--signal-type <n...>", "Signal type(s), repeatable: 1–18 (default: all types)", (v: string, acc: number[]) => { acc.push(parseInt(v, 10)); return acc; }, [] as number[])
    .option("--mc-min <usd>", "Min market cap at trigger time (USD)", parseFloat)
    .option("--mc-max <usd>", "Max market cap at trigger time (USD)", parseFloat)
    .option("--trigger-mc-min <usd>", "Min market cap at signal trigger (USD)", parseFloat)
    .option("--trigger-mc-max <usd>", "Max market cap at signal trigger (USD)", parseFloat)
    .option("--total-fee-min <usd>", "Min total fees paid (USD)", parseFloat)
    .option("--total-fee-max <usd>", "Max total fees paid (USD)", parseFloat)
    .option("--min-create-or-open-ts <ts>", "Min token creation or open timestamp (Unix seconds string)")
    .option("--max-create-or-open-ts <ts>", "Max token creation or open timestamp (Unix seconds string)")
    .option("--groups <json>", "Multi-group override: JSON array of group objects — overrides all individual flags when provided")
    .option("--raw", "Output raw JSON")
    .action(async (opts: Record<string, unknown>) => {
      validateChain(opts["chain"] as string);
      if (!["sol", "bsc"].includes(opts["chain"] as string)) {
        console.error(`[gmgn-cli] market signal only supports sol and bsc, got "${opts["chain"]}"`);
        process.exit(1);
      }

      let groups: TokenSignalGroup[];
      if (opts["groups"] != null) {
        try {
          groups = JSON.parse(opts["groups"] as string) as TokenSignalGroup[];
        } catch {
          console.error(`[gmgn-cli] --groups must be a valid JSON array, e.g. '[{"signal_type":[12,14]},{"signal_type":[6,7],"mc_min":50000}]'`);
          process.exit(1);
        }
      } else {
        const group: TokenSignalGroup = {};
        const signalType = opts["signalType"] as number[] | undefined;
        if (signalType?.length) group.signal_type = signalType;
        if (opts["mcMin"] != null) group.mc_min = opts["mcMin"] as number;
        if (opts["mcMax"] != null) group.mc_max = opts["mcMax"] as number;
        if (opts["triggerMcMin"] != null) group.trigger_mc_min = opts["triggerMcMin"] as number;
        if (opts["triggerMcMax"] != null) group.trigger_mc_max = opts["triggerMcMax"] as number;
        if (opts["totalFeeMin"] != null) group.total_fee_min = opts["totalFeeMin"] as number;
        if (opts["totalFeeMax"] != null) group.total_fee_max = opts["totalFeeMax"] as number;
        if (opts["minCreateOrOpenTs"] != null) group.min_create_or_open_ts = opts["minCreateOrOpenTs"] as string;
        if (opts["maxCreateOrOpenTs"] != null) group.max_create_or_open_ts = opts["maxCreateOrOpenTs"] as string;
        groups = [group];
      }

      const client = new OpenApiClient(getConfig());
      const data = await client.getTokenSignalV2(opts["chain"] as string, groups).catch(exitOnError);
      printResult(data, opts["raw"] as boolean | undefined);
    });
}

// ---- Trenches filter field definitions ----

type TrenchesFieldType = "int" | "float" | "string" | "duration";

interface TrenchesFilterField {
  api: string;
  type: TrenchesFieldType;
  desc: string;
}

// All server-side filter fields for market trenches
// API field names map to CLI flags by replacing _ with - (e.g. min_volume_24h → --min-volume-24h)
const TRENCHES_FILTER_FIELDS: TrenchesFilterField[] = [
  // Trading activity (24h)
  { api: "min_volume_24h",    type: "float",  desc: "Min 24h trading volume (USD)" },
  { api: "max_volume_24h",    type: "float",  desc: "Max 24h trading volume (USD)" },
  { api: "min_net_buy_24h",   type: "float",  desc: "Min 24h net buy volume (USD)" },
  { api: "max_net_buy_24h",   type: "float",  desc: "Max 24h net buy volume (USD)" },
  { api: "min_swaps_24h",     type: "int",    desc: "Min 24h total swap count" },
  { api: "max_swaps_24h",     type: "int",    desc: "Max 24h total swap count" },
  { api: "min_buys_24h",      type: "int",    desc: "Min 24h buy count" },
  { api: "max_buys_24h",      type: "int",    desc: "Max 24h buy count" },
  { api: "min_sells_24h",     type: "int",    desc: "Min 24h sell count" },
  { api: "max_sells_24h",     type: "int",    desc: "Max 24h sell count" },
  { api: "min_visiting_count", type: "int",   desc: "Min visitor count" },
  { api: "max_visiting_count", type: "int",   desc: "Max visitor count" },
  // Market & liquidity
  { api: "min_progress",      type: "float",  desc: "Min bonding curve progress (0–1)" },
  { api: "max_progress",      type: "float",  desc: "Max bonding curve progress (0–1, 1 = completed)" },
  { api: "min_marketcap",     type: "float",  desc: "Min market cap (USD)" },
  { api: "max_marketcap",     type: "float",  desc: "Max market cap (USD)" },
  { api: "min_liquidity",     type: "float",  desc: "Min liquidity (USD)" },
  { api: "max_liquidity",     type: "float",  desc: "Max liquidity (USD)" },
  // Token age
  { api: "min_created",       type: "duration", desc: "Min token age — unit required: seconds (e.g. 30s) or minutes (e.g. 0.5m / 1m / 5m / 30m / 1h)" },
  { api: "max_created",       type: "duration", desc: "Max token age — unit required: seconds (e.g. 30s) or minutes (e.g. 0.5m / 1m / 5m / 30m / 1h)" },
  // Holders
  { api: "min_holder_count",  type: "int",    desc: "Min holder count" },
  { api: "max_holder_count",  type: "int",    desc: "Max holder count" },
  { api: "min_top_holder_rate",       type: "float", desc: "Min top-10 holder concentration (0–1)" },
  { api: "max_top_holder_rate",       type: "float", desc: "Max top-10 holder concentration (0–1)" },
  // Risk signals
  { api: "min_rug_ratio",     type: "float",  desc: "Min rug pull risk score (0–1)" },
  { api: "max_rug_ratio",     type: "float",  desc: "Max rug pull risk score (0–1, e.g. 0.3 to exclude rugs)" },
  { api: "min_bundler_rate",  type: "float",  desc: "Min bundle-bot trading ratio (0–1)" },
  { api: "max_bundler_rate",  type: "float",  desc: "Max bundle-bot trading ratio (0–1)" },
  { api: "min_insider_ratio", type: "float",  desc: "Min insider trading ratio (0–1)" },
  { api: "max_insider_ratio", type: "float",  desc: "Max insider trading ratio (0–1)" },
  { api: "min_entrapment_ratio",      type: "float", desc: "Min entrapment trading ratio (0–1)" },
  { api: "max_entrapment_ratio",      type: "float", desc: "Max entrapment trading ratio (0–1)" },
  { api: "min_private_vault_hold_rate", type: "float", desc: "Min private vault holding ratio (0–1)" },
  { api: "max_private_vault_hold_rate", type: "float", desc: "Max private vault holding ratio (0–1)" },
  { api: "min_top70_sniper_hold_rate",  type: "float", desc: "Min top-70 sniper holding ratio (0–1)" },
  { api: "max_top70_sniper_hold_rate",  type: "float", desc: "Max top-70 sniper holding ratio (0–1)" },
  { api: "min_bot_count",     type: "int",    desc: "Min bot wallet count" },
  { api: "max_bot_count",     type: "int",    desc: "Max bot wallet count" },
  { api: "min_bot_degen_rate",        type: "float", desc: "Min bot-degen wallet ratio (0–1)" },
  { api: "max_bot_degen_rate",        type: "float", desc: "Max bot-degen wallet ratio (0–1)" },
  { api: "min_fresh_wallet_rate",     type: "float", desc: "Min fresh wallet ratio (0–1)" },
  { api: "max_fresh_wallet_rate",     type: "float", desc: "Max fresh wallet ratio (0–1)" },
  { api: "min_total_fee",             type: "float", desc: "Min total fee" },
  { api: "max_total_fee",             type: "float", desc: "Max total fee" },
  // Smart money
  { api: "min_smart_degen_count",     type: "int",   desc: "Min smart-money holder count" },
  { api: "max_smart_degen_count",     type: "int",   desc: "Max smart-money holder count" },
  { api: "min_renowned_count",        type: "int",   desc: "Min KOL / renowned wallet count" },
  { api: "max_renowned_count",        type: "int",   desc: "Max KOL / renowned wallet count" },
  // Dev / creator
  { api: "min_creator_balance_rate",        type: "float", desc: "Min creator holding ratio (0–1)" },
  { api: "max_creator_balance_rate",        type: "float", desc: "Max creator holding ratio (0–1)" },
  { api: "min_creator_created_count",       type: "int",   desc: "Min creator total token creation count" },
  { api: "max_creator_created_count",       type: "int",   desc: "Max creator total token creation count" },
  { api: "min_creator_created_open_count",  type: "int",   desc: "Min creator graduated token count" },
  { api: "max_creator_created_open_count",  type: "int",   desc: "Max creator graduated token count" },
  { api: "min_creator_created_open_ratio",  type: "float", desc: "Min creator graduation ratio (0–1)" },
  { api: "max_creator_created_open_ratio",  type: "float", desc: "Max creator graduation ratio (0–1)" },
  // Social
  { api: "min_x_follower",            type: "int",   desc: "Min Twitter / X follower count" },
  { api: "max_x_follower",            type: "int",   desc: "Max Twitter / X follower count" },
  { api: "min_twitter_rename_count",  type: "int",   desc: "Min Twitter rename count (high = suspicious)" },
  { api: "max_twitter_rename_count",  type: "int",   desc: "Max Twitter rename count" },
  { api: "min_tg_call_count",         type: "int",   desc: "Min Telegram call count" },
  { api: "max_tg_call_count",         type: "int",   desc: "Max Telegram call count" },
];

// Named filter presets using actual server-side API field names
const TRENCHES_FILTER_PRESETS: Record<string, Record<string, number | string>> = {
  safe: {
    max_rug_ratio: 0.3,
    max_bundler_rate: 0.3,
    max_insider_ratio: 0.3,
  },
  "smart-money": {
    min_smart_degen_count: 1,
  },
  strict: {
    max_rug_ratio: 0.3,
    max_bundler_rate: 0.3,
    max_insider_ratio: 0.3,
    min_smart_degen_count: 1,
    min_volume_24h: 1000,
  },
};

// Convert API snake_case field to Commander.js opts key
// Commander.js camelCase: only converts -[a-z] patterns, digits stay as-is
// e.g. min_volume_24h → min-volume-24h → minVolume-24h (digit prefix -24 is NOT converted)
// e.g. min_smart_degen_count → min-smart-degen-count → minSmartDegenCount (all letters, converts fully)
function apiFieldToCliKey(apiField: string): string {
  return apiField
    .replace(/_/g, '-')
    .replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
}

// Client-side sort helpers (API does not support server-side sort for trenches)
interface TrenchesCategory {
  [key: string]: unknown;
}

const TRENCHES_SORT_ASC_DEFAULTS = new Set(["rug_ratio"]);
const TRENCHES_STRING_NUMERIC_FIELDS = new Set(["usd_market_cap", "liquidity", "volume_1h", "volume_24h"]);

function sortTrenchesCategory(items: TrenchesCategory[], sortBy: string, direction: string): TrenchesCategory[] {
  const dir = direction || (TRENCHES_SORT_ASC_DEFAULTS.has(sortBy) ? "asc" : "desc");
  return [...items].sort((a, b) => {
    const aVal = TRENCHES_STRING_NUMERIC_FIELDS.has(sortBy)
      ? parseFloat(String(a[sortBy] ?? 0))
      : Number(a[sortBy] ?? 0);
    const bVal = TRENCHES_STRING_NUMERIC_FIELDS.has(sortBy)
      ? parseFloat(String(b[sortBy] ?? 0))
      : Number(b[sortBy] ?? 0);
    return dir === "asc" ? aVal - bVal : bVal - aVal;
  });
}

function sortTrenchesResult(data: Record<string, unknown>, sortBy: string, direction: string): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(data)) {
    result[key] = Array.isArray(val) ? sortTrenchesCategory(val as TrenchesCategory[], sortBy, direction) : val;
  }
  return result;
}
