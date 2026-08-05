# multi-agent-memory

Shared, local-first long-term memory for Codex, Pi, OpenCode, Claude Code, and other agent CLIs.

The project gives multiple agent clients one human-readable memory Vault. You
can open it in Obsidian, review proposed memories, and keep confirmed
preferences and project decisions available across tools.

## What it does

- stores Markdown in an Obsidian-compatible Vault;
- uses SQLite FTS5 only as a rebuildable local search cache;
- recalls confirmed global and project-scoped memories at agent startup;
- keeps new memories as candidates until a human confirms them;
- saves concise session summaries and crash-recovery receipts;
- provides thin Codex, Pi, OpenCode, and Claude Code adapters;
- has no network service, telemetry, or hosted memory dependency.

The important boundary is deliberate: adapters can automatically recall memory,
but they do not silently summarize arbitrary transcripts. For durable memory,
ask the agent to summarize a meaningful cycle or use a natural-language memory
command.

## Install

After the package is published to PyPI, the shortest daily command is mam.
For a one-shot run without cloning this repository, use uvx with the package
selected explicitly:

    uvx --from multi-agent-memory mam init
    uvx --from multi-agent-memory mam status
    uvx --from multi-agent-memory mam context "project decisions"

For repeated use, install the CLI once with uv tool:

    uv tool install multi-agent-memory
    mam init

The longer multi-agent-memory command and the original memoryctl command remain
available as aliases:

    multi-agent-memory status
    memoryctl status

Requires Python 3.11 or newer. For contributors who want to work from source,
the setup uses uv:

    git clone https://github.com/YOUR-USERNAME/multi-agent-memory.git
    cd multi-agent-memory
    uv sync
    uv run mam init

For a global CLI installation from a local checkout:

    uv tool install .
    mam init

## Upgrade

For a persistent installation made with uv tool, upgrade the CLI from PyPI:

    uv tool upgrade multi-agent-memory
    mam --help
    mam status

The package provides the mam, multi-agent-memory, and memoryctl command names;
upgrading the package updates all three entry points together.

If you use the one-shot uvx form, force uv to refresh its cached package:

    uvx --refresh --from multi-agent-memory mam status

Adapter files are separate from the Python package installation. After an
upgrade, synchronize the adapter for the current agent when the release may
contain adapter or protocol changes:

    mam install --agent codex
    mam install --agent pi
    mam install --agent opencode
    mam install --agent claude

Codex and Claude Code hooks are merged and unrelated settings/hooks are
preserved. Pi and OpenCode adapter files managed by this project are backed up
before replacement. Claude Code's managed protocol block in CLAUDE.md is
updated in place while user-authored instructions remain intact. If an
existing Pi or OpenCode file was installed manually or has no project marker,
the command refuses to overwrite it; inspect the file first, then explicitly
use the force option only if replacing it is intended. Restart the affected
agent after updating its adapter.

Upgrading the package does not rewrite the Vault, delete memories, or upload
session data. Run mam rebuild-index only when release notes request an index
rebuild or after manually editing the Vault. If a future release requires a
Vault migration, it will be called out separately in its release notes.

For a local source checkout used by contributors, update the checkout and
reinstall the tool:

    git pull --ff-only
    uv tool install --force .

## Configure the Vault

Create a settings file from the example:

    mkdir -p ~/.config/multi-agent-memory
    cp config.example.yaml ~/.config/multi-agent-memory/settings.yaml

Then edit vault to your Obsidian Vault path and pass it explicitly:

    mam --config ~/.config/multi-agent-memory/settings.yaml init

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

    mam session-summary --text "## Outcome ..."
    mam propose --type preferences --text "Use Chinese and lead with the conclusion."
    mam search "deployment" --include-candidates
    mam confirm PENDING_MEMORY_ID
    mam forget MEMORY_ID
    mam context "project decisions"

## Project-level memory

Project memories use --type project and a project name. When run inside a
Git checkout, memoryctl propose --type project detects the nearest
directory containing .git and records its name. You can always override it:

    mam propose --type project --project my-app \
      --text "Batch jobs must report resolved and unresolved items."

Global memories have scope: global; project memories have scope: project
and a project field. memoryctl context includes global memories plus
memories matching the current project.

## Agent adapters

See adapters/README.md for installation details.

For a user-facing natural-language setup flow, copy
docs/agent-install-prompt.md and send it to the agent CLI. It instructs the
agent to install with uv, preserve existing configuration, select the current
adapter, initialize the Vault, and verify the result.

- Codex: merge adapters/codex/hooks.example.json into your hooks file.
- Pi: copy adapters/pi/agent-memory.js into the extensions directory.
- OpenCode: copy adapters/opencode/agent-memory.js into the plugins directory.

After installing the published package, adapter installation is also available
without a checkout:

    mam install

With no options, mam install opens an interactive multi-select menu. Use
Up/Down to move, Space to select, and Enter to confirm. The menu includes
Codex, Pi, OpenCode, Claude Code, and all.

For scripts, CI, or agent instructions, use explicit options:

    mam install --agent codex
    mam install --agent pi --agent claude
    mam install --all

The previous command remains available as a compatibility alias:

    mam install-agent --agent claude

The supported dedicated adapters are Codex, Pi, OpenCode, and Claude Code.
Hermes and OpenClaw are intentionally not included in this release.

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

Then save it with mam session-summary --file summary.md or let an
adapter consume the file named by AGENT_MEMORY_SUMMARY_FILE.

## Safety and deletion

Never commit your Vault, SQLite index, transcript, credentials, or agent
configuration containing secrets. See docs/privacy.md.

mam forget ID marks a note deprecated, so it is excluded from recall
while remaining auditable. For permanent deletion, remove the Markdown file
manually and run mam rebuild-index; also review your backups and sync
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
