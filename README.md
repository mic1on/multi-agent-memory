# multi-agent-memory

Shared, local-first long-term memory for Codex, Pi, OpenCode, and other agent CLIs.

The project gives multiple agent clients one human-readable memory Vault. You
can open it in Obsidian, review proposed memories, and keep confirmed
preferences and project decisions available across tools.

## What it does

- stores Markdown in an Obsidian-compatible Vault;
- uses SQLite FTS5 only as a rebuildable local search cache;
- recalls confirmed global and project-scoped memories at agent startup;
- keeps new memories as candidates until a human confirms them;
- saves concise session summaries and crash-recovery receipts;
- provides thin Codex, Pi, and OpenCode adapters;
- has no network service, telemetry, or hosted memory dependency.

The important boundary is deliberate: adapters can automatically recall memory,
but they do not silently summarize arbitrary transcripts. For durable memory,
ask the agent to summarize a meaningful cycle or use a natural-language memory
command.

## Install

Requires Python 3.11 or newer. The recommended setup uses uv:

    git clone https://github.com/YOUR-USERNAME/multi-agent-memory.git
    cd multi-agent-memory
    uv sync
    uv run memoryctl init

For a global CLI installation:

    uv tool install .
    memoryctl init

The package uses Dynaconf for YAML and environment configuration. The CLI does
not create a Vault until a command such as init or propose needs it.

## Configure the Vault

Create a settings file from the example:

    mkdir -p ~/.config/multi-agent-memory
    cp config.example.yaml ~/.config/multi-agent-memory/settings.yaml

Then edit vault to your Obsidian Vault path and pass it explicitly:

    memoryctl --config ~/.config/multi-agent-memory/settings.yaml init

Or configure with environment variables:

    export AGENT_MEMORY_VAULT="$HOME/Documents/Obsidian/AgentMemory"
    export AGENT_MEMORY_STATE_DIR="$HOME/.local/share/multi-agent-memory"

Configuration precedence is command-line config file, environment variables,
then platform defaults. The Vault is user data; keep it outside this Git repo.

## Vault layout

    00-profile/     confirmed global preferences
    10-projects/    project-scoped memories
    20-decisions/   confirmed decisions
    30-learnings/   reusable lessons
    90-sessions/    concise session summaries
    inbox/          candidates awaiting review
    .memory/pending crash-recovery receipts

Markdown is authoritative. Editing a Markdown note in Obsidian takes effect on
the next search or context call because the SQLite cache is rebuilt from the
Vault.

## Natural-language use

After installing the protocol and an adapter, talk to any connected agent:

    帮我总结这轮记忆
    记住：使用中文沟通，先给结论
    确认刚才那条记忆
    忘掉关于部署方式的记忆
    回忆关于这个项目的决策

The agent translates these into CLI calls and reports the result. You do not
need to open a terminal. Candidates remain inactive until confirmation.

The equivalent CLI commands are:

    memoryctl session-summary --text "## Outcome ..."
    memoryctl propose --type preferences --text "Use Chinese and lead with the conclusion."
    memoryctl search "deployment" --include-candidates
    memoryctl confirm PENDING_MEMORY_ID
    memoryctl forget MEMORY_ID
    memoryctl context "project decisions"

## Project-level memory

Project memories use --type project and a project name. When run inside a
Git checkout, memoryctl propose --type project detects the nearest
directory containing .git and records its name. You can always override it:

    memoryctl propose --type project --project my-app \
      --text "Batch jobs must report resolved and unresolved items."

Global memories have scope: global; project memories have scope: project
and a project field. memoryctl context includes global memories plus
memories matching the current project.

## Agent adapters

See adapters/README.md for installation details.

- Codex: merge adapters/codex/hooks.example.json into your hooks file.
- Pi: copy adapters/pi/agent-memory.js into the extensions directory.
- OpenCode: copy adapters/opencode/agent-memory.js into the plugins directory.

All adapters call the memoryctl executable from PATH. They do not include
machine-specific paths. At shutdown they write a pending receipt only if
AGENT_MEMORY_SUMMARY_FILE points to an explicitly prepared summary file.

## Session summaries and automatic collection

This system does not claim to automatically understand every message in a
session. Automatic hooks can recover pending summaries and inject existing
memory. The active agent must create a concise boundary summary, for example:

    ## Outcome
    Implemented the shared memory CLI.
    ## Decisions
    Markdown remains authoritative; candidates require confirmation.
    ## Reusable learnings
    Adapters should call the installed CLI instead of hard-coded paths.
    ## Open questions
    None.
    ## Next action
    Review the release diff.

Then save it with memoryctl session-summary --file summary.md or let an
adapter consume the file named by AGENT_MEMORY_SUMMARY_FILE.

## Safety and deletion

Never commit your Vault, SQLite index, transcript, credentials, or agent
configuration containing secrets. See docs/privacy.md.

memoryctl forget ID marks a note deprecated, so it is excluded from recall
while remaining auditable. For permanent deletion, remove the Markdown file
manually and run memoryctl rebuild-index; also review your backups and sync
history.

## Development

    uv sync
    uv run pytest
    python -m compileall src
    node --check adapters/pi/agent-memory.js
    node --check adapters/opencode/agent-memory.js

The project targets Python 3.11+ and keeps runtime configuration in YAML when
configuration is needed. Contributions should include focused tests and must
not add personal Vault data.

## License

MIT. See LICENSE.
