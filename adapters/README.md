# Agent adapters

All adapters assume that the mam command is installed and available on PATH.
They are intentionally thin:

- startup runs mam recover;
- the agent receives the mam protocol and confirmed context;
- shutdown writes a pending receipt only when AGENT_MEMORY_SUMMARY_FILE
  points to an explicitly created summary file.

The adapters never read arbitrary transcript files, send data to a service, or
promote candidate memories. Copy the relevant files into the agent supported
extension or hooks directory and merge them with existing configuration.
For a published release, install the command once before enabling an adapter:

    uv tool install multi-agent-memory
    mam status

The one-shot uvx --from multi-agent-memory mam ... form is excellent for
manual commands, but a persistent uv tool installation is more reliable for
agent hooks that run repeatedly.

## Codex

Review and merge codex/hooks.example.json into the Codex hooks file. Do not
replace unrelated hooks. A stop hook is inert unless
AGENT_MEMORY_SUMMARY_FILE points to a readable file.

## Pi

Copy pi/agent-memory.js to the Pi extensions directory and restart Pi. Pis
extension API supplies the current working directory to the CLI.

## OpenCode

Copy opencode/agent-memory.js to the OpenCode plugins directory and restart
OpenCode. The plugin caches context per session to avoid repeated index reads.

## Claude Code

Install the Claude Code adapter from the published package:

    mam install --agent claude

This merges SessionStart and Stop hooks into ~/.claude/settings.json and adds a
managed protocol block to ~/.claude/CLAUDE.md. Existing settings and user
instructions are preserved. Restart Claude Code after the adapter changes.

## ZCode

ZCode uses user-level hooks in `~/.zcode/cli/config.json`; project-level Hook
configuration is ignored by ZCode. Install the adapter with:

```bash
mam install --agent zcode
```

The installer preserves unrelated settings, enables `hooks.enabled`, and merges
SessionStart and Stop process hooks under `hooks.events`. Start a new ZCode
session after installation because ZCode snapshots Hook configuration per
session.

The package does not currently provide Hermes or OpenClaw adapters.
