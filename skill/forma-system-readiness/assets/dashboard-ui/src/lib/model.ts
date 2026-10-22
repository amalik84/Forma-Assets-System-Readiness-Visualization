// Turns the raw snapshot into what the UI shows: verdict per system, gate matrix, topology roll-up.
// Pure TS (no React) so it can be tested with `npm run test:logic`.
import type { Asset, Ref, Snapshot } from "../types.ts"
import { layoutGraph } from "./layout.ts"
import type { Layout } from "./layout.ts"

export type Verdict = "go" | "cond" | "nogo"

export interface Item {
  r: Ref
  col: string
  assets: { a: Asset; path: string[] }[]
}

export interface Sys {
  name: string
  assetCount: number
  readyCount: number
  assets: Asset[]
  items: Item[]
  blocking: Item[]
  warn: Item[]
  verdict: Verdict
}

export interface Flow {
  up: string[] // every system that must be ready before this one (transitive)
  down: string[] // every system that depends on this one (transitive)
  upBlocked: string[] // upstream systems currently NO-GO
  downBlocking: number // distinct blocking items anywhere downstream
  downWarn: number
  downWorst: Verdict
}

export interface Model {
  sys: Sys[]
  byName: Map<string, Sys>
  cols: string[]
  today: Date
  hero: { go: number; cond: number; nogo: number; total: number; blockers: number; overdue: number; allGo: boolean }
  flow: Map<string, Flow>
  layout: Layout
  feeds: [string, string][]
}

export const VERDICT_RANK: Record<Verdict, number> = { nogo: 0, cond: 1, go: 2 }
export const VERDICT_LABEL: Record<Verdict, string> = { go: "GO", cond: "CONDITIONAL", nogo: "NO-GO" }

export function parseDate(v?: string | null): Date | null {
  if (!v) return null
  const d = new Date(String(v).slice(0, 10) + "T00:00:00")
  return Number.isNaN(d.getTime()) ? null : d
}

export function isOverdue(r: Ref, today: Date): boolean {
  const d = parseDate(r.due)
  return r.kind === "issue" && r.state === "blocking" && !!d && d < today
}

export const itemKey = (r: Ref) => `${r.kind}|${r.id}`

function colOf(r: Ref): string {
  if (r.kind === "form") return "Forms"
  if (r.kind === "status") return "Status rule"
  return r.type ? String(r.type).split(" / ")[0] : "Issues"
}

export function sortSys(a: Sys, b: Sys): number {
  return VERDICT_RANK[a.verdict] - VERDICT_RANK[b.verdict] || b.blocking.length - a.blocking.length || a.name.localeCompare(b.name)
}

export function buildModel(snap: Snapshot): Model {
  const today = new Date(snap.meta.generatedAt.slice(0, 10) + "T00:00:00")

  const sys: Sys[] = snap.systems.map((s) => {
    const assets = s.assetIds.map((i) => snap.assets[i]).filter(Boolean)
    const map = new Map<string, Item>()
    for (const a of assets) {
      for (const r of a.refs) {
        if (r.state === "ok") continue
        const k = itemKey(r)
        let it = map.get(k)
        if (!it) { it = { r, col: "", assets: [] }; map.set(k, it) }
        it.assets.push({ a, path: r.path })
      }
    }
    const items = [...map.values()]
    const blocking = items.filter((i) => i.r.state === "blocking")
    const warn = items.filter((i) => i.r.state !== "blocking")
    return {
      name: s.name, assetCount: s.assetCount, readyCount: s.readyCount, assets, items, blocking, warn,
      verdict: blocking.length ? "nogo" : warn.length ? "cond" : "go",
    } as Sys
  })

  // gate columns: the 5 most common issue types, "Other issues", Forms, Status rule
  const typeCount = new Map<string, number>()
  sys.forEach((s) => s.items.forEach((i) => {
    if (i.r.kind === "issue") typeCount.set(colOf(i.r), (typeCount.get(colOf(i.r)) ?? 0) + 1)
  }))
  const topTypes = [...typeCount.entries()].sort((a, b) => b[1] - a[1]).map((e) => e[0])
  const issueCols = topTypes.slice(0, 5)
  const cols = [...issueCols]
  if (topTypes.length > 5) cols.push("Other issues")
  if (sys.some((s) => s.items.some((i) => i.r.kind === "form"))) cols.push("Forms")
  if (sys.some((s) => s.items.some((i) => i.r.kind === "status"))) cols.push("Status rule")
  if (!cols.length) cols.push("Issues", "Forms")
  sys.forEach((s) => s.items.forEach((i) => {
    const c = colOf(i.r)
    i.col = i.r.kind === "issue" && !issueCols.includes(c) ? "Other issues" : c
  }))

  const byName = new Map(sys.map((s) => [s.name, s]))

  // hero numbers
  const n = { go: 0, cond: 0, nogo: 0 }
  sys.forEach((s) => { n[s.verdict]++ })
  const uniq = new Map<string, Item>()
  sys.forEach((s) => s.blocking.forEach((i) => uniq.set(itemKey(i.r), i)))
  const overdue = [...uniq.values()].filter((i) => isOverdue(i.r, today)).length
  const hero = { ...n, total: sys.length, blockers: uniq.size, overdue, allGo: sys.length > 0 && n.nogo === 0 }

  // topology: transitive up/down sets and roll-up
  const feeds = (snap.topology?.feeds ?? []).filter(([a, b]) => byName.has(a) && byName.has(b))
  const outs = new Map<string, string[]>(), ins = new Map<string, string[]>()
  sys.forEach((s) => { outs.set(s.name, []); ins.set(s.name, []) })
  feeds.forEach(([a, b]) => { outs.get(a)!.push(b); ins.get(b)!.push(a) })
  const reach = (start: string, adj: Map<string, string[]>) => {
    const seen = new Set<string>(), stack = [...(adj.get(start) ?? [])]
    while (stack.length) {
      const x = stack.pop()!
      if (seen.has(x) || x === start) continue
      seen.add(x)
      stack.push(...(adj.get(x) ?? []))
    }
    return [...seen]
  }
  const flow = new Map<string, Flow>()
  sys.forEach((s) => {
    const up = reach(s.name, ins), down = reach(s.name, outs)
    const keysB = new Set<string>(), keysW = new Set<string>()
    down.forEach((d) => {
      byName.get(d)!.blocking.forEach((i) => keysB.add(itemKey(i.r)))
      byName.get(d)!.warn.forEach((i) => keysW.add(itemKey(i.r)))
    })
    const worst: Verdict = down.some((d) => byName.get(d)!.verdict === "nogo") ? "nogo" : down.some((d) => byName.get(d)!.verdict === "cond") ? "cond" : "go"
    flow.set(s.name, {
      up, down, upBlocked: up.filter((u) => byName.get(u)!.verdict === "nogo"),
      downBlocking: keysB.size, downWarn: keysW.size, downWorst: worst,
    })
  })

  const layout = layoutGraph(sys.map((s) => s.name), feeds)
  return { sys, byName, cols, today, hero, flow, layout, feeds }
}
