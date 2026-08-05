# Multi-Agent Memory Implementation Plan

> For agentic workers: Implement this plan task-by-task and keep each task independently testable.

**Goal:** Publish a local-first shared memory layer that lets Codex, Pi, and OpenCode recall the same confirmed memories and store concise session summaries in an Obsidian-compatible Vault.

**Architecture:** Markdown files in a configured Vault are authoritative. A SQLite FTS5 database in a separate state directory is a disposable search cache rebuilt from Markdown. A small Python CLI owns all mutations and adapters only call the CLI through PATH.

**Tech Stack:** Python 3.11+, uv, Dynaconf, SQLite FTS5, Markdown front matter, pytest, JavaScript adapters for Codex/Pi/OpenCode.

---

### Task 1: Core configuration and Vault store

**Files:**
- Create: pyproject.toml
- Create: src/multi_agent_memory/config.py
- Create: src/multi_agent_memory/store.py
- Create: src/multi_agent_memory/__init__.py

- [ ] Define Settings with YAML-first Dynaconf loading and environment overrides for Vault, state, index, and recall limit.
- [ ] Define atomic Markdown writes, file locking, front matter parsing, layer layout, candidate activation, deprecation, pending receipt recovery, and SQLite FTS5 rebuild/search.
- [ ] Keep all defaults platform-relative; never embed the maintainer home directory or Vault.

### Task 2: CLI and natural-language protocol

**Files:**
- Create: src/multi_agent_memory/cli.py
- Create: src/multi_agent_memory/project.py
- Create: AGENT-MEMORY.md
- Create: adapters/codex/hooks.example.json

- [ ] Expose init, status, search, recall, context, propose, confirm, forget, session-summary, pending, recover, and rebuild-index.
- [ ] Use hyphenated public options while accepting underscore aliases for migration compatibility.
- [ ] Make candidates inert until explicit confirmation and make empty pending requests a no-op.
- [ ] Define the agent-facing Chinese and English protocol without claiming that shell hooks can summarize arbitrary transcripts.

### Task 3: Agent adapters

**Files:**
- Create: adapters/pi/agent-memory.js
- Create: adapters/opencode/agent-memory.js

- [ ] Recall confirmed context at startup/agent-start.
- [ ] Run recovery on session start.
- [ ] Allow an explicitly supplied summary file to be saved at shutdown, but never persist a full transcript automatically.

### Task 4: Documentation, examples, tests, and release hygiene

**Files:**
- Create: README.md, LICENSE, .gitignore, .python-version
- Create: config.example.yaml, adapters/README.md, docs/privacy.md, docs/migration.md
- Create: tests/test_store.py, tests/test_cli.py, tests/test_adapters.py
- Create: .github/workflows/test.yml

- [ ] Document installation with uv, configuration, Obsidian layout, project scope, natural-language commands, adapter installation, privacy, deletion, migration, and troubleshooting.
- [ ] Test candidate lifecycle, indexing, summaries, pending recovery, config isolation, and JavaScript syntax.
- [ ] Add a release scan that rejects private session data, SQLite files, credentials, and maintainer-specific absolute paths.

### Task 5: Local verification and publication gate

- [ ] Run uv sync, uv run pytest, Python compilation, JavaScript syntax checks, and a secret/path scan.
- [ ] Inspect the final diff and verify the local repository has no user Vault or session files.
- [ ] Stop and ask the captain before creating a GitHub repository or running git push.

