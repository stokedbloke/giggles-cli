# Codex Workflow Guide

Use this checklist whenever you run the PRP workflow with the Codex CLI.

## 1. Prep the Session
- Open a fresh Codex CLI conversation.
- Paste the full contents of `CLAUDE.md` so the assistant inherits the guardrails.
- Mention any high-level context that lives outside the repo (deployment environment, credentials, etc.).

## 2. Generate a PRP
1. Share the feature brief (e.g. `INITIAL.md`) or any other specification file.
2. Paste the instructions from `.claude/commands/generate-prp.md`.
3. Ask Codex to generate a PRP for the supplied file.
4. Confirm the resulting PRP is saved under `PRPs/<feature-slug>.md`.

## 3. Execute the PRP
1. Share the generated PRP path with Codex.
2. Paste the instructions from `.claude/commands/execute-prp.md`.
3. Ask Codex to implement the plan end-to-end, running every validation gate in the PRP.

## 4. Wrap Up
- Review the summary and ensure all PRP acceptance criteria are addressed.
- Update `TASK.md`, documentation, or follow-on PRPs as needed.
- Commit the changes once you have verified tests pass locally.
