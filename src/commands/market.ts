import { Command } from "commander";
import { OpenApiClient, TokenSignalGroup, HotSearchesParam } from "../client/OpenApiClient.js";
import { getConfig } from "../config.js";
import { exitOnError, printResult } from "../output.js";
import { validateAddress, validateChain, validateSearchChain, normalizeSearchQuery } from "../validate.js";

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

// --is-og / --is-launched are tri-state: true, false, or omitted (no filter at all).
// A plain boolean flag cannot express "false", so they take an explicit value.
function parseSearchBool(value: string, flag: string): string {
  if (value === "true" || value === "false") return value;
  console.error(`[gmgn-cli] Invalid ${flag} "${value}". Must be true or false.`);
  process.exit(1);
}

export function registerMarketCommands(program: Command): void {
  const market = program.command("market").description("Market data commands");

  market
    .command("kline")
    .description("Get token K-line (candlestick) data")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .requiredOption("--address <address>", "Token contract address")
    .requiredOption("--resolution <resolution>", "Candlestick resolution: 30s / 1m / 5m / 15m / 1h / 4h / 1d")
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

  const trendingCmd = market
    .command("trending")
    .description("Get trending token swap data")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
    .requiredOption("--interval <interval>", "Time interval: 1m / 5m / 1h / 6h / 24h")
    .option("--limit <n>", "Number of results (default 100, max 100)", parseInt)
    .option("--order-by <field>", "Sort field: default / volume / swaps / marketcap / holder_count / price / change1h / ... (see docs for full list)")
    .option("--direction <dir>", "Sort direction: asc / desc")
    .option("--filter <tag...>", "Filter tags, repeatable. sol: renounced / frozen / has_social / not_wash_trading / ... evm: not_honeypot / verified / renounced / locked / ... (see docs for full list)")
    .option("--platform <name...>", "Platform filter, repeatable. sol: Pump.fun / letsbonk / moonshot_app / ... bsc: fourmeme / four_xmode_agent / cubepeg / likwid / goplus_creator / goplus_skills / openfour / flap / flap_stocks / flap_aioracle / clanker / ... base: clanker / flaunch / zora / ... eth: trench / clanker / klik / livo / stroid / pool_uniswap_v2 / pool_uniswap_v3 / printr (see docs for full list)")
    .option("--raw", "Output raw JSON");

  // Dynamically register all server-side min_*/max_* range filter flags
  for (const def of RANK_RANGE_FIELDS) {
    const flag = def.api.replace(/_/g, "-");
    if (def.type === "int") {
      trendingCmd.option(`--${flag} <${def.type}>`, def.desc, parseInt);
    } else if (def.type === "float") {
      trendingCmd.option(`--${flag} <${def.type}>`, def.desc, parseFloat);
    } else {
      trendingCmd.option(`--${flag} <value>`, def.desc);
    }
  }

  trendingCmd.action(async (opts) => {
    validateChain(opts.chain);
    const extra: Record<string, string | number | string[]> = {};
    if (opts.limit != null) extra["limit"] = opts.limit;
    if (opts.orderBy) extra["order_by"] = opts.orderBy;
    if (opts.direction) extra["direction"] = opts.direction;
    if (opts.filter?.length) extra["filters"] = opts.filter;
    if (opts.platform?.length) extra["platforms"] = opts.platform;

    // Apply server-side min_*/max_* range filters
    const optsMap = opts as Record<string, unknown>;
    for (const def of RANK_RANGE_FIELDS) {
      const val = optsMap[apiFieldToCliKey(def.api)];
      if (val != null) extra[def.api] = val as string | number;
    }

    const client = new OpenApiClient(getConfig());
    const data = await client.getTrendingSwaps(opts.chain, opts.interval, extra).catch(exitOnError);
    printResult(data, opts.raw);
  });

  const trenchesCmd = market
    .command("trenches")
    .description("Get Trenches token data (new creation, near completion, completed)")
    .requiredOption("--chain <chain>", "Chain: sol / bsc / base / eth / robinhood / arc / stable")
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
    .requiredOption("--chain <chain>", "Chain: sol / bsc / robinhood / arc / stable")
    .option("--signal-type <n...>", "Signal type(s), repeatable: 1–21 (default: all types)", (v: string, acc: number[]) => { acc.push(parseInt(v, 10)); return acc; }, [] as number[])
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
      if (!["sol", "bsc", "robinhood", "arc", "stable"].includes(opts["chain"] as string)) {
        console.error(`[gmgn-cli] market signal only supports sol, bsc, robinhood, arc and stable, got "${opts["chain"]}"`);
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

  const hotSearchesCmd = market
    .command("hot-searches")
    .description("Get the hot-search ranking (most-searched tokens) for one or more chains")
    .option("--chain <chain...>", "Chain(s), repeatable: sol / bsc / base / eth / robinhood / arc / stable (default: all default chains)")
    .option("--interval <interval>", "Time window: 1m / 5m / 1h / 6h / 24h (default 24h)", "24h")
    .option("--limit <n>", "Max results per chain (default 500)", parseInt)
    .option("--filter <tag...>", "Boolean filter tags, repeatable. sol defaults: renounced / frozen; EVM defaults: not_honeypot / verified / renounced")
    .option("--params <json>", "Full params override: JSON array of param objects — overrides --chain/--interval/--limit/--filter and all range flags when provided")
    .option("--raw", "Output raw JSON");

  // Reuse the same min_*/max_* range flags as `market trending` — the hot_searches
  // endpoint accepts the identical rank-style metric names inside `filter` and
  // translates them server-side per interval (min_created/max_created are durations).
  for (const def of RANK_RANGE_FIELDS) {
    const flag = def.api.replace(/_/g, "-");
    if (def.type === "int") {
      hotSearchesCmd.option(`--${flag} <${def.type}>`, def.desc, parseInt);
    } else if (def.type === "float") {
      hotSearchesCmd.option(`--${flag} <${def.type}>`, def.desc, parseFloat);
    } else if (def.type === "duration") {
      hotSearchesCmd.option(`--${flag} <duration>`, def.desc, parseDuration);
    } else {
      hotSearchesCmd.option(`--${flag} <value>`, def.desc);
    }
  }

  hotSearchesCmd.action(async (opts) => {
    const interval = String(opts.interval);
    if (!HOT_SEARCHES_INTERVALS.has(interval)) {
      console.error(`[gmgn-cli] Invalid --interval "${interval}". Must be one of: ${[...HOT_SEARCHES_INTERVALS].join(", ")}`);
      process.exit(1);
    }

    let params: HotSearchesParam[];
    if (opts.params != null) {
      try {
        params = JSON.parse(opts.params as string) as HotSearchesParam[];
      } catch {
        console.error(`[gmgn-cli] --params must be a valid JSON array, e.g. '[{"chain":"sol","interval":"24h","filters":["renounced","frozen"],"limit":500,"min_liquidity":1000}]'`);
        process.exit(1);
      }
    } else {
      // Empty params lets the server apply its default 5-chain config. Filter fields
      // are flattened directly onto each param (no nested `filter` object).
      const optsMap = opts as Record<string, unknown>;
      const chains: string[] = opts.chain?.length ? (opts.chain as string[]) : [];
      params = chains.map((chain) => {
        const param: HotSearchesParam = { label: "hot-search", chain, interval };
        if (opts.filter?.length) param.filters = opts.filter as string[];
        if (opts.limit != null) param.limit = opts.limit as number;
        // Fold in any rank-style min_*/max_* range flags (incl. min_created/max_created).
        for (const def of RANK_RANGE_FIELDS) {
          const val = optsMap[apiFieldToCliKey(def.api)];
          if (val != null) param[def.api] = val as number | string;
        }
        return param;
      });
    }

    const client = new OpenApiClient(getConfig());
    const data = await client.getHotSearches(params).catch(exitOnError);
    printResult(data, opts.raw);
  });

  market
    .command("search")
    .description("Search for a specific token or wallet by name, symbol, contract address, wallet address, or ENS")
    .requiredOption("-q, --query <keyword>", "Search keyword: token name / symbol / contract address / wallet address / ENS")
    .option("--chain <chain>", 'Scope results to one chain, or "all" (default: search all chains)')
    .option("--launchpad-platform <platform...>", "Launchpad platform filter, repeatable (max 50), e.g. pump / moonshot / raydium. Filters tokens only")
    .option("--is-og <bool>", "true = OG tokens only; false = non-OG only; omit for no filter. Tokens only")
    .option("--is-launched <bool>", "true = already-launched tokens only; omit for no filter. Tokens only")
    .option("--order-by <field>", 'Only "weight" is accepted — sorts tokens by weighted relevance and drops honeypots. Tokens only')
    .option("--raw", "Output raw JSON")
    .action(async (opts) => {
      const query = normalizeSearchQuery(String(opts.query));
      const extra: Record<string, string | number | string[]> = {};

      if (opts.chain) {
        validateSearchChain(opts.chain);
        // The upstream endpoint does not understand chain="all" — it answers with an
        // empty result set instead of an error, which reads as "no such token" and is
        // worse than failing. Omitting the parameter is what actually searches every
        // chain, so accept the documented spelling and translate it, loudly.
        if (opts.chain === "all") {
          console.warn(
            '[gmgn-cli] Note: --chain all is not accepted upstream (it returns no results). Searching all chains by omitting the chain filter instead.'
          );
        } else {
          extra["chain"] = opts.chain;
        }
      }
      if (opts.launchpadPlatform?.length) {
        const platforms = opts.launchpadPlatform as string[];
        if (platforms.length > 50) {
          console.error(`[gmgn-cli] Too many --launchpad-platform values: ${platforms.length}. Maximum is 50.`);
          process.exit(1);
        }
        extra["launchpad_platform"] = platforms;
      }
      if (opts.isOg != null) extra["is_og"] = parseSearchBool(String(opts.isOg), "--is-og");
      if (opts.isLaunched != null) extra["is_launched"] = parseSearchBool(String(opts.isLaunched), "--is-launched");
      if (opts.orderBy != null) {
        if (opts.orderBy !== "weight") {
          console.error(`[gmgn-cli] Invalid --order-by "${opts.orderBy}". Only "weight" is supported.`);
          process.exit(1);
        }
        extra["order_by"] = "weight";
      }

      const client = new OpenApiClient(getConfig());
      const data = await client.searchMarket(query, extra).catch(exitOnError);
      printResult(data, opts.raw);
    });
}

const HOT_SEARCHES_INTERVALS = new Set(["1m", "5m", "1h", "6h", "24h"]);

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
  { api: "min_created",       type: "duration", desc: "Min token age — unit recommended: seconds (e.g. 30s) or minutes (e.g. 0.5m / 1m / 5m / 30m). Bare numbers treated as minutes." },
  { api: "max_created",       type: "duration", desc: "Max token age — unit recommended: seconds (e.g. 30s) or minutes (e.g. 0.5m / 1m / 5m / 30m). Bare numbers treated as minutes." },
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

// Server-side numeric range filters for `market trending` (/v1/market/rank).
// Passed through as min_<metric>/max_<metric> query params; the service applies the
// metrics it understands and ignores the rest. min_created/max_created are token-age
// windows expressed as duration strings (e.g. 30m / 6h / 7d) — note these use m/h/d,
// NOT the s/m form used by trenches; min_created is a minimum age, max_created a maximum.
// The raw upstream rank interface accepts minutes only; the openapi-service does not
// forward this field — it evaluates the age window itself (cutoff = now - duration,
// native for m/h/d), so h/d are valid through this CLI. Passed through verbatim
// (string); a bare number with no unit suffix is rejected.
const RANK_RANGE_FIELDS: TrenchesFilterField[] = [
  { api: "min_volume",                    type: "float", desc: "Min trading volume (USD)" },
  { api: "max_volume",                    type: "float", desc: "Max trading volume (USD)" },
  { api: "min_liquidity",                 type: "float", desc: "Min liquidity (USD)" },
  { api: "max_liquidity",                 type: "float", desc: "Max liquidity (USD)" },
  { api: "min_marketcap",                 type: "float", desc: "Min market cap (USD)" },
  { api: "max_marketcap",                 type: "float", desc: "Max market cap (USD)" },
  { api: "min_history_highest_marketcap", type: "float", desc: "Min historical highest market cap (USD)" },
  { api: "max_history_highest_marketcap", type: "float", desc: "Max historical highest market cap (USD)" },
  { api: "min_swaps",                     type: "int",   desc: "Min swap count" },
  { api: "max_swaps",                     type: "int",   desc: "Max swap count" },
  { api: "min_holder_count",              type: "int",   desc: "Min holder count" },
  { api: "max_holder_count",              type: "int",   desc: "Max holder count" },
  { api: "min_gas_fee",                   type: "float", desc: "Min gas fee" },
  { api: "max_gas_fee",                   type: "float", desc: "Max gas fee" },
  { api: "min_renowned_count",            type: "int",   desc: "Min KOL / renowned wallet count" },
  { api: "max_renowned_count",            type: "int",   desc: "Max KOL / renowned wallet count" },
  { api: "min_smart_degen_count",         type: "int",   desc: "Min smart-money holder count" },
  { api: "max_smart_degen_count",         type: "int",   desc: "Max smart-money holder count" },
  { api: "min_bot_degen_count",           type: "int",   desc: "Min bot-degen wallet count" },
  { api: "max_bot_degen_count",           type: "int",   desc: "Max bot-degen wallet count" },
  { api: "min_visiting_count",            type: "int",   desc: "Min visitor count" },
  { api: "max_visiting_count",            type: "int",   desc: "Max visitor count" },
  { api: "min_price_change_percent",      type: "float", desc: "Min price change ratio over the interval" },
  { api: "max_price_change_percent",      type: "float", desc: "Max price change ratio over the interval" },
  { api: "min_insider_rate",              type: "float", desc: "Min insider trading ratio (0–1); tokens lacking this field are excluded" },
  { api: "max_insider_rate",              type: "float", desc: "Max insider trading ratio (0–1); tokens lacking this field are excluded" },
  { api: "min_bundler_rate",              type: "float", desc: "Min bundle-bot trading ratio (0–1); tokens lacking this field are excluded" },
  { api: "max_bundler_rate",              type: "float", desc: "Max bundle-bot trading ratio (0–1); tokens lacking this field are excluded" },
  { api: "min_entrapment_ratio",          type: "float", desc: "Min entrapment trading ratio (0–1); tokens lacking this field are excluded" },
  { api: "max_entrapment_ratio",          type: "float", desc: "Max entrapment trading ratio (0–1); tokens lacking this field are excluded" },
  { api: "min_top10_holder_rate",         type: "float", desc: "Min top-10 holder concentration (0–1)" },
  { api: "max_top10_holder_rate",         type: "float", desc: "Max top-10 holder concentration (0–1)" },
  { api: "min_top70_sniper_hold_rate",    type: "float", desc: "Min top-70 sniper holding ratio (0–1)" },
  { api: "max_top70_sniper_hold_rate",    type: "float", desc: "Max top-70 sniper holding ratio (0–1)" },
  { api: "min_dev_team_hold_rate",        type: "float", desc: "Min dev-team holding ratio (0–1); also excludes creator-close tokens" },
  { api: "max_dev_team_hold_rate",        type: "float", desc: "Max dev-team holding ratio (0–1)" },
  { api: "min_created",                   type: "string", desc: "Min token age (minimum age). Duration with unit suffix m/h/d, e.g. 30m / 6h / 7d (h/d evaluated server-side; raw upstream takes minutes only). A bare number with no unit is rejected." },
  { api: "max_created",                   type: "string", desc: "Max token age (maximum age). Duration with unit suffix m/h/d, e.g. 600m / 24h (h/d evaluated server-side; raw upstream takes minutes only). A bare number with no unit is rejected." },
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
// Commander.js camelCase: converts -[a-z] to uppercase, and removes hyphen before digits
// e.g. min_volume_24h → min-volume-24h → minVolume-24h → minVolume24h
// e.g. min_smart_degen_count → min-smart-degen-count → minSmartDegenCount
function apiFieldToCliKey(apiField: string): string {
  return apiField
    .replace(/_/g, '-')
    .replace(/-([a-z])/g, (_, c: string) => c.toUpperCase())
    .replace(/-(\d)/g, '$1');
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
