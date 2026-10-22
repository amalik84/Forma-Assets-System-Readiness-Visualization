import { Info } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { NODE_H, NODE_W } from "@/lib/layout"
import type { Model } from "@/lib/model"
import type { Snapshot } from "@/types"
import { VERDICT_LABEL } from "@/lib/model"
import { VerdictIcon, verdictBar, verdictSoft } from "./bits"

interface Props {
  model: Model
  snap: Snapshot
  selSys: string | null
  onSystem: (name: string) => void
}

export function Topology({ model, snap, selSys, onSystem }: Props) {
  const { layout, flow, byName } = model
  const topo = snap.topology
  const focus = selSys && flow.has(selSys) && layout.nodes.some((n) => n.id === selSys)
    ? new Set<string>([selSys, ...flow.get(selSys)!.up, ...flow.get(selSys)!.down])
    : null
  const dim = (id: string) => (focus && !focus.has(id) ? "opacity-25" : "")

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Launch dependencies</CardTitle>
        <CardDescription>
          A system cannot launch before the systems above it. Open items roll up: the badge on a system counts blocking items further down its
          branch. Click a system to trace what it depends on and what depends on it.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        {topo?.placeholder && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>Starter dependencies</AlertTitle>
            <AlertDescription>
              These links come from <code>{topo.source ?? "systems.json"}</code> and are an example. Edit that file to match how this project actually
              launches, then run <code>python fomo1.py render --open</code>.
            </AlertDescription>
          </Alert>
        )}
        {topo?.error && (
          <Alert variant="destructive">
            <AlertTitle>Could not read dependencies</AlertTitle>
            <AlertDescription>{topo.error}</AlertDescription>
          </Alert>
        )}
        {topo && topo.unmatched.length > 0 && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>{topo.unmatched.length} pair(s) ignored</AlertTitle>
            <AlertDescription>
              System names not found on the dashboard: {topo.unmatched.map((p) => `${p[0]} → ${p[1]}`).join("; ")}
            </AlertDescription>
          </Alert>
        )}

        {layout.nodes.length === 0 ? (
          <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
            No dependencies defined yet. Add pairs like <code>["Electrical", "HVAC"]</code> to <code>systems.json</code> (upstream first).
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border bg-background/60 p-4">
            <div className="relative mx-auto" style={{ width: layout.width, height: layout.height }}>
              <svg className="absolute inset-0" width={layout.width} height={layout.height} aria-hidden>
                <defs>
                  <marker id="arrow-grey" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M0,0 L8,4 L0,8 z" fill="#a9a89d" />
                  </marker>
                  <marker id="arrow-red" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                    <path d="M0,0 L8,4 L0,8 z" fill="hsl(0 60% 52%)" />
                  </marker>
                </defs>
                {layout.edges.map((e) => {
                  const blocked = byName.get(e.from)?.verdict === "nogo"
                  const visible = !focus || (focus.has(e.from) && focus.has(e.to))
                  return (
                    <path
                      key={e.from + ">" + e.to}
                      d={e.d}
                      fill="none"
                      stroke={blocked ? "hsl(0 60% 52%)" : "#a9a89d"}
                      strokeWidth={1.75}
                      strokeDasharray={blocked ? "6 4" : undefined}
                      markerEnd={`url(#${blocked ? "arrow-red" : "arrow-grey"})`}
                      opacity={visible ? 1 : 0.15}
                    />
                  )
                })}
              </svg>
              {layout.nodes.map((n) => {
                const s = byName.get(n.id)!
                const f = flow.get(n.id)!
                const sel = n.id === selSys
                return (
                  <Tooltip key={n.id}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => onSystem(n.id)}
                        className={cn(
                          "absolute flex flex-col justify-center rounded-lg border bg-card px-3 text-left shadow-sm transition-opacity hover:shadow-md",
                          dim(n.id),
                          sel && "ring-2 ring-ring ring-offset-2"
                        )}
                        style={{ left: n.x, top: n.y, width: NODE_W, height: NODE_H }}
                      >
                        <span className={cn("absolute inset-y-0 left-0 w-1.5 rounded-l-lg", verdictBar[s.verdict])} />
                        <span className="flex items-center gap-1.5 pl-1.5">
                          <VerdictIcon v={s.verdict} />
                          <span className="truncate text-sm font-semibold">{s.name}</span>
                        </span>
                        <span className="pl-1.5 text-xs text-muted-foreground">
                          {s.blocking.length} blocking · {s.assetCount.toLocaleString()} assets
                        </span>
                        {(f.downBlocking > 0 || f.downWarn > 0) && (
                          <span
                            className={cn(
                              "absolute -right-2 -top-2.5 rounded-full border-2 border-card px-1.5 text-[11px] font-bold leading-5",
                              f.downBlocking ? "bg-nogo text-white" : "bg-cond text-black"
                            )}
                          >
                            ▼{f.downBlocking || f.downWarn}
                          </span>
                        )}
                        {f.upBlocked.length > 0 && s.verdict !== "nogo" && (
                          <span className="absolute -bottom-2 left-3 rounded-full border-2 border-card bg-nogo-soft px-1.5 text-[10px] font-semibold leading-4 text-nogo-ink">
                            fed by blocked
                          </span>
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <b>{s.name}</b> · {VERDICT_LABEL[s.verdict]}
                      <br />
                      {s.blocking.length} blocking, {s.warn.length} warning · {s.assetCount.toLocaleString()} assets
                      {f.upBlocked.length > 0 && (
                        <>
                          <br />
                          Fed by blocked: {f.upBlocked.join(", ")}
                        </>
                      )}
                      {f.down.length > 0 && (
                        <>
                          <br />
                          Downstream: {f.downBlocking} blocking items across {f.down.length} system(s)
                        </>
                      )}
                    </TooltipContent>
                  </Tooltip>
                )
              })}
            </div>
          </div>
        )}

        {layout.isolated.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Independent systems ({layout.isolated.length}): no dependencies defined
            </p>
            <div className="flex flex-wrap gap-1.5">
              {layout.isolated
                .map((id) => byName.get(id)!)
                .sort((a, b) => (a.verdict === b.verdict ? a.name.localeCompare(b.name) : a.verdict === "nogo" ? -1 : b.verdict === "nogo" ? 1 : a.verdict === "cond" ? -1 : 1))
                .map((s) => (
                  <button
                    key={s.name}
                    onClick={() => onSystem(s.name)}
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors hover:bg-accent",
                      s.name === selSys && "ring-2 ring-ring ring-offset-1"
                    )}
                  >
                    <VerdictIcon v={s.verdict} className="h-3.5 w-3.5" />
                    <span className="font-medium">{s.name}</span>
                    {s.blocking.length > 0 && (
                      <span className={cn("rounded px-1 font-semibold tabular-nums", verdictSoft.nogo)}>{s.blocking.length}</span>
                    )}
                  </button>
                ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
