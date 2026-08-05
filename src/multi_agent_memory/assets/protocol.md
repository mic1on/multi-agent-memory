# Multi-Agent Memory Protocol

Use the local mam command for shared memory across agent clients. When this
adapter is installed, prefer mam for memories intended to be shared across
agents. Other memory tools may coexist; do not disable or prohibit them, and
always follow an explicit user instruction about which memory system to use.

The current user instruction always wins. At session start, use mam context to
recall confirmed memories. When the user says 帮我总结这轮记忆 or 总结这轮,
produce a concise summary and run mam session-summary --text. When the user
says 记住：..., 写入记忆, 写入偏好记忆, 保存这个偏好, or equivalent wording,
run mam propose --type preferences --text ...; candidates remain inactive until
the user confirms them. Use the agent's command tool to run these mam commands
and report the command result. When the user says 确认刚才那条记忆, find exactly one
candidate and run mam confirm ID. When the user says 忘掉关于..., find the
intended active memory and run mam forget ID. When the user says 回忆关于...,
run mam context "..." and use its output. Project-specific memories use
mam propose --type project.

Never save passwords, tokens, cookies, private keys, or complete transcripts.
Never claim a memory operation succeeded until the command succeeds. Project
memories must be proposed with mam propose --type project.
