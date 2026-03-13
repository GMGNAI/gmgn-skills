export function printResult(data: unknown, raw?: boolean): void {
  if (raw) {
    console.log(JSON.stringify(data));
  } else {
    console.log(JSON.stringify(data, null, 2));
  }
}

export function exitOnError(err: Error): never {
  console.error(`[gmgn-cli] ${err.message}`);
  if (process.env.GMGN_DEBUG) {
    if ((err as NodeJS.ErrnoException).code) {
      console.error(`[gmgn-cli] code: ${(err as NodeJS.ErrnoException).code}`);
    }
    if ((err as { cause?: unknown }).cause) {
      console.error(`[gmgn-cli] cause: ${(err as { cause?: unknown }).cause}`);
    }
    console.error(err.stack ?? "");
  }
  process.exit(1);
}
