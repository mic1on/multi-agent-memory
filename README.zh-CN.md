# multi-agent-memory

面向 Codex、Pi、OpenCode、Claude Code 及其他 Agent CLI 的本地优先共享长期记忆。

多个 Agent 共用同一个人类可读的 Markdown Vault。你可以用 Obsidian 打开 Vault，
审查待确认记忆，并让全局偏好、项目决策和可复用经验在不同 Agent 之间保持一致。

## 功能概览

- 使用 Obsidian 兼容的 Markdown Vault；
- 使用 SQLite FTS5 作为可重建的本地搜索缓存；
- 启动时召回已确认的全局记忆和项目级记忆；
- 新记忆先进入候选区，必须经过用户确认才会生效；
- 保存简短的会话总结和崩溃恢复摘要；
- 提供 Codex、Pi、OpenCode、Claude Code 四个专用适配器；
- 不依赖网络服务，不上传记忆，不包含托管式记忆后端。

重要边界：适配器可以自动召回已有记忆，但不会静默读取和总结完整 transcript。
需要长期保存时，请让 Agent 总结一个有意义的工作周期，或直接使用自然语言记忆命令。

## 安装

要求 Python 3.11+。推荐使用 uv。发布到 PyPI 后，日常使用可以直接运行：

    uvx --from multi-agent-memory mam init
    uvx --from multi-agent-memory mam status
    uvx --from multi-agent-memory mam context "项目决策"

长期使用时安装一次：

    uv tool install multi-agent-memory
    mam init

### 让 Agent 帮你安装

不想自己执行命令时，把下面这段话直接发给当前的 Codex、Pi、OpenCode 或 Claude Code：

```text
帮我安装并配置 multi-agent-memory。

请按以下要求执行：
1. 使用 uv tool install multi-agent-memory，不要 git clone，不要使用 sudo。
2. 识别当前是 Codex、Pi、OpenCode 还是 Claude Code，只安装当前 Agent 的适配器。
3. 使用 mam init 初始化本地 Vault；如果设置了 AGENT_MEMORY_VAULT 就使用它，
   否则先告诉我将使用的 Vault 路径，再初始化。
4. 使用 mam install --agent codex|pi|opencode|claude 安装对应适配器。
5. 保留已有配置：合并 Codex/Claude Code 的 settings/hooks，保留 Pi/OpenCode 已有文件；
   遇到不明确或非本项目管理的文件时先停止并报告，不要使用 --force。
6. 不要读取、上传或保存完整会话，不要保存密码、token、Cookie 或私钥。
7. 执行 mam status 验证，并告诉我安装位置和是否需要重启 Agent。
8. 将 mam protocol 的规则加入当前 Agent 的用户级指令（如果支持），不要修改项目文件。
9. 最后告诉我如何使用这些自然语言命令：
   帮我总结这轮记忆；记住：...；确认刚才那条记忆；忘掉关于...；回忆关于...。
```

完整版本见 [docs/agent-install-prompt.md](docs/agent-install-prompt.md)。

## 升级

使用 uv tool 安装的用户：

    uv tool upgrade multi-agent-memory
    mam status

如果使用一次性 uvx：

    uvx --refresh --from multi-agent-memory mam status

如果版本包含适配器或协议更新，同步当前 Agent：

    mam install --agent codex
    mam install --agent pi
    mam install --agent opencode
    mam install --agent claude

升级不会重写 Vault、删除记忆或上传会话数据。Codex 和 Claude Code 的 hooks 会合并；
Pi、OpenCode 以及由本项目管理的指令文件更新前会备份。

## 配置共享 Vault

可以复制示例配置：

    mkdir -p ~/.config/multi-agent-memory
    cp config.example.yaml ~/.config/multi-agent-memory/settings.yaml

编辑 settings.yaml 中的 vault，或使用环境变量：

    export AGENT_MEMORY_VAULT="$HOME/Documents/Obsidian/AgentMemory"
    export AGENT_MEMORY_STATE_DIR="$HOME/.local/share/multi-agent-memory"

初始化并查看状态：

    mam init
    mam status

默认目录结构：

    00-profile/     已确认的全局偏好
    10-projects/    项目级记忆
    20-decisions/  已确认的决策
    30-learnings/  可复用经验
    90-sessions/   会话总结
    inbox/         待确认候选记忆
    .memory/pending 崩溃恢复摘要

Markdown 是权威数据源。你可以直接在 Obsidian 中编辑 Markdown；下一次 search、recall
或 context 会从 Markdown 重建 SQLite 索引。

## 基本使用

### 候选记忆

写入一条候选偏好：

    mam propose --type preferences --text "使用中文沟通，回答先给结论。"

搜索候选：

    mam search "中文" --include-candidates

确认候选：

    mam confirm MEMORY_ID

遗忘一条记忆：

    mam forget MEMORY_ID

forget 只会将记忆标记为 deprecated，使其不再召回，同时保留审计记录。

### 项目级记忆

在 Git 项目目录中运行：

    mam propose --type project --text "批处理必须汇报已解决、未解决、原因和日志。"

CLI 会寻找最近的 .git 目录并记录项目名。也可以显式指定：

    mam propose --type project --project my-app --text "数据库迁移必须提供回滚方案。"

context 会组合全局记忆和当前项目匹配的记忆。

### 会话总结

让 Agent 生成以下结构的简短摘要：

    ## Outcome
    ## Decisions
    ## Reusable learnings
    ## Open questions
    ## Next action

然后保存：

    mam session-summary --file summary.md

也可以直接说：

    帮我总结这轮记忆

### 自然语言记忆命令

接入适配器并加载协议后，可以直接对任意 Agent 说：

- 帮我总结这轮记忆 / 总结这轮：生成简短总结并保存；
- 记住：...：写入候选记忆，不自动激活；
- 确认刚才那条记忆：确认唯一的候选记忆；
- 忘掉关于...：搜索并废弃对应记忆；
- 回忆关于...：查询共享上下文。

当前用户指令永远优先于记忆内容。

## Agent 适配器

安装全部已支持适配器：

    mam install --all

交互式选择安装：

    mam install

菜单中可用 ↑/↓ 移动、空格勾选、回车确认。

脚本化安装单个或多个：

    mam install --agent claude
    mam install --agent pi --agent claude

旧命令仍可用：

    mam install-agent --agent claude

当前专用适配器：

- Codex：合并用户级 hooks；
- Pi：安装扩展；
- OpenCode：安装插件；
- Claude Code：合并 ~/.claude/settings.json，并更新 ~/.claude/CLAUDE.md 的托管区块。

Hermes 和 OpenClaw 暂不包含在本版本中。

## 隐私与删除

这是本地优先工具，没有网络客户端，不会把记忆发送给项目维护者。
不要保存密码、API key、Cookie、私钥、无关个人信息或完整 transcript。
Vault 和 SQLite 索引不要提交到 Git。

mam forget MEMORY_ID 会保留审计记录。若要永久删除，手动删除 Vault 中对应 Markdown，
然后执行：

    mam rebuild-index

同时检查备份和 Obsidian 同步历史。

## 开发与支持范围

开发环境：

    uv sync
    uv run pytest
    python -m compileall src

项目要求 Python 3.11+，使用 uv 管理依赖，配置优先 YAML/Dynaconf。

## 发布到 PyPI

GitHub Actions 会在 Pull Request 和 push 时运行测试矩阵并构建 wheel/sdist。
只有推送匹配 v* 的 tag 时才会进入 PyPI 发布流程；workflow 会先检查 tag
版本是否与 pyproject.toml 中的版本一致。

发布使用 PyPI Trusted Publishing 和 GitHub OIDC，不在仓库中保存 PyPI token。
首次发布前，需要在 PyPI 中为项目 multi-agent-memory 配置 Trusted Publisher：

- Owner：mic1on
- Repository：multi-agent-memory
- Workflow：release.yml
- Environment：pypi

同时在 GitHub 仓库设置中创建同名的 pypi environment。之后修改
pyproject.toml 的 version，提交并推送对应 tag：

    git tag v0.1.1
    git push origin main v0.1.1

tag workflow 会运行测试、构建发行包、检查 tag/版本一致性，然后发布到 PyPI。
不要重复使用已经发布过的 tag 或版本号。

MIT License，详见 [LICENSE](LICENSE)。

英文文档：[README.md](README.md)；安装提示词：[docs/agent-install-prompt.md](docs/agent-install-prompt.md)。
