# Android Architecture

| Field | Value |
|--------|-------|
| Name | Android Architecture |
| Version | 1.0.0 |
| Status | Living Document |
| Last Updated | 2026-08-08 |
| Applies To | Finance Analytics |

---

# Purpose

This document defines the Android architecture used throughout the project.

The objective is to keep the codebase simple, consistent and easy to evolve.

This project intentionally avoids unnecessary architectural complexity.

---

# Architectural Principles

- MVVM
- Feature-first structure
- Repository Pattern
- Dependency Injection with Koin
- Single source of truth
- State-driven UI
- Simplicity over abstraction

---

# High-Level Architecture

```
UI (Jetpack Compose)
        │
        ▼
ViewModel
        │
        ▼
Repository
   ┌────┴────┐
   ▼         ▼
Local     Remote
(Room)   (Retrofit)
```

---

# Feature Structure

Every feature follows the same layout.

```
feature/

presentation/
data/
model/

FeatureModule.kt
```

## presentation/

Contains:

- Screen
- ViewModel
- UiState
- Events
- Reusable UI components

## data/

Contains:

- Repository interface
- Repository implementation
- Local data source
- Remote data source (if required)

## model/

Contains domain models used by the feature.

---

# Responsibilities

## Compose UI

Responsible for:

- Rendering UI
- Collecting user input
- Displaying state

Must not:

- Access Room
- Access Retrofit
- Contain business logic

---

## ViewModel

Responsible for:

- Exposing immutable UiState
- Handling user events
- Coordinating repositories
- Launching coroutines

Must not:

- Know database details
- Know network implementation
- Contain UI code

---

## Repository

Responsible for:

- Providing data
- Hiding implementation details
- Combining local and remote sources
- Mapping data when required

Must not:

- Expose DAOs
- Expose Retrofit APIs
- Leak implementation details

---

# Data Flow

```
User Action
      │
      ▼
Compose
      │
      ▼
ViewModel
      │
      ▼
Repository
      │
      ▼
Room / Retrofit
      │
      ▼
Repository
      │
      ▼
ViewModel
      │
      ▼
UiState
      │
      ▼
Compose
```

---

# Dependency Injection

Koin is used throughout the project.

Each feature owns its own Koin module.

Modules expose only the dependencies required by that feature.

---

# State Management

Every screen exposes a single immutable UiState.

User interactions are represented as Events.

One-off actions (navigation, snackbars, etc.) should be modelled separately from persistent UI state.

---

# Coroutines

- Use structured concurrency.
- Expose Flow from repositories where appropriate.
- Use suspend functions for one-shot operations.
- Never block the main thread.

---

# Error Handling

Errors should be represented explicitly.

Repositories return domain-friendly results.

ViewModels convert those results into UI state.

---

# Testing Strategy

Test independently:

- Repository
- ViewModel
- Business logic

UI tests are added only where they provide meaningful value.

---

# Out of Scope

This document does not define:

- Backend architecture
- Database schema
- Analytics algorithms
- Product requirements

---

# Key Decisions

- MVVM instead of Clean Architecture.
- Koin instead of Hilt.
- Feature-first organization.
- Repository Pattern.
- Keep abstractions minimal until complexity requires them.

---

# Related Documents

- 00_ENGINEERING_STACK.md
- 01_ANDROID_BLUEPRINT.md
- 03_ANDROID_FEATURE_TEMPLATE.md (not yet created — planned for a future PR)
- 04_FEATURE_REVIEW_CHECKLIST.md (not yet created — planned for a future PR)
- 06_AI_CONTEXT.md

---

# Changelog

## 1.0.0

Initial version.
