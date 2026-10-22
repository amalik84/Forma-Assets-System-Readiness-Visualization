// Layered (top to bottom) graph layout with orthogonal, rounded connectors. Pure TS, no dependencies.
// Upstream systems sit above the systems they feed. Long edges get invisible waypoints so lines never cross nodes.

export const NODE_W = 188
export const NODE_H = 66
export const GAP_X = 24
export const GAP_Y = 72
const DUMMY_W = 16
const R = 8 // corner radius

export interface LNode { id: string; x: number; y: number; w: number; layer: number }
export interface LEdge { from: string; to: string; d: string }
export interface Layout {
  nodes: LNode[]
  edges: LEdge[]
  width: number
  height: number
  isolated: string[]
  cyclic: boolean
}

interface WorkNode { id: string; layer: number; dummy: boolean; w: number; cx: number }

function roundedPath(pts: [number, number][]): string {
  if (pts.length < 2) return ""
  let d = `M${pts[0][0]},${pts[0][1]}`
  for (let i = 1; i < pts.length - 1; i++) {
    const [px, py] = pts[i - 1]
    const [cx, cy] = pts[i]
    const [nx, ny] = pts[i + 1]
    const l1 = Math.hypot(cx - px, cy - py)
    const l2 = Math.hypot(nx - cx, ny - cy)
    const r = Math.min(R, l1 / 2, l2 / 2)
    if (r < 0.5) { d += ` L${cx},${cy}`; continue }
    const ax = cx - ((cx - px) / l1) * r, ay = cy - ((cy - py) / l1) * r
    const bx = cx + ((nx - cx) / l2) * r, by = cy + ((ny - cy) / l2) * r
    d += ` L${ax.toFixed(1)},${ay.toFixed(1)} Q${cx},${cy} ${bx.toFixed(1)},${by.toFixed(1)}`
  }
  const last = pts[pts.length - 1]
  return d + ` L${last[0]},${last[1]}`
}

export function layoutGraph(allIds: string[], feeds: [string, string][]): Layout {
  const inGraph = new Set<string>()
  feeds.forEach(([a, b]) => { inGraph.add(a); inGraph.add(b) })
  const ids = allIds.filter((i) => inGraph.has(i))
  const isolated = allIds.filter((i) => !inGraph.has(i))
  if (!ids.length) return { nodes: [], edges: [], width: 0, height: 0, isolated, cyclic: false }

  // --- 1. layers by longest path from sources (Kahn); anything left over is in a cycle
  const out = new Map<string, string[]>(), indeg = new Map<string, number>()
  ids.forEach((i) => { out.set(i, []); indeg.set(i, 0) })
  feeds.forEach(([a, b]) => { out.get(a)!.push(b); indeg.set(b, indeg.get(b)! + 1) })
  const layer = new Map<string, number>()
  const queue = ids.filter((i) => indeg.get(i) === 0)
  queue.forEach((i) => layer.set(i, 0))
  const deg = new Map(indeg)
  for (let qi = 0; qi < queue.length; qi++) {
    const u = queue[qi]
    for (const v of out.get(u)!) {
      layer.set(v, Math.max(layer.get(v) ?? 0, layer.get(u)! + 1))
      deg.set(v, deg.get(v)! - 1)
      if (deg.get(v) === 0) queue.push(v)
    }
  }
  const cyclic = queue.length < ids.length
  if (cyclic) {
    const top = Math.max(0, ...layer.values())
    ids.forEach((i) => { if (!layer.has(i)) layer.set(i, top + 1) })
  }

  // --- 2. edges as chains with dummy waypoints
  const nodes = new Map<string, WorkNode>()
  ids.forEach((i) => nodes.set(i, { id: i, layer: layer.get(i)!, dummy: false, w: NODE_W, cx: 0 }))
  const chains: { from: string; to: string; ids: string[] }[] = []
  feeds.forEach(([a, b], k) => {
    let la = layer.get(a)!, lb = layer.get(b)!
    if (lb <= la) lb = la + 1 // back edge in a cycle: draw it downward anyway
    const chain = [a]
    for (let l = la + 1; l < lb; l++) {
      const id = `~${k}_${l}`
      nodes.set(id, { id, layer: l, dummy: true, w: DUMMY_W, cx: 0 })
      chain.push(id)
    }
    chain.push(b)
    chains.push({ from: a, to: b, ids: chain })
  })
  const nLayers = Math.max(...[...nodes.values()].map((n) => n.layer)) + 1

  // keep each connected chain together (components ordered by first appearance in systems.json)
  const adj = new Map<string, string[]>()
  ids.forEach((i) => adj.set(i, []))
  feeds.forEach(([a, b]) => { adj.get(a)!.push(b); adj.get(b)!.push(a) })
  const comp = new Map<string, number>()
  let nComp = 0
  feeds.forEach(([a, b]) => {
    for (const start of [a, b]) {
      if (comp.has(start)) continue
      const st = [start]
      comp.set(start, nComp)
      while (st.length) {
        const x = st.pop()!
        for (const y of adj.get(x)!) if (!comp.has(y)) { comp.set(y, nComp); st.push(y) }
      }
      nComp++
    }
  })
  chains.forEach((c) => c.ids.forEach((id) => { if (!comp.has(id)) comp.set(id, comp.get(c.from)!) }))

  const rows: string[][] = Array.from({ length: nLayers }, () => [])
  ;[...nodes.values()]
    .sort((p, q) => comp.get(p.id)! - comp.get(q.id)! || p.id.localeCompare(q.id))
    .forEach((n) => rows[n.layer].push(n.id))

  // neighbours between adjacent layers
  const up = new Map<string, string[]>(), down = new Map<string, string[]>()
  nodes.forEach((_, id) => { up.set(id, []); down.set(id, []) })
  chains.forEach((c) => {
    for (let i = 0; i < c.ids.length - 1; i++) { down.get(c.ids[i])!.push(c.ids[i + 1]); up.get(c.ids[i + 1])!.push(c.ids[i]) }
  })

  // --- 3. order within layers (barycentre sweeps reduce crossings)
  const pos = new Map<string, number>()
  const reindex = () => rows.forEach((r) => r.forEach((id, i) => pos.set(id, i)))
  reindex()
  const bary = (id: string, nb: Map<string, string[]>) => {
    const ns = nb.get(id)!
    return ns.length ? ns.reduce((s, n) => s + pos.get(n)!, 0) / ns.length : pos.get(id)!
  }
  for (let pass = 0; pass < 6; pass++) {
    const downward = pass % 2 === 0
    const range = downward ? rows.map((_, i) => i).slice(1) : rows.map((_, i) => i).slice(0, -1).reverse()
    for (const l of range) {
      const nb = downward ? up : down
      // nodes with no neighbours in this direction keep their slot; only connected ones are re-sorted
      const row = rows[l]
      const sorted = row.filter((id) => nb.get(id)!.length)
        .map((id) => ({ id, b: bary(id, nb) }))
        .sort((p, q) => p.b - q.b || pos.get(p.id)! - pos.get(q.id)!)
      let k = 0
      rows[l] = row.map((id) => (nb.get(id)!.length ? sorted[k++].id : id))
      reindex()
    }
  }

  // --- 4. x coordinates: start packed, then pull towards neighbours and resolve overlaps
  const wOf = (id: string) => nodes.get(id)!.w
  rows.forEach((r) => {
    let x = 0
    r.forEach((id) => { const n = nodes.get(id)!; n.cx = x + n.w / 2; x += n.w + GAP_X })
  })
  const rowWidth = (r: string[]) => r.reduce((s, id) => s + wOf(id) + GAP_X, -GAP_X)
  const maxW = Math.max(...rows.map(rowWidth))
  rows.forEach((r) => { const shift = (maxW - rowWidth(r)) / 2; r.forEach((id) => { nodes.get(id)!.cx += shift }) })
  const spread = (r: string[]) => {
    for (let i = 1; i < r.length; i++) {
      const a = nodes.get(r[i - 1])!, b = nodes.get(r[i])!
      const min = a.cx + a.w / 2 + GAP_X + b.w / 2
      if (b.cx < min) b.cx = min
    }
    for (let i = r.length - 2; i >= 0; i--) { // keep left-aligned compaction from drifting right
      const a = nodes.get(r[i])!, b = nodes.get(r[i + 1])!
      const max = b.cx - b.w / 2 - GAP_X - a.w / 2
      if (a.cx > max) a.cx = max
    }
  }
  for (let pass = 0; pass < 8; pass++) {
    const downward = pass % 2 === 0
    const range = downward ? rows.map((_, i) => i).slice(1) : rows.map((_, i) => i).slice(0, -1).reverse()
    for (const l of range) {
      const nb = downward ? up : down
      rows[l].forEach((id) => {
        const ns = nb.get(id)!
        if (ns.length) nodes.get(id)!.cx = ns.reduce((s, n) => s + nodes.get(n)!.cx, 0) / ns.length
      })
      spread(rows[l])
    }
  }
  const minX = Math.min(...[...nodes.values()].map((n) => n.cx - n.w / 2))
  nodes.forEach((n) => { n.cx -= minX })
  const width = Math.max(...[...nodes.values()].map((n) => n.cx + n.w / 2))
  const height = nLayers * NODE_H + (nLayers - 1) * GAP_Y

  // --- 5. connectors: down from parent, across a channel, down into child; channels staggered per parent
  const top = (l: number) => l * (NODE_H + GAP_Y)
  const parentOrder = new Map<string, number>()
  let po = 0
  chains.forEach((c) => { if (!parentOrder.has(c.from)) parentOrder.set(c.from, po++) })
  const edges: LEdge[] = chains.map((c) => {
    const pts: [number, number][] = []
    const off = 14 + (parentOrder.get(c.from)! % 5) * 8
    const first = nodes.get(c.ids[0])!
    pts.push([first.cx, top(first.layer) + NODE_H])
    for (let i = 1; i < c.ids.length; i++) {
      const a = nodes.get(c.ids[i - 1])!, b = nodes.get(c.ids[i])!
      const yMid = top(a.layer) + NODE_H + off
      pts.push([a.cx, yMid], [b.cx, yMid])
      if (b.dummy) pts.push([b.cx, top(b.layer) + NODE_H])
      else pts.push([b.cx, top(b.layer)])
    }
    // drop collinear points
    const clean = pts.filter((p, i) => i === 0 || i === pts.length - 1 || !((pts[i - 1][0] === p[0] && p[0] === pts[i + 1][0]) || (pts[i - 1][1] === p[1] && p[1] === pts[i + 1][1])))
    return { from: c.from, to: c.to, d: roundedPath(clean) }
  })

  const outNodes: LNode[] = ids.map((id) => {
    const n = nodes.get(id)!
    return { id, x: n.cx - n.w / 2, y: top(n.layer), w: n.w, layer: n.layer }
  })
  return { nodes: outNodes, edges, width, height, isolated, cyclic }
}
