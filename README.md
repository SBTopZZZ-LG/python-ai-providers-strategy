# Python AI Providers Strategy Template

I built this template because I usually work on AI-enabled projects that need to switch between multiple providers, and I wanted a reusable foundation that avoids rebuilding the same provider wiring and lifecycle code in every new repository.

## Introduction

This project is an async-first Python template that applies a provider strategy + factory pattern to AI integrations.

Design goals:

- Decouple application code from provider-specific SDK logic.
- Standardize provider lifecycle operations (`initialize`, `send`, `dispose`).
- Centralize construction and resource management in one place.
- Make it straightforward to add new AI providers with minimal changes.

## Requirements

- Python 3.10+
- Dependencies from `requirements.txt`

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Run demo:

```bash
python3 main.py
```

## Project Structure

```text
.
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── requirements.txt
├── main.py
└── ai_providers/
    ├── __init__.py
    ├── base.py
    ├── copilot.py
    └── factory.py
```

Module responsibilities:

- `main.py`: Example entry point showing how to consume a managed provider.
- `ai_providers/base.py`: Generic provider contract and base options class.
- `ai_providers/copilot.py`: Concrete provider implementation for Copilot SDK.
- `ai_providers/factory.py`: Provider creation/disposal + managed context API.
- `ai_providers/__init__.py`: Public exports for package consumers.

## Provider + Factory Strategy

### Base Provider Contract

`BaseAIProvider` defines the lifecycle contract for all providers:

- `initialize_session()`
- `send_message_and_await_response(message: str) -> str`
- `dispose_session()`

Every provider must implement these async methods.

### Provider Options

Each concrete provider has a typed options dataclass inheriting from `BaseAIProviderOptions`.

Example (`CopilotProviderOptions`):

- `client`
- `model`
- `timeout`

### Factory Responsibilities

`create_ai_provider(config)`:

- Accepts generic `AIProviderConfig`.
- Selects concrete provider by `ProviderType`.
- Starts provider dependencies (for Copilot: `CopilotClient.start()`).
- Returns a configured provider instance.

`dispose_ai_provider(provider)`:

- Disposes provider session and associated client resources.
- Raises typed errors on unsupported providers or cleanup failures.

`managed_ai_provider(config)`:

- Async context manager that creates provider on enter and disposes on exit.
- Recommended API for most application code.

## AsyncExitStack Lifecycle Design

The template uses `contextlib.AsyncExitStack` in the factory to ensure deterministic cleanup.

### Why AsyncExitStack

- Handles multiple async cleanup callbacks safely.
- Executes teardown in reverse order (LIFO), matching dependency chains.
- Reduces manual nested `try/except/finally` complexity.

### How It Is Used Here

In create path:

1. Start client.
2. Register rollback callback (`client.stop`) in the stack.
3. Build provider.
4. Call `stack.pop_all()` on success so rollback does not run.

In dispose path:

1. Register `client.stop` callback (if available).
2. Register `provider.dispose_session` callback.
3. Let stack exit run callbacks in reverse order.

Because of LIFO, session disposal runs before client stop.

## Usage

### Recommended Usage (`managed_ai_provider`)

```python
import asyncio
from ai_providers import AIProviderConfig, ProviderType, managed_ai_provider


async def run() -> None:
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4o",
        timeout=120,
    )

    async with managed_ai_provider(config) as provider:
        await provider.initialize_session()
        response = await provider.send_message_and_await_response("Hello")
        print(response)


if __name__ == "__main__":
    asyncio.run(run())
```

## Adding a New Provider

### 1. Create a provider module

Add a new file under `ai_providers/` (for example `openai_provider.py`) with:

- An options dataclass inheriting `BaseAIProviderOptions`.
- A provider class inheriting `BaseAIProvider[YourOptions]`.
- Implementations for all lifecycle methods.

### 2. Add enum value

Update `ProviderType` in `ai_providers/factory.py`.

### 3. Extend factory create/dispose

In `create_ai_provider(config)`:

- Add a branch for the new provider.
- Start SDK/client resources.
- Register rollback callbacks with `AsyncExitStack`.
- Construct provider and return after `stack.pop_all()`.

In `dispose_ai_provider(provider)`:

- Add type-specific cleanup registration.
- Keep cleanup operations stack-managed and async-safe.

### 4. Export the new provider

Update `ai_providers/__init__.py` exports.

### 5. Add dependency

Update `requirements.txt` if the provider requires an SDK.

## Error Handling Notes

- Invalid or unsupported providers raise `ValueError`.
- Startup/initialization/cleanup runtime failures raise `RuntimeError`.
- Concrete providers should validate required options early.

## Extension Guidelines

- Keep provider-specific SDK code inside provider modules, not app code.
- Keep `main.py` orchestration-oriented and provider-agnostic.
- Prefer `managed_ai_provider` in app code for automatic lifecycle handling.
- Keep options strongly typed to simplify validation and refactoring.

## Current Dependency

| Provider | Package | Version Constraint | Notes |
| --- | --- | --- | --- |
| Copilot | github-copilot-sdk | >=0.1.25,<0.2.0 | Active provider in this template |

Planned providers can be added as new rows as they are implemented.

## TODO

- [x] Use AsyncExitStack to manage resource life-cycle and maintain clean code
- [ ] Unit/Integration tests for ai_providers package, and all providers
- [ ] Add Claude AI provider
- [ ] Add OpenAI provider

## License

See `LICENSE`.
