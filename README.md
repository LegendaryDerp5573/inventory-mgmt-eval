# Inventory Management Workflow Evaluation

A HUD RL environment for evaluating **GPT OSS 120B** as an agent that operates a **gym inventory management system**. This workflow uses tool-based business task execution and SQL state validation, not bug fixing.

## Project overview

This project evaluates how well an agent can complete real operational tasks in an inventory + member support workflow:

- **Domain:** Gym-style business inventory and member inquiry handling.
- **Agent role:** Receive plain-English instructions, call backend tools, and update state correctly.
- **Evaluation target:** End-to-end workflow correctness measured from database state after task completion.

## Environment description

The environment exposes nine agent tools backed by HTTP calls to `BACKEND_URL`:

- `get_items`
- `get_item`
- `update_quantity`
- `update_availability`
- `check_restock`
- `get_members`
- `get_member`
- `resolve_inquiry`
- `get_audit`

The backend (`backend/app.py`) serves these routes and persists data in SQLite (`inventory/inventory.db`). The environment scenario in `env.py` prompts the agent and then validates final state using SQL checks.

## Branch structure

| Branch | Role |
|--------|------|
| **`main`** / **`golden`** | Working workflow implementation used for this evaluation setup. |
| **`baseline`** | Unused in this workflow-based approach. |
| **`test`** | Unused in this workflow-based approach. |

## 1. Deploy to Platform

If you haven't already, connect this repo to hud.ai:

1. Push to GitHub  
2. Go to [hud.ai](https://hud.ai) → **New** → **Environment**  
3. Connect your GitHub repo  
4. Your environment builds automatically on each push  

Once deployed, your environment is accessible by its slug (e.g., `my-org/inventory-workflow`).

## 2. Define tools and scenarios

**Tools** are HTTP wrappers to the inventory backend APIs:

```python
@env.tool()
async def get_items() -> Any: ...

@env.tool()
async def update_quantity(item_id: int, quantity: int) -> Any: ...

@env.tool()
async def resolve_inquiry(member_id: int, resolved: bool) -> Any: ...
```

**Scenario** is `workflow`, which takes:

- `instruction: str`
- `checks: list[dict]` where each dict has:
  - `query` (SQL string)
  - `expected` (expected scalar result)

```python
@env.scenario("workflow")
async def workflow(instruction: str, checks: Sequence[Mapping[str, Any]]):
    _ = yield instruction
    # run SQL checks against inventory/inventory.db
    yield 1.0 if all_checks_pass else 0.0
```

### Scoring

Scoring is **SQL-based**, not pytest-based:

1. Agent completes the task using tools.
2. Evaluator opens SQLite at `inventory/inventory.db`.
3. Each check query is executed and compared to its `expected` value.
4. Reward is **1.0** only if **all** checks pass, otherwise **0.0**.

### How tasks work

1. The task provides a plain-English business instruction (for example, adjust stock and resolve a member inquiry).
2. The scenario yields that instruction as the prompt.
3. The agent calls one or more tools to perform the workflow.
4. After the agent response, SQL checks verify final database state.
5. Score is returned from those checks.

## 3. Create tasks from scenarios

Tasks are scenario instances with explicit instructions and SQL checks.

**In code:**

```python
tasks = [
    env(
        "workflow",
        instruction="Restock Hand Wraps to 12 and mark availability correctly.",
        checks=[
            {"query": "SELECT quantity FROM items WHERE sku='SKU002'", "expected": 12},
            {"query": "SELECT available FROM items WHERE sku='SKU002'", "expected": 1},
        ],
    ),
]
```

**From JSON:**

```json
[
  {
    "env": {"name": "my-org/inventory-workflow"},
    "scenario": "workflow",
    "args": {
      "instruction": "Resolve Dana Lee's inquiry as unresolved.",
      "checks": [
        {"query": "SELECT total_inquiries FROM members WHERE email='dana@gym.com'", "expected": 6}
      ]
    }
  }
]
```

## 4. Run evaluations

Run tasks and see results on hud.ai.

**CLI:**

```bash
hud eval ./remote_tasks.json --model gpt-4o --remote
hud eval my-org/inventory-workflow-tasks --model gpt-4o --remote --group 5
```

**Python:**

```python
import hud
from hud.agents import OpenAIChatAgent

tasks = [env("workflow", instruction="...", checks=[...])]

async with hud.eval(tasks) as ctx:
    agent = OpenAIChatAgent.create(model="gpt-4o")
    await agent.run(ctx)
```

## Task difficulty breakdown

| Level | Description |
|-------|-------------|
| **Easy** | Single tool call with an obvious action (e.g., set one quantity). |
| **Medium** | 2-3 steps; requires filtering records or light math before acting. |
| **Hard** | Multi-step workflows with conditional logic and/or ambiguous phrasing. |

## Local development

```bash
# Start backend (port 8005)
uvicorn backend.app:app --port 8005 --reload

# Reset and reseed database
curl -X POST http://localhost:8005/reset
```

Available API routes:

- `GET /health`
- `POST /reset`
- `GET /items`
- `GET /items/{item_id}`
- `PUT /items/{item_id}/quantity`
- `PUT /items/{item_id}/available`
- `GET /items/{item_id}/restock`
- `GET /members`
- `GET /members/{member_id}`
- `PUT /members/{member_id}/resolve`
- `GET /audit`

## Structure

```
inventory-mgmt-env/
├── env.py                 # HUD environment: workflow tools + SQL-scored scenario
├── backend/
│   ├── __init__.py
│   └── app.py             # FastAPI backend (health/reset/items/members/audit)
├── inventory/
│   ├── __init__.py
│   ├── api.py             # Flask API module (inventory/member routes)
│   ├── database.py        # SQLite connection + schema setup
│   ├── inventory.py       # Inventory business logic + audit
│   ├── members.py         # Member inquiry business logic
│   └── seed.py            # Deterministic seed data for startup/reset
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_backend.py
├── local_test.py
├── remote_test.py
├── remote_tasks.json
├── Dockerfile.hud
├── pyproject.toml
└── README.md
```

## Documentation

Full documentation: [docs.hud.ai](https://docs.hud.ai)
