# Ecosystem & Official Backstage Skills

Complementary skills from the open-source ecosystem and official Backstage.io.
Install into `.fullsend/customized/skills/` or your local skills directory.

> URLs and repos may change over time. Verify before installing.

## Frontend Quality (skills.sh)

**Essential:**

| Skill | Source | What it adds |
|-------|--------|-------------|
| `ui-ux-pro-max` | nextlevelbuilder/ui-ux-pro-max-skill | 99 UX rules — accessibility, touch targets, animation, forms, navigation |
| `frontend-design` | anthropics/skills | Design thinking, anti-AI-aesthetic, microcopy quality |
| `webapp-testing` | anthropics/skills | Playwright-based browser testing, server lifecycle |

**Recommended:**

| Skill | Source | What it adds |
|-------|--------|-------------|
| `design-taste-frontend` | leonxlnx/taste-skill | Anti-slop discipline, design inference |
| `emil-design-eng` | emilkowalski/skills | Animation decisions, CSS polish |

```bash
npx skills add https://github.com/nextlevelbuilder/ui-ux-pro-max-skill --skill ui-ux-pro-max
npx skills add https://github.com/anthropics/skills --skill frontend-design
npx skills add https://github.com/anthropics/skills --skill webapp-testing
npx skills add https://github.com/leonxlnx/taste-skill --skill taste-skill
npx skills add https://github.com/emilkowalski/skills --skill emil-design-eng
```

## Official Backstage Skills (backstage.io)

Migration and instrumentation workflows maintained by the Backstage team.

```bash
npx skills add https://backstage.io
```

| Skill | Use when... |
|-------|------------|
| `mui-to-bui-migration` | Migrating a plugin from MUI to BUI (component-by-component guide) |
| `plugin-new-frontend-system-support` | Adding NFS support while keeping legacy working (dual entry point) |
| `plugin-full-frontend-system-migration` | Fully migrating a plugin to NFS, dropping legacy |
| `app-frontend-system-migration` | Migrating an entire Backstage app to the new frontend system |
| `plugin-analytics-instrumentation` | Adding analytics events via Backstage Analytics API |
| `onboard-to-openapi-server` | Migrating backend router to typed OpenAPI tooling |
