# Frontend Spec Guidance

When writing specs, PRDs, or OpenSpec proposals/designs for frontend features,
include these sections. Works with spec-start, OpenSpec, or any spec workflow.
Scale to complexity.

## Components

List every component the feature introduces or modifies. State what it is,
what it does, and its key interactions.

```markdown
### FilterPanel
Sidebar with search input and category checkboxes. Filters the main data table.
- Search: debounced text input, filters by name
- Categories: checkbox group, multiple selection, filters immediately on change
- Reset: button that clears all filters

### DataTable
Sortable, paginated table showing filtered results.
- Columns: name, status, last updated, actions
- Sort: click column header toggles asc/desc
- Pagination: 25 rows per page
- Row click navigates to detail page
- Empty state when no results match filters
```

Describe what the user sees and does, not implementation details.

## Design Reference

Point to where the design lives.

```markdown
Figma: https://figma.com/file/abc123/feature-name
Frames: "Dashboard — Desktop", "Dashboard — Mobile"
```

With Figma MCP configured (`claude plugin install figma@claude-plugins-official`),
the agent reads the design directly — component structure, layout constraints,
spacing tokens, typography. No manual token tables or mockup exports needed.

When no Figma exists:
- Reference existing UI: "Follow the layout of the existing Topology page"
- Compose from design system: "BUI Card grid, 3 columns on desktop, 1 on mobile"
- Attach mockups in the spec directory

## Acceptance Criteria

Concrete, testable statements per component. The definition of "done."

```markdown
### FilterPanel
- Typing in search filters the table within 300ms (debounced)
- Selecting a category checkbox immediately filters visible rows
- Clicking Reset clears search input and unchecks all checkboxes
- Filter state persists in URL query params (shareable, survives refresh)

### DataTable
- Clicking a column header sorts the table; clicking again reverses sort
- When filters return zero results: "No results match your filters" with Reset action
- Loading state shows skeleton rows while data loads
- Error state shows error message with Retry button
```

Specific and testable — not "should be responsive" or "handles errors gracefully."

## Accessibility

Only when the component has custom interaction patterns beyond standard HTML.

```markdown
- Tab order: search → checkboxes → reset → table headers → table rows
- Filter changes announced: "Showing 12 of 45 results" via live region
- Sort state announced: "Sorted by name, ascending" on column activation
```

Skip for components that are pure composition of standard elements.

## Scaling

| Complexity | Components | Design | Acceptance | Accessibility |
|-----------|------------|--------|------------|---------------|
| Simple | 1-2 lines | Skip | 2-3 criteria | Skip |
| Medium | Full list | Figma link or reference | Full criteria | If custom interaction |
| Large | Full list | Figma + frames | Full criteria | Full section |
