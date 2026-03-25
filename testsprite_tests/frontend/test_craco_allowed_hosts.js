/**
 * TestSprite — craco ALLOWED_HOSTS gate (Node.js static analysis)
 *
 * Verifies that frontend/craco.config.js correctly gates `allowedHosts`
 * behind the ALLOWED_HOSTS environment variable without running a dev server.
 *
 * Usage: node testsprite_tests/frontend/test_craco_allowed_hosts.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const CRACO_PATH = path.resolve(__dirname, '../../frontend/craco.config.js');

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✅  PASS — ${message}`);
    passed++;
  } else {
    console.error(`  ❌  FAIL — ${message}`);
    failed++;
  }
}

console.log('\n🧪  TestSprite: craco ALLOWED_HOSTS gate\n');

// --- Load source ---
assert(fs.existsSync(CRACO_PATH), 'craco.config.js exists at expected path');
const src = fs.readFileSync(CRACO_PATH, 'utf8');

// --- Assertions ---
assert(
  !/(devServerConfig\.allowedHosts\s*=\s*['"]all['"])/.test(src) ||
    /process\.env\.ALLOWED_HOSTS/.test(src),
  'allowedHosts="all" is not set unconditionally'
);

assert(
  /process\.env\.ALLOWED_HOSTS/.test(src),
  'process.env.ALLOWED_HOSTS is referenced'
);

assert(
  /if\s*\(\s*process\.env\.ALLOWED_HOSTS\s*\)/.test(src),
  'if (process.env.ALLOWED_HOSTS) guard is present'
);

assert(
  /\.split\(/.test(src) && /\.trim\(\)/.test(src),
  'split + trim logic present for comma-separated hosts'
);

assert(
  /\.filter\(Boolean\)/.test(src),
  '.filter(Boolean) removes empty entries'
);

assert(
  /'all'/.test(src) || /"all"/.test(src),
  'ALLOWED_HOSTS=all opt-in case is handled'
);

// --- Summary ---
console.log(`\nResults: ${passed} passed, ${failed} failed\n`);
process.exit(failed > 0 ? 1 : 0);
