# Create Backend Plugin

Scaffold and implement a backend dynamic plugin for Red Hat Developer Hub (RHDH).

## When to Use

- New backend API plugins
- Backend modules for existing plugins (e.g., `catalog-backend-module-*`)
- Scaffolder actions and templates
- Catalog processors and providers
- Authentication modules
- Any server-side functionality for RHDH

**Not for frontend plugins** — use the `frontend` command instead.

## Workflow

1. Determine RHDH version
2. Scaffold app and plugin
3. Implement plugin logic
4. Export and package (see `export` command)
5. Configure for RHDH

## Step 1: Determine RHDH Version

Use the target RHDH version established in `SKILL.md`. Ask the user for it if it is still unresolved.

## Step 2: Scaffold App and Plugin

Run the scaffold script from the directory where the app should be created:

```bash
python scripts/scaffold.py \
  --type backend \
  --rhdh-version 1.9 \
  --plugin-id my-plugin
```

Run `python scripts/scaffold.py --help` for all options.

> **Note:** The Backstage app exists only to provide the correct CLI version for plugin generation. All development and testing happens in the plugin directory.

The generated plugin structure:

```
plugins/<plugin-id>-backend/
├── src/
│   ├── index.ts           # Main entry point
│   ├── plugin.ts          # Plugin definition (new backend system)
│   └── service/
│       └── router.ts      # Express router
├── package.json
└── README.md
```

## Step 3: Implement Plugin Logic

Backend plugins **must** use the new backend system for dynamic plugin compatibility. Export a default using `createBackendPlugin()` or `createBackendModule()`.

### Plugin definition (`src/plugin.ts`)

```typescript
import {
  coreServices,
  createBackendPlugin,
} from '@backstage/backend-plugin-api';
import { createRouter } from './service/router';

export const myPlugin = createBackendPlugin({
  pluginId: 'my-plugin',
  register(env) {
    env.registerInit({
      deps: {
        httpRouter: coreServices.httpRouter,
        logger: coreServices.logger,
        config: coreServices.rootConfig,
      },
      async init({ httpRouter, logger, config }) {
        httpRouter.use(
          await createRouter({
            logger,
            config,
          }),
        );
        httpRouter.addAuthPolicy({
          path: '/health',
          allow: 'unauthenticated',
        });
      },
    });
  },
});

export default myPlugin;
```

### Entry point (`src/index.ts`)

```typescript
export { default } from './plugin';
```

Build and verify:

```bash
cd plugins/<plugin-id>-backend
yarn build
```

## Step 4: Export and Package

Use the `export` command for the full pipeline. Quick version:

```bash
cd plugins/<plugin-id>-backend
npx @red-hat-developer-hub/cli@latest plugin export
npx @red-hat-developer-hub/cli@latest plugin package \
  --tag quay.io/<namespace>/<plugin-name>:v0.1.0
podman push quay.io/<namespace>/<plugin-name>:v0.1.0
```

For advanced options (dependency handling, multi-plugin bundles, tgz/npm), use the `export` command reference.

## Step 5: Configure for RHDH

Add to `dynamic-plugins.yaml`:

```yaml
plugins:
  - package: oci://quay.io/<namespace>/<plugin-name>:v0.1.0!<plugin-id>-backend-dynamic
    disabled: false
    pluginConfig:
      myPlugin:
        someOption: value
```

For local testing, copy `dist-dynamic` to RHDH's `dynamic-plugins-root`:

```bash
cp -r dist-dynamic /path/to/rhdh/dynamic-plugins-root/<plugin-id>-backend-dynamic
```

> **Windows:** Use `xcopy /E /I` or `robocopy /E` instead of `cp -r`.

See `examples/dynamic-plugins.yaml` for complete configuration examples.

## Common Issues

### Plugin Not Loading

- Verify plugin uses new backend system (`createBackendPlugin`)
- Check plugin is exported as default export
- Ensure version compatibility with target RHDH

### Dependency Conflicts

- Use `--shared-package` to exclude problematic shared deps
- Use `--embed-package` to bundle required deps

### Build Failures

- Run `yarn tsc` to check TypeScript errors before export
- Ensure all `@backstage/*` versions match target RHDH
