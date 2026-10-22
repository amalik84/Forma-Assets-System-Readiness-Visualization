// Sanity checks for the model + graph layout. Usage:
//   npm run test:logic                     (uses public/sample-data.json)
//   node --experimental-strip-types scripts/check-logic.mts ../app/output/latest.json
import { readFileSync } from "node:fs"
import { buildModel } from "../src/lib/model.ts"
import { NODE_H, NODE_W } from "../src/lib/layout.ts"

const file = process.argv[2] ?? new URL("../public/sample-data.json", import.meta.url).pathname
const snap = JSON.parse(readFileSync(file, "utf8"))
const m = buildModel(snap)

let failed = 0
const check = (ok: boolean, msg: string) => { console.log((ok ? "  ok   " : "  FAIL ") + msg); if (!ok) failed++ }

console.log(`systems=${m.sys.length} cols=${JSON.stringify(m.cols)}`)
console.log(`hero=${JSON.stringify(m.hero)}`)
check(m.hero.go + m.hero.cond + m.hero.nogo === m.hero.total, "verdict counts add up")
check(m.sys.every((s) => s.blocking.length + s.warn.length === s.items.length), "blocking + warn = items")
check(m.sys.every((s) => s.items.every((i) => m.cols.includes(i.col))), "every item lands in a gate column")

const L = m.layout
console.log(`graph: ${L.nodes.length} connected, ${L.isolated.length} independent, ${m.feeds.length} links, ${L.width.toFixed(0)}x${L.height.toFixed(0)}, cyclic=${L.cyclic}`)
L.nodes.forEach((n) => console.log(`   layer ${n.layer}  x=${n.x.toFixed(0).padStart(4)} y=${n.y}  ${n.id}`))
const byLayer = new Map<number, typeof L.nodes>()
L.nodes.forEach((n) => byLayer.set(n.layer, [...(byLayer.get(n.layer) ?? []), n]))
let overlap = false
byLayer.forEach((ns) => {
  ns.sort((a, b) => a.x - b.x)
  for (let i = 1; i < ns.length; i++) if (ns[i].x < ns[i - 1].x + ns[i - 1].w) overlap = true
})
check(!overlap, "no two nodes overlap in a layer")
check(L.nodes.every((n) => n.x >= 0 && n.x + n.w <= L.width + 0.5), "all nodes inside the canvas")
const layerOf = new Map(L.nodes.map((n) => [n.id, n.layer]))
check(m.feeds.every(([a, b]) => layerOf.get(a)! < layerOf.get(b)!), "every upstream sits above what it feeds")
check(L.edges.length === m.feeds.length && L.edges.every((e) => e.d.startsWith("M")), "one connector per link")
console.log(`   sample connector: ${L.edges[0]?.d}`)
m.sys.filter((s) => m.flow.get(s.name)!.upBlocked.length).slice(0, 3)
  .forEach((s) => console.log(`   ${s.name} is fed by blocked: ${m.flow.get(s.name)!.upBlocked.join(", ")}`))
void NODE_H; void NODE_W
console.log(failed ? `\n${failed} check(s) failed` : "\nall checks passed")
process.exit(failed ? 1 : 0)
