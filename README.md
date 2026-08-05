# multi-agent-memory

Local-first, shared long-term memory for Codex, Pi, OpenCode, Claude Code, and other agent CLIs.

All agents can use the same human-readable Markdown Vault, including global preferences, project decisions, and reusable learnings. The SQLite index is only a rebuildable local search cache. There is no hosted service, telemetry, or automatic upload.

中文文档：[README.zh-CN.md](README.zh-CN.md)

## Install

Requires Python 3.11+. The recommended installation uses [uv](https://docs.astral.sh/uv/):

~~~bash
uv tool install multi-agent-memory
mam init
mam status
~~~

For one-off commands:

~~~bash
uvx --from multi-agent-memory mam status
~~~

### Install an agent adapter

Install one adapter, all adapters, or choose interactively:

~~~bash
mam install --agent pi
mam install --all
mam install
~~~

You can also ask the current agent:

> Install and configure multi-agent-memory for the current agent. Use uv tool install multi-agent-memory, preserve existing configuration, run mam init, install only the current agent's adapter with mam install --agent ..., run mam status, and tell me whether a restart is needed. Do not use sudo, overwrite unmanaged files, or read and upload complete transcripts, credentials, tokens, cookies, or private keys.

Supported adapters:

| Agent | Installation |
| --- | --- |
| Codex | mam install --agent codex |
| Pi | mam install --agent pi |
| OpenCode | mam install --agent opencode |
| Claude Code | mam install --agent claude |

Restart the agent after installing or upgrading its adapter. Hermes and OpenClaw are not supported yet.

## Everyday use

Ask a connected agent in natural language:

~~~text
帮我总结这轮记忆
记住：使用中文沟通，回答先给结论
确认刚才那条记忆
忘掉关于部署方式的记忆
回忆关于这个项目的决策
~~~

Or use the CLI directly:

~~~bash
mam context
mam propose --type preferences --text "Use Chinese and lead with the conclusion."
mam search "deployment" --include-candidates
mam confirm MEMORY_ID
mam forget MEMORY_ID
~~~

New memories are candidates and do not affect recall until confirmed. mam forget marks a memory deprecated; it remains auditable.

## Global and project memory

Global memories apply everywhere. Project memories apply when the agent is inside the matching Git checkout:

~~~bash
mam propose --type project \
  --text "Batch jobs must report resolved and unresolved items."

mam propose --type project --project my-app \
  --text "Database migrations must include a rollback plan."
~~~

mam context combines global memories with memories for the current project.

## Vault and privacy

The Markdown Vault is the source of truth and can be opened in Obsidian. Set its location with environment variables:

~~~bash
export AGENT_MEMORY_VAULT="$HOME/Documents/Obsidian/AgentMemory"
export AGENT_MEMORY_STATE_DIR="$HOME/.local/share/multi-agent-memory"
mam init
~~~

Adapters recall confirmed memories automatically. They do not silently summarize arbitrary transcripts. Ask the agent to summarize a meaningful work cycle, or provide a summary file:

~~~bash
mam session-summary --file summary.md
~~~

Do not store or commit credentials, API keys, cookies, private keys, complete transcripts, the Vault, or the SQLite index. For permanent deletion, remove the Markdown note and rebuild the index:

~~~bash
mam rebuild-index
~~~

## Upgrade

~~~bash
uv tool upgrade multi-agent-memory
mam install --all
mam status
~~~

If the tool was installed with an exact version pin, use:

~~~bash
uv tool install --force multi-agent-memory@latest
~~~

Upgrading does not delete the Vault or memories. Managed adapter files are backed up when replaced; unrelated configuration is preserved.

## Development

~~~bash
uv sync
uv run pytest
python -m compileall src
node --check adapters/pi/agent-memory.js
node --check adapters/opencode/agent-memory.js
~~~

MIT License. See [LICENSE](LICENSE).
