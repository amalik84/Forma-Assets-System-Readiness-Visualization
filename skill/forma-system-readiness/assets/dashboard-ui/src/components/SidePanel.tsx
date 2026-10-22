import { useState, type ReactNode } from "react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"
import { isOverdue, sortSys, type Model, type Sys } from "@/lib/model"
import type { Asset, Snapshot } from "@/types"
import { ItemLink, StateBadge, Stat, VerdictBadge, VerdictIcon } from "./bits"

/* ---------------- verdict summary ---------------- */
export function VerdictCard({ model, onSystem }: { model: Model; onSystem: (n: string) => void }) {
  const worst = model.sys.slice().sort(sortSys).filter((s) => s.blocking.length).slice(0, 6)
  const max = Math.max(1, ...worst.map((s) => s.blocking.length))
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Systems by verdict</CardTitle>
      </CardHeader>
      <CardContent>
        <Stat label="✕ No-go (blocking items open)" value={model.hero.nogo} tone="text-nogo-ink" />
        <Stat label="! Conditional (warnings only)" value={model.hero.cond} tone="text-cond-ink" />
        <Stat label="✓ Go" value={model.hero.go} tone="text-go-ink" />
        {worst.length > 0 && (
          <>
            <Separator className="my-3" />
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Most blocking items</p>
            <div className="space-y-1.5">
              {worst.map((s) => (
                <button key={s.name} onClick={() => onSystem(s.name)} className="flex w-full items-center gap-2 text-left">
                  <span className="w-36 truncate text-xs" title={s.name}>{s.name}</span>
                  <span className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                    <span className="block h-full rounded-full bg-nogo" style={{ width: `${(s.blocking.length / max) * 100}%` }} />
                  </span>
                  <span className="w-7 text-right text-xs font-semibold tabular-nums">{s.blocking.length}</span>
                </button>
              ))}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

/* ---------------- trend ---------------- */
export function TrendCard({ snap }: { snap: Snapshot }) {
  const pts = (snap.history ?? []).slice(-60).map((r) => ({ d: String(r.date ?? "").slice(0, 10), i: +r.openIssues || 0, f: +r.openForms || 0 }))
  const [hover, setHover] = useState<number | null>(null)
  const W = 380, H = 190, l = 34, r = 10, t = 10, b = 24
  const max = Math.max(4, ...pts.map((p) => Math.max(p.i, p.f)))
  const X = (k: number) => l + (k / Math.max(1, pts.length - 1)) * (W - l - r)
  const Y = (n: number) => t + (1 - n / max) * (H - t - b)
  const path = (key: "i" | "f") => pts.map((p, k) => `${k ? "L" : "M"}${X(k).toFixed(1)},${Y(p[key]).toFixed(1)}`).join(" ")
  const cur = hover ?? pts.length - 1
  const delta = pts.length > 1 ? pts[pts.length - 1].i + pts[pts.length - 1].f - (pts[0].i + pts[0].f) : 0
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Trend</CardTitle>
        <CardDescription>Open issues and forms on assets, one point per run.</CardDescription>
      </CardHeader>
      <CardContent>
        {pts.length < 2 ? (
          <div className="rounded-md border border-dashed p-5 text-center text-sm text-muted-foreground">The trend appears after two or more daily runs.</div>
        ) : (
          <>
            <svg viewBox={`0 0 ${W} ${H}`} width="100%" onMouseLeave={() => setHover(null)}
              onMouseMove={(e) => {
                const bx = e.currentTarget.getBoundingClientRect()
                const x = ((e.clientX - bx.left) / bx.width) * W
                setHover(Math.max(0, Math.min(pts.length - 1, Math.round(((x - l) / (W - l - r)) * (pts.length - 1)))))
              }}>
              {[0, 0.5, 1].map((f) => {
                const v = Math.round(max * f)
                return (
                  <g key={f}>
                    <line x1={l} x2={W - r} y1={Y(v)} y2={Y(v)} stroke="hsl(52 10% 86%)" />
                    <text x={l - 6} y={Y(v) + 4} textAnchor="end" fontSize="11" fill="hsl(45 3% 52%)">{v}</text>
                  </g>
                )
              })}
              <text x={X(0)} y={H - 6} fontSize="11" fill="hsl(45 3% 52%)">{pts[0].d.slice(5)}</text>
              <text x={X(pts.length - 1)} y={H - 6} fontSize="11" textAnchor="end" fill="hsl(45 3% 52%)">{pts[pts.length - 1].d.slice(5)}</text>
              <path d={path("i")} fill="none" stroke="hsl(0 60% 52%)" strokeWidth="2" strokeLinejoin="round" />
              <path d={path("f")} fill="none" stroke="hsl(212 68% 50%)" strokeWidth="2" strokeLinejoin="round" />
              <line x1={X(cur)} x2={X(cur)} y1={t} y2={H - b} stroke="hsl(52 10% 70%)" />
              <circle cx={X(cur)} cy={Y(pts[cur].i)} r="4" fill="hsl(0 60% 52%)" stroke="white" strokeWidth="2" />
              <circle cx={X(cur)} cy={Y(pts[cur].f)} r="4" fill="hsl(212 68% 50%)" stroke="white" strokeWidth="2" />
            </svg>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span>{pts[cur].d}</span>
              <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-nogo" />Issues {pts[cur].i}</span>
              <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: "hsl(212 68% 50%)" }} />Forms {pts[cur].f}</span>
              <span className="ml-auto">Since {pts[0].d}: {delta <= 0 ? `down ${-delta}` : `up ${delta}`}</span>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

/* ---------------- details ---------------- */
interface DetailProps {
  model: Model
  sys: Sys | null
  selCell: { sys: string; col: string } | null
  asset: Asset | null
  onSystem: (n: string) => void
}

function SystemLine({ s, onSystem }: { s: Sys; onSystem: (n: string) => void }) {
  return (
    <button onClick={() => onSystem(s.name)} className="flex w-full items-center gap-2 rounded px-1 py-1 text-left text-sm hover:bg-accent">
      <VerdictIcon v={s.verdict} />
      <span className="flex-1 truncate">{s.name}</span>
      <span className="text-xs text-muted-foreground">{s.blocking.length} blocking</span>
    </button>
  )
}

export function DetailsCard({ model, sys, selCell, asset, onSystem }: DetailProps) {
  const order: Record<string, number> = { blocking: 0, unknown: 1, warning: 2, ok: 3 }

  let title = "Details"
  let body: ReactNode = <p className="text-sm text-muted-foreground">Click a system, a cell in the matrix, or an asset to see what is behind it.</p>

  if (asset) {
    title = "Asset references"
    const groups: [string, string][] = [["status", "Status rule"], ["issue", "Issues"], ["form", "Forms"], ["document", "Documents"], ["asset", "Linked assets"], ["rfi", "RFIs"]]
    body = (
      <div className="space-y-3">
        <div>
          <div className="text-base font-semibold">{asset.url ? <a className="text-link hover:underline" href={asset.url} target="_blank" rel="noopener noreferrer">{asset.name}</a> : asset.name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <span>{asset.system} · {asset.category} · {asset.status ?? "no status"}</span>
            {asset.ready ? <Badge variant="outline" className="border-transparent bg-go-soft text-go-ink">CLEAR</Badge> : <Badge variant="outline" className="border-transparent bg-nogo-soft text-nogo-ink">NOT READY</Badge>}
          </div>
        </div>
        {groups.map(([kind, label]) => {
          const rs = asset.refs.filter((r) => r.kind === kind).sort((a, b) => order[a.state] - order[b.state])
          if (!rs.length) return null
          return (
            <div key={kind}>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">{label} ({rs.length})</p>
              <div className="divide-y rounded-md border">
                {rs.map((r) => (
                  <div key={r.kind + r.id} className="p-2.5 text-sm">
                    <div className="flex items-start justify-between gap-2"><ItemLink r={r} /><StateBadge r={r} /></div>
                    <div className="mt-0.5 text-xs text-muted-foreground">
                      {r.path.map((p, i) => (i === r.path.length - 1 ? <b key={i} className="font-medium text-foreground">{p}</b> : <span key={i}>{p} → </span>))}
                      {r.due ? ` · ${r.kind === "issue" ? "due" : "dated"} ${String(r.due).slice(0, 10)}` : ""}
                      {r.type ? ` · ${r.type}` : ""}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )
        })}
        {!asset.refs.length && <p className="text-sm text-muted-foreground">No linked issues, forms or documents found.</p>}
      </div>
    )
  } else if (selCell && model.byName.get(selCell.sys)) {
    const s = model.byName.get(selCell.sys)!
    const l = s.items.filter((i) => i.col === selCell.col).sort((a, b) => (a.r.state === "blocking" ? 0 : 1) - (b.r.state === "blocking" ? 0 : 1))
    title = `${s.name} · ${selCell.col}`
    body = l.length ? (
      <div className="divide-y rounded-md border">
        {l.map((i) => (
          <div key={i.r.kind + i.r.id} className="p-2.5 text-sm">
            <div className="flex items-start justify-between gap-2"><b><ItemLink r={i.r} /></b><StateBadge r={i.r} /></div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {i.r.type || i.r.kind}{i.r.due ? ` · ${i.r.kind === "issue" ? "due" : "dated"} ${String(i.r.due).slice(0, 10)}` : ""}
              {isOverdue(i.r, model.today) && <b className="text-nogo-ink"> · overdue</b>}
            </div>
            <div className="text-xs text-muted-foreground">
              {i.assets.length > 1 ? `on ${i.assets.length} assets (e.g. ${i.assets[0].a.name})` : i.assets[0].a.name}
            </div>
          </div>
        ))}
      </div>
    ) : (
      <p className="text-sm text-muted-foreground">✓ No open items on this gate.</p>
    )
  } else if (sys) {
    const f = model.flow.get(sys.name)
    title = sys.name
    const up = (f?.up ?? []).map((n) => model.byName.get(n)!).filter(Boolean)
    const down = (f?.down ?? []).map((n) => model.byName.get(n)!).filter(Boolean)
    body = (
      <div className="space-y-3">
        <div className="flex items-center gap-2"><VerdictBadge v={sys.verdict} /><span className="text-xs text-muted-foreground">{sys.assetCount.toLocaleString()} assets · {sys.readyCount.toLocaleString()} clear</span></div>
        <div>
          <Stat label="Blocking items" value={sys.blocking.length} tone={sys.blocking.length ? "text-nogo-ink" : undefined} />
          <Stat label="Warnings" value={sys.warn.length} tone={sys.warn.length ? "text-cond-ink" : undefined} />
        </div>
        {f && f.upBlocked.length > 0 && (
          <div className="rounded-md border border-nogo/40 bg-nogo-soft p-2.5 text-sm text-nogo-ink">
            ⚠ Cannot launch until <b>{f.upBlocked.join(", ")}</b> {f.upBlocked.length > 1 ? "are" : "is"} unblocked.
          </div>
        )}
        {f && f.down.length > 0 && (
          <div className="rounded-md border p-2.5 text-sm">
            ▼ Downstream: <b>{f.downBlocking}</b> blocking item(s) across {f.down.length} system(s) depend on this one.
          </div>
        )}
        {up.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Fed by ({up.length})</p>
            {up.map((s) => <SystemLine key={s.name} s={s} onSystem={onSystem} />)}
          </div>
        )}
        {down.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">Feeds ({down.length})</p>
            {down.map((s) => <SystemLine key={s.name} s={s} onSystem={onSystem} />)}
          </div>
        )}
        {!up.length && !down.length && <p className="text-xs text-muted-foreground">No dependencies defined for this system in systems.json.</p>}
      </div>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-base">{title}</CardTitle></CardHeader>
      <CardContent className={cn("max-h-[640px] overflow-auto")}>{body}</CardContent>
    </Card>
  )
}
