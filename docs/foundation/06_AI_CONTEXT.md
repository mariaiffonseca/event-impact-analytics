# AI Context

> Version: 1.0.0
> Status: Living Document
> Last Updated: 2026-08-08

## Purpose

This document is provided to an AI assistant at the beginning of a new conversation.
It contains the permanent engineering context for the project.

## Project Mission

Build high-quality software using pragmatic engineering practices.

## Engineering Philosophy

- MVVM
- Feature-first architecture
- Repository Pattern
- Pragmatic architecture
- Simplicity over cleverness
- Architecture emerges from complexity

## Technology Stack

### Android
- Kotlin
- Jetpack Compose
- Koin
- Room
- Retrofit
- Coroutines + Flow
- DataStore

### Backend
- Python
- FastAPI
- SQLAlchemy
- Pydantic
- uv

### Analytics
- Pandas
- DuckDB
- Scikit-learn
- Plotly
- Jupyter

## Rules

- ViewModels never access Room or Retrofit directly.
- Repositories hide implementation details.
- Avoid unnecessary abstractions.
- Do not introduce UseCases without meaningful business logic.
- Prefer immutable state.
- Keep code simple and readable.

## Expected Behaviour

- Explain trade-offs.
- Respect the existing architecture.
- Prefer incremental improvements.
- Ask for clarification if requirements are ambiguous.

## Forbidden Behaviour

- Do not rewrite unrelated code.
- Do not introduce libraries without justification.
- Do not overengineer.
- Do not change public APIs unnecessarily.

## Testing

Whenever new behaviour is introduced:
- Suggest unit tests.
- Mention edge cases.

## Context Priority

1. 00_ENGINEERING_STACK.md
2. 01_ANDROID_BLUEPRINT.md
3. 02_ANDROID_ARCHITECTURE.md
4. 03_ANDROID_FEATURE_TEMPLATE.md (not yet created — planned for a future PR)
5. 04_FEATURE_REVIEW_CHECKLIST.md (not yet created — planned for a future PR)
6. Current feature requirements

## Definition of Done

- Follows architecture
- Testable
- Readable
- Maintainable
- Consistent

## Changelog

### 1.0.0
Initial version.
