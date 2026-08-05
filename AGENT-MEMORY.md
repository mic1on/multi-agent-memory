# Shared agent memory protocol

This protocol is designed to be installed into Codex, Pi, and OpenCode. The
installed memoryctl command is the only writer. Markdown in the configured
Vault is authoritative; SQLite is only a rebuildable search cache.

At session start, recall relevant confirmed memories. The current user
instruction always wins. At a meaningful boundary, save a concise summary or
propose only a reusable fact for review. Never store secrets, credentials,
private keys, cookies, or complete transcripts. Candidate memories remain inert
until the user explicitly confirms them.

## Natural-language commands

Treat these as first-class instructions; the user should not need a terminal:

- 帮我总结这轮记忆 / 总结这轮: produce a short summary and call
  memoryctl session-summary --text ... .
- 记住：...: call memoryctl propose --text ...; report the candidate ID.
- 确认刚才那条记忆: identify exactly one pending candidate, then call
  memoryctl confirm <id>.
- 忘掉关于...: identify the intended active memory, then call
  memoryctl forget <id>.
- 回忆关于...: call memoryctl context "..." and apply its output.

Never claim that a memory was saved, confirmed, or forgotten until the command
succeeds. Project-scoped memories should include --type project; the CLI
auto-detects the nearest directory containing .git when possible.

## Boundary summary format

Keep summaries concise:

    ## Outcome
    ## Decisions
    ## Reusable learnings
    ## Open questions
    ## Next action

