import { useMemo, useState } from "react"
import { Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { TooltipProvider } from "@/components/ui/tooltip"
import { buildModel, sortSys } from "@/lib/model"
import type { Snapshot } from "@/types"
import { GateMatrix } from "@/components/GateMatrix"
import { ItemsPanel } from "@/components/ItemsPanel"
import { Kpis } from "@/components/Kpis"
import { DetailsCard, TrendCard, VerdictCard } from "@/components/SidePanel"
import { Topology } from "@/components/Topology"

export default function App({ snap }: { snap: Snapshot }) {
  const model = useMemo(() => buildModel(snap), [snap])
  const [view, setView] = useState<"all" | "bad">("all")
  const [q, setQ] = useState("")
  const [selSys, setSelSys] = useState<string | null>(null)
  const [selCell, setSelCell] = useState<{ sys: string; col: string } | null>(null)
  const [selAsset, setSelAsset] = useState<string | null>(null)

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return model.sys.filter((s) => (view === "all" || s.verdict !== "go") && (!needle || s.name.toLowerCase().includes(needle))).sort(sortSys)
  }, [model, view, q])

  const effective = selSys && model.byName.has(selSys) ? selSys : (rows[0] ?? model.sys.slice().sort(sortSys)[0])?.name ?? null
  const sys = effective ? model.byName.get(effective)! : null
  const asset = selAsset ? snap.assets[selAsset] ?? null : null

  const pickSystem = (name: string) => { setSelSys(name); setSelCell(null); setSelAsset(null) }
  const pickCell = (name: string, col: string) => { setSelSys(name); setSelCell({ sys: name, col }); setSelAsset(null) }
  const pickAsset = (id: string) => { setSelAsset(id); setSelCell(null) }

  const grouping = snap.meta.groupBy === "category" ? "asset category" : `"${snap.meta.systemAttribute}"`

  return (
    <TooltipProvider delayDuration={120}>
      <div className="min-h-screen">
        <header className="border-b bg-card">
          <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-3 px-6 py-4">
            <div>
              <h1 className="text-lg font-semibold tracking-tight">FOMO1 · System readiness</h1>
              <p className="text-sm text-muted-foreground">
                {snap.meta.projectName} · systems grouped by {grouping}
              </p>
            </div>
            <Badge variant="secondary" className="font-normal">Refreshed {snap.meta.generatedAt.replace("T", " ")}</Badge>
          </div>
        </header>

        <main className="mx-auto max-w-[1600px] space-y-4 px-6 py-5">
          <Kpis model={model} snap={snap} />

          <div className="flex flex-wrap items-center gap-3">
            <ToggleGroup type="single" variant="outline" size="sm" value={view} onValueChange={(v) => v && setView(v as "all" | "bad")}>
              <ToggleGroupItem value="all">All systems</ToggleGroupItem>
              <ToggleGroupItem value="bad">Not ready only</ToggleGroupItem>
            </ToggleGroup>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input className="h-9 w-60 pl-8" placeholder="Search systems…" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
          </div>

          <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_400px]">
            <div className="min-w-0 space-y-4">
              <GateMatrix model={model} rows={rows} selSys={effective} selCell={selCell} onSystem={pickSystem} onCell={pickCell} />
              <Topology model={model} snap={snap} selSys={effective} onSystem={pickSystem} />
              <ItemsPanel model={model} sys={sys} selAsset={selAsset} onAsset={pickAsset} />
            </div>
            <div className="space-y-4">
              <VerdictCard model={model} onSystem={pickSystem} />
              <TrendCard snap={snap} />
              <DetailsCard model={model} sys={sys} selCell={selCell} asset={asset} onSystem={pickSystem} />
            </div>
          </div>
        </main>

        <footer className="px-6 pb-8 text-center text-xs text-muted-foreground">
          Read-only snapshot · {snap.meta.apiCalls ?? "–"} API calls · {snap.meta.durationSec ?? "–"}s · closed issue statuses: {snap.meta.issueClosed.join(", ")} · open form statuses: {snap.meta.formOpen.join(", ")}
        </footer>
      </div>
    </TooltipProvider>
  )
}
