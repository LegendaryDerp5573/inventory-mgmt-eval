# Inventory Management Evaluation

A HUD RL environment for evaluating **GPT OSS 120B** (and other models) on a **Flask + SQLite** inventory management codebase. Agents receive bug descriptions, edit code with shell and file tools, and are scored by whether **pytest** passes.

## Project overview

This project measures how well a model can **diagnose and fix real bugs** in a small but realistic Python service:

- **Stack:** SQLite for persistence; **`inventory/`** holds a **Flask** HTTP API (`inventory/api.py`) plus pure-Python modules for business logic. A separate **FastAPI** app (`backend/app.py`) exposes **health** and **database reset** for the HUD harness (port **8005**).
- **Goal:** Compare models on code-repair tasks with **binary rewards** (all tests pass → **1.0**, any failure → **0.0**).

## Environment description

The codebase models a **gym-style retail** operation:

- **Inventory** — Track items (SKU, quantity, restock thresholds, availability), restock checks, in-stock rates, and simple audit-style reports (`inventory/inventory.py`, `inventory/database.py`).
- **Members** — Staff or front-desk users with inquiry resolution stats (`inventory/members.py`).

Eval tasks inject bugs into **`inventory/inventory.py`** and **`inventory/members.py`** (and optionally related wiring). The agent must restore behavior expected by the tests under **`tests/`**.

## Branch structure

| Branch | Role |
|--------|------|
| **`main`** / **`golden`** | Correct reference implementation; tests should pass. |
| **`baseline`** | Buggy code for agent repair tasks. |
| **`test`** | Pytest suite and fixtures (often mirrored or merged with `tests/` at repo root). |

Use **golden** as the ground truth when authoring or validating tasks; ship **baseline** to agents for eval.

## 1. Deploy to Platform

If you haven't already, connect this repo to hud.ai:

1. Push to GitHub  
2. Go to [hud.ai](https://hud.ai) → **New** → **Environment**  
3. Connect your GitHub repo  
4. Your environment builds automatically on each push  

Once deployed, your environment is accessible by its slug (e.g., `my-org/inventory-mgmt`).

## 2. Define tools and scenarios

**Tools** are functions the agent can call. **`bash_tool`** runs a shell command in the project root; **`edit_tool`** reads a file (no `content`) or overwrites it (with `content`). Paths must stay inside the project directory.

**Scenarios** define the evaluation lifecycle: prompt the agent, then score.

```python
from hud import Environment

env = Environment(name="inventory")

@env.tool()
async def bash_tool(command: str) -> str:
    ...

@env.tool()
async def edit_tool(path: str, content: str | None = None) -> str:
    ...

@env.scenario("fix-bug")
async def fix_bug(task_description: str):
    _ = yield task_description                    # Prompt → agent edits code
    # After the agent responds, pytest runs on tests/
    yield 1.0 if process.returncode == 0 else 0.0
```

The HTTP client still targets the FastAPI backend on **`BACKEND_PORT`** (default **8005**) for **`@env.initialize`** health checks; **reward** is **not** derived from backend state—it comes **only** from the **pytest** exit code.

### How tasks work

1. The platform (or harness) passes a **`task_description`** (the bug report).  
2. The scenario **yields** that string as the **prompt** to the agent.  
3. The agent uses **`bash_tool`** and **`edit_tool`** to fix the code.  
4. After the agent finishes, the scenario runs **`pytest`** on the **`tests/`** directory at the project root.  
5. **Score:** **1.0** if pytest exits **0**, **0.0** otherwise.

Between eval episodes, call **`POST /reset`** on the backend (or restart the backend) to wipe and reinitialize the SQLite DB so each run starts clean.

## 3. Create tasks from scenarios

Tasks are scenario instances with specific arguments.

**In code:**

```python
tasks = [
    env("fix-bug", task_description="Fix off-by-one in restock check when quantity equals threshold."),
    env("fix-bug", task_description="Member resolution rate divides wrong when total_inquiries is zero."),
]
```

**From JSON:**

```json
[
  {"env": {"name": "my-org/inventory-mgmt"}, "scenario": "fix-bug", "args": {"task_description": "..."}}
]
```

**On platform:**  
After deploying, create tasks from your scenarios on hud.ai. Access them by slug:

```python
from hud.datasets import load_tasks
tasks = load_tasks("my-org/inventory-mgmt-tasks")
```

## 4. Run evaluations

Run tasks and see results on hud.ai. You have three options:

**On platform:**  
Run evaluations at scale directly on [hud.ai](https://hud.ai) with parallel execution and automatic tracing.

**CLI:**

```bash
hud eval ./remote_tasks.json --model gpt-4o --remote  # https://hud.ai/models
hud eval my-org/inventory-mgmt-tasks --model gpt-4o --remote --group 5
```

**Python:**

```python
import hud
from hud.agents import OpenAIChatAgent  # See all models: https://hud.ai/models

tasks = [env("fix-bug", task_description="...")]

async with hud.eval(tasks) as ctx:
    agent = OpenAIChatAgent.create(model="gpt-4o")  # Uses inference.hud.ai
    await agent.run(ctx)

# Results are automatically traced to hud.ai
```

**With variants (A/B testing):**

```python
async with hud.eval(tasks, variants={"model": ["gpt-4o-mini", "gpt-4o"]}, group=2) as ctx:
    agent = OpenAIChatAgent.create(model=ctx.variants["model"])
    await agent.run(ctx)
```

## Task difficulty breakdown

Bugs are categorized to span **`inventory/inventory.py`** and **`inventory/members.py`**:

| Level | Examples |
|-------|----------|
| **Easy** | Wrong comparison (`<=` vs `<`), forgetting to update **`available`** when quantity changes, single-branch mistakes in **`check_restock`**. |
| **Medium** | Incorrect **`get_instock_rate`** or **`run_audit_report`** aggregation; **`resolve_inquiry`** double-counting or not incrementing **`total_inquiries`**; edge cases around zero quantity. |
| **Hard** | Subtle inconsistencies across DB reads/writes, wrong field used in a query, or logic that only fails under multi-step sequences (still covered by pytest). |

Author tasks so each maps to one focused bug class and is fully specified in **`task_description`**.

## Local development

```bash
# Start the FastAPI backend (health + DB reset; initializes SQLite on startup)
uvicorn backend.app:app --port 8005 --reload

# Optional: reset DB between manual runs (empty schema + tables recreated)
curl -X POST http://localhost:8005/reset

# Run the test suite (same command used for scoring in fix-bug)
pytest tests/

# Optional: local HUD-style checks
python local_test.py
python remote_test.py
```

The SQLite file is created under **`inventory/inventory.db`** when the backend starts (or when **`inventory.database.setup()`** runs). No separate seed script is required for an empty DB; use your tests or small scripts to insert rows if you need fixtures beyond **`tests/conftest.py`**.

## Structure

```
inventory-mgmt-env/
├── env.py                 # Environment: bash_tool, edit_tool, fix-bug scenario
├── backend/
│   └── app.py             # FastAPI: /health, /reset, DB init (port 8005)
├── inventory/
│   ├── database.py        # SQLite setup (setup / initialize_database)
│   ├── inventory.py       # Items: add/remove/update, restock, audit, rates
│   ├── members.py         # Members: CRUD-ish, inquiries, resolution rate
│   └── api.py             # Flask routes wrapping inventory + members
├── tests/
│   ├── conftest.py
│   └── test_backend.py
├── local_test.py
├── remote_test.py
├── remote_tasks.json
├── Dockerfile.hud
└── pyproject.toml
```

## Documentation

Full documentation: [docs.hud.ai](https://docs.hud.ai)
