const assert = require('assert');

const baseUrl = process.argv[2] || 'http://127.0.0.1:4321';
const paths = ['/ko/', '/ko/handbook/', '/ko/news/', '/login'];

function extractCspNonce(cspHeader) {
  const match = cspHeader.match(/script-src[^;]*'nonce-([^']+)'/i);
  return match ? match[1] : null;
}

function extractScriptTags(html) {
  return [...html.matchAll(/<script\b([^>]*)>/gi)].map((match) => match[0]);
}

async function run() {
  for (const path of paths) {
    const response = await fetch(new URL(path, baseUrl));
    assert.equal(response.status, 200, `Expected 200 for ${path}, got ${response.status}`);

    const cspHeader = response.headers.get('content-security-policy') || '';
    const expectedNonce = extractCspNonce(cspHeader);
    assert(expectedNonce, `Missing script-src nonce in CSP header for ${path}`);

    const html = await response.text();
    const scriptTags = extractScriptTags(html);
    assert(scriptTags.length > 0, `Expected script tags in ${path}`);

    const missingNonce = scriptTags.filter((tag) => !/\bnonce\s*=\s*["'][^"']+["']/i.test(tag));
    assert.equal(
      missingNonce.length,
      0,
      `Found script tags without nonce on ${path}:\n${missingNonce.slice(0, 5).join('\n')}`,
    );

    const invalidNonce = scriptTags.filter((tag) => {
      const match = tag.match(/\bnonce\s*=\s*["']([^"']+)["']/i);
      return match && match[1] !== expectedNonce;
    });
    assert.equal(
      invalidNonce.length,
      0,
      `Found script tags with mismatched nonce on ${path}:\n${invalidNonce.slice(0, 5).join('\n')}`,
    );
  }

  console.log('csp-inline-scripts.test: ok');
}

run().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
