const CLI = "memoryctl"

export default function agentMemory(pi) {
  pi.on("session_start", async (event, ctx) => {
    if (!["startup", "resume", "new"].includes(event.reason)) return
    await ctx.exec(CLI, ["recover"], { cwd: ctx.cwd, timeout: 3000 })
  })

  pi.on("before_agent_start", async (event, ctx) => {
    const result = await ctx.exec(CLI, ["context"], { cwd: ctx.cwd, timeout: 3000 })
    if (result.code !== 0 || !result.stdout.trim()) return
    return { systemPrompt: event.systemPrompt + "\n\n" + result.stdout.trim() }
  })

  pi.on("session_shutdown", async (_event, ctx) => {
    const sessionId = "pi-" + process.pid + "-" + Date.now()
    const summaryFile = process.env.AGENT_MEMORY_SUMMARY_FILE || ""
    await ctx.exec(CLI, ["pending", "--session-id", sessionId, "--summary-file", summaryFile], { cwd: ctx.cwd, timeout: 3000 })
  })
}
