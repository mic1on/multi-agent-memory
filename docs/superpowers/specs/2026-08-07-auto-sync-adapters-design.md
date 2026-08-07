# Automatic Agent Adapter Synchronization

## Problem

`uv tool upgrade multi-agent-memory` updates the `mam` executable but does not
reinstall the prompt, hooks, or plugins already copied into an agent's home
configuration. Users should not need to remember a second `mam install` step.

## Design

`mam recover` is the synchronization trigger. All supported adapters already
invoke `mam recover` during startup, so an existing adapter installation can
bootstrap synchronization after the Python package itself is upgraded.

Successful explicit installs record managed agents in a JSON manifest under
`Settings.state_dir`. Each record stores the installed package version and a
fingerprint of the packaged adapter assets. On `recover`, all manifest-managed
agents are synchronized when the fingerprint changes. The operation is local,
idempotent, serialized with the existing state lock, and does not write to the
Vault.

When no manifest exists, the installer performs conservative legacy detection:
the Pi and OpenCode managed-file marker, the Claude managed instruction block
and hooks, or the complete Codex mam hook signature must be present before an
agent is adopted. Ambiguous or unmanaged targets are left untouched.

## Safety and Failure Handling

- Dedicated managed Pi/OpenCode files are backed up before replacement.
- JSON hooks preserve unrelated fields and hooks; only mam-owned commands are
  merged or updated.
- Claude updates only the marked `CLAUDE.md` block.
- Malformed or ambiguous targets produce a recorded conflict/error and are not
  overwritten. `recover` still completes its existing summary recovery.
- Automatic synchronization is enabled by default and can be disabled with
  `AGENT_MEMORY_AUTO_SYNC_ADAPTERS=false` or the equivalent configuration.
- Synchronization output never enters `context` or `protocol` stdout.
- `mam status` reports adapter synchronization state.

## Testing

Tests cover manifest creation, fingerprint-based upgrades, legacy bootstrap,
preservation of unrelated configuration, conflict handling, disabled auto-sync,
idempotency, status reporting, and clean `recover`/`context`/`protocol` output.
