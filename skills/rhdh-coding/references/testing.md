# Backstage Testing Patterns

## TestApiProvider + renderInTestApp

The dominant pattern. `renderInTestApp` provides routing/theme; `TestApiProvider` supplies mock APIs.

```tsx
// badges plugin (community-plugins) — EntityBadgesDialog.test.tsx
import { renderInTestApp, TestApiProvider } from '@backstage/test-utils';

const mockApi: jest.Mocked<BadgesApi> = {
  getEntityBadgeSpecs: jest.fn().mockResolvedValue([
    { id: 'testbadge', badge: { label: 'test', message: 'badge' } },
  ]),
};
const rendered = await renderInTestApp(
  <TestApiProvider apis={[[badgesApiRef, mockApi], [errorApiRef, {} as ErrorApi]]}>
    <EntityProvider entity={mockEntity}>
      <EntityBadgesDialog open />
    </EntityProvider>
  </TestApiProvider>,
);
await expect(rendered.findByText('test: badge')).resolves.toBeInTheDocument();
```

## mountedRoutes for Routable Extensions

When a component uses `useRouteRef`, pass `mountedRoutes` as second arg to `renderInTestApp`:

```tsx
// x2a plugin (rhdh-plugins) — Dashboard.test.tsx
await renderInTestApp(<TestApiProvider apis={[...]}><Dashboard /></TestApiProvider>,
  { mountedRoutes: { '/x2a': rootRouteRef } });
```

## Mocking API Clients (mock the interface, not HTTP)

```tsx
// x2a plugin — Dashboard.test.tsx
import { mockApis } from '@backstage/test-utils';
const discoveryApiMock = mockApis.discovery({ baseUrl: 'http://localhost:1234' });
const permissionApiMock = {
  authorize: jest.fn().mockResolvedValue({ result: AuthorizeResult.ALLOW }),
};
```

## Entity Context Mocking

**EntityProvider wrapper** (badges plugin): `<EntityProvider entity={mockEntity}><MyComponent /></EntityProvider>`

**jest.mock useEntity** (acs plugin, community-plugins):

```tsx
jest.mock('@backstage/plugin-catalog-react', () => ({
  ...jest.requireActual('@backstage/plugin-catalog-react'),
  useEntity: jest.fn().mockReturnValue({
    metadata: { annotations: { 'acs/deployment-name': 'test-deployment' } },
  }),
}));
```

Always spread `jest.requireActual()` to preserve other exports.

## Testing Async Components

Use `waitFor` or `findByText`/`findByRole` for data-loading components:

```tsx
await waitFor(() => expect(screen.getByText('Loading...')).toBeInTheDocument()); // acs plugin
await expect(rendered.findByText('test: badge')).resolves.toBeInTheDocument(); // badges plugin
```

## Testing Custom Hooks

**Simple hooks** (mock `useApi` directly):

```tsx
// adoption-insights plugin — useActiveUsers.test.tsx
import { renderHook, waitFor } from '@testing-library/react';

const mockApi = { getActiveUsers: jest.fn() };
(useApi as jest.Mock).mockReturnValue(mockApi);
mockApi.getActiveUsers.mockResolvedValueOnce({ data: [] });

const { result } = renderHook(() => useActiveUsers());
expect(result.current.loading).toBe(true);
await waitFor(() => {
  expect(result.current.loading).toBe(false);
});
```

**Hooks that need TestApiProvider** (when the hook calls `useApi` internally):

```tsx
// boost plugin — useAiAssets.test.ts
import { type ReactNode, createElement } from 'react';
import { TestApiProvider } from '@backstage/test-utils';
import { renderHook, waitFor } from '@testing-library/react';
import { catalogApiRef } from '@backstage/plugin-catalog-react';

const mockCatalogApi = { getEntities: jest.fn() };

function wrapper({ children }: { children: ReactNode }) {
  return createElement(TestApiProvider, {
    apis: [[catalogApiRef, mockCatalogApi]],
    children,
  } as any);
}

const { result } = renderHook(() => useAiAssets(), { wrapper });
await waitFor(() => expect(result.current.loading).toBe(false));
```

Note: use `createElement` instead of JSX in `.test.ts` files (non-TSX). The
`as any` cast on the props object works around a TypeScript overload resolution
issue with `TestApiProvider` + `createElement`.

## MSW for HTTP Tests (real API client classes)

```tsx
// x2a plugin — Dashboard.test.tsx
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import { registerMswTestHooks } from '@backstage/test-utils';

const server = setupServer();
registerMswTestHooks(server); // handles listen/close/reset
beforeEach(() => {
  server.use(rest.get('/*', (_, res, ctx) => res(ctx.status(200), ctx.json({}))));
});
```

## Permission Testing (SWR cache reset)

```tsx
// playlist plugin (community-plugins)
<SWRConfig value={{ provider: () => new Map() }}>
  <TestApiProvider apis={[[permissionApiRef, permissionApi]]}>
    <PlaylistPage />
  </TestApiProvider>
</SWRConfig>
```

## Common Gotchas

- **renderInTestApp is async** -- always `await` it. Forgetting causes flaky tests.
- **No default React imports** -- use `import { createElement, type ReactNode } from 'react'`, not `import React from 'react'`. The eslint `no-restricted-syntax` rule blocks default React imports per the JSX transform migration.
- **No snapshots with MUI** -- non-deterministic class names. Unused except for SVG icons.
- **jest.mock hoisting** -- use `jest.requireActual()` inside mock factories for partial mocks.
- **Translation mocking** -- rhdh-plugins use `test-utils/mockTranslations.ts`. Mock `useTranslation`.
- **Accessibility testing** -- neither repo currently uses jest-axe or axe-core in unit tests. The official `plugin-analytics-instrumentation` skill notes that BUI components have built-in a11y. For a11y enforcement, consider e2e axe-core via Playwright (the rhdh-plugins homepage workspace has an example in `e2e-tests/utils/accessibility.ts`).
