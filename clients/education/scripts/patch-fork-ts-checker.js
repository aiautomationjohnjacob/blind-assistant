/**
 * Patch script: give fork-ts-checker-webpack-plugin its own local ajv@6
 *
 * WHY THIS EXISTS:
 *   react-scripts@5 bundles fork-ts-checker-webpack-plugin@6.5.x, which has a nested
 *   ajv-keywords@3.5.2 that requires ajv@^6. However, schema-utils@4 (also in the tree)
 *   requires ajv@^8 and ajv-keywords@^5. The npm `overrides` field forces ajv@^8 at the
 *   top level so schema-utils@4 works, but this breaks fork-ts-checker's nested
 *   ajv-keywords@3.5.2 which resolves ajv from the top level and gets ajv@8.
 *
 *   npm nested overrides (`"fork-ts-checker-webpack-plugin": {"ajv-keywords": "^5"}`)
 *   are not applied when `--legacy-peer-deps` is used, so we must patch manually.
 *
 *   This script installs ajv@^6 inside the fork-ts-checker-webpack-plugin's own
 *   node_modules directory, so its ajv-keywords@3.5.2 resolves to ajv@6 (compatible).
 *
 * SAFE TO DELETE if react-scripts is upgraded or replaced with Vite.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const FORK_TS_DIR = path.join(
  __dirname,
  '..',
  'node_modules',
  'fork-ts-checker-webpack-plugin',
);
const FORK_TS_NODE_MODULES = path.join(FORK_TS_DIR, 'node_modules');
const FORK_TS_AJV_DIR = path.join(FORK_TS_NODE_MODULES, 'ajv');

// Only patch if fork-ts-checker-webpack-plugin is installed (dev environment check)
if (!fs.existsSync(FORK_TS_DIR)) {
  console.log('patch-fork-ts-checker: fork-ts-checker-webpack-plugin not found, skipping.');
  process.exit(0);
}

// Check if ajv@6 is already installed in the nested location
if (fs.existsSync(FORK_TS_AJV_DIR)) {
  const ajvPkg = JSON.parse(fs.readFileSync(path.join(FORK_TS_AJV_DIR, 'package.json'), 'utf8'));
  if (ajvPkg.version && ajvPkg.version.startsWith('6.')) {
    console.log(`patch-fork-ts-checker: ajv@${ajvPkg.version} already present in fork-ts-checker, skipping.`);
    process.exit(0);
  }
}

// Install ajv@6 inside fork-ts-checker-webpack-plugin's own node_modules
console.log('patch-fork-ts-checker: Installing ajv@^6.12.6 inside fork-ts-checker-webpack-plugin/node_modules/...');
try {
  execSync('npm install ajv@^6.12.6 --prefix . --no-save --legacy-peer-deps', {
    cwd: FORK_TS_DIR,
    stdio: 'pipe',
  });
  console.log('patch-fork-ts-checker: ajv@6 installed successfully.');
} catch (err) {
  // Non-fatal: if the patch fails, the build may fail with a clear error message.
  // This is better than crashing postinstall silently.
  console.warn('patch-fork-ts-checker: Failed to install ajv@6:', err.message);
  console.warn('If the build fails with ajv-related errors, see scripts/patch-fork-ts-checker.js');
}
