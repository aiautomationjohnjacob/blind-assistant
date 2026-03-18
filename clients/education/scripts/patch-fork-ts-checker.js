/**
 * Patch script: give legacy webpack plugins and linting tools their own local ajv@6
 *
 * WHY THIS EXISTS:
 *   react-scripts@5 is EOL and has two conflicting ajv requirement trees:
 *   - terser-webpack-plugin, webpack → schema-utils@4 → ajv-keywords@5 → ajv@^8
 *   - eslint@8, babel-loader, file-loader, fork-ts-checker-webpack-plugin →
 *       ajv-keywords@3.x → ajv@^6
 *
 *   The npm `overrides` field forces ajv@^8 globally so schema-utils@4 works.
 *   But packages with nested ajv-keywords@3.x then resolve ajv from the top level
 *   (getting ajv@8), causing API compatibility crashes (_opts undefined, _formats
 *   undefined, etc).
 *
 *   npm nested overrides do not apply when `--legacy-peer-deps` is used (npm
 *   ignores override constraints in that mode). So we manually install ajv@^6 inside
 *   each affected package's own node_modules directory.
 *
 *   This runs as a `postinstall` script so it applies after every `npm install` or
 *   `npm ci`. It is idempotent: already-patched packages are skipped.
 *
 * AFFECTED PACKAGES (have their own nested ajv-keywords@3.x or eslint that needs ajv@6):
 *   - fork-ts-checker-webpack-plugin (nested ajv-keywords@3.5.2 + eslint)
 *   - file-loader (nested ajv-keywords@3.5.2 + eslint + @eslint/eslintrc)
 *   - babel-loader (nested ajv-keywords@3.5.2 + eslint + @eslint/eslintrc)
 *   - eslint (top-level; uses ajv@6 API in lib/shared/ajv.js)
 *   - @eslint/eslintrc (top-level; uses ajv@6 API in lib/shared/ajv.js)
 *
 * SAFE TO DELETE if react-scripts is upgraded to v6+, or replaced with Vite/rspack.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const NODE_MODULES = path.join(__dirname, '..', 'node_modules');

/**
 * Install ajv@^6 inside a specific package's node_modules directory.
 * Returns true if patched (or already patched), false if failed.
 */
function patchPackage(packagePath) {
  const packageName = packagePath.replace(NODE_MODULES + path.sep, '');

  // Skip if package is not installed
  if (!fs.existsSync(packagePath)) {
    return true; // not installed = not broken
  }

  const nestedNodeModules = path.join(packagePath, 'node_modules');
  const nestedAjv = path.join(nestedNodeModules, 'ajv');

  // Check if ajv@6 is already present and correct
  if (fs.existsSync(nestedAjv)) {
    try {
      const ajvPkg = JSON.parse(
        fs.readFileSync(path.join(nestedAjv, 'package.json'), 'utf8')
      );
      if (ajvPkg.version && ajvPkg.version.startsWith('6.')) {
        console.log(
          `patch-ajv6: ${packageName} already has ajv@${ajvPkg.version}, skipping.`
        );
        return true;
      }
    } catch (e) {
      // package.json unreadable — fall through and reinstall
    }
  }

  // Ensure node_modules directory exists
  if (!fs.existsSync(nestedNodeModules)) {
    fs.mkdirSync(nestedNodeModules, { recursive: true });
  }

  console.log(`patch-ajv6: Installing ajv@^6.12.6 inside ${packageName}/node_modules/...`);
  try {
    execSync('npm install ajv@^6.12.6 --prefix . --no-save --legacy-peer-deps', {
      cwd: packagePath,
      stdio: 'pipe',
    });
    console.log(`patch-ajv6: ${packageName} patched successfully.`);
    return true;
  } catch (err) {
    console.warn(`patch-ajv6: Failed to patch ${packageName}:`, err.message);
    return false;
  }
}

// Packages that use ajv@6 APIs but are exposed to top-level ajv@8 via overrides:
const PACKAGES_TO_PATCH = [
  // Webpack loaders with nested ajv-keywords@3.x
  path.join(NODE_MODULES, 'fork-ts-checker-webpack-plugin'),
  path.join(NODE_MODULES, 'file-loader'),
  path.join(NODE_MODULES, 'babel-loader'),
  // Top-level eslint and @eslint/eslintrc use _opts.defaultMeta (ajv@6 API)
  path.join(NODE_MODULES, 'eslint'),
  path.join(NODE_MODULES, '@eslint', 'eslintrc'),
];

let patchCount = 0;
let failCount = 0;

for (const pkgPath of PACKAGES_TO_PATCH) {
  const success = patchPackage(pkgPath);
  if (success) {
    patchCount++;
  } else {
    failCount++;
  }
}

if (failCount > 0) {
  console.warn(
    `patch-ajv6: ${failCount} package(s) could not be patched. ` +
    'Build may fail with ajv-related errors. See scripts/patch-fork-ts-checker.js.'
  );
} else {
  console.log(`patch-ajv6: Done. All ${patchCount} packages are ready.`);
}
