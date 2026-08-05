# Privacy and data boundaries

Multi-Agent Memory is local-first. The CLI writes only to the Vault and state
directory configured by the user. It has no network client and does not send
memory data to the project maintainers.

The Markdown Vault is authoritative and may contain private information. Keep
it outside Git, back it up securely, and do not put it inside this repository.
The SQLite file is a disposable index and should also stay outside Git.

Do not save passwords, API keys, cookies, private keys, personal identifiers
that are not needed, or complete agent transcripts. Prefer a short statement
of a reusable preference, decision, or lesson. Candidates are inert until
explicitly confirmed.

To remove a memory from recall while keeping an audit trail, run:

    memoryctl forget MEMORY_ID

To permanently remove data, delete the corresponding Markdown file from the
Vault and rebuild the index. This is an intentional manual operation because
the project cannot know which backups or Obsidian sync copies exist.

