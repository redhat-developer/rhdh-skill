# OCP Coverage Analysis

Cross-reference RHDH cluster pools, CI test configs, RHDH lifecycle, and OCP lifecycle data to identify coverage gaps and stale configurations.

## Run

```bash
uv run scripts/analyze_coverage.py
uv run scripts/analyze_coverage.py --repo-dir /path/to/openshift/release
```

## Two Dimensions of Support

| Dimension | Source | Meaning |
|-----------|--------|---------|
| **OCP supported** | OCP lifecycle API | The OCP version itself is still receiving updates |
| **RHDH supported** | RHDH lifecycle API | RHDH officially supports running on this OCP version |

Both must be satisfied for a cluster pool and test entry to exist.

## Output

1. **Current State** -- pools, test entries, lifecycle data
2. **OCP Version Matrix** -- combined view with OCP_SUPP, RHDH_SUPP, phase
3. **Analysis Results** -- categorized actions:
   - **REMOVE** -- OCP version is end-of-life
   - **REVIEW** -- needs judgment (compatibility mismatch)
   - **ADD** -- missing pool or test entry
4. **Summary** -- counts per action category

## Workflow After Analysis

1. Handle REMOVE items first -- delete pools/tests for OCP-EOL versions
2. Review REVIEW items -- decide based on context
3. Handle ADD items -- use `workflows/ocp-pools.md` and `workflows/ocp-jobs.md`
4. Run `make update` after all changes
5. Commit both config and generated files together
