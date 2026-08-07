import { spawn } from "node:child_process"

const CLI = "mam"

function run(args, cwd) {
  return new Promise((resolve) => {
    const child = spawn(CLI, args, { cwd: cwd || process.cwd(), env: process.env, stdio: ["ignore", "pipe", "ignore"] })
    let output = ""
    const timer = setTimeout(() => { child.kill("SIGTERM"); resolve("") }, 3000)
    child.stdout.setEncoding("utf8")
    child.stdout.on("data", (chunk) => { output += chunk })
    child.on("error", () => { clearTimeout(timer); resolve("") })
    child.on("close", (code) => { clearTimeout(timer); resolve(code === 0 ? output.trim() : "") })
  })
}

export const AgentMemoryPlugin = async ({ directory }) => {
  const cache = new Map()
  const sessionIds = new Set()
  const protocol = await run(["protocol"], directory)
  await run(["recover"], directory)
  return {
    dispose: async () => {
      await Promise.all([...sessionIds].map((sessionId) =>
        run(["pending", "--session-id", sessionId, "--summary-file", process.env.AGENT_MEMORY_SUMMARY_FILE || ""], directory),
      ))
    },
    "experimental.chat.system.transform": async (input, output) => {
      const key = input.sessionID || "__global__"
      if (key !== "__global__") sessionIds.add(key)
      let context = cache.get(key)
      if (context === undefined) {
        context = await run(["context"], directory)
        cache.set(key, context)
      }
      if (protocol) output.system.push(protocol)
      if (context) output.system.push(context)
    },
  }
}
