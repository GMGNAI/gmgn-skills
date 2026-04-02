#!/usr/bin/env node
import { createRequire } from "module";
const { version } = createRequire(import.meta.url)("../package.json") as { version: string };
import { setGlobalDispatcher, ProxyAgent, Agent, buildConnector } from "undici";
import { SocksClient } from "socks";
import * as tls from "tls";
import { Command } from "commander";
import { registerTokenCommands } from "./commands/token.js";
import { registerMarketCommands } from "./commands/market.js";
import { registerPortfolioCommands } from "./commands/portfolio.js";
import { registerTrackCommands } from "./commands/track.js";
import { registerSwapCommands } from "./commands/swap.js";
import { registerCookingCommands } from "./commands/cooking.js";

const proxy = process.env.HTTPS_PROXY ?? process.env.https_proxy
           ?? process.env.HTTP_PROXY  ?? process.env.http_proxy;
if (proxy) {
  const u = new URL(proxy);
  if (u.protocol === "socks5:" || u.protocol === "socks4:") {
    const type = u.protocol === "socks5:" ? 5 : 4;
    setGlobalDispatcher(new Agent({
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      connect: async (options: any, callback: any) => {
        try {
          const { socket } = await SocksClient.createConnection({
            proxy: { host: u.hostname, port: parseInt(u.port || "1080"), type },
            command: "connect",
            destination: { host: options.hostname!, port: +options.port! },
            socket_options: { family: 4 } as any,
          });
          if (options.protocol === "https:") {
            callback(null, tls.connect({ socket, servername: options.hostname, rejectUnauthorized: options.rejectUnauthorized !== false }));
          } else {
            callback(null, socket);
          }
        } catch (err) {
          callback(err as Error, null);
        }
      },
    }));
  } else {
    setGlobalDispatcher(new ProxyAgent(proxy));
  }
} else {
  // Force IPv4 for all connections (no proxy mode)
  const connector = buildConnector({ family: 4 } as any);
  setGlobalDispatcher(new Agent({ connect: connector }));
}

const program = new Command();

program
  .name("gmgn-cli")
  .version(version)
  .description("GMGN OpenAPI CLI — market data, token info, portfolio, track KOL/smart money trades, and swap");

registerTokenCommands(program);
registerMarketCommands(program);
registerPortfolioCommands(program);
registerTrackCommands(program);
registerSwapCommands(program);
registerCookingCommands(program);

program.parseAsync().catch((err) => {
  console.error(`[gmgn-cli] ${err.message}`);
  process.exit(1);
});
