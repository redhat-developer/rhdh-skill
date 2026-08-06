# E2E Patterns: Shared Playwright Infrastructure

Common patterns across all `rhdh-plugins` workspaces. Reference this when writing reproduction tests (Step 3).

## Shared Architecture

All workspaces with e2e tests follow the same structure:

```
workspaces/<workspace>/
├── playwright.config.ts          # Multi-locale, dual-mode config
├── e2e-tests/
│   ├── *.test.ts                 # Test files
│   └── utils/
│       ├── translations.ts       # i18n helper
│       ├── *Helpers.ts           # Workspace-specific helpers
│       ├── accessibility.ts      # a11y testing
│       └── localeSkip.ts         # Locale skip logic
├── app-config.yaml               # Base Backstage config
└── e2e-tests/test_yamls/         # Per-locale test configs
```

## Multi-Locale Setup

All workspaces use the same 6 locales:

```typescript
const LOCALES = ['en', 'de', 'es', 'fr', 'it', 'ja'] as const;
```

Each locale gets its own frontend and backend port:

```typescript
const FRONTEND_PORT_BASE = 3000;  // en=3000, de=3001, es=3002, ...
const BACKEND_PORT_BASE = 7007;   // en=7007, de=7008, es=7009, ...
```

**For reproduction tests**: always run against `en` only (fastest feedback):

```
APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en
```

## Dual-Mode (APP_MODE)

All workspaces support two frontend modes via the `APP_MODE` environment variable:

- `legacy` (default) — uses `packages/app-legacy` or `yarn start:legacy`
- `nfs` — uses the New Frontend System via `packages/app` or `yarn start`

The `playwright.config.ts` reads this:

```typescript
const appMode = process.env.APP_MODE || 'legacy';
const startCommand = appMode === 'legacy' ? 'yarn start:legacy' : 'yarn start';
```

**For reproduction**: run legacy first. After the fix, verify both modes.

## Translation Helpers

Most workspaces have a `getTranslations()` helper that loads the plugin's translation keys for the current locale. Use these for i18n-safe selectors:

```typescript
import { getTranslations, type InsightsMessages } from './utils/translations.js';

test.beforeAll(async ({ browser }) => {
  const translations = getTranslations(locale);
  // Use translations.header.title instead of hardcoded "Adoption Insights"
});
```

**Why**: hardcoded English strings break in non-`en` locales. Always use translation keys when available.

## Common Playwright Selectors

Prefer accessibility-first selectors:

```typescript
// Role-based (best)
page.getByRole('button', { name: 'Submit' })
page.getByRole('combobox')
page.getByRole('listbox')
page.getByRole('tab', { name: translations.tabs.overview })

// Text-based (good for translated text)
page.getByText(translations.header.dateRange.defaultLabel)

// Test ID (fallback)
page.getByTestId('date-range-select')

// CSS selector (last resort)
page.locator('.MuiSelect-root')
```

## Waiting Patterns

```typescript
// Wait for navigation to complete
await page.waitForURL('**/adoption-insights');

// Wait for network idle
await page.waitForLoadState('networkidle');

// Wait for specific element
await expect(page.getByRole('heading', { name: title })).toBeVisible();

// Custom wait for data flush
await waitForDataFlush();  // workspace-specific helper
```

## MUI Component Patterns

Many rhdh-plugins use Material-UI. Common interaction patterns:

```typescript
// MUI Select (dropdown)
const select = page.getByText(translations.header.dateRange.defaultLabel).first();
await select.click();
const listbox = page.getByRole('listbox');
await expect(listbox).toBeVisible();

// MUI Select with keyboard
await page.keyboard.press('ArrowDown');
const focused = listbox.locator(':focus');
await expect(focused).toHaveCount(1);
await page.keyboard.press('Enter');

// MUI Tab
await page.getByRole('tab', { name: 'Details' }).click();

// MUI Table
const rows = page.getByRole('row');
await expect(rows).toHaveCount(expectedCount);
```

## Repro Test Template

Use this skeleton for reproduction tests:

```typescript
import { test, expect, Page, BrowserContext } from '@playwright/test';

test.use({
  video: { mode: 'on', size: { width: 1280, height: 720 } },
});

test.describe('Repro: <JIRA-KEY> — <short description>', () => {
  let page: Page;
  let context: BrowserContext;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();
    // Navigate to the relevant page
  });

  test.afterAll(async () => {
    await context.close();
  });

  test('<expected behavior that currently fails>', async () => {
    // Steps to reproduce from Jira
    // ...
    // Assertion that should pass when the bug is fixed
  });
});
```

## Running a Single Test

```bash
# Legacy mode, en locale only (fastest for reproduction)
APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en

# NFS mode (for verification after fix)
APP_MODE=nfs npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en

# With headed browser (for debugging)
APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en --headed

# With trace (for detailed debugging)
APP_MODE=legacy npx playwright test e2e-tests/_repro-<KEY>.test.ts --project=en --trace on
```

## Common yarn Scripts

All workspaces follow the same script naming:

```bash
yarn test:e2e:legacy    # APP_MODE=legacy playwright test
yarn test:e2e:nfs       # APP_MODE=nfs playwright test
yarn test:e2e:all       # Run both modes
yarn tsc:full           # Full TypeScript type check
yarn test --watchAll=false  # Unit tests (no watch mode)
```
