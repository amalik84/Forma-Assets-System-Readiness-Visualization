import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { Model } from "@/lib/model"
import type { Snapshot } from "@/types"

function Segment({ n, total, className }: { n: number; total: number; className: string }) {
  if (!n || !total) return null
  return <div className={cn("h-full", className)} style={{ width: `${(n / total) * 100}%` }} />
}

export function Kpis({ model, snap }: { model: Model; snap: Snapshot }) {
  const h = model.hero
  const pct = snap.summary.assets ? Math.round((snap.summary.assetsReady / snap.summary.assets) * 100) : 100
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardContent className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Programme verdict</p>
          <div
            className={cn(
              "mt-2 inline-flex items-center rounded-lg border-2 px-4 py-1.5 text-2xl font-bold",
              !h.total ? "border-border text-muted-foreground" : h.allGo ? "border-go bg-go-soft text-go-ink" : "border-nogo bg-nogo-soft text-nogo-ink"
            )}
          >
            {!h.total ? "–" : h.allGo ? "✓ GO" : "✕ NO-GO"}
          </div>
          <div className="mt-3 flex h-2 overflow-hidden rounded-full bg-muted">
            <Segment n={h.nogo} total={h.total} className="bg-nogo" />
            <Segment n={h.cond} total={h.total} className="bg-cond" />
            <Segment n={h.go} total={h.total} className="bg-go" />
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            {h.nogo} no-go · {h.cond} conditional · {h.go} go
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Systems clear to launch</p>
          <p className="mt-2 text-4xl font-bold tabular-nums">
            {h.go}
            <span className="text-2xl font-semibold text-muted-foreground"> / {h.total}</span>
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            {snap.summary.assetsReady.toLocaleString()} of {snap.summary.assets.toLocaleString()} assets clear ({pct}%)
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Blocking items to close</p>
          <p className="mt-2 text-4xl font-bold tabular-nums">{h.blockers}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            {snap.summary.openIssues} open issues · {snap.summary.openForms} open forms on assets
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Blocking issues past due</p>
          <p className={cn("mt-2 text-4xl font-bold tabular-nums", h.overdue ? "text-nogo-ink" : "")}>{h.overdue}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            {snap.summary.unlinkedOpenIssues} open issues are not linked to any asset
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
