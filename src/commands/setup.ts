import { Command } from "commander";
import * as crypto from "crypto";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";

const GLOBAL_ENV_PATH = path.join(os.homedir(), ".config", "gmgn", ".env");
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

function extractRawPublicKey(publicPem: string): string {
  // Strip PEM headers and decode to get raw 32-byte Ed25519 public key, then base64
  const b64 = publicPem
    .replace(/-----BEGIN PUBLIC KEY-----|-----END PUBLIC KEY-----|\n/g, "");
  const der = Buffer.from(b64, "base64");
  // Ed25519 SPKI DER: 12-byte header + 32-byte key
  return der.slice(12).toString("base64");
}

export function registerSetupCommands(program: Command): void {
  program
    .command("setup")
    .description("Check GMGN API Key configuration and generate keys if needed")
    .action(async () => {
      // Step 1: check if already configured
      if (hasApiKey()) {
        console.log("✓ GMGN_API_KEY is already configured. No action needed.");
        return;
      }

      // Step 2: reuse existing private key or generate new one
      let privatePem: string;
      let publicPem: string;

      const existing = hasPrivateKey();
      if (existing.found && existing.pem) {
        // Derive public key from existing private key
        const privKey = crypto.createPrivateKey(existing.pem);
        const pubKey = crypto.createPublicKey(privKey);
        publicPem = pubKey.export({ type: "spki", format: "pem" }) as string;
        privatePem = existing.pem;
      } else {
        const kp = generateKeyPair();
        privatePem = kp.privatePem;
        publicPem = kp.publicPem;

        // Save private key to global config
        writeEnvFile(GLOBAL_ENV_PATH, {
          GMGN_PRIVATE_KEY: privatePem.replace(/\n/g, "\\n"),
        });
        console.log(`✓ Private key generated and saved to ${GLOBAL_ENV_PATH}`);
      }

      // Step 3: build link and prompt user
      const rawPubKey = extractRawPublicKey(publicPem);
      const encodedPubKey = encodeURIComponent(rawPubKey);
      const link = `${GMGN_API_URL}?pbk=${encodedPubKey}`;

      console.log("");
      console.log("One more step — please click the link below to create your GMGN API Key.");
      console.log("Once created, send me the API Key and I will finish the configuration:");
      console.log("");
      console.log(`  ${link}`);
      console.log("");
    });

  program
    .command("save-key")
    .description("Save GMGN API Key to global config after obtaining it from the website")
    .requiredOption("--api-key <key>", "Your GMGN API Key from gmgn.ai/ai")
    .action(async (opts) => {
      const apiKey: string = opts.apiKey;
      if (!apiKey || apiKey.length < 8) {
        console.error("[gmgn-cli] Error: invalid API Key format.");
        process.exit(1);
      }
      writeEnvFile(GLOBAL_ENV_PATH, { GMGN_API_KEY: apiKey });
      console.log(`✓ GMGN_API_KEY saved to ${GLOBAL_ENV_PATH}`);
      console.log("  Configuration complete. You can now use all GMGN Skill commands.");
    });
}
