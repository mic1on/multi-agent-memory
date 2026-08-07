# Natural-language installation prompt

Copy the prompt below and send it to Codex, Pi, OpenCode, Claude Code, or another agent CLI.
The agent should execute the installation locally and report each completed step.

```text
Install multi-agent-memory for me as a shared local memory layer.

Requirements:
1. Detect which agent CLI you are running: Codex, Pi, OpenCode, Claude Code, or another client.
2. Do not clone a repository. Install the published package with uv tool install multi-agent-memory.
   If uv is unavailable, explain that and stop before changing files. Do not silently install
   system-wide packages with sudo.
3. Verify that mam --help and mam status work.
4. Use the existing AGENT_MEMORY_VAULT environment variable when it is set. Otherwise use
   the default local Obsidian-compatible Vault path and show me the path before initialization.
5. Run mam init. Do not read, upload, or print the contents of existing Vault notes.
6. After identifying the current agent, install only its adapter: use
   mam install --agent codex, --agent pi, --agent opencode, or --agent claude.
   If you cannot identify the host agent, ask me whether to install codex, pi,
   opencode, claude, or all.
7. Preserve unrelated configuration. Do not overwrite existing Codex hooks, Claude Code
   settings, Pi extensions, OpenCode plugins, or Claude Code instructions. For Claude Code,
   merge settings.json and add/update only the marked block in CLAUDE.md. If a target file is
   unmanaged or ambiguous, stop and report it.
8. Print mam status after installation and explain where the adapter was installed.
9. Print mam protocol and add its content to your agent instructions only if the host agent
   supports a user-level instruction file. Do not modify project files without my approval.

Privacy rules:
- Never store passwords, API keys, cookies, private keys, or complete transcripts.
- Never send Vault data or session data to a remote service.
- Do not activate a candidate memory without my explicit confirmation.
- Do not delete existing files. Backups and changes must be reported.

After installation, explain how I can use these natural-language commands:
- 帮我总结这轮记忆
- 记住：...
- 确认刚才那条记忆
- 忘掉关于...
- 回忆关于...
```

## Short version

For agents that already understand the project, this shorter request is enough:

```text
帮我安装并配置 multi-agent-memory：使用 uv tool install，不要 clone；
自动识别当前是 Codex、Pi、OpenCode 还是 Claude Code，安装对应适配器；保留现有配置，
不要读取或上传完整会话；运行 mam init 和 mam status 验证；最后告诉我安装位置
和如何用自然语言总结、记住、确认、忘掉、回忆记忆。
```

## What the agent should run

The expected command sequence is:

    uv tool install multi-agent-memory
    mam --help
    mam init
    mam install --agent CURRENT_AGENT
    mam status
    mam protocol

The explicit agent value is codex, pi, opencode, or all. The installation command
refuses to overwrite unmanaged adapter files. The auto value is available as a deliberate
all-adapters fallback for hosts that cannot identify themselves; an agent should prefer its
own explicit value.
## Natural-language upgrade prompt

Users can later send this to the same agent:

```text
帮我升级 multi-agent-memory。

请按以下要求执行：
1. 如果是 uv tool 安装，执行 uv tool upgrade multi-agent-memory；如果只是一次性 uvx，
   使用 uvx --refresh --from multi-agent-memory mam status 验证最新版。
2. 不要 clone 仓库，不要使用 sudo，不要删除 Vault 或任何记忆文件。
3. 先执行 mam status，再升级；升级后再次执行 mam status。
4. 升级后，适配器会在下一次 Agent 启动时自动同步。先运行 mam status；如果报告
   conflict 或 error，不要使用 --force，先报告并等待我的决定。
5. 保留现有配置。Claude Code 只合并 settings.json 并更新 CLAUDE.md 中的托管区块；
   只有安装新 Agent 时才执行 mam install --agent codex|pi|opencode|claude。
6. 不要读取、上传或保存完整会话；不要自动确认候选记忆。
7. 告诉我升级前后的状态、使用的命令、适配器是否更新，以及是否需要重启 Agent。
```
