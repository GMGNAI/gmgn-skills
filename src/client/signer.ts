import * as crypto from "crypto";
import * as fs from "fs";
import * as path from "path";

export type SignAlgorithm = "Ed25519" | "RSA-SHA256";

/**
 * Detect signing algorithm from PEM private key
 */
export function detectAlgorithm(pem: string): SignAlgorithm {
  const key = crypto.createPrivateKey(pem);
  switch (key.asymmetricKeyType) {
    case "ed25519": return "Ed25519";
    case "rsa":     return "RSA-SHA256";
    default:
      throw new Error(`Unsupported key type: ${key.asymmetricKeyType}. Supported: Ed25519, RSA`);
  }
}

/**
 * Build auth query params (timestamp + client_id)
 * timestamp: Unix seconds, server validates within ±5s
 * client_id: UUID, replays rejected within 7s
 */
export function buildAuthQuery(): { timestamp: number; client_id: string } {
  return {
    timestamp: Math.floor(Date.now() / 1000),
    client_id: crypto.randomUUID(),
  };
}

/**
 * Build the signature message (critical auth)
 * Format: {sub_path}:{sorted_query_string}:{request_body}:{timestamp}
 * sorted_query_string: all query params (including timestamp, client_id) sorted alphabetically by key
 */
export function buildMessage(
  subPath: string,
  queryParams: Record<string, string | number>,
  body: string,
  timestamp: number
): string {
  const sortedQs = Object.keys(queryParams)
    .sort()
    .map((k) => `${k}=${queryParams[k]}`)
    .join("&");
  return `${subPath}:${sortedQs}:${body}:${timestamp}`;
}

/**
 * Load private key file (PEM format)
 */
export function loadPrivateKey(keyPath: string): string {
  const resolved = path.resolve(process.cwd(), keyPath);
  return fs.readFileSync(resolved, "utf-8");
}

/**
 * Sign a message and return the base64-encoded signature
 *
 * Ed25519: signs raw message bytes (no hashing)
 * RSA-SHA256: RSA-PSS + SHA256, salt length = 32 (matches server-side rsa.VerifyPSS nil opts)
 */
export function sign(
  message: string,
  privateKeyPem: string,
  algorithm: SignAlgorithm
): string {
  const msgBuf = Buffer.from(message, "utf-8");

  if (algorithm === "Ed25519") {
    const sig = crypto.sign(null, msgBuf, privateKeyPem);
    return sig.toString("base64");
  }

  // RSA-SHA256 with PSS padding, salt length = digest length (32)
  const sig = crypto.sign("sha256", msgBuf, {
    key: privateKeyPem,
    padding: crypto.constants.RSA_PKCS1_PSS_PADDING,
    saltLength: 32,
  });
  return sig.toString("base64");
}
