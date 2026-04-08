import { config as loadDotenv } from "dotenv";
import { homedir } from "os";
import { join } from "path";


// Load global config first (~/.config/gmgn/.env), then project .env (project takes precedence)
loadDotenv({ path: join(homedir(), ".config", "gmgn", ".env") });
loadDotenv({ override: true });

export interface Config {
  apiKey: string;
  privateKeyPem?: string;
  host: string;
}

let _config: Config | null = null;
const PRIVATE_KEY_REQUIRED_MSG =
  "GMGN_PRIVATE_KEY is required for critical-auth commands (swap, order get/strategy, and order quote on BSC)";

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

  const host = process.env.GMGN_HOST ?? "https://openapi.gmgn.ai";
  _config = { apiKey: apiKey!, privateKeyPem, host };
  return _config;
}

function die(msg: string): never {
  console.error(`[gmgn-cli] Error: ${msg}`);
  process.exit(1);
}
