# Android Blueprint

> Version: 1.0.0
> Status: Living Document
> Last Updated: 2026-08-08

## Purpose

Defines how Android features are implemented across all projects.

## Design Philosophy

- MVVM
- Feature-first
- Repository Pattern
- Pragmatic Architecture
- Offline-first when appropriate

## Module Structure

```text
app/

core/
    common/
    designsystem/
    database/
    network/
    navigation/
    analytics/
    testing/

features/
    dashboard/
    transactions/
    reports/
    settings/
```

## Feature Structure

```text
transactions/

data/
presentation/
model/
TransactionsModule.kt
```

### presentation

```text
TransactionsScreen.kt
TransactionsViewModel.kt
TransactionsUiState.kt
TransactionsEvent.kt
components/
```

### data

```text
TransactionsRepository.kt
TransactionsRepositoryImpl.kt
TransactionDao.kt
TransactionApi.kt
```

## Architectural Rules

- No UseCases unless there is meaningful business logic.
- Repositories are the only access point to data.
- ViewModels never access Room or Retrofit directly.
- Avoid unnecessary model duplication.
- Every abstraction must have a purpose.

## Dependency Injection

Standard: Koin

## State Management

Each screen owns:
- UiState
- Event

Introduce Effects only when one-off events become necessary.

## Feature Checklist

- Create package structure
- Define UiState
- Define Events
- Create Repository
- Register Koin module
- Write tests
