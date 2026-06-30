# Backstage UI (BUI) Reference

> Last verified: July 2026 against `@backstage/ui` in Backstage 1.45.x / RHDH 1.9.
> Always check `node_modules/@backstage/ui/dist/index.d.ts` for actual prop types.

Setup: `yarn add @backstage/ui @remixicon/react` and add `import '@backstage/ui/css/styles.css'` to `src/index.ts`.

BUI uses **CSS Modules** with CSS custom properties — not makeStyles or CSS-in-JS.

```css
/* MyComponent.module.css */
@layer components {
  .container {
    padding: var(--bui-space-4);
    background-color: var(--bui-bg-surface-1);
    border-radius: var(--bui-radius-2);
  }
}
```

```tsx
import { Box, Text } from '@backstage/ui';
import styles from './MyComponent.module.css';

export const MyComponent = () => (
  <Box className={styles.container}>
    <Text variant="title-small">Title</Text>
  </Box>
);
```

## Component Mapping

| BUI | Replaces MUI | Key differences |
|-----|-------------|-----------------|
| `Text` | `Typography` | `variant`: title-large/medium/small/x-small, body-large/medium/small/x-small. `weight`, `truncate` props. |
| `Button` | `Button` | `variant="primary"/"secondary"/"tertiary"`, `isDisabled`, `destructive`, `loading` |
| `ButtonIcon` | `IconButton` | `icon={<RiIcon />}`, `onPress` (not `onClick`), needs `aria-label` |
| `Card` + `CardHeader/Body/Footer` | `Paper`, `Card` | Discriminated union: `CardLinkVariant` (href + label), `CardButtonVariant` (onPress + label), or `CardStaticVariant`. No `onClick`. |
| `Flex` | `Box display="flex"` | `direction`, `align`, `justify="between"` (not `"space-between"`). Has `p`, `m`, `gap`, `grow` utility props. |
| `Grid.Root` + `Grid.Item` | `Grid container/item` | `columns={{ sm: '12' }}`, `colSpan={{ sm: '12', md: '6' }}` |
| `TextField` | `TextField` | `isRequired`, `onChange` receives string directly (not event!) |
| `PasswordField` | — | Password input with show/hide toggle |
| `Dialog` + `DialogTrigger` | `Dialog` | Trigger pattern |
| `Tabs` + `TabList/Tab/TabPanel` | `Tabs/TabList/TabPanel` | `defaultSelectedKey`, id-based |
| `Menu` + `MenuTrigger/MenuItem` | `Menu/Popover` | Trigger pattern. Also: `MenuSection`, `MenuSeparator`, `SubmenuTrigger` |
| `Tooltip` + `TooltipTrigger` | `Tooltip` | Both imported from `@backstage/ui` |
| `Tag` | `Chip` | Direct replacement |
| `TagGroup` | — | Grouped tags |
| `Select` | `Select` | Multi: `selectionMode="multiple"`, `value: Key[]`, `onChange: (value: Key[]) => void`. Single: `value: Key \| null`, `onChange: (value: Key \| Key[] \| null) => void`. Uses `options` array of `{id, label}`. |
| `Switch` | `Switch` | Toggle |
| `Checkbox` | `Checkbox` | Checkbox input |
| `CheckboxGroup` | — | Grouped checkboxes with shared label, `orientation`, `isRequired` |
| `RadioGroup` + `Radio` | `RadioGroup` | BUI pattern |
| `SearchField` | `InputBase` | Search input |
| `SearchAutocomplete` | — | Search with autocomplete popover (`SearchAutocompleteItem`) |
| `Skeleton` | `Skeleton` | Loading placeholder |
| `Accordion` + `AccordionTrigger/Panel` | `Accordion` | Trigger pattern. `AccordionGroup` for multiple. |
| `Alert` | `@material-ui/lab Alert` | `status`, `title`, `description` props |
| `Badge` | — | `size` and `icon` props only — no `variant`. Inline badge/label. |
| `DateRangePicker` | — | Date range input field |
| `FieldLabel` | — | Form field label with description and secondary label |
| `Header` | — | Page header with breadcrumbs and tabs |
| `PluginHeader` | — | Plugin-level header (used by NFS PageLayout automatically) |
| `List` + `ListRow` | `List/ListItem` | BUI list pattern |
| `Slider` | — | Range slider input |
| `Table` + `useTable` | `Table` | Data tables with `useTable` hook (supports `complete`, `offset`, `cursor` pagination). Requires `isRowHeader: true` on at least one `ColumnConfig`. Cells must use `CellText` or `CellProfile` as top-level element. |
| `TablePagination` | — | Standalone pagination component |
| `FullPage` | — | Full-page layout wrapper |
| `Container` | — | Centered content container with max-width |
| `VisuallyHidden` | — | Accessibility helper |

## Icons

Use `@remixicon/react` — not `@material-ui/icons`.

```tsx
import { RiSearchLine, RiCloseLine } from '@remixicon/react';
<RiSearchLine size={16} />
```

| MUI Icon | Remix Icon |
|----------|------------|
| Close | RiCloseLine |
| Search | RiSearchLine |
| Settings | RiSettingsLine |
| Add | RiAddLine |
| Delete | RiDeleteBinLine |
| Edit | RiEditLine |
| Check | RiCheckLine |
| Error | RiErrorWarningLine |
| Warning | RiAlertLine |
| Info | RiInformationLine |
| ExpandMore | RiArrowDownSLine |
| ChevronRight | RiArrowRightSLine |
| Menu | RiMenuLine |
| MoreVert | RiMore2Line |
| Visibility | RiEyeLine |

Full catalog: https://remixicon.com/

## CSS Variables

| Category | Variables |
|----------|----------|
| Spacing | `--bui-space-1` (4px) … `--bui-space-8` (32px) |
| Foreground | `--bui-fg-primary`, `--bui-fg-secondary`, `--bui-fg-link`, `--bui-fg-danger` |
| Background | `--bui-bg-surface-0` (page), `--bui-bg-surface-1` (card), `--bui-bg-hover`, `--bui-bg-solid` |
| Border | `--bui-border`, `--bui-ring` |
| Radius | `--bui-radius-2`, `--bui-radius-3`, `--bui-radius-full` |
| Typography | `--bui-font-regular`, `--bui-font-size-1/2/3`, `--bui-font-weight-regular/bold` |

## MUI Spacing → BUI Spacing

| `theme.spacing(n)` | BUI variable |
|--------------------|-------------|
| `theme.spacing(0.5)` | `var(--bui-space-1)` |
| `theme.spacing(1)` | `var(--bui-space-2)` |
| `theme.spacing(2)` | `var(--bui-space-4)` |
| `theme.spacing(3)` | `var(--bui-space-6)` |
| `theme.spacing(4)` | `var(--bui-space-8)` |

## MUI Colors → BUI Colors

| `theme.palette.*` | BUI variable |
|-------------------|-------------|
| `text.primary` | `var(--bui-fg-primary)` |
| `text.secondary` | `var(--bui-fg-secondary)` |
| `background.paper` | `var(--bui-bg-surface-1)` |
| `background.default` | `var(--bui-bg-surface-0)` |
| `error.main` | `var(--bui-fg-danger)` |
| `divider` | `var(--bui-border)` |

## Responsive

```tsx
import { useBreakpoint } from '@backstage/ui';
const { breakpoint, up, down } = useBreakpoint();
// breakpoint: 'initial' | 'xs' | 'sm' | 'md' | 'lg' | 'xl'
// up('md') → true if viewport >= md
// down('sm') → true if viewport <= sm
```

## Important

This reference is a quick-start guide, not the source of truth. Always check
`node_modules/@backstage/ui/dist/index.d.ts` for actual prop types before using
a BUI component for the first time. Common surprises: Card variant unions,
Select onChange signatures, Table column requirements.

## Known Limitations

BUI does not yet have: Timeline, Autocomplete.
Use MUI v5 (`@mui/material`) for these — add the class name generator when mixing.

Some Backstage APIs (e.g., NavItemBlueprint `icon` prop) expect MUI `IconComponent`
type. Remix icons aren't type-compatible — use MUI icons for these specific cases.

## Further Reference

- BUI docs: https://ui.backstage.io
- Full migration guide: `mui-to-bui-migration` skill in community-plugins
