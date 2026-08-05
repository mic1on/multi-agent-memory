import { spawn } from "node:child_process"

const CLI = "mam"
const COMMAND_TIMEOUT_MS = 3000

function run(args, cwd) {
  return new Promise((resolve) => {
    let stdout = ""
    let stderr = ""
    let settled = false
    let child

    const finish = (result) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve(result)
    }

    const timer = setTimeout(() => {
      child?.kill("SIGTERM")
      finish({ code: -1, stdout, stderr: "command timed out" })
    }, COMMAND_TIMEOUT_MS)

    try {
      child = spawn(CLI, args, {
        cwd: cwd || process.cwd(),
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"],
      })
    } catch (error) {
      finish({ code: -1, stdout, stderr: String(error) })
      return
    }

    child.stdout.setEncoding("utf8")
    child.stderr.setEncoding("utf8")
    child.stdout.on("data", (chunk) => { stdout += chunk })
    child.stderr.on("data", (chunk) => { stderr += chunk })
    child.once("error", (error) => finish({ code: -1, stdout, stderr: String(error) }))
    child.once("close", (code) => finish({ code: code ?? -1, stdout, stderr }))
  })
}

export default function agentMemory(pi) {
  pi.on("session_start", async (event, ctx) => {
    if (!["startup", "resume", "new"].includes(event.reason)) return
    await run(["recover"], ctx.cwd)
  })

  pi.on("before_agent_start", async (event, ctx) => {
    const result = await run(["context"], ctx.cwd)
    if (result.code !== 0 || !result.stdout.trim()) return
    return { systemPrompt: event.systemPrompt + "\n\n" + result.stdout.trim() }
  })

  pi.on("session_shutdown", async (_event, ctx) => {
    const sessionId = "pi-" + process.pid + "-" + Date.now()
    const summaryFile = process.env.AGENT_MEMORY_SUMMARY_FILE || ""
    await run(["pending", "--session-id", sessionId, "--summary-file", summaryFile], ctx.cwd)
  })
}
