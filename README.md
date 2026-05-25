# Python AI Providers Strategy Template

I built this template because I usually work on AI-enabled projects that need to switch between multiple providers, and I wanted a reusable foundation that avoids rebuilding the same provider wiring, lifecycle code, and agent orchestration in every new repository.

## Introduction

This project is an async-first Python template that applies a provider strategy + factory pattern to AI integrations.

Design goals:

- Decouple application code from provider-specific SDK logic.
- Standardize provider lifecycle operations (`start`, `send`, `stop`).
- Centralize construction and resource management in one place.
- Make it straightforward to add new providers with minimal changes.
- Keep the `ai_providers` package fully self-contained — no concepts from the agent layer leak into it.
- Define agents as declarative contracts (identity only), so the caller retains full control over lifecycle and configuration.
- Use Pydantic for options validation and discriminated unions.

## Requirements

- Python 3.11+
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
├── pyproject.toml
├── pyrightconfig.json
├── main.py
├── ai_providers/
│   ├── __init__.py
│   ├── base.py
│   ├── config.py
│   ├── copilot.py
│   ├── factory.py
│   ├── registry.py
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

- `main.py`: Example entry point showing how to construct options, select an agent, and run a provider session.
- `ai_providers/base.py`: Generic provider contract, base options (Pydantic), all tool-related types (`BaseTool`, `ToolHandler`, `ToolInvocation`, `ToolResult`), `JSONParseError`, and high-level query methods (`query`, `query_json`).
- `ai_providers/copilot.py`: Concrete provider implementation for the Copilot SDK (0.3.x).
- `ai_providers/factory.py`: Provider creation/disposal, and the `managed_ai_provider` context manager.
- `ai_providers/tools.py`: `define_tool` decorator — auto-generates JSON Schema from Pydantic models and wraps plain functions as `BaseTool` instances.
- `ai_providers/config.py`: `AIConfig` type alias for Pydantic discriminated union of provider options.
- `ai_providers/registry.py`: Provider registry with `@register_provider` decorator and `get_provider_class` lookup.
- `ai_providers/__init__.py`: Public exports for package consumers.
- `agents/base.py`: `BaseAgent` — an abstract base class declaring the two class-level attributes every agent must define: `system_prompt` and `tools`.
- `agents/helpful_assistant.py`: Example concrete agent. Defines its persona and tools; contains no lifecycle logic.
- `tools/`: Shared tool definitions reusable across multiple agents (stateless and stateful factory patterns).

## Provider + Factory Strategy

### Base Provider Contract

`BaseAIProvider` defines the lifecycle contract for all providers:

- `start()` — establish connections and initialise the session
- `send_message_and_await_response(message: str) -> str`
- `stop()` — tear down the session and release connections

Every provider must implement these async methods.

### Provider Options (Pydantic)

Each concrete provider has a typed options class inheriting from `BaseAIOptions` (a Pydantic `BaseModel`).

Example (`CopilotOptions`):

- `type: Literal["copilot"]` — provider type discriminator
- `model: str` — model identifier (default: `"claude-sonnet-4.6"`)
- `timeout: float` — timeout in seconds (default: `300.0`)
- `github_token: str | None` — optional GitHub PAT for authentication

### Factory Responsibilities

`create_ai_provider(options, system_prompt, tools)`:

- Accepts provider options, system prompt, and tools directly.
- Looks up the provider class via the registry using `options.type`.
- Returns an **unstarted** provider instance.

`dispose_ai_provider(provider)`:

- Calls `provider.stop()` to release all resources.

`managed_ai_provider(options, system_prompt, tools)`:

- Async context manager that creates the provider, calls `start()`, and stops fully on exit.
- This is the primary entry point for running a provider session — callers use it directly.

### Registry Pattern

You can read more about the Registry Pattern here: [geeksforgeeks.org/system-design/registry-pattern](https://www.geeksforgeeks.org/system-design/registry-pattern/).

Providers are registered via a class decorator:

```python
from ai_providers import register_provider, BaseAIProvider, BaseAIOptions

@register_provider("copilot")
class CopilotProvider(BaseAIProvider[CopilotOptions]):
    ...
```

The factory looks up providers by their type ID:

```python
from ai_providers import get_provider_class

provider_class = get_provider_class("copilot")
```

## Agents

### Design Philosophy

The `agents` package and the `ai_providers` package are intentionally decoupled. Earlier iterations coupled them by having agents accept a config, inject their `system_prompt` and `tools` into it, and manage the provider lifecycle internally. That approach created two problems:

- The `ai_providers` package needed concepts (like a "backend-only" config) that only existed to serve the agent pattern.
- Callers had no control over the provider lifecycle — it was hidden inside the agent.

The current design separates responsibilities cleanly:

- **`ai_providers`** owns everything about talking to a backend: construction, lifecycle, and querying. It has no knowledge of agents.
- **`agents`** owns identity only: what persona to use and what tools to expose.

### What `BaseAgent` Is

`BaseAgent` is an abstract base class — a contract, not an implementation. It declares two class-level attributes that every concrete agent must define:

```python
class BaseAgent(ABC):
    system_prompt: str
    tools: tuple[BaseTool, ...]
```

There is no constructor, no lifecycle logic, and no provider reference. Inheriting from `ABC` makes direct instantiation of `BaseAgent` a `TypeError`, which ensures subclasses always declare both attributes.

### Defining an Agent

A concrete agent is a class with two attributes:

```python
class HelpfulAssistantAgent(BaseAgent):
    system_prompt: str = "You are a helpful assistant."
    tools: tuple[BaseTool, ...] = (ping_pong, prefixed_ping_pong)
```

Nothing else. The agent carries no state and manages no resources.

### How the Caller Uses an Agent

The caller constructs the options, drawing `system_prompt` and `tools` from the chosen agent class:

```python
from ai_providers import CopilotOptions, managed_ai_provider
from agents import HelpfulAssistantAgent

options = CopilotOptions(model="claude-sonnet-4.6", timeout=120)

async with managed_ai_provider(
    options,
    system_prompt=HelpfulAssistantAgent.system_prompt,
    tools=HelpfulAssistantAgent.tools,
) as provider:
    response = await provider.query("Hello")
    print(response)
```

This means:

- Swapping agents is a single-line change (`HelpfulAssistantAgent` → `AnotherAgent`).
- Lifecycle control stays entirely with the caller.
- The `ai_providers` package remains fully agnostic of the agents package.

### Query Interface

`query` and `query_json` are methods on `BaseAIProvider`, not on agents. They are available on any provider instance yielded by `managed_ai_provider`:

- `provider.query(message: str) -> str` — send a message, return the raw response string.
- `provider.query_json(message: str, max_retries: int = 3) -> dict` — send a message, parse the response as JSON. On parse failure, automatically sends the error back to the model and retries up to `max_retries` times before raising `JSONParseError`.

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

The decorated name becomes a `BaseTool` instance — assign it to the `tools` argument directly.

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

Return values are normalised automatically: `str` → success result, `None` → empty success, `dict` → passed through (or JSON-serialized if no `resultType`), `list` → JSON-serialized, Pydantic model → JSON-serialized.

### Where to Define Tools

#### Agent-specific tools

Tools that belong to one agent should be defined at module level in the same file as the agent:

```python
# agents/my_agent.py
from pydantic import BaseModel, Field
from ai_providers import BaseTool, define_tool
from .base import BaseAgent

class _SummaryParams(BaseModel):
    text: str = Field(description="Text to summarise")

@define_tool(description="Summarise a block of text")
def _summarise(params: _SummaryParams) -> str:
    return summarise(params.text)

class MyAgent(BaseAgent):
    system_prompt: str = "You are a summarisation assistant."
    tools: tuple[BaseTool, ...] = (_summarise,)
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
tools = (search_web,)
```

**Stateful factory** — tools that close over a runtime dependency (e.g. a database connection or API client). Define a factory function that accepts the dependency and returns a `BaseTool`. The dependency is bound at agent construction time and is invisible to the model:

```python
# tools/database.py
def make_query_tool(db_url: str) -> BaseTool:
    @define_tool(description="Run a read-only database query")
    def query_db(params: QueryParams) -> str:
        return run_query(db_url, params.sql)  # db_url closed over
    return query_db
```

```python
# main.py (or wherever the session is set up)
from tools.database import make_query_tool
from agents import MyAgent

tools = (*MyAgent.tools, make_query_tool(db_url))

async with managed_ai_provider(options, system_prompt=MyAgent.system_prompt, tools=tools) as provider:
    response = await provider.query("Hello")
```

The rule of thumb: if the dependency can be represented as data in the tool's arguments, keep it module-level. If it is a runtime resource that the agent lifecycle manages, bind it at construction time via a factory.

## Adding a New Agent

### 1. Create an agent module

Add a new file under `agents/` inheriting from `BaseAgent`:

- Define `system_prompt` as a class-level string attribute.
- Define `tools` as a class-level tuple of `BaseTool` instances.
- Define any agent-specific tools at module level in the same file.

```python
# agents/my_agent.py
from ai_providers import BaseTool
from .base import BaseAgent

class MyAgent(BaseAgent):
    system_prompt: str = "You are a specialist assistant."
    tools: tuple[BaseTool, ...] = ()
```

### 2. Export the agent

Update `agents/__init__.py` exports.

### 3. Use the agent

In your entry point, pass the agent's attributes to `managed_ai_provider`:

```python
from ai_providers import CopilotOptions, managed_ai_provider
from agents import MyAgent

options = CopilotOptions(model="claude-sonnet-4.6", timeout=120)

async with managed_ai_provider(
    options,
    system_prompt=MyAgent.system_prompt,
    tools=MyAgent.tools,
) as provider:
    response = await provider.query("Hello")
```

### 4. Add shared tools (optional)

If a tool is needed by multiple agents, add it to the `tools/` package following the stateless or stateful factory patterns described above.

---

## Adding a New Provider

### 1. Create a provider module

Add a new file under `ai_providers/` (for example `openai_provider.py`) with:

- An options class inheriting `BaseAIOptions` with `type: Literal["openai"]`.
- A provider class inheriting `BaseAIProvider[YourOptions]`.
- Implementations for `start()`, `stop()`, and `send_message_and_await_response()`.
- Decorate the class with `@register_provider("openai")`.

### 2. Add to config union

Update `AIConfig` in `ai_providers/config.py`:

```python
AIConfig = Annotated[
    Union[CopilotOptions, OpenAIOptions],  # Add new options here
    Field(discriminator="type"),
]
```

### 3. Export the new provider

Update `ai_providers/__init__.py` exports.

### 4. Add dependency

Update `requirements.txt` if the provider requires an SDK.

## Error Handling Notes

- Unsupported provider types raise `KeyError`.
- Startup/initialization/cleanup runtime failures raise `RuntimeError`.
- Concrete providers should validate required options early and raise `ValueError` for invalid configuration.

## Extension Guidelines

- Keep provider-specific SDK code inside provider modules, not app code.
- Keep `main.py` orchestration-oriented and provider-agnostic.
- Prefer `managed_ai_provider` in app code for automatic lifecycle handling.
- Keep options strongly typed with Pydantic to simplify validation and refactoring.

## Current Dependency

| Provider | Package | Version Constraint | Notes |
| --- | --- | --- | --- |
| Copilot | github-copilot-sdk | >=0.3.0,<0.4.0 | Active provider in this template |

Planned providers can be added as new rows as they are implemented.

## Code Quality

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

Install pre-commit hooks:

```bash
pre-commit install
```

Run manually:

```bash
ruff check .
ruff format .
```

## TODO

- [x] Use Pydantic for options with discriminated union support
- [x] Add registry pattern for provider discovery
- [x] Add `agents` package with `BaseAgent` (identity only) and `HelpfulAssistantAgent` example
- [x] Add `define_tool` decorator with Pydantic schema auto-generation
- [x] Add `tools/` package for shared tools with stateless and stateful factory patterns
- [x] Add ruff linting and formatting with pre-commit hooks
- [ ] Add agent factory / registry (similar to `ai_providers/factory.py`) under `agents/factory.py`
- [ ] Unit/Integration tests for `ai_providers`, `agents`, and `tools` packages
- [ ] Add Claude AI provider
- [ ] Add OpenAI provider

## License

See `LICENSE`.
