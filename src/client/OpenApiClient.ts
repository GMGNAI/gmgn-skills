/**
 * OpenApiClient — GMGN OpenAPI external client
 *
 * Auth modes:
 *   Normal (market/token/portfolio): X-APIKEY + timestamp + client_id
 *   Critical (swap and order routes): normal auth + X-Signature (private key signature)
 */

import { buildAuthQuery, buildMessage, detectAlgorithm, sign } from "./signer.js";

const RATE_LIMIT_RETRY_BUFFER_MS = 1000;
const DEFAULT_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS = 5000;

interface PreparedRequest {
  method: string;
  subPath: string;
  url: string;
  headers: Record<string, string>;
  body: string | null;
  curlStr: string;
}

interface ResponseEnvelope {
  code: number | string;
  data?: unknown;
  message?: string;
  error?: string;
}

interface OpenApiErrorParams {
  method: string;
  path: string;
  status: number;
  apiCode?: number | string;
  apiError?: string;
  apiMessage?: string;
  resetAtUnix?: number;
}

class OpenApiError extends Error {
  readonly method: string;
  readonly path: string;
  readonly status: number;
  readonly apiCode?: number | string;
  readonly apiError?: string;
  readonly apiMessage?: string;
  readonly resetAtUnix?: number;

  constructor(params: OpenApiErrorParams) {
    super(buildOpenApiErrorMessage(params));
    this.name = "OpenApiError";
    this.method = params.method;
    this.path = params.path;
    this.status = params.status;
    this.apiCode = params.apiCode;
    this.apiError = params.apiError;
    this.apiMessage = params.apiMessage;
    this.resetAtUnix = params.resetAtUnix;
  }
}

export interface Config {
  apiKey: string;
  privateKeyPem?: string;
  host: string;
}

export interface SwapParams {
  chain: string;
  from_address: string;
  input_token: string;
  output_token: string;
  input_amount: string;
  swap_mode?: string;
  input_amount_bps?: string;
  output_amount?: string;
  slippage?: number;
  auto_slippage?: boolean;
  min_output_amount?: string;
  is_anti_mev?: boolean;
  priority_fee?: string;
  tip_fee?: string;
  auto_tip_fee?: boolean;
  max_auto_fee?: string;
  gas_price?: string;
  max_fee_per_gas?: string;
  max_priority_fee_per_gas?: string;
  condition_orders?: StrategyConditionOrder[];
  sell_ratio_type?: string;
}

export interface StrategyConditionOrder {
  order_type: string;   // "profit_stop" | "loss_stop" | "profit_stop_trace" | "loss_stop_trace"
  side: string;         // "sell"
  price_scale?: string;
  sell_ratio: string;
  drawdown_rate?: string;
}

export interface MultiSwapParams {
  chain: string;
  accounts: string[];
  input_token: string;
  output_token: string;
  input_amount?: Record<string, string>;
  input_amount_bps?: Record<string, string>;
  output_amount?: Record<string, string>;
  swap_mode?: string;
  slippage?: number;
  auto_slippage?: boolean;
  is_anti_mev?: boolean;
  priority_fee?: string;
  tip_fee?: string;
  auto_tip_fee?: boolean;
  max_auto_fee?: string;
  gas_price?: string;
  max_fee_per_gas?: string;
  max_priority_fee_per_gas?: string;
  condition_orders?: StrategyConditionOrder[];
  sell_ratio_type?: string;
}

export interface StrategyCreateParams {
  chain: string;
  from_address: string;
  base_token: string;
  quote_token: string;
  order_type: string;
  sub_order_type: string;
  check_price: string;
  open_price?: string;
  amount_in?: string;
  amount_in_percent?: string;
  limit_price_mode?: string;
  price_gap_ratio?: string;
  expire_in?: number;
  sell_ratio_type?: string;
  slippage?: number;
  auto_slippage?: boolean;
  fee?: string;
  gas_price?: string;
  max_fee_per_gas?: string;
  max_priority_fee_per_gas?: string;
  is_anti_mev?: boolean;
  anti_mev_mode?: string;
  priority_fee?: string;
  tip_fee?: string;
  custom_rpc?: string;
}

export interface StrategyCancelParams {
  chain: string;
  from_address: string;
  order_id: string;
  order_type?: string;
  close_sell_model?: string;
}

export interface TokenSignalGroup {
  signal_type?: number[];
  mc_min?: number;
  mc_max?: number;
  trigger_mc_min?: number;
  trigger_mc_max?: number;
  total_fee_min?: number;
  total_fee_max?: number;
  min_create_or_open_ts?: string;
  max_create_or_open_ts?: string;
}

export interface CreateTokenParams {
  chain: string;
  dex: string;
  from_address: string;
  name: string;
  symbol: string;
  buy_amt: string;
  image?: string;
  image_url?: string;
  website?: string;
  twitter?: string;
  telegram?: string;
  slippage?: number;
  auto_slippage?: boolean;
  priority_fee?: string;
  tip_fee?: string;
  gas_price?: string;
  max_priority_fee_per_gas?: string;
  max_fee_per_gas?: string;
  is_anti_mev?: boolean;
  anti_mev_mode?: string;
}

export class OpenApiClient {
  private readonly apiKey: string;
  private readonly privateKeyPem: string | undefined;
  private readonly host: string;

  constructor(config: Config) {
    this.apiKey = config.apiKey;
    this.privateKeyPem = config.privateKeyPem;
    this.host = config.host.replace(/\/$/, "");
  }

  // ---- Token endpoints (normal auth) ----

  async getTokenInfo(chain: string, address: string): Promise<unknown> {
    return this.normalRequest("GET", "/v1/token/info", { chain, address });
  }

  async getTokenSecurity(chain: string, address: string): Promise<unknown> {
    return this.normalRequest("GET", "/v1/token/security", { chain, address });
  }

  async getTokenPoolInfo(chain: string, address: string): Promise<unknown> {
    return this.normalRequest("GET", "/v1/token/pool_info", { chain, address });
  }

  async getTokenTopHolders(chain: string, address: string, extra: Record<string, string | number> = {}): Promise<unknown> {
    return this.normalRequest("GET", "/v1/market/token_top_holders", { chain, address, ...extra });
  }

  async getTokenTopTraders(chain: string, address: string, extra: Record<string, string | number> = {}): Promise<unknown> {
    return this.normalRequest("GET", "/v1/market/token_top_traders", { chain, address, ...extra });
  }

  // ---- Market endpoints (normal auth) ----

  async getTokenKline(
    chain: string,
    address: string,
    resolution: string,
    from?: number,
    to?: number
  ): Promise<unknown> {
    const query: Record<string, string | number> = { chain, address, resolution };
    if (from != null) query["from"] = from;
    if (to != null) query["to"] = to;
    return this.normalRequest("GET", "/v1/market/token_kline", query);
  }

  // ---- Portfolio endpoints (normal auth) ----

  async getWalletHoldings(
    chain: string,
    walletAddress: string,
    extra: Record<string, string | number> = {}
  ): Promise<unknown> {
    return this.normalRequest("GET", "/v1/user/wallet_holdings", {
      chain,
      wallet_address: walletAddress,
      ...extra,
    });
  }

  async getWalletActivity(
    chain: string,
    walletAddress: string,
    extra: Record<string, string | number | string[]> = {}
  ): Promise<unknown> {
    return this.normalRequest("GET", "/v1/user/wallet_activity", {
      chain,
      wallet_address: walletAddress,
      ...extra,
    });
  }

  async getWalletStats(chain: string, walletAddresses: string[], period = "7d"): Promise<unknown> {
    return this.normalRequest("GET", "/v1/user/wallet_stats", {
      chain,
      wallet_address: walletAddresses,
      period,
    });
  }

  async getWalletTokenBalance(
    chain: string,
    walletAddress: string,
    tokenAddress: string
  ): Promise<unknown> {
    return this.normalRequest("GET", "/v1/user/wallet_token_balance", { chain, wallet_address: walletAddress, token_address: tokenAddress });
  }

  async getTrenches(chain: string, types?: string[], platforms?: string[], limit?: number, filters?: Record<string, number | string>): Promise<unknown> {
    const body = buildTrenchesBody(chain, types, platforms, limit, filters);
    return this.normalRequest("POST", "/v1/trenches", { chain }, body);
  }

  // ---- Market trending endpoints (normal auth) ----

  async getTrendingSwaps(
    chain: string,
    interval: string,
    extra: Record<string, string | number | string[]> = {}
  ): Promise<unknown> {
    return this.normalRequest("GET", "/v1/market/rank", { chain, interval, ...extra });
  }

  async getTokenSignalV2(chain: string, groups: TokenSignalGroup[]): Promise<unknown> {
    return this.normalRequest("POST", "/v1/market/token_signal", {}, { chain, groups });
  }

  // ---- User endpoints (normal auth) ----

  async getUserInfo(): Promise<any> {
    const data = await this.normalRequest("GET", "/v1/user/info", {});
    // [NÂNG CẤP V102.8] Khắc phục Issue #7: Hoán đổi token_address cho Solana
    if (data && typeof data === "object" && "wallets" in data) {
      const wallets = (data as any).wallets;
      if (Array.isArray(wallets)) {
        wallets.forEach((w: any) => {
          if (w.chain === "sol" && w.balances && Array.isArray(w.balances)) {
            w.balances.forEach((b: any) => {
              if (b.token_address && b.address) {
                // Hoán đổi lại các trường bị sai lệch theo báo cáo Issue #7
                const temp = b.token_address;
                b.token_address = b.address;
                b.address = temp;
              }
            });
          }
        });
      }
    }
    return data;
  }

  async getFollowWallet(chain: string, extra: Record<string, string | number | string[]> = {}): Promise<unknown> {
    return this.criticalRequest("GET", "/v1/trade/follow_wallet", { chain, ...extra }, null);
  }

  async getKol(chain?: string, limit?: number): Promise<unknown> {
    const query: Record<string, string | number> = {};
    if (chain) query["chain"] = chain;
    if (limit != null) query["limit"] = limit;
    return this.normalRequest("GET", "/v1/user/kol", query);
  }

  async getSmartMoney(chain?: string, limit?: number): Promise<unknown> {
    const query: Record<string, string | number> = {};
    if (chain) query["chain"] = chain;
    if (limit != null) query["limit"] = limit;
    return this.normalRequest("GET", "/v1/user/smartmoney", query);
  }

  async getCreatedTokens(chain: string, walletAddress: string, extra: Record<string, string | number> = {}): Promise<unknown> {
    return this.normalRequest("GET", "/v1/user/created_tokens", { chain, wallet_address: walletAddress, ...extra });
  }

  async quoteOrder(
    chain: string,
    from_address: string,
    input_token: string,
    output_token: string,
    input_amount: string,
    slippage: number
  ): Promise<unknown> {
    const query = { chain, from_address, input_token, output_token, input_amount, slippage };
    return this.criticalRequest("GET", "/v1/trade/quote", query, null);
  }

  // ---- Swap endpoints (critical auth) ----

  async swap(params: SwapParams): Promise<unknown> {
    return this.criticalRequest("POST", "/v1/trade/swap", {}, params);
  }

  async multiSwap(params: MultiSwapParams): Promise<unknown> {
    return this.criticalRequest("POST", "/v1/trade/multi_swap", {}, params);
  }

  async queryOrder(orderId: string, chain: string): Promise<unknown> {
    return this.criticalRequest("GET", "/v1/trade/query_order", { order_id: orderId, chain }, null);
  }

  // ---- Strategy order endpoints (critical auth) ----

  async createStrategyOrder(params: StrategyCreateParams): Promise<unknown> {
    return this.criticalRequest("POST", "/v1/trade/strategy/create", {}, params);
  }

  async getStrategyOrders(chain: string, extra: Record<string, string | number> = {}): Promise<unknown> {
    return this.criticalRequest("GET", "/v1/trade/strategy/orders", { chain, ...extra }, null);
  }

  async cancelStrategyOrder(params: StrategyCancelParams): Promise<unknown> {
    return this.criticalRequest("POST", "/v1/trade/strategy/cancel", {}, params);
  }

  // ---- Cooking endpoints ----

  async getCookingStatistics(): Promise<unknown> {
    return this.normalRequest("GET", "/v1/cooking/statistics", {});
  }

  async createToken(params: CreateTokenParams): Promise<unknown> {
    return this.criticalRequest("POST", "/v1/cooking/create_token", {}, params);
  }

  // ---- Internal methods ----

  private async normalRequest(
    method: string,
    subPath: string,
    queryExtra: Record<string, string | number | string[]>,
    body: unknown = null
  ): Promise<unknown> {
    return this.executePreparedRequest(() => {
      const { timestamp, client_id } = buildAuthQuery();
      const query: Record<string, string | number | string[]> = { ...queryExtra, timestamp, client_id };
      const url = buildUrl(`${this.host}${subPath}`, query);
      const headers: Record<string, string> = {
        "X-APIKEY": this.apiKey,
        "Content-Type": "application/json",
      };
      const bodyStr = body !== null ? JSON.stringify(body) : null;
      return {
        method,
        subPath,
        url,
        headers,
        body: bodyStr,
        curlStr: formatCurl(method, url, headers, bodyStr),
      };
    }, true);
  }

  private async criticalRequest(
    method: string,
    subPath: string,
    queryExtra: Record<string, string | number | string[]>,
    body: unknown
  ): Promise<unknown> {
    if (!this.privateKeyPem) {
      throw new Error("GMGN_PRIVATE_KEY is required for critical-auth commands (swap, order, and follow-wallet commands)");
    }

    return this.executePreparedRequest(() => {
      const { timestamp, client_id } = buildAuthQuery();
      const query: Record<string, string | number | string[]> = { ...queryExtra, timestamp, client_id };
      const bodyStr = body !== null ? JSON.stringify(body) : "";
      const message = buildMessage(subPath, query, bodyStr, timestamp);
      const signature = sign(message, this.privateKeyPem!, detectAlgorithm(this.privateKeyPem!));

      const url = buildUrl(`${this.host}${subPath}`, query);
      const headers: Record<string, string> = {
        "X-APIKEY": this.apiKey,
        "X-Signature": signature,
        "Content-Type": "application/json",
      };
      return {
        method,
        subPath,
        url,
        headers,
        body: bodyStr || null,
        curlStr: formatCurl(method, url, headers, bodyStr || null),
      };
    }, method !== "POST");
  }

  private async executePreparedRequest(
    prepare: () => PreparedRequest,
    autoRetryOnRateLimit: boolean
  ): Promise<unknown> {
    const maxAttempts = autoRetryOnRateLimit ? 2 : 1;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      const request = prepare();
      const res = await this.doFetch(
        request.method,
        request.subPath,
        request.url,
        request.headers,
        request.body,
        request.curlStr
      );

      try {
        return this.parseResponse(request.method, request.subPath, res, request.curlStr);
      } catch (err) {
        const retryDelayMs = getRateLimitRetryDelayMs(err, attempt, maxAttempts, autoRetryOnRateLimit);
        if (retryDelayMs == null) {
          throw err;
        }

        if (process.env.GMGN_DEBUG) {
          console.error(
            `[gmgn-cli] ${request.method} ${request.subPath} hit rate limit, retrying once in ${Math.ceil(retryDelayMs / 1000)}s`
          );
        }
        await sleep(retryDelayMs);
      }
    }

    throw new Error("Unexpected retry loop exit");
  }

  private async doFetch(
    method: string,
    subPath: string,
    url: string,
    headers: Record<string, string>,
    body: string | null,
    curlStr: string
  ): Promise<Response> {
    try {
      return await fetch(url, { method, headers, body: body ?? undefined });
    } catch (err: unknown) {
      const cause = extractRootCause(err);
      const errorCode = (cause as NodeJS.ErrnoException).code;

      // Detect IPv4 unavailability errors
      if (errorCode === "EADDRNOTAVAIL" || errorCode === "ENETUNREACH") {
        throw new Error(
          `Network unreachable (${errorCode}): Your system may not support IPv4. ` +
          `Please check your network configuration or contact support.`
        );
      }

      if (process.env.GMGN_DEBUG) console.error(`${curlStr}\n[error] fetch failed: ${cause}`);
      throw new Error(`${method} ${subPath} fetch failed: ${cause}`);
    }
  }

  private async parseResponse(
    method: string,
    path: string,
    res: Response,
    curlStr: string
  ): Promise<unknown> {
    const fail = (msg: string, body: string | null = null): never => {
      if (process.env.GMGN_DEBUG) {
        console.error(`${curlStr}\n${formatResponse(res, body)}`);
      }
      throw new Error(msg);
    };

    const resetAtUnix = parseRateLimitReset(res.headers.get("x-ratelimit-reset"));

    let text!: string;
    try {
      text = await res.text();
    } catch (err) {
      fail(`${method} ${path} failed: HTTP ${res.status} (failed to read response body: ${err})`);
    }

    let json!: ResponseEnvelope;
    try {
      json = JSON.parse(text);
    } catch {
      fail(`${method} ${path} failed: HTTP ${res.status} (non-JSON response)`, text);
    }

    if (json.code !== 0) {
      if (process.env.GMGN_DEBUG) {
        console.error(`${curlStr}\n${formatResponse(res, text)}`);
      }
      throw new OpenApiError({
        method,
        path,
        status: res.status,
        apiCode: json.code,
        apiError: json.error,
        apiMessage: json.message,
        resetAtUnix,
      });
    }

    return json.data;
  }
}

function getRateLimitRetryDelayMs(
  err: unknown,
  attempt: number,
  maxAttempts: number,
  autoRetryOnRateLimit: boolean
): number | null {
  if (!autoRetryOnRateLimit || attempt >= maxAttempts) {
    return null;
  }
  if (!(err instanceof OpenApiError)) {
    return null;
  }
  if (err.apiError !== "RATE_LIMIT_EXCEEDED" && err.apiError !== "RATE_LIMIT_BANNED") {
    return null;
  }
  if (err.resetAtUnix == null) {
    return null;
  }

  const waitMs = Math.max(err.resetAtUnix * 1000 - Date.now(), 0) + RATE_LIMIT_RETRY_BUFFER_MS;
  return waitMs <= getAutoRetryMaxWaitMs() ? waitMs : null;
}

function parseRateLimitReset(raw: string | null): number | undefined {
  if (raw == null || raw.trim() === "") {
    return undefined;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

function getAutoRetryMaxWaitMs(): number {
  const raw = process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
  if (!raw) {
    return DEFAULT_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : DEFAULT_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
}

function buildOpenApiErrorMessage(params: OpenApiErrorParams): string {
  const parts = [`${params.method} ${params.path} failed: HTTP ${params.status}`];
  if (params.apiCode != null) parts.push(`code=${params.apiCode}`);
  if (params.apiError) parts.push(`error=${params.apiError}`);
  if (params.apiMessage) parts.push(`message=${params.apiMessage}`);

  let message = parts.join(" ");

  if (params.status !== 429) {
    return message;
  }

  const resetText = params.resetAtUnix != null
    ? formatRateLimitReset(params.resetAtUnix)
    : "an unknown time";

  if (params.apiError === "ERROR_RATE_LIMIT_BLOCKED") {
    return `${message}. Repeated business errors triggered a temporary block until ${resetText}. Fix the underlying request before retrying.`;
  }

  if (params.apiError === "RATE_LIMIT_EXCEEDED" || params.apiError === "RATE_LIMIT_BANNED") {
    return `${message}. Rate limit resets at ${resetText}. Stop sending requests before then; repeated requests can extend the ban by 5s up to 5 minutes.`;
  }

  return `${message}. Received HTTP 429; retry after ${resetText}.`;
}

function formatRateLimitReset(resetAtUnix: number): string {
  const resetAt = new Date(resetAtUnix * 1000);
  const remainingSeconds = Math.max(Math.ceil((resetAt.getTime() - Date.now()) / 1000), 0);
  return `${formatLocalTimestamp(resetAt)} (~${remainingSeconds}s remaining)`;
}

function formatLocalTimestamp(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  const offsetMinutes = -date.getTimezoneOffset();
  const sign = offsetMinutes >= 0 ? "+" : "-";
  const absOffsetMinutes = Math.abs(offsetMinutes);
  const offsetHours = String(Math.floor(absOffsetMinutes / 60)).padStart(2, "0");
  const offsetMins = String(absOffsetMinutes % 60).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} GMT${sign}${offsetHours}:${offsetMins}`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function formatResponse(res: Response, body: string | null): string {
  const headerLines = [...res.headers.entries()].map(([k, v]) => `  ${k}: ${v}`).join("\n");
  return `[response] HTTP ${res.status}\n${headerLines}\n\n${body ?? "(no body)"}`;
}

const REDACTED_HEADERS = new Set(["x-apikey"]);

function formatCurl(method: string, url: string, headers: Record<string, string>, body: string | null): string {
  const headerArgs = Object.entries(headers)
    .map(([k, v]) => `  -H '${k}: ${REDACTED_HEADERS.has(k.toLowerCase()) ? "***" : v}'`)
    .join(" \\\n");
  const bodyArg = body ? ` \\\n  -d '${body.replace(/'/g, "'\\''")}'` : "";
  return `\n[curl]\ncurl -X ${method} '${url}' \\\n${headerArgs}${bodyArg}\n`;
}

const TRENCHES_PLATFORMS: Record<string, string[]> = {
  sol: [
    "Pump.fun", "pump_mayhem", "pump_mayhem_agent", "pump_agent",
    "letsbonk", "bonkers", "bags", "memoo", "liquid", "bankr", "zora",
    "surge", "anoncoin", "moonshot_app", "wendotdev", "heaven", "sugar",
    "token_mill", "believe", "trendsfun", "trends_fun", "jup_studio",
    "Moonshot", "boop", "ray_launchpad", "meteora_virtual_curve", "xstocks",
  ],
  bsc: [
    "fourmeme", "fourmeme_agent", "bn_fourmeme", "four_xmode_agent",
    "flap", "clanker", "lunafun",
  ],
  base: [
    "clanker", "bankr", "flaunch", "zora", "zora_creator",
    "baseapp", "basememe", "virtuals_v2", "klik",
  ],
};

const TRENCHES_QUOTE_ADDRESS_TYPES: Record<string, number[]> = {
  sol:  [4, 5, 3, 1, 13, 0],
  bsc:  [6, 7, 1, 16, 8, 3, 9, 10, 2, 17, 18, 0],
  base: [11, 3, 12, 13, 0],
};

function buildTrenchesBody(chain: string, types?: string[], platforms?: string[], limit?: number, filters?: Record<string, number | string>): Record<string, unknown> {
  const selectedTypes = types?.length ? types : ["new_creation", "near_completion", "completed"];
  const launchpad_platform = platforms?.length ? platforms : (TRENCHES_PLATFORMS[chain] ?? []);
  const quote_address_type = TRENCHES_QUOTE_ADDRESS_TYPES[chain] ?? [];
  const actualLimit = limit ?? 80;
  const section: Record<string, unknown> = {
    filters: ["offchain", "onchain"],
    launchpad_platform,
    quote_address_type,
    launchpad_platform_v2: true,
    limit: actualLimit,
    ...filters,
  };
  const body: Record<string, unknown> = { version: "v2" };
  for (const type of selectedTypes) {
    body[type] = { ...section };
  }
  return body;
}

function buildUrl(base: string, query: Record<string, string | number | string[]>): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (Array.isArray(v)) {
      for (const item of v) params.append(k, item);
    } else {
      params.set(k, String(v));
    }
  }
  return `${base}?${params.toString()}`;
}

// Recursively extract the root cause from nested Error.cause chain
function extractRootCause(err: unknown): unknown {
  if (err instanceof Error && err.cause) {
    return extractRootCause(err.cause);
  }
  return err;
}
