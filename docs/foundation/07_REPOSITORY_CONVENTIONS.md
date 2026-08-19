# Repository Conventions

| Field | Value |
|--------|-------|
| Name | Repository Conventions |
| Version | 1.0.0 |
| Status | Living Document |
| Last Updated | 2026-08-08 |

---

# Purpose

Define the repository conventions used across the project.

---

# Branch Naming

Use:

- chore/<name>
- feature/<name>
- fix/<name>
- docs/<name>
- refactor/<name>

Examples:

- chore/repository-bootstrap
- feature/csv-import
- feature/dashboard
- refactor/import-module

---

# Commit Convention

Use Conventional Commits. A pull request may contain multiple commits when separating meaningful implementation steps improves readability, reviewability, or traceability. Commits should represent coherent changes rather than arbitrary file groupings.

Examples:

- chore(repo): bootstrap repository
- build(android): configure compose
- feat(import): add csv parser
- fix(import): handle invalid files
- docs(project): update roadmap
- refactor(core): simplify repository

---

# Pull Requests

Every PR must:

- Implement one objective only.
- Stay within scope.
- Include tests where applicable.
- Update documentation if required.
- Stop after opening the PR.

---

# Code Reviews

Before opening a PR:

- Run tests.
- Check formatting.
- Review against 04_FEATURE_REVIEW_CHECKLIST.md (not yet created — planned for a future PR; skip this step until it exists).

---

# Documentation

Update documentation only if:

- Architecture changes.
- Folder structure changes.
- Public APIs change.
- Engineering decisions change.

---

# Definition of Done

A task is complete when:

- Code builds.
- Tests pass.
- Documentation is updated (if needed).
- PR is ready for review.

---

# Related Documents

- 04_FEATURE_REVIEW_CHECKLIST.md
- 06_AI_CONTEXT.md
