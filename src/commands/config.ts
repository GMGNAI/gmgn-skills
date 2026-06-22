import { Command } from "commander";
import * as crypto from "crypto";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

const GMGN_CONFIG_DIR = path.join(os.homedir(), ".config", "gmgn");
const GLOBAL_ENV_PATH = path.join(GMGN_CONFIG_DIR, ".env");
const KEYS_FILE = path.join(GMGN_CONFIG_DIR, "keys.pem");
const GMGN_API_URL = "https://gmgn.ai/ai/generateapi";

function readEnvFile(filePath: string): Record<string, string> {
  if (!fs.existsSync(filePath)) return {};
  const lines = fs.readFileSync(filePath, "utf-8").split("\n");
  const result: Record<string, string> = {};
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
    result[key] = val;
  }
  return result;
}

function writeEnvFile(filePath: string, vars: Record<string, string>): void {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const existing = readEnvFile(filePath);
  const merged = { ...existing, ...vars };
  const content = Object.entries(merged)
    .map(([k, v]) => `${k}=${v.includes("\n") ? `"${v.replace(/\n/g, "\\n")}"` : v}`)
    .join("\n") + "\n";
  fs.writeFileSync(filePath, content, { mode: 0o600 });
}

export function registerSetupCommands(program: Command): void {
  program
    .command("config")
    .description("Generate an Ed25519 key pair and output a pre-filled GMGN API Key creation link")
    .action(async () => {
      // Generate a new Ed25519 key pair unconditionally
      const { privateKey, publicKey } = crypto.generateKeyPairSync("ed25519");
      const privatePem = privateKey.export({ type: "pkcs8", format: "pem" }) as string;
      const publicPem = publicKey.export({ type: "spki", format: "pem" }) as string;

      // Append both keys to keys.pem to preserve history
      fs.mkdirSync(GMGN_CONFIG_DIR, { recursive: true });
      const entry = `# Private Key\n${privatePem}\n# Public Key\n${publicPem}\n`;
      fs.appendFileSync(KEYS_FILE, entry, { mode: 0o600 });

      // Overwrite GMGN_PRIVATE_KEY in ~/.config/gmgn/.env with the new private key
      writeEnvFile(GLOBAL_ENV_PATH, {
        GMGN_PRIVATE_KEY: privatePem.replace(/\n/g, "\\n"),
      });

      console.log(`✓ Ed25519 key pair generated and saved to ${KEYS_FILE}`);

      // Build pre-filled link with full PEM public key as pbk parameter
      const link = `${GMGN_API_URL}?pbk=${encodeURIComponent(publicPem)}`;

      // Detect system locale and output guidance in the matching language
      const locale = (process.env.LANG ?? process.env.LC_ALL ?? process.env.LC_MESSAGES ?? "").toLowerCase();
      let message: string;
      if (locale.startsWith("zh_tw") || locale.startsWith("zh_hk")) {
        message = "請點擊連結建立你的 GMGN API Key，完成後將 Key 發給我，我來幫你完成配置：";
      } else if (locale.startsWith("zh")) {
        message = "请点击链接创建你的 GMGN API Key，完成后将 Key 发给我，我来帮你完成配置：";
      } else {
        message = "Please click the link below to create your GMGN API Key. Once created, send me the API Key and I will finish the configuration:";
      }

      console.log("");
      console.log(message);
      console.log(link);
      console.log("");
    });
}
