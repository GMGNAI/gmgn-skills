import { config as loadDotenv } from "dotenv";
import { chmodSync, existsSync, statSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const GLOBAL_ENV_PATH = join(homedir(), ".config", "gmgn", ".env");

// The credential file holds a plaintext private key and API key. Before loading
// it, make sure it is not readable by other users on the machine. If the file is
// group/other-accessible we tighten it to 0600 and warn — this reduces the blast
// radius of the plaintext-credential storage called out in the security review.
function enforceCredentialFilePermissions(path: string): void {
  if (process.platform === "win32" || !existsSync(path)) return;
  try {
    const mode = statSync(path).mode & 0o777;
    if (mode & 0o077) {
      chmodSync(path, 0o600);
      console.error(
        `[gmgn-cli] Warning: ${path} was accessible to other users (mode ${mode.toString(8)}). ` +
          `Permissions tightened to 600. Your GMGN private key is stored here in plaintext — ` +
          `keep this file private and consider a dedicated trading wallet with limited funds.`
      );
    }
  } catch {
    // Non-fatal: if we cannot stat/chmod, fall through to normal loading.
  }
}

enforceCredentialFilePermissions(GLOBAL_ENV_PATH);

// Precedence: shell environment > project .env (cwd) > global ~/.config/gmgn/.env.
// dotenv never overwrites a variable that is already set, so the higher-priority
// source must be loaded first and the global file only fills in what is missing.
export function loadEnvFiles(): void {
  loadDotenv();
  loadDotenv({ path: GLOBAL_ENV_PATH });
}

loadEnvFiles();

export interface Config {
  apiKey: string;
  privateKeyPem?: string;
  host: string;
}

let _config: Config | null = null;
const PRIVATE_KEY_REQUIRED_MSG =
  "GMGN_PRIVATE_KEY is required for critical-auth commands (swap, order, and follow-wallet commands)";

export function getConfig(requirePrivateKey = false): Config {
  if (_config) {
    if (requirePrivateKey && !_config.privateKeyPem) {
      die(PRIVATE_KEY_REQUIRED_MSG);
    }
    return _config;
  }

  const apiKey = process.env.GMGN_API_KEY;
  if (!apiKey) {
    die("GMGN_API_KEY is required. Set it in your .env file or environment.");
  }

  let privateKeyPem: string | undefined;
  const privateKey = process.env.GMGN_PRIVATE_KEY;
  if (privateKey) {
    // Support escaped newlines (e.g. from single-line .env values)
    privateKeyPem = privateKey.replace(/\\n/g, "\n");
  } else if (requirePrivateKey) {
    die(PRIVATE_KEY_REQUIRED_MSG);
  }

  const host = "https://openapi.gmgn.ai";
  _config = { apiKey: apiKey!, privateKeyPem, host };
  return _config;
}

function die(msg: string): never {
  console.error(`[gmgn-cli] Error: ${msg}`);
  process.exit(1);
}
