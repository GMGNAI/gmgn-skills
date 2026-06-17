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

function hasApiKey(): boolean {
  // Check project .env first, then global config
  const projectEnv = readEnvFile(path.join(process.cwd(), ".env"));
  if (projectEnv["GMGN_API_KEY"]) return true;
  const globalEnv = readEnvFile(GLOBAL_ENV_PATH);
  return !!globalEnv["GMGN_API_KEY"];
}

function hasPrivateKey(): { found: boolean; pem?: string } {
  const globalEnv = readEnvFile(GLOBAL_ENV_PATH);
  if (globalEnv["GMGN_PRIVATE_KEY"]) {
    return { found: true, pem: globalEnv["GMGN_PRIVATE_KEY"].replace(/\\n/g, "\n") };
  }
  return { found: false };
}

function generateKeyPair(): { privatePem: string; publicPem: string } {
  const { privateKey, publicKey } = crypto.generateKeyPairSync("ed25519");
  const privatePem = privateKey.export({ type: "pkcs8", format: "pem" }) as string;
  const publicPem = publicKey.export({ type: "spki", format: "pem" }) as string;
  return { privatePem, publicPem };
}


export function registerSetupCommands(program: Command): void {
  program
    .command("config")
    .description("Check GMGN API Key configuration and generate an Ed25519 key pair if needed")
    .action(async () => {
      // Skip if already configured
      if (hasApiKey()) {
        console.log("✓ GMGN_API_KEY is already configured. No action needed.");
        return;
      }

      // Reuse existing private key or generate a new Ed25519 key pair
      let privatePem: string;
      let publicPem: string;

      const existing = hasPrivateKey();
      if (existing.found && existing.pem) {
        const privKey = crypto.createPrivateKey(existing.pem);
        const pubKey = crypto.createPublicKey(privKey);
        publicPem = pubKey.export({ type: "spki", format: "pem" }) as string;
        privatePem = existing.pem;
      } else {
        const kp = generateKeyPair();
        privatePem = kp.privatePem;
        publicPem = kp.publicPem;

        // Save both keys into a single keys.pem file for user backup
        fs.mkdirSync(GMGN_CONFIG_DIR, { recursive: true });
        const keyFileContent = `# Private Key\n${privatePem}\n# Public Key\n${publicPem}`;
        fs.writeFileSync(KEYS_FILE, keyFileContent, { mode: 0o600 });

        // Also write private key inline into ~/.config/gmgn/.env as GMGN_PRIVATE_KEY
        writeEnvFile(GLOBAL_ENV_PATH, {
          GMGN_PRIVATE_KEY: privatePem.replace(/\n/g, "\\n"),
        });
        console.log(`✓ Ed25519 key pair generated and saved to ${KEYS_FILE}`);
      }

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
