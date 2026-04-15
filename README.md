# Python AI Providers Strategy Template

I built this template because I usually work on AI-enabled projects that need to switch between multiple providers, and I wanted a reusable foundation that avoids rebuilding the same provider wiring, lifecycle code, and agent orchestration in every new repository.

## Introduction

This project is an async-first Python template that applies a provider strategy + factory pattern to AI integrations.

Design goals:

- Decouple application code from provider-specific SDK logic.
- Standardize provider lifecycle operations (`initialize`, `send`, `dispose`).
- Centralize construction and resource management in one place.
- Make it straightforward to add new AI providers with minimal changes.
- Provide a clean agent abstraction that encapsulates provider lifecycle and exposes a high-level query interface.
- Allow tool definitions to live close to the code that uses them, while sharing common tools across agents without duplication.

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
├── pyrightconfig.json
├── main.py
├── ai_providers/
│   ├── __init__.py
│   ├── base.py
│   ├── copilot.py
│   ├── factory.py
│   └── tools.py
├── agents/
│   ├── __init__.py
│   ├── base.py
│   └── helpful_assistant.py
└── tools/
    ├── __init__.py
    └── ping_pong.py
```

Module responsibilities:

- `main.py`: Example entry point showing how to construct and run an agent.
- `ai_providers/base.py`: Generic provider contract, base options, and all tool-related types (`BaseTool`, `ToolHandler`, `ToolInvocation`, `ToolResult`).
- `ai_providers/copilot.py`: Concrete provider implementation for the Copilot SDK.
- `ai_providers/factory.py`: Provider creation/disposal + managed context API.
- `ai_providers/tools.py`: `define_tool` decorator — auto-generates JSON Schema from Pydantic models and wraps plain functions as `BaseTool` instances.
- `ai_providers/__init__.py`: Public exports for package consumers.
- `agents/base.py`: `BaseAgent` — manages provider lifecycle via `AsyncExitStack` and exposes `query` / `query_json`.
- `agents/helpful_assistant.py`: Example concrete agent with its own agent-specific tool definitions.
- `tools/`: Shared tool definitions reusable across multiple agents (stateless and stateful factory patterns).

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
- `system_prompt`
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
- Used internally by `BaseAgent`; available directly for lower-level access.

### AsyncExitStack Lifecycle Design

Both the factory and `BaseAgent` use `contextlib.AsyncExitStack` for deterministic LIFO cleanup.

In the factory create path:

1. Start client.
2. Register rollback callback (`client.stop`) in the stack.
3. Build provider.
4. Call `stack.pop_all()` on success so rollback does not run.

In the factory dispose path:

1. Register `client.stop` callback (if available).
2. Register `provider.dispose_session` callback.
3. Stack unwinds in reverse order: session disposal → client stop.

## Agents

### What `BaseAgent` Does

`BaseAgent` wraps the full provider lifecycle so application code only interacts with a single `async with` context and two query methods.

On enter:

1. Opens an `AsyncExitStack`.
2. Enters `managed_ai_provider` — creates the provider and registers its cleanup.
3. Calls `provider.initialize_session()`.

On exit:

1. `AsyncExitStack` unwinds in LIFO order: session disposal → client stop.

### Query Interface

- `query(message: str) -> str` — send a message, return the raw response string.
- `query_json(message: str, max_retries: int = 3) -> dict` — send a message, parse the response as JSON. On parse failure, automatically sends the error back to the model and retries up to `max_retries` times before raising `JSONParseError`.

### Recommended Usage (`BaseAgent` subclass)

```python
import asyncio
from ai_providers import AIProviderConfig, ProviderType
from agents import HelpfulAssistantAgent


async def run() -> None:
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4o",
        timeout=120,
    )

    async with HelpfulAssistantAgent(config) as agent:
        response = await agent.query("Hello")
        print(response)


if __name__ == "__main__":
    asyncio.run(run())
```

### Direct Provider Usage (`managed_ai_provider`)

If you need lower-level access without an agent wrapper:

```python
import asyncio
from ai_providers import AIProviderConfig, ProviderType, managed_ai_provider


async def run() -> None:
    config = AIProviderConfig(
        provider_type=ProviderType.COPILOT,
        model="gpt-4o",
        system_prompt="You are a helpful assistant.",
        timeout=120,
    )

    async with managed_ai_provider(config) as provider:
        await provider.initialize_session()
        response = await provider.send_message_and_await_response("Hello")
        print(response)


if __name__ == "__main__":
    asyncio.run(run())
```

## Tools

### Defining Tools with `@define_tool`

`define_tool` turns a plain function into a `BaseTool`. When the first parameter is typed as a Pydantic model, the JSON Schema is generated automatically:

```python
from pydantic import BaseModel, Field
from ai_providers import define_tool

class SearchParams(BaseModel):
    query: str = Field(description="The search query")

@define_tool(description="Search the web for a query")
def search_web(params: SearchParams) -> str:
    return do_search(params.query)
```

The decorated name becomes a `BaseTool` instance — assign it to `config.tools` directly.

`define_tool` can also be used as a plain function call when the handler is defined elsewhere:

```python
tool = define_tool("search_web", description="Search the web", handler=my_handler)
```

### Supported Handler Signatures

| Signature | Behaviour |
| --- | --- |
| `fn()` | Called with no arguments |
| `fn(invocation: ToolInvocation)` | Receives the raw invocation dict |
| `fn(params: PydanticModel)` | Parameters validated and unpacked via Pydantic |
| `fn(params: PydanticModel, invocation: ToolInvocation)` | Params + raw invocation |

Return values are normalised automatically: `str` → success result, `None` → empty success, `dict` → passed through, Pydantic model → JSON-serialised.

### Where to Define Tools

#### Agent-specific tools

Tools that belong to one agent should be defined at module level in the same file as the agent. They sit alongside the class they support and are not exported:

```python
# agents/my_agent.py
from pydantic import BaseModel, Field
from ai_providers import AIProviderConfig, define_tool
from .base import BaseAgent

class _SummaryParams(BaseModel):
    text: str = Field(description="Text to summarise")

@define_tool(description="Summarise a block of text")
def _summarise(params: _SummaryParams) -> str:
    return summarise(params.text)

class MyAgent(BaseAgent):
    def __init__(self, config: AIProviderConfig):
        config.tools = [_summarise]
        super().__init__(config)
```

#### Shared tools (`tools/` package)

Tools used by more than one agent live in the `tools/` package. Two patterns are supported:

**Stateless** — pure functions with no external dependencies. Define with `@define_tool` and import directly:

```python
# tools/search.py
@define_tool(description="Search the web")
def search_web(params: SearchParams) -> str:
    ...

# agents/my_agent.py
from tools.search import search_web
config.tools = [search_web]
```

**Stateful factory** — tools that close over a runtime dependency (e.g. a database connection or API client). Define a factory function that accepts the dependency and returns a `BaseTool`. The dependency is bound at agent construction time and is invisible to the model:

```python
# tools/database.py
def make_query_tool(db_url: str) -> BaseTool:
    @define_tool(description="Run a read-only database query")
    def query_db(params: QueryParams) -> str:
        return run_query(db_url, params.sql)  # db_url closed over
    return query_db

# agents/my_agent.py
from tools.database import make_query_tool

class MyAgent(BaseAgent):
    def __init__(self, config: AIProviderConfig, db_url: str):
        config.tools = [make_query_tool(db_url)]
        super().__init__(config)
```

The rule of thumb: if the dependency can be represented as data in the tool's arguments, keep it module-level. If it is a runtime resource that the agent lifecycle manages, bind it at construction time via a factory.

## Adding a New Agent

### 1. Create an agent module

Add a new file under `agents/` inheriting from `BaseAgent`:

- Set `config.system_prompt` in `__init__`.
- Assign agent-specific tools to `config.tools` before calling `super().__init__(config)`.
- Define agent-local tools at module level in the same file.

### 2. Export the agent

Update `agents/__init__.py` exports.

### 3. Add shared tools (optional)

If a tool is needed by multiple agents, add it to the `tools/` package following the stateless or stateful factory patterns described above.

---

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
- [x] Add `agents` package with `BaseAgent` (AsyncExitStack lifecycle, `query`, `query_json`) and `HelpfulAssistantAgent` example
- [x] Add `define_tool` decorator with Pydantic schema auto-generation
- [x] Add `tools/` package for shared tools with stateless and stateful factory patterns
- ~~[ ] Add agent factory / registry (similar to `ai_providers/factory.py`) under `agents/factory.py`~~
- [ ] Unit/Integration tests for `ai_providers`, `agents`, and `tools` packages
- [ ] Add Claude AI provider
- [ ] Add OpenAI provider

## License

See `LICENSE`.
