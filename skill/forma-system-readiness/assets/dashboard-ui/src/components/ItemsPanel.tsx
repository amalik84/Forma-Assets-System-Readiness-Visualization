import { useMemo, useState, type ReactNode } from "react"
import { Search } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { cn } from "@/lib/utils"
import { isOverdue, parseDate, sortSys, type Item, type Model, type Sys } from "@/lib/model"
import { ItemLink, StateBadge, VerdictIcon, fmtDate } from "./bits"

interface Props {
  model: Model
  sys: Sys | null
  selAsset: string | null
  onAsset: (id: string) => void
}

const BLOCK_CAP = 200
const ASSET_CAP = 150

function viaOf(it: Item) {
  const p = it.assets[0].path.slice(0, -1)
  return p.length <= 1 ? <Badge variant="secondary">Direct on asset</Badge> : <Badge variant="outline" className="whitespace-normal font-normal">{p.slice(1).join(" → ")}</Badge>
}

export function ItemsPanel({ model, sys, selAsset, onAsset }: Props) {
  const [scope, setScope] = useState<"focus" | "all">("focus")
  const [aq, setAq] = useState("")

  const groups = useMemo(() => {
    const list = scope === "focus" && sys ? [sys] : model.sys.slice().sort(sortSys).filter((s) => s.blocking.length)
    const key = (i: Item): [number, number] => {
      const d = parseDate(i.r.due)
      return [isOverdue(i.r, model.today) ? 0 : 1, d ? d.getTime() : 9e15]
    }
    return list.map((s) => ({ s, rows: s.blocking.slice().sort((a, b) => { const x = key(a), y = key(b); return x[0] - y[0] || x[1] - y[1] }) }))
  }, [scope, sys, model])

  const assets = useMemo(() => {
    if (!sys) return []
    const q = aq.trim().toLowerCase()
    return sys.assets
      .filter((a) => !q || `${a.name} ${a.category} ${a.description ?? ""}`.toLowerCase().includes(q))
      .sort((a, b) => b.blockers - a.blockers || b.warnings - a.warnings || a.name.localeCompare(b.name))
  }, [sys, aq])

  let shown = 0
  let hidden = 0
  const totalBlocking = new Set(groups.flatMap((g) => g.rows.map((i) => i.r.kind + "|" + i.r.id))).size

  return (
    <Card>
      <Tabs defaultValue="blocking">
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0 pb-3">
          <CardTitle className="text-base">{sys ? sys.name : "Items"}</CardTitle>
          <TabsList>
            <TabsTrigger value="blocking">Blocking items ({totalBlocking})</TabsTrigger>
            <TabsTrigger value="assets">Assets ({sys ? sys.assetCount.toLocaleString() : 0})</TabsTrigger>
          </TabsList>
        </CardHeader>
        <CardContent className="pt-0">
          <TabsContent value="blocking" className="mt-0 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-muted-foreground">Open issues and open forms reached from assets. Overdue issues first.</p>
              <ToggleGroup type="single" size="sm" variant="outline" value={scope} onValueChange={(v) => v && setScope(v as "focus" | "all")}>
                <ToggleGroupItem value="focus">This system</ToggleGroupItem>
                <ToggleGroupItem value="all">All systems</ToggleGroupItem>
              </ToggleGroup>
            </div>
            <div className="max-h-[460px] overflow-auto rounded-md border">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    <TableHead>Item</TableHead>
                    <TableHead>Reached via</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {groups.map(({ s, rows }) => (
                    <TableGroup key={s.name} s={s} showHeader={scope === "all"}>
                      {rows.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={5} className="text-sm text-muted-foreground">✓ Nothing blocks this system.</TableCell>
                        </TableRow>
                      )}
                      {rows.map((i) => {
                        if (shown >= BLOCK_CAP) { hidden++; return null }
                        shown++
                        const od = isOverdue(i.r, model.today)
                        const d = parseDate(i.r.due)
                        return (
                          <TableRow key={i.r.kind + i.r.id}>
                            <TableCell className="max-w-[260px]">
                              <div className="font-medium"><ItemLink r={i.r} /></div>
                              <div className="text-xs text-muted-foreground">
                                {i.assets.length > 1 ? `on ${i.assets.length} assets` : i.assets[0].a.name}
                              </div>
                            </TableCell>
                            <TableCell>{viaOf(i)}</TableCell>
                            <TableCell className="text-xs">{i.r.type || i.r.kind}</TableCell>
                            <TableCell><StateBadge r={i.r} /></TableCell>
                            <TableCell className={cn("whitespace-nowrap text-xs", od && "font-semibold text-nogo-ink")}>
                              {d ? fmtDate(d) : ""}{od ? " · overdue" : ""}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableGroup>
                  ))}
                  {hidden > 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-xs text-muted-foreground">… {hidden} more not shown. Focus a single system to see all of its items.</TableCell>
                    </TableRow>
                  )}
                  {groups.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">✓ No blocking items anywhere.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <TabsContent value="assets" className="mt-0 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-muted-foreground">
                Blockers first{assets.length > ASSET_CAP ? `, showing the first ${ASSET_CAP} of ${assets.length.toLocaleString()}` : ""}. Click an asset to see everything linked to it.
              </p>
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input className="h-9 w-56 pl-8" placeholder="Search assets…" value={aq} onChange={(e) => setAq(e.target.value)} />
              </div>
            </div>
            <div className="max-h-[460px] overflow-auto rounded-md border">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card">
                  <TableRow>
                    <TableHead>Asset</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Readiness</TableHead>
                    <TableHead>Linked</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assets.slice(0, ASSET_CAP).map((a) => {
                    const n = (k: string) => a.refs.filter((r) => r.kind === k).length
                    return (
                      <TableRow key={a.id} onClick={() => onAsset(a.id)} className={cn("cursor-pointer", a.id === selAsset && "bg-accent/70")}>
                        <TableCell className="max-w-[260px]">
                          <div className="truncate font-medium">{a.name}</div>
                          {a.description && <div className="truncate text-xs text-muted-foreground">{a.description}</div>}
                        </TableCell>
                        <TableCell className="text-xs">{a.category}</TableCell>
                        <TableCell className="text-xs">{a.status}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {a.ready ? (
                              <Badge variant="outline" className="border-transparent bg-go-soft text-go-ink">CLEAR</Badge>
                            ) : (
                              <Badge variant="outline" className="border-transparent bg-nogo-soft text-nogo-ink">{a.blockers} BLOCKER{a.blockers > 1 ? "S" : ""}</Badge>
                            )}
                            {a.warnings > 0 && <Badge variant="outline" className="border-transparent bg-cond-soft text-cond-ink">{a.warnings} warn</Badge>}
                          </div>
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                          {n("issue")} issues · {n("form")} forms · {n("document")} docs
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {!assets.length && (
                    <TableRow>
                      <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">No assets.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </TabsContent>
        </CardContent>
      </Tabs>
    </Card>
  )
}

function TableGroup({ s, showHeader, children }: { s: Sys; showHeader: boolean; children: ReactNode }) {
  return (
    <>
      {showHeader && (
        <TableRow className="bg-muted/60 hover:bg-muted/60">
          <TableCell colSpan={5} className="py-1.5 text-sm font-semibold">
            <span className="inline-flex items-center gap-1.5">
              <VerdictIcon v={s.verdict} />
              {s.name}
              <span className="font-normal text-muted-foreground">· {s.blocking.length} blocking</span>
            </span>
          </TableCell>
        </TableRow>
      )}
      {children}
    </>
  )
}
