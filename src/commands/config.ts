import { Command } from "commander";
import * as crypto from "crypto";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execSync } from "child_process";
import { loadEnvFiles } from "../config.js";

const GMGN_CONFIG_DIR = path.join(os.homedir(), ".config", "gmgn");
const KEYPAIR_FILE = path.join(GMGN_CONFIG_DIR, "keypair.pem");
const ENV_FILE = path.join(GMGN_CONFIG_DIR, ".env");
const GMGN_API_URL = "https://gmgn.ai/ai/generateapi";

type Lang = "zh-CN" | "zh-TW" | "en";

function detectLang(): Lang {
  const locale =
    process.env.LANG ||
    process.env.LC_ALL ||
    process.env.LC_MESSAGES ||
    Intl.DateTimeFormat().resolvedOptions().locale ||
    "en";
  const l = locale.toLowerCase();
  if (l.startsWith("zh_tw") || l.startsWith("zh-tw") || l.startsWith("zh_hk") || l.startsWith("zh-hk")) return "zh-TW";
  if (l.startsWith("zh")) return "zh-CN";
  return "en";
}

const MESSAGES = {
  linkGuide: {
    "zh-CN": (link: string) =>
      `请点击下方链接创建你的 GMGN API Key，完成后将 Key 发给我，我来帮你完成配置：\n${link}`,
    "zh-TW": (link: string) =>
      `請點擊下方連結建立你的 GMGN API Key，完成後將 Key 發給我，我來幫你完成配置：\n${link}`,
    en: (link: string) =>
      `Please click the link below to create your GMGN API Key. Once created, send me the API Key and I will finish the configuration:\n${link}`,
  },
  verifySuccess: {
    "zh-CN": "配置验证成功，可以开始使用了。",
    "zh-TW": "配置驗證成功，可以開始使用了。",
    en: "Configuration verified successfully. You are ready to use GMGN.",
  },
  verifyFail: {
    "zh-CN":
      "配置验证失败：API Key 与本地密钥不匹配。\n请确认：\n1. API Key 是否填写正确；\n2. 创建 API Key 时，是否使用的是页面自动填入的公钥。",
    "zh-TW":
      "配置驗證失敗：API Key 與本地密鑰不匹配。\n請確認：\n1. API Key 是否填寫正確；\n2. 創建 API Key 時，是否使用的是頁面自動填入的公鑰。",
    en: "Configuration verification failed: API Key does not match your local key pair.\nPlease confirm:\n1. Whether the API Key was entered correctly.\n2. Whether you used the public key that was pre-filled on the page when creating the API Key.",
  },
  verifyNetworkFail: {
    "zh-CN": "配置已写入，但验证请求失败（可能是网络问题）。你可以先尝试使用，如遇接口报错再重新配置。",
    "zh-TW": "配置已寫入，但驗證請求失敗（可能是網路問題）。你可以先嘗試使用，如遇介面報錯再重新配置。",
    en: "Configuration saved, but the verification request failed (possibly a network issue). You can try using it now and reconfigure if you encounter API errors.",
  },
};

function getOrCreateKeypair(): string {
  fs.mkdirSync(GMGN_CONFIG_DIR, { recursive: true });

  if (fs.existsSync(KEYPAIR_FILE)) {
    const content = fs.readFileSync(KEYPAIR_FILE, "utf-8");
    const match = content.match(/(-----BEGIN PUBLIC KEY-----[\s\S]+?-----END PUBLIC KEY-----)/);
    if (!match) {
      console.error("Error: keypair.pem exists but public key could not be parsed. Delete ~/.config/gmgn/keypair.pem and try again.");
      process.exit(1);
    }
    return match[1] + "\n";
  }

  const { privateKey, publicKey } = crypto.generateKeyPairSync("ed25519");
  const privatePem = privateKey.export({ type: "pkcs8", format: "pem" }) as string;
  const publicPem = publicKey.export({ type: "spki", format: "pem" }) as string;
  const entry = `# Private Key\n${privatePem}\n# Public Key\n${publicPem}\n`;
  fs.writeFileSync(KEYPAIR_FILE, entry, { mode: 0o600 });
  return publicPem;
}

function writeEnv(apiKey: string, privatePem: string): void {
  const pkOneLine = privatePem.replace(/\r?\n/g, "\\n");
  let existing = fs.existsSync(ENV_FILE) ? fs.readFileSync(ENV_FILE, "utf-8") : "";
  existing = existing
    .split("\n")
    .filter((l) => !/^GMGN_API_KEY=|^GMGN_PRIVATE_KEY=/.test(l))
    .join("\n")
    .trim();
  const content = (existing ? existing + "\n" : "") + `GMGN_API_KEY=${apiKey}\nGMGN_PRIVATE_KEY=${pkOneLine}\n`;
  fs.mkdirSync(GMGN_CONFIG_DIR, { recursive: true });
  fs.writeFileSync(ENV_FILE, content, { mode: 0o600 });
}

function verify(): "ok" | "auth_fail" | "network_fail" {
  try {
    execSync("gmgn-cli track follow-wallet --chain sol --limit 1", { stdio: "pipe" });
    return "ok";
  } catch (e: unknown) {
    const output = [
      (e as any).stderr?.toString() ?? "",
      (e as any).stdout?.toString() ?? "",
    ].join(" ");
    if (/401|403|unauthorized|forbidden|invalid.*key|key.*invalid|signature/i.test(output)) {
      return "auth_fail";
    }
    return "network_fail";
  }
}

export function registerConfigCommands(program: Command): void {
  const cmd = program
    .command("config")
    .description("Generate an Ed25519 key pair and output a pre-filled GMGN API Key creation link, or apply an API Key");

  cmd
    .option("--check", "Check if GMGN_API_KEY is configured (exit 0 = found, exit 1 = not found)")
    .option("--apply <api_key>", "Write API Key + private key to ~/.config/gmgn/.env and verify")
    .action(async (opts) => {
      const lang = detectLang();

      if (opts.check) {
        loadEnvFiles();
        process.exit(process.env.GMGN_API_KEY ? 0 : 1);
      }

      if (opts.apply) {
        // --apply: read private key from keypair.pem, write .env, verify
        if (!fs.existsSync(KEYPAIR_FILE)) {
          console.error("Error: ~/.config/gmgn/keypair.pem not found. Run `gmgn-cli config` first to generate a key pair.");
          process.exit(1);
        }
        const content = fs.readFileSync(KEYPAIR_FILE, "utf-8");
        const match = content.match(/(-----BEGIN PRIVATE KEY-----[\s\S]+?-----END PRIVATE KEY-----)/);
        if (!match) {
          console.error("Error: keypair.pem exists but private key could not be parsed. Delete ~/.config/gmgn/keypair.pem and run `gmgn-cli config` again.");
          process.exit(1);
        }
        writeEnv(opts.apply, match[1]);

        const result = verify();
        if (result === "ok") {
          console.log(MESSAGES.verifySuccess[lang]);
        } else if (result === "auth_fail") {
          console.error(MESSAGES.verifyFail[lang]);
          process.exit(1);
        } else {
          console.log(MESSAGES.verifyNetworkFail[lang]);
        }
        return;
      }

      // Default: generate/reuse keypair, output link with guidance
      const publicPem = getOrCreateKeypair();
      const link = `${GMGN_API_URL}?pbk=${encodeURIComponent(publicPem)}`;
      console.log(MESSAGES.linkGuide[lang](link));
    });
}
