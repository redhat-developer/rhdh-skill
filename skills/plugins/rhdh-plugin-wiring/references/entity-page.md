# Entity Page Customization Reference

Customize the Backstage catalog entity pages with dynamic plugins.

## Entity Page Structure

Entity pages in RHDH consist of:

- **Tabs**: Major sections (Overview, CI, Docs, etc.)
- **Cards**: Content within tabs
- **Context Menu**: Actions in the top-right menu
- **Context Providers**: React contexts for data sharing

## Default Entity Tabs

| Route | Title | Mount Point | Entity Kind |
|-------|-------|-------------|-------------|
| `/` | Overview | `entity.page.overview` | Any |
| `/topology` | Topology | `entity.page.topology` | Any |
| `/issues` | Issues | `entity.page.issues` | Any |
| `/pr` | Pull/Merge Requests | `entity.page.pull-requests` | Any |
| `/ci` | CI | `entity.page.ci` | Any |
| `/cd` | CD | `entity.page.cd` | Any |
| `/kubernetes` | Kubernetes | `entity.page.kubernetes` | Any |
| `/image-registry` | Image Registry | `entity.page.image-registry` | Any |
| `/monitoring` | Monitoring | `entity.page.monitoring` | Any |
| `/lighthouse` | Lighthouse | `entity.page.lighthouse` | Any |
| `/api` | Api | `entity.page.api` | Service, Component |
| `/dependencies` | Dependencies | `entity.page.dependencies` | Component |
| `/docs` | Docs | `entity.page.docs` | TechDocs available |
| `/definition` | Definition | `entity.page.definition` | API |
| `/system` | Diagram | `entity.page.diagram` | System |

## Adding Custom Tabs

### New Tab with Mount Point

```yaml
entityTabs:
  - path: /my-custom-tab
    title: My Custom Tab
    mountPoint: entity.page.my-custom-tab

mountPoints:
  - mountPoint: entity.page.my-custom-tab/cards
    importName: MyTabContent
```

### Tab Visibility

Tabs become visible when:

1. At least one plugin contributes to their mount point, OR
2. They have static content (like Overview)

### Tab Priority

Control tab ordering with priority (higher appears first):

```yaml
entityTabs:
  - path: /my-tab
    title: My Tab
    mountPoint: entity.page.my-tab
    priority: 100  # Appears before lower priority tabs
```

### Hide Default Tab

Set negative priority to hide:

```yaml
entityTabs:
  - path: /topology
    title: Topology
    mountPoint: entity.page.topology
    priority: -1  # Hidden
```

### Rename Existing Tab

```yaml
entityTabs:
  - path: /
    title: General  # Renamed from "Overview"
    mountPoint: entity.page.overview
```

## Adding Cards to Tabs

### Overview Card

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyOverviewCard
```

### Card with Layout

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyCard
    config:
      layout:
        gridColumn: '1 / -1'     # Full width
        gridRowStart: 1          # First row
        gridRowEnd: 3            # Span 2 rows
```

### Grid Layout Properties

Entity pages use CSS Grid. Available properties:

| Property | Description | Example |
|----------|-------------|---------|
| `gridColumn` | Column span | `'1 / -1'` (full), `'span 2'` |
| `gridRow` | Row span | `'1 / 3'` (rows 1-2) |
| `gridColumnStart` | Start column | `1` |
| `gridColumnEnd` | End column | `-1` (last) |
| `gridRowStart` | Start row | `1` |
| `gridRowEnd` | End row | `3` |

### Conditional Cards

Show cards only for specific entities:

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyCard
    config:
      if:
        allOf:
          - isKind: component
          - isType: service
```

## Condition Types

### isKind

Filter by entity kind:

```yaml
if:
  isKind: component

# Multiple kinds
if:
  anyOf:
    - isKind: component
    - isKind: resource
```

Valid kinds: `component`, `api`, `group`, `user`, `resource`, `system`, `domain`, `location`, `template`

### isType

Filter by entity spec.type:

```yaml
if:
  isType: service

# Multiple types
if:
  anyOf:
    - isType: service
    - isType: website
```

### hasAnnotation

Filter by annotation presence:

```yaml
if:
  hasAnnotation: github.com/project-slug

# Multiple annotations
if:
  allOf:
    - hasAnnotation: backstage.io/techdocs-ref
    - hasAnnotation: github.com/project-slug
```

### Custom Conditions

Import condition function from plugin:

```yaml
mountPoints:
  - mountPoint: entity.page.overview/cards
    importName: MyCard
    config:
      if:
        allOf:
          - isMyPluginEnabled  # Function from plugin
```

Plugin must export the function:

```typescript
// src/conditions.ts
import { Entity } from '@backstage/catalog-model';

export const isMyPluginEnabled = (entity: Entity): boolean => {
  return entity.metadata.annotations?.['my-plugin/enabled'] === 'true';
};

// src/index.ts
export { isMyPluginEnabled } from './conditions';
```

## Condition Operators

### allOf (AND)

All conditions must be true:

```yaml
if:
  allOf:
    - isKind: component
    - isType: service
    - hasAnnotation: my-plugin/enabled
```

### anyOf (OR)

At least one condition must be true:

```yaml
if:
  anyOf:
    - isKind: component
    - isKind: api
```

### oneOf (XOR)

Exactly one condition must be true:

```yaml
if:
  oneOf:
    - isType: service
    - isType: website
```

### Nested Conditions

```yaml
if:
  allOf:
    - isKind: component
    - anyOf:
        - isType: service
        - isType: website
```

## Context Providers

Add React context providers to entity pages:

```yaml
mountPoints:
  - mountPoint: entity.page.overview/context
    importName: MyContextProvider
```

Context providers wrap the tab content, enabling data sharing.

## Context Menu

Add items to the entity context menu (top-right):

```yaml
mountPoints:
  - mountPoint: entity.context.menu
    importName: MyContextDialog
    config:
      props:
        title: My Action
        icon: settings
```

### Dialog Component Requirements

```typescript
export interface MyDialogProps {
  open: boolean;
  onClose: () => void;
}

export const MyContextDialog = ({ open, onClose }: MyDialogProps) => (
  <Dialog open={open} onClose={onClose}>
    {/* Dialog content */}
  </Dialog>
);
```

## Card Component Patterns

### Basic Info Card

```typescript
import { InfoCard } from '@backstage/core-components';
import { useEntity } from '@backstage/plugin-catalog-react';

export const MyEntityCard = () => {
  const { entity } = useEntity();

  return (
    <InfoCard title="My Plugin">
      <p>Entity: {entity.metadata.name}</p>
    </InfoCard>
  );
};
```

### Card with Loading State

```typescript
import { InfoCard, Progress } from '@backstage/core-components';
import { useAsync } from 'react-use';

export const MyAsyncCard = () => {
  const { entity } = useEntity();
  const { loading, error, value } = useAsync(() => fetchData(entity));

  if (loading) return <Progress />;
  if (error) return <Alert severity="error">{error.message}</Alert>;

  return (
    <InfoCard title="Data">
      <pre>{JSON.stringify(value, null, 2)}</pre>
    </InfoCard>
  );
};
```

### Card with Actions

```typescript
import { InfoCard } from '@backstage/core-components';
import { IconButton } from '@material-ui/core';
import RefreshIcon from '@material-ui/icons/Refresh';

export const MyCardWithActions = () => {
  const handleRefresh = () => { /* ... */ };

  return (
    <InfoCard
      title="My Card"
      action={
        <IconButton onClick={handleRefresh}>
          <RefreshIcon />
        </IconButton>
      }
    >
      {/* Content */}
    </InfoCard>
  );
};
```

## Full Tab Content

For custom tabs, create a full-page component:

```typescript
import { Content, ContentHeader, SupportButton } from '@backstage/core-components';
import { useEntity } from '@backstage/plugin-catalog-react';

export const MyTabContent = () => {
  const { entity } = useEntity();

  return (
    <Content>
      <ContentHeader title="My Custom Tab">
        <SupportButton>Help for my plugin</SupportButton>
      </ContentHeader>
      {/* Tab content */}
    </Content>
  );
};
```

## Best Practices

### 1. Use Entity Hooks

```typescript
import { useEntity } from '@backstage/plugin-catalog-react';

const { entity, loading, error } = useEntity();
```

### 2. Handle Loading States

Always handle loading and error states in cards.

### 3. Responsive Layout

Use grid properties that work on different screen sizes:

```yaml
config:
  layout:
    gridColumn: '1 / -1'  # Full width on all screens
```

### 4. Meaningful Conditions

Only show cards when they provide value:

```yaml
if:
  hasAnnotation: my-plugin/project-id
```

### 5. Consistent Styling

Use Backstage core components for consistent look:

- `InfoCard` for cards
- `Content` and `ContentHeader` for tabs
- `Progress` and `Alert` for states
