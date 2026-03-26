/**
 * OpenApiClient — GMGN OpenAPI external client
 *
 * Auth modes:
 *   Normal (market/token/portfolio): X-APIKEY + timestamp + client_id
 *   Critical (swap/order): normal auth + X-Signature (private key signature)
 */

import { buildAuthQuery, buildMessage, detectAlgorithm, sign } from "./signer.js";

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

  async getTrenches(chain: string, types?: string[], platforms?: string[], limit?: number): Promise<unknown> {
    const body = buildTrenchesBody(chain, types, platforms, limit);
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

  // ---- User endpoints (normal auth) ----

  async getUserInfo(): Promise<unknown> {
    return this.normalRequest("GET", "/v1/user/info", {});
  }

  async getFollowWallet(chain: string, extra: Record<string, string | number | string[]> = {}): Promise<unknown> {
    return this.normalRequest("GET", "/v1/trade/follow_wallet", { chain, ...extra });
  }

  async getKol(limit?: number): Promise<unknown> {
    const query: Record<string, string | number> = {};
    if (limit != null) query["limit"] = limit;
    return this.normalRequest("GET", "/v1/user/kol", query);
  }

  async getSmartMoney(limit?: number): Promise<unknown> {
    const query: Record<string, string | number> = {};
    if (limit != null) query["limit"] = limit;
    return this.normalRequest("GET", "/v1/user/smartmoney", query);
  }

  async quoteOrder(
    chain: string,
    from_address: string,
    input_token: string,
    output_token: string,
    input_amount: string,
    slippage: number
  ): Promise<unknown> {
    return this.normalRequest("GET", "/v1/trade/quote", {
      chain, from_address, input_token, output_token, input_amount, slippage,
    });
  }

  // ---- Swap endpoints (critical auth) ----

  async swap(params: SwapParams): Promise<unknown> {
    return this.criticalRequest("POST", "/v1/trade/swap", {}, params);
  }

  async queryOrder(orderId: string, chain: string): Promise<unknown> {
    return this.criticalRequest("GET", "/v1/trade/query_order", { order_id: orderId, chain }, null);
  }

  // ---- Internal methods ----

  private async normalRequest(
    method: string,
    subPath: string,
    queryExtra: Record<string, string | number | string[]>,
    body: unknown = null
  ): Promise<unknown> {
    const { timestamp, client_id } = buildAuthQuery();
    const query: Record<string, string | number | string[]> = { ...queryExtra, timestamp, client_id };

    const url = buildUrl(`${this.host}${subPath}`, query);
    const headers: Record<string, string> = {
      "X-APIKEY": this.apiKey,
      "Content-Type": "application/json",
    };
    const bodyStr = body !== null ? JSON.stringify(body) : null;
    const curlStr = formatCurl(method, url, headers, bodyStr);
    const res = await this.doFetch(method, subPath, url, headers, bodyStr, curlStr);
    return this.parseResponse(method, subPath, res, curlStr);
  }

  private async criticalRequest(
    method: string,
    subPath: string,
    queryExtra: Record<string, string | number>,
    body: unknown
  ): Promise<unknown> {
    if (!this.privateKeyPem) {
      throw new Error("GMGN_PRIVATE_KEY is required for swap/order commands");
    }

    const { timestamp, client_id } = buildAuthQuery();
    const query: Record<string, string | number> = { ...queryExtra, timestamp, client_id };

    const bodyStr = body !== null ? JSON.stringify(body) : "";
    const message = buildMessage(subPath, query, bodyStr, timestamp);
    const signature = sign(message, this.privateKeyPem, detectAlgorithm(this.privateKeyPem));

    const url = buildUrl(`${this.host}${subPath}`, query);
    const headers: Record<string, string> = {
      "X-APIKEY": this.apiKey,
      "X-Signature": signature,
      "Content-Type": "application/json",
    };
    const curlStr = formatCurl(method, url, headers, bodyStr || null);
    const res = await this.doFetch(method, subPath, url, headers, bodyStr || null, curlStr);
    return this.parseResponse(method, subPath, res, curlStr);
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
      const cause = err instanceof Error ? (err.cause ?? err) : err;
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

    let text!: string;
    try {
      text = await res.text();
    } catch (err) {
      fail(`${method} ${path} failed: HTTP ${res.status} (failed to read response body: ${err})`);
    }

    let json!: { code: number | string; data?: unknown; message?: string; error?: string };
    try {
      json = JSON.parse(text);
    } catch {
      fail(`${method} ${path} failed: HTTP ${res.status} (non-JSON response)`, text);
    }

    if (json.code !== 0) {
      fail(
        `${method} ${path} failed: HTTP ${res.status} code=${json.code} error=${json.error ?? ""} message=${json.message ?? ""}`,
        text
      );
    }

    return json.data;
  }
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

function buildTrenchesBody(chain: string, types?: string[], platforms?: string[], limit?: number): Record<string, unknown> {
  const selectedTypes = types?.length ? types : ["new_creation", "near_completion", "completed"];
  const launchpad_platform = platforms?.length ? platforms : (TRENCHES_PLATFORMS[chain] ?? []);
  const quote_address_type = TRENCHES_QUOTE_ADDRESS_TYPES[chain] ?? [];
  const actualLimit = limit ?? 80;
  const section = {
    filters: ["offchain", "onchain"],
    launchpad_platform,
    quote_address_type,
    launchpad_platform_v2: true,
    limit: actualLimit,
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
