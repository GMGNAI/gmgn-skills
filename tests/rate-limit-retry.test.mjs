import assert from 'node:assert/strict';
import test from 'node:test';
import { generateKeyPairSync } from 'node:crypto';
import { createServer } from 'node:http';
import { OpenApiClient } from '../dist/client/OpenApiClient.js';

// Offline transport fixture: never contacts GMGN or loads credential files.
function limited(error = 'RATE_LIMIT_EXCEEDED', reset = Math.floor(Date.now() / 1000)) {
  return new Response(JSON.stringify({ code: 429, error, message: 'fixture cooldown' }), {
    status: 429,
    headers: reset == null ? {} : { 'x-ratelimit-reset': String(reset) },
  });
}

function fixture(t, responses) {
  const originalFetch = globalThis.fetch;
  const originalWait = process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
  delete process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    assert.equal(new URL(url).origin, 'https://offline.invalid');
    calls.push({ url: new URL(url), options, at: Date.now() });
    assert.ok(responses.length, 'unexpected extra request');
    const response = responses.shift();
    if (response instanceof Error) throw response;
    return response;
  };
  t.after(() => {
    globalThis.fetch = originalFetch;
    if (originalWait === undefined) delete process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
    else process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS = originalWait;
  });
  return { client: new OpenApiClient({ apiKey: 'offline-fixture', host: 'https://offline.invalid' }), calls };
}

function success() {
  return new Response(JSON.stringify({ code: 0, data: { fixture: true } }));
}

const read = client => client.getTokenInfo('robinhood', '0x0000000000000000000000000000000000000001');

test('read retries a short parsed rate limit once, after the buffer, with fresh request identity', async t => {
  const { client, calls } = fixture(t, [limited(), success()]);
  assert.deepEqual(await read(client), { fixture: true });
  assert.equal(calls.length, 2);
  assert.ok(calls[1].at - calls[0].at >= 950, 'must wait for the one-second retry buffer');
  assert.notEqual(calls[0].url.searchParams.get('client_id'), calls[1].url.searchParams.get('client_id'));
  assert.equal(calls[1].options.method, 'GET');
  assert.equal(calls[0].url.pathname, calls[1].url.pathname);
});

test('a second rate limit is propagated without a third request', async t => {
  const { client, calls } = fixture(t, [limited(), limited()]);
  await assert.rejects(read(client), { apiError: 'RATE_LIMIT_EXCEEDED' });
  assert.equal(calls.length, 2);
});

test('a short RATE_LIMIT_BANNED uses the same single retry', async t => {
  const { client, calls } = fixture(t, [limited('RATE_LIMIT_BANNED'), success()]);
  assert.deepEqual(await read(client), { fixture: true });
  assert.equal(calls.length, 2);
});

test('the explicit zero wait setting disables retries', async t => {
  const { client, calls } = fixture(t, [limited()]);
  process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS = '0';
  await assert.rejects(read(client), { apiError: 'RATE_LIMIT_EXCEEDED' });
  assert.equal(calls.length, 1);
});

for (const [name, response] of [
  ['long cooldown', () => limited('RATE_LIMIT_EXCEEDED', Math.floor(Date.now() / 1000) + 30)],
  ['missing reset', () => limited('RATE_LIMIT_EXCEEDED', null)],
  ['invalid reset', () => limited('RATE_LIMIT_EXCEEDED', 'invalid')],
  ['maximum ban', () => limited('RATE_LIMIT_BANNED_MAX')],
  ['business-error block', () => limited('ERROR_RATE_LIMIT_BLOCKED')],
  ['plan upgrade', () => limited('PLAN_UPGRADE_REQUIRED')],
  ['non-JSON response', () => new Response('unavailable', { status: 503 })],
  ['network error', () => new Error('fixture connection lost')],
]) {
  test(`${name} is not retried`, async t => {
    const { client, calls } = fixture(t, [response()]);
    await assert.rejects(read(client));
    assert.equal(calls.length, 1);
  });
}

test('a successful first response does not retry', async t => {
  const { client, calls } = fixture(t, [success()]);
  assert.deepEqual(await read(client), { fixture: true });
  assert.equal(calls.length, 1);
});

// Disposable test key stays in memory; no user wallet or configuration is read.
function signedFixture(t, responses) {
  const { calls } = fixture(t, responses);
  const { privateKey } = generateKeyPairSync('ed25519');
  const client = new OpenApiClient({
    apiKey: 'offline-fixture', host: 'https://offline.invalid',
    privateKeyPem: privateKey.export({ type: 'pkcs8', format: 'pem' }),
  });
  return { client, calls };
}

test('signed reads retry with regenerated authentication', async t => {
  const { client, calls } = signedFixture(t, [limited(), success()]);
  assert.deepEqual(await client.getFollowWallet('robinhood'), { fixture: true });
  assert.equal(calls.length, 2);
  assert.notEqual(calls[0].options.headers['X-Signature'], calls[1].options.headers['X-Signature']);
  assert.notEqual(calls[0].url.searchParams.get('client_id'), calls[1].url.searchParams.get('client_id'));
});

for (const method of ['swap', 'multiSwap', 'createStrategyOrder', 'cancelStrategyOrder', 'createToken']) {
  test(`signed write ${method} never retries a rate limit`, async t => {
    const { client, calls } = signedFixture(t, [limited()]);
    await assert.rejects(client[method]({ chain: 'robinhood' }), { apiError: 'RATE_LIMIT_EXCEEDED' });
    assert.equal(calls.length, 1);
    assert.equal(calls[0].options.method, 'POST');
  });
}

test('existing read-only POST policy is preserved', async t => {
  const { client, calls } = fixture(t, [limited(), success()]);
  assert.deepEqual(await client.getCalloutGlobal(['robinhood']), { fixture: true });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.body, calls[1].options.body);
});

test('real loopback HTTP waits past a future reset before retrying', async t => {
  const previousWait = process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
  delete process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
  const calls = [];
  let reset;
  const server = createServer((req, res) => {
    calls.push({ url: req.url, at: Date.now() });
    if (calls.length === 1) {
      reset = Math.floor(Date.now() / 1000) + 1;
      res.writeHead(429, { 'content-type': 'application/json', 'x-ratelimit-reset': String(reset) });
      res.end(JSON.stringify({ code: 429, error: 'RATE_LIMIT_EXCEEDED' }));
    } else {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ code: 0, data: { loopback: true } }));
    }
  });
  t.after(async () => {
    if (previousWait === undefined) delete process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS;
    else process.env.GMGN_RATE_LIMIT_AUTO_RETRY_MAX_WAIT_MS = previousWait;
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const client = new OpenApiClient({ apiKey: 'offline-fixture', host: `http://127.0.0.1:${server.address().port}` });
  assert.deepEqual(await read(client), { loopback: true });
  assert.equal(calls.length, 2);
  assert.ok(calls[1].at >= reset * 1000 + 950, 'retry must follow reset plus the safety buffer');
});
