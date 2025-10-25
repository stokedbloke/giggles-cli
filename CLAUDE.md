## 🔐 How to Use This File with Codex
- Start every Codex CLI session by pasting this entire file so the assistant inherits the project guardrails.
- If `PLANNING.md` or `TASK.md` is missing, ask whether to create it before proceeding.
- Assume the assistant cannot see files unless you explicitly share paths or excerpts.
- Run commands inside the `venv_linux` virtual environment for all Python tooling (tests, scripts, formatters).

## 🔄 Project Awareness & Context
- Read `PLANNING.md` (when present) at the start of a new task to understand architecture, goals, style, and constraints.
- Check `TASK.md` before starting work. If the task is missing, add it with a brief description and today's date.
- Keep naming conventions, file structure, and architecture patterns consistent with what `PLANNING.md` describes.

## 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
  For agents this looks like:
    - `agent.py` - Main agent definition and execution logic 
    - `tools.py` - Tool functions used by the agent 
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

## 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

## ✅ Task Completion
- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a “Discovered During Work” section.

## 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

## 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

## 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.

## 🚨 CRITICAL: NO FAKE IMPLEMENTATIONS
- **NEVER return fake success messages** when core functionality is not implemented
- **NEVER show "success" toasts** when the actual work failed or was skipped
- **ALWAYS be honest about mock implementations** - clearly label them as "MOCK" or "TODO"
- **NEVER implement placeholder functions** that return empty results without clear warnings
- **ALWAYS verify core functionality works** before claiming success
- **NEVER fake API responses** - if external APIs aren't implemented, return errors, not fake data
- **ALWAYS test the actual functionality** before declaring it complete

## 🔍 MANDATORY VERIFICATION CHECKLIST
Before claiming any feature is "working" or "complete":
- [ ] Does it actually perform the core function it claims to do?
- [ ] Are external API calls real, not mocked?
- [ ] Are file operations actually happening?
- [ ] Are database operations actually storing/retrieving data?
- [ ] Are success messages truthful about what actually happened?
- [ ] Have you tested the feature end-to-end?

## 🚫 ANTI-PATTERNS TO NEVER DO AGAIN
- ❌ Don't return empty arrays and claim "no data found" when you never actually looked for data
- ❌ Don't show "success" messages when the core functionality is completely fake
- ❌ Don't implement mock functions without clear "MOCK" warnings
- ❌ Don't claim features are "working" when they're just placeholder implementations
- ❌ Don't fake external API responses without clearly labeling them as fake