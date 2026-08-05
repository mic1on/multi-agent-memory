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
  await run(["recover"], directory)
  return {
    "experimental.chat.system.transform": async (input, output) => {
      const key = input.sessionID || "__global__"
      let context = cache.get(key)
      if (context === undefined) {
        context = await run(["context"], directory)
        cache.set(key, context)
      }
      if (context) output.system.push(context)
    },
  }
}
