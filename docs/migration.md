# Migration from the original local prototype

The public package keeps the same Markdown layer names and front matter fields
as the original prototype:

    00-profile/     confirmed global preferences
    10-projects/    project-scoped memories
    20-decisions/   confirmed decisions
    30-learnings/   reusable lessons
    90-sessions/    session summaries
    inbox/          unconfirmed candidates
    .memory/pending crash-recovery receipts

Point vault or AGENT_MEMORY_VAULT at the existing Vault. The first init or
rebuild-index recreates the disposable SQLite index from Markdown. Do not copy
the old SQLite database into a public Git repository.

Existing integrations using underscore options continue to work for
source_session and session_id; new documentation uses source-session and
session-id.

The public adapters intentionally use memoryctl from PATH. Remove local
absolute paths from old copies and merge the example hooks with existing agent
configuration instead of replacing it.
