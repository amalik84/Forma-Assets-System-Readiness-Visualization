import type { ReactNode } from "react"
import { AlertTriangle, CheckCircle2, ExternalLink, XCircle } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { Ref } from "@/types"
import { VERDICT_LABEL, type Verdict } from "@/lib/model"

export const fmtDate = (d: Date) => d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })

export const verdictText: Record<Verdict, string> = {
  go: "text-go-ink",
  cond: "text-cond-ink",
  nogo: "text-nogo-ink",
}
export const verdictSoft: Record<Verdict, string> = {
  go: "bg-go-soft text-go-ink",
  cond: "bg-cond-soft text-cond-ink",
  nogo: "bg-nogo-soft text-nogo-ink",
}
export const verdictBar: Record<Verdict, string> = { go: "bg-go", cond: "bg-cond", nogo: "bg-nogo" }

export function VerdictIcon({ v, className }: { v: Verdict; className?: string }) {
  const Icon = v === "go" ? CheckCircle2 : v === "cond" ? AlertTriangle : XCircle
  return <Icon className={cn("h-4 w-4 shrink-0", verdictText[v], className)} aria-label={VERDICT_LABEL[v]} />
}

export function VerdictBadge({ v, className }: { v: Verdict; className?: string }) {
  return (
    <Badge variant="outline" className={cn("border-transparent font-semibold", verdictSoft[v], className)}>
      {VERDICT_LABEL[v]}
    </Badge>
  )
}

const stateStyle: Record<string, string> = {
  blocking: "bg-nogo-soft text-nogo-ink",
  warning: "bg-cond-soft text-cond-ink",
  unknown: "bg-cond-soft text-cond-ink",
  ok: "bg-go-soft text-go-ink",
}

export function StateBadge({ r }: { r: Ref }) {
  const text = r.state === "unknown" ? "no access" : r.status || (r.state === "blocking" ? "blocking" : r.state)
  if (r.state === "ok" && !r.status) return null
  return (
    <Badge variant="outline" className={cn("border-transparent", stateStyle[r.state])}>
      {text}
    </Badge>
  )
}

export function ItemLink({ r, text }: { r: Ref; text?: string }) {
  const label = text ?? r.label
  if (!r.url) return <span>{label}</span>
  return (
    <a href={r.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-link hover:underline">
      {label}
      <ExternalLink className="h-3 w-3 opacity-60" />
    </a>
  )
}

export function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 py-1 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-semibold tabular-nums", tone)}>{value}</span>
    </div>
  )
}
