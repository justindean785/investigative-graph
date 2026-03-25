/**
 * TestSprite — Frontend API Config Tests (Node.js static analysis)
 *
 * Verifies that frontend/src/config/api.js reads REACT_APP_BACKEND_URL
 * and REACT_APP_API_KEY from the environment and sets the axios default header.
 *
 * Usage: node testsprite_tests/frontend/test_api_config.js
 */
'use strict';

const fs = require('fs');
const path = require('path');

const API_CONFIG_PATH = path.resolve(
  __dirname,
  '../../frontend/src/config/api.js'
);

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

console.log('\n🧪  TestSprite: Frontend API Config\n');

assert(
  fs.existsSync(API_CONFIG_PATH),
  'frontend/src/config/api.js exists'
);

const src = fs.existsSync(API_CONFIG_PATH)
  ? fs.readFileSync(API_CONFIG_PATH, 'utf8')
  : '';

assert(
  /REACT_APP_BACKEND_URL/.test(src),
  'REACT_APP_BACKEND_URL is read from process.env'
);

assert(
  /REACT_APP_API_KEY/.test(src),
  'REACT_APP_API_KEY is read from process.env'
);

assert(
  /axios\.defaults\.headers/.test(src) && /x-api-key/.test(src),
  'axios default x-api-key header is configured'
);

console.log(`\nResults: ${passed} passed, ${failed} failed\n`);
process.exit(failed > 0 ? 1 : 0);
