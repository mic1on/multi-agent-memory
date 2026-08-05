# multi-agent-memory

面向 Codex、Pi、OpenCode、Claude Code 及其他 Agent CLI 的本地优先共享长期记忆。

所有 Agent 共用同一个人类可读的 Markdown Vault，保存全局偏好、项目决策和可复用经验。SQLite 只作为可重建的本地搜索缓存。项目没有托管服务、遥测，也不会自动上传数据。

英文文档：[README.md](README.md)

## 安装

要求 Python 3.11+，推荐使用 [uv](https://docs.astral.sh/uv/)：

~~~bash
uv tool install multi-agent-memory
mam init
mam status
~~~

临时执行命令可以使用：

~~~bash
uvx --from multi-agent-memory mam status
~~~

### 安装 Agent 适配器

可以安装单个适配器、全部适配器，或进入交互式选择：

~~~bash
mam install --agent pi
mam install --all
mam install
~~~

也可以直接对当前 Agent 说：

> 请为当前 Agent 安装并配置 multi-agent-memory。使用 uv tool install multi-agent-memory，保留已有配置，执行 mam init，使用 mam install --agent ... 只安装当前 Agent 的适配器，最后执行 mam status 并告诉我是否需要重启。不要使用 sudo，不要覆盖非本项目管理的文件，不要读取或上传完整会话、凭据、Token、Cookie 或私钥。

当前支持的适配器：

| Agent | 安装命令 |
| --- | --- |
| Codex | mam install --agent codex |
| Pi | mam install --agent pi |
| OpenCode | mam install --agent opencode |
| Claude Code | mam install --agent claude |

安装或升级适配器后请重启 Agent。Hermes 和 OpenClaw 暂不支持。

## 日常使用

接入适配器后，可以直接对 Agent 说：

~~~text
帮我总结这轮记忆
记住：使用中文沟通，回答先给结论
确认刚才那条记忆
忘掉关于部署方式的记忆
回忆关于这个项目的决策
~~~

也可以直接使用 CLI：

~~~bash
mam context
mam propose --type preferences --text "使用中文沟通，回答先给结论。"
mam search "部署" --include-candidates
mam confirm MEMORY_ID
mam forget MEMORY_ID
~~~

新记忆会先进入候选区，确认后才会参与召回。mam forget 会将记忆标记为 deprecated，保留审计记录但不再召回。

## 全局记忆与项目记忆

全局记忆处处生效；项目记忆会在 Agent 位于对应 Git 项目中时生效：

~~~bash
mam propose --type project \
  --text "批处理必须汇报已解决、未解决和原因。"

mam propose --type project --project my-app \
  --text "数据库迁移必须提供回滚方案。"
~~~

mam context 会组合全局记忆和当前项目匹配的记忆。

## Vault 与隐私

Markdown Vault 是权威数据源，可以直接用 Obsidian 打开。可以通过环境变量指定位置：

~~~bash
export AGENT_MEMORY_VAULT="$HOME/Documents/Obsidian/AgentMemory"
export AGENT_MEMORY_STATE_DIR="$HOME/.local/share/multi-agent-memory"
mam init
~~~

适配器会自动召回已确认记忆，但不会静默读取和总结任意 transcript。需要保存工作周期时，请让 Agent 总结，或提供摘要文件：

~~~bash
mam session-summary --file summary.md
~~~

不要保存或提交凭据、API Key、Cookie、私钥、完整会话、Vault 或 SQLite 索引。若要永久删除记忆，删除对应 Markdown 后重建索引：

~~~bash
mam rebuild-index
~~~

## 升级

~~~bash
uv tool upgrade multi-agent-memory
mam install --all
mam status
~~~

如果工具是精确版本安装的，使用：

~~~bash
uv tool install --force multi-agent-memory@latest
~~~

升级不会删除 Vault 或记忆。替换项目管理的适配器文件时会自动备份，并保留无关配置。

## 开发

~~~bash
uv sync
uv run pytest
python -m compileall src
node --check adapters/pi/agent-memory.js
node --check adapters/opencode/agent-memory.js
~~~

MIT License，详见 [LICENSE](LICENSE)。
