# glab reads

Read patterns for GitLab merge requests, pipelines, and repository content, plus
the places where a caller who learned GitHub first gets a wrong answer.
Everything here is read-only. The commands in the last section are payloads that
this skill builds and hands back; see the mutation boundary in `SKILL.md`.

## Point glab at the right host

RHDH's GitLab work lives on `gitlab.cee.redhat.com`, not `gitlab.com`. Inside a
checkout, `glab` reads the host from the git remotes. Outside one, name it:

```bash
glab auth status
GITLAB_HOST=gitlab.cee.redhat.com glab mr list --repo rhidp/rhdh
glab mr view 17 --repo https://gitlab.cee.redhat.com/rhidp/rhdh
```

`-R, --repo` accepts `OWNER/REPO`, `GROUP/NAMESPACE/REPO`, or a full URL, so a
nested group path and an explicit host both work. Authenticating is
`glab auth login --hostname <host>`, which this skill never runs: report the
missing capability instead.

## Shape the query

Ask for `--output json` (`-F json`) and filter with `--jq`, the same discipline
as `gh`:

```bash
glab mr list --repo rhidp/rhdh --per-page 50 --output json
glab mr view 17 --repo rhidp/rhdh --output json --jq '.state'
```

Two shell and flag traps:

- In `glab api`, `-F` means `--field`, not `--output`. Spell `--output json` in
  full whenever the command might be `glab api`.
- `!` is history expansion in an interactive bash, so an MR shorthand has to be
  single-quoted: `'rhidp/rhdh!17'`. The `!=` trap described in
  `references/gh-cli.md` applies to `--jq` filters here for the same reason.

## Read a merge request

```bash
glab mr view <iid> --repo <group/project> --output json
glab mr view <iid> --repo <group/project> --comments
glab api projects/rhidp%2Frhdh/merge_requests/17
```

`:id` in a GitLab endpoint is the numeric project ID or the URL-encoded project
path, so `rhidp/rhdh` becomes `rhidp%2Frhdh`. Inside a checkout,
`projects/:fullpath/...` substitutes it. Read the API object directly when a
field name has to be exact; the CLI's JSON is a rendering of the same object,
and its coverage varies by `glab` version.

Field names come from the API, so they are snake_case and do not match GitHub's:

| Issue context field | GitLab source |
|---|---|
| `key` | `<group/project>#<iid>` for an issue, `<group/project>!<iid>` for an MR |
| `summary` | `.title` |
| `description` | `.description`, not `.body` |
| `state` | `.state`: `opened`, `closed`, `merged`, or `locked` |
| `labels` | `.labels[]`, already a list of strings |
| `number` | `.iid`, the per-project number — `.id` is a global ID and is not the number in the URL |
| `comments` | `glab api projects/:fullpath/issues/<iid>/notes`, or `--comments` on `view` |
| `source` | `gitlab` |

GitHub returns `OPEN` and `CLOSED`; GitLab returns lowercase, and adds `merged`,
which GitHub reports as a closed PR with `merged: true`. Normalize before
comparing, and never compare the raw strings across forges.

An MR carries `sha` (the head commit), `detailed_merge_status`, `draft`,
`source_branch`, `target_branch`, and `head_pipeline`.

## Pipelines, not checks

GitLab has no `statusCheckRollup`. The verdict on a merge request is a pipeline,
and a pipeline belongs to a commit:

```bash
glab ci status --repo <group/project> --branch <source-branch> --output json
glab ci list --repo <group/project> --sha <head-sha> --output json
glab api projects/rhidp%2Frhdh/merge_requests/17 --output json
```

On `glab ci status`, `--output json` is incompatible with `--live`, `--wait`,
and `--compact`.

Two reasons a green pipeline is not a green merge request:

- The pipeline ran on an earlier commit. Take `sha` from the MR and confirm the
  pipeline reports the same one.
- The project runs merged results pipelines, which test a temporary commit
  combining source and target that exists on neither branch. Its SHA is not the
  source branch head, so a `--branch` lookup can miss it entirely.
  `head_pipeline` on the MR object is the authoritative link in that case.

## Read a file

```bash
glab api "projects/rhidp%2Frhdh/repository/files/docs%2FREADME.md/raw?ref=<sha-or-branch>"
```

The file path is URL-encoded too, so `docs/README.md` becomes `docs%2FREADME.md`
and slashes inside it must be escaped. Unlike the GitHub contents API, `/raw`
returns the file as it is, with no base64 step.

## Payloads, not executions

This skill constructs these and hands them back. The calling skill states the
command, gets approval, runs it, and reports the outcome, under the rule
`/mutation-gate` owns.

```bash
glab mr note <iid> --repo <group/project> --message "<exact body>"
glab issue note <iid> --repo <group/project> --message "<exact body>"
glab mr update <iid> --repo <group/project> --label "<label>"
glab mr update <iid> --repo <group/project> --unlabel "<label>"
glab issue update <iid> --repo <group/project> --label "<label>"
glab mr approve <iid> --repo <group/project> --sha <head-sha>
```

Pass `--sha` on an approval: it must match the MR head commit, so the approval
cannot land on a commit nobody read. Recent `glab` also spells a comment as
`glab mr note create <iid> -m "<body>"`; check `glab mr note --help` if the flat
form is rejected.

Read the approval state before proposing an approval:

```bash
glab mr approvers <iid> --repo <group/project> --output json
glab api projects/rhidp%2Frhdh/merge_requests/17/approvals
```

The approvals endpoint returns `approved`, `approvals_required`,
`approvals_left`, and `approved_by`.

## Errors

| Scenario | Action |
|---|---|
| `glab` not installed | Report the missing capability. It is optional, and only GitLab work needs it |
| `glab auth status` fails for the host | Report that `glab auth login --hostname <host>` is required, and stop |
| 404 on a project path | The path is case-sensitive and includes every parent group; confirm the full namespace before retrying |
| A number with no sigil | Ask whether it is an issue or an MR. The two counters are independent within a project |
| An MR reference vanished from the command line | `!` expanded in bash; quote it |
