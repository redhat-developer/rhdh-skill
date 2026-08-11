# Reference: Active Verification Process (Shared)

Shared Phase 6 for all PR review workflows. This phase verifies the PR's specific changes on the cluster — not generic health checks. The goal is to exercise the exact code paths the PR modified and capture evidence that the behavioral change works as intended.

<verification_process>

## Active Verification

### 6.1 Analyze the diff

Read the diff hunks from Phase 1. For each changed file, understand:

- What the code did **before** the change
- What it does **after**
- What behavioral difference this introduces on a running cluster

Map each change to a concrete cluster-observable effect — something you can trigger and measure. If a change has no cluster-observable effect (e.g., pure refactor with identical behavior, documentation-only update, CI config change), state that explicitly and explain why.

### 6.2 Propose a verification plan

Present the plan to the user. For each test, specify:

- **What to do**: the exact cluster action
- **What to observe**: where to look (logs, resource spec, status, events, HTTP response)
- **Pass criteria**: what output means the change works
- **Fail criteria**: what output means the change is broken

**STOP. Do not run any verification commands. Present the plan and wait for the user to accept it before proceeding to 6.3.**

### 6.3 Execute the plan

Only after the user accepts the plan:

Run each verification step on the cluster. For every step, capture the actual command output as evidence. Do not summarize — show the raw output so the user can see exactly what happened.

</verification_process>
