# Dynamic Plugin Export Options

Complete reference for `@red-hat-developer-hub/cli plugin export` command options.

## Basic Usage

```bash
npx @red-hat-developer-hub/cli@latest plugin export
```

Run from the plugin's root directory (where `package.json` is located). Creates `dist-dynamic/` directory.

## Command Options

### --shared-package

Control which packages are considered shared (provided by RHDH at runtime).

**Default behavior:** All `@backstage/*` scoped packages are shared.

```bash
# Add a package to shared list
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package @my-org/shared-utils

# Exclude a @backstage package from shared (bundle it instead)
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package '!/@backstage/plugin-notifications/'

# Multiple shared package rules
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package @my-org/shared-utils \
  --shared-package '!/@backstage/plugin-some-other/'
```

**Pattern syntax:**

- Prefix with `!` to negate (exclude from shared)
- Use regex patterns: `'!/@backstage\/plugin-notifications/'`

### --embed-package

Merge package code directly into the plugin bundle.

**Default behavior:** Packages with `-node` or `-common` suffix are auto-embedded.

```bash
# Embed a workspace package
npx @red-hat-developer-hub/cli@latest plugin export \
  --embed-package @my-org/plugin-common

# Embed multiple packages
npx @red-hat-developer-hub/cli@latest plugin export \
  --embed-package @my-org/common \
  --embed-package @my-org/utils
```

**Use cases:**

- Workspace packages that aren't published
- Third-party packages that need modification
- Packages with version conflicts

## Dependency Categories

### Shared Dependencies

- Become `peerDependencies` in generated package.json
- Not bundled in plugin package
- Provided by RHDH at runtime
- Must be version-compatible with target RHDH

**Default shared:**

- All `@backstage/*` packages

### Private Dependencies

- Listed in `bundleDependencies`
- Included in `node_modules/` within `dist-dynamic/`
- Isolated from RHDH's dependencies

**Default private:**

- Non-backstage dependencies
- Dependencies explicitly excluded from shared

### Embedded Dependencies

- Code merged into plugin bundle
- No separate entry in node_modules
- Dependencies hoisted to plugin level

**Default embedded:**

- Packages with `-node` suffix
- Packages with `-common` suffix

## Output Structure

After export, `dist-dynamic/` contains:

### Backend Plugins

```
dist-dynamic/
├── package.json          # Modified for dynamic loading
├── dist/
│   ├── index.js          # Compiled plugin code
│   └── configSchema.json # Self-contained config schema
└── node_modules/         # Private dependencies (if any)
```

### Frontend Plugins

```
dist-dynamic/
├── package.json
├── dist-scalprum/        # Webpack federated modules
│   ├── plugin-manifest.json
│   └── static/
│       ├── main.js
│       └── main.js.map   # Source maps
└── node_modules/
```

## Modified package.json

The generated `package.json` includes:

```json
{
  "name": "@my-org/my-plugin-dynamic",
  "version": "1.0.0",
  "main": "dist/index.js",
  "peerDependencies": {
    "@backstage/backend-plugin-api": "^1.3.0"
  },
  "bundleDependencies": [
    "some-private-dep"
  ],
  "backstage": {
    "role": "backend-plugin"
  }
}
```

## Scalprum Configuration (Frontend)

Frontend plugins require Scalprum configuration for module federation.

### Auto-generated

If not specified, CLI generates defaults:

```json
{
  "scalprum": {
    "name": "my-org.plugin-my-plugin",
    "exposedModules": {
      "PluginRoot": "./src/index.ts"
    }
  }
}
```

### Custom Configuration

Add to `package.json` before export:

```json
{
  "scalprum": {
    "name": "custom-package-name",
    "exposedModules": {
      "FooModule": "./src/foo.ts",
      "BarModule": "./src/bar.ts"
    }
  }
}
```

## Troubleshooting

### Build Errors Before Export

```bash
# Check TypeScript compilation
yarn tsc

# Ensure dependencies installed
yarn install
```

### Missing Dependency Errors

```bash
# Install missing dev dependency
yarn add -D <missing-package>

# Re-run export
npx @red-hat-developer-hub/cli@latest plugin export
```

### Version Conflicts

Check target RHDH version compatibility:

1. Identify target RHDH version
2. Match `@backstage/*` versions to that RHDH
3. Update package.json dependencies
4. Re-run `yarn install`
5. Re-export

### Shared Dependency Not Found

If RHDH doesn't provide an expected shared dependency:

```bash
# Bundle it instead of sharing
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package '!/@backstage/problematic-package/'
```

### Embedded Package Issues

If embedding causes conflicts:

```bash
# Check if package should be shared instead
npx @red-hat-developer-hub/cli@latest plugin export \
  --shared-package @problem/package
```

## Best Practices

### 1. Lock Backstage Versions

```json
{
  "dependencies": {
    "@backstage/backend-plugin-api": "1.3.1"
  }
}
```

### 2. Minimize Dependencies

Keep dependencies minimal to reduce bundle size and conflicts.

### 3. Test Before Publishing

```bash
cp -r dist-dynamic /path/to/rhdh/dynamic-plugins-root/my-plugin-dynamic
yarn workspace backend start
```

### 4. Include Config Schema

```typescript
// src/config.ts
export interface Config {
  myPlugin?: {
    /**
     * Description for users
     * @visibility backend
     */
    apiUrl?: string;
  };
}
```

### 5. Document Required Configuration

Include example configuration with your plugin documentation.
