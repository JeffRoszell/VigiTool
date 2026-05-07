# Versioning

This project uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`) adapted for
research-software lifecycle, plus an explicit link to the PI protocol
revision the code targets.

## Bump rules

| Bump  | When                                                                                                                                                  |
|-------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| MAJOR | Any change that requires an IRB amendment, switches the experimental paradigm, or breaks the saved JSON schema **after** v1.0.0.                       |
| MINOR | Protocol-revision-aligned features (e.g. PI protocol U2 → U3), new tasks, new integrations (EEG, eye-tracking). Pre-1.0, schema breaks live here too. |
| PATCH | Bug fixes, internal refactors, docs, test-only changes — no participant-facing or data-format change.                                                  |

## Pre-1.0 vs post-1.0

- **Pre-1.0** (current state): the schema is still in flux. Breaking schema
  changes are allowed in MINOR bumps. This phase ends when the PI signs off
  on data collection beginning.
- **Post-1.0**: the schema is locked. Any breaking change is a MAJOR bump,
  and old data must remain readable by the analysis pipeline (or a
  migration script must be supplied).

## Protocol revision tag

The PI tracks design iterations as `U1`, `U2`, `U3`, … (e.g.
`Background/Cognitive Vigilance Task_U3.docx`). Every CHANGELOG entry
records the protocol revision the code targets so reviewers can match
code state to design doc state.

Example: `[0.2.0] – 2026-05-06 — Protocol: U3`

## Where the version is recorded

- `pyproject.toml` — `project.version` (authoritative).
- `CHANGELOG.md` — human-readable history with protocol-revision tag.
- Git tags — `vX.Y.Z` annotated tag on the merge commit, created after the
  PR lands on `main`.

## Tagging workflow

After a release PR merges:

```bash
git checkout main
git pull
git tag -a v0.2.0 -m "v0.2.0 — Protocol U3"
git push origin v0.2.0
```

Use annotated tags (`-a`), not lightweight tags, so reviewers see the
release message in `git log`.

## When to bump

Bumping happens **in the PR that delivers the change** (not in a separate
"release" PR). The PR updates `pyproject.toml` and adds a CHANGELOG entry
under `[Unreleased]` → renames it to the new version with the date when
ready to merge. This keeps the version, the changes, and the merge commit
in lockstep.
