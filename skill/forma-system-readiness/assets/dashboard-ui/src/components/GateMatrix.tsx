import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { Model, Sys } from "@/lib/model"
import { VerdictBadge, verdictBar } from "./bits"

interface Props {
  model: Model
  rows: Sys[]
  selSys: string | null
  selCell: { sys: string; col: string } | null
  onSystem: (name: string) => void
  onCell: (sys: string, col: string) => void
}

export function GateMatrix({ model, rows, selSys, selCell, onSystem, onCell }: Props) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Gate matrix</CardTitle>
        <CardDescription>
          Open items per system and gate. Red = blocking item open, amber = warning (draft, or an item you cannot see), green = clear.
          Click a cell for the items, or a system name to focus it.
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="min-w-[200px]">System</TableHead>
              {model.cols.map((c) => (
                <TableHead key={c} className="max-w-[96px] px-1 text-center text-xs leading-tight">
                  {c}
                </TableHead>
              ))}
              <TableHead className="min-w-[130px]">Verdict</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((s) => {
              const pct = s.assetCount ? Math.round((s.readyCount / s.assetCount) * 100) : 100
              return (
                <TableRow key={s.name} className={cn(s.name === selSys && "bg-accent/60")}>
                  <TableCell className="py-1.5">
                    <button className="block w-full text-left" onClick={() => onSystem(s.name)}>
                      <span className="block truncate text-sm font-semibold">{s.name}</span>
                      <span className="block text-xs text-muted-foreground">
                        {s.assetCount.toLocaleString()} assets · {s.readyCount.toLocaleString()} clear
                      </span>
                      <span className="mt-1 block h-1 w-32 overflow-hidden rounded-full bg-muted">
                        <span className={cn("block h-full", verdictBar.go)} style={{ width: `${pct}%` }} />
                      </span>
                    </button>
                  </TableCell>
                  {model.cols.map((c) => {
                    const l = s.items.filter((i) => i.col === c)
                    const b = l.filter((i) => i.r.state === "blocking").length
                    const w = l.length - b
                    const tone = b
                      ? "bg-nogo text-white hover:bg-nogo/90"
                      : w
                        ? "bg-cond-soft text-cond-ink hover:bg-cond-soft/70"
                        : "bg-go-soft text-go-ink hover:bg-go-soft/70"
                    const sel = selCell?.sys === s.name && selCell.col === c
                    return (
                      <TableCell key={c} className="p-1 text-center">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => onCell(s.name, c)}
                              className={cn(
                                "h-9 w-full min-w-[52px] rounded-md text-xs font-semibold tabular-nums transition-colors",
                                tone,
                                sel && "ring-2 ring-ring ring-offset-1"
                              )}
                            >
                              {l.length ? l.length : "✓"}
                            </button>
                          </TooltipTrigger>
                          <TooltipContent>
                            <b>{s.name}</b> · {c}
                            <br />
                            {b} blocking{w ? `, ${w} warning` : ""}
                          </TooltipContent>
                        </Tooltip>
                      </TableCell>
                    )
                  })}
                  <TableCell className="py-1.5">
                    <VerdictBadge v={s.verdict} />
                    {s.blocking.length > 0 && (
                      <span className="mt-0.5 block text-xs text-muted-foreground">
                        {s.blocking.length} blocking{s.warn.length ? ` · ${s.warn.length} warn` : ""}
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
            {!rows.length && (
              <TableRow>
                <TableCell colSpan={model.cols.length + 2} className="py-8 text-center text-sm text-muted-foreground">
                  No systems match.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
