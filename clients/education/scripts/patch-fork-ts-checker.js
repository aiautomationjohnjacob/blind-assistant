/**
 * Patch script: give legacy webpack plugins their own local ajv@6
 *
 * WHY THIS EXISTS:
 *   react-scripts@5 uses several webpack plugins that have nested ajv-keywords@3.x,
 *   which requires ajv@^6. However, schema-utils@4 (also in the tree) requires ajv@^8
 *   and ajv-keywords@^5. The npm `overrides` field forces ajv@^8 at the top level so
 *   schema-utils@4 works, but this breaks any plugin with nested ajv-keywords@3.x
 *   because they resolve ajv from the top level (getting ajv@8, which is incompatible).
 *
 *   npm nested overrides (`"fork-ts-checker-webpack-plugin": {"ajv-keywords": "^5"}`)
 *   are silently ignored when `--legacy-peer-deps` is used, so we must patch manually.
 *
 *   This script installs ajv@^6 inside each affected plugin's own node_modules directory
 *   so their ajv-keywords@3.x resolves to ajv@6 (the compatible version).
 *
 * AFFECTED PLUGINS (have nested ajv-keywords@3.x without their own ajv):
 *   - fork-ts-checker-webpack-plugin@6.5.3
 *   - file-loader@6.2.0
 *   - babel-loader@8.x
 *
 * SAFE TO DELETE if react-scripts is upgraded to v6+, or replaced with Vite/rspack.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const NODE_MODULES = path.join(__dirname, '..', 'node_modules');

// Packages that have their own nested ajv-keywords@3.x but no local ajv@6
const AFFECTED_PLUGINS = [
  'fork-ts-checker-webpack-plugin',
  'file-loader',
  'babel-loader',
];

let patchCount = 0;

for (const plugin of AFFECTED_PLUGINS) {
  const pluginDir = path.join(NODE_MODULES, plugin);

  // Skip if plugin is not installed (optional dep or not in this environment)
  if (!fs.existsSync(pluginDir)) {
    console.log(`patch-fork-ts-checker: ${plugin} not found, skipping.`);
    continue;
  }

  // Only patch plugins that have their own nested ajv-keywords
  const nestedAjvKeywords = path.join(pluginDir, 'node_modules', 'ajv-keywords');
  if (!fs.existsSync(nestedAjvKeywords)) {
    console.log(`patch-fork-ts-checker: ${plugin} has no nested ajv-keywords, skipping.`);
    continue;
  }

  const nestedAjv = path.join(pluginDir, 'node_modules', 'ajv');

  // Check if ajv@6 is already installed in the nested location
  if (fs.existsSync(nestedAjv)) {
    try {
      const ajvPkg = JSON.parse(fs.readFileSync(path.join(nestedAjv, 'package.json'), 'utf8'));
      if (ajvPkg.version && ajvPkg.version.startsWith('6.')) {
        console.log(`patch-fork-ts-checker: ${plugin} already has ajv@${ajvPkg.version}, skipping.`);
        continue;
      }
    } catch (e) {
      // package.json unreadable — fall through and reinstall
    }
  }

  // Install ajv@6 inside this plugin's own node_modules
  console.log(`patch-fork-ts-checker: Installing ajv@^6.12.6 inside ${plugin}/node_modules/...`);
  try {
    execSync('npm install ajv@^6.12.6 --prefix . --no-save --legacy-peer-deps', {
      cwd: pluginDir,
      stdio: 'pipe',
    });
    console.log(`patch-fork-ts-checker: ${plugin} patched successfully.`);
    patchCount++;
  } catch (err) {
    // Non-fatal: if the patch fails, the build may fail with a clear error message.
    console.warn(`patch-fork-ts-checker: Failed to patch ${plugin}:`, err.message);
    console.warn('If the build fails with ajv-related errors, see scripts/patch-fork-ts-checker.js');
  }
}

if (patchCount > 0) {
  console.log(`patch-fork-ts-checker: Done. Patched ${patchCount} plugin(s).`);
} else {
  console.log('patch-fork-ts-checker: All plugins already patched or not affected.');
}
