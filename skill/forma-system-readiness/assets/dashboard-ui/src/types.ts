// Shape of output/latest.json, produced by app/readiness.py (see knowledge/06_dashboard_spec.md)

export type RefKind = "issue" | "form" | "document" | "asset" | "rfi" | "status" | "other"
export type RefState = "ok" | "blocking" | "warning" | "unknown"

export interface Ref {
  kind: RefKind
  id: string
  label: string
  path: string[]
  url: string | null
  status: string | null
  state: RefState
  due?: string | null
  type?: string | null
  assignee?: string | null
}

export interface Asset {
  id: string
  name: string
  description: string | null
  category: string
  status: string | null
  system: string
  ready: boolean
  blockers: number
  warnings: number
  url: string | null
  refs: Ref[]
}

export interface SystemRow {
  name: string
  assetIds: string[]
  assetCount: number
  readyCount: number
  ready: boolean
  openIssues: number
  openForms: number
  warnings: number
}

export interface Topology {
  feeds: [string, string][] // [upstream, downstream]: downstream cannot launch before upstream is ready
  unmatched: [string, string][]
  placeholder: boolean
  source: string | null
  error?: string
}

export interface Snapshot {
  meta: {
    projectName: string
    projectId: string
    generatedAt: string
    groupBy: string
    systemAttribute: string
    maxDepth: number
    issueClosed: string[]
    formOpen: string[]
    apiCalls?: number
    durationSec?: number
  }
  summary: {
    systems: number
    systemsReady: number
    assets: number
    assetsReady: number
    openIssues: number
    openForms: number
    unlinkedOpenIssues: number
    totalIssues: number
    totalForms: number
  }
  systems: SystemRow[]
  assets: Record<string, Asset>
  topology?: Topology
  history: Record<string, string>[]
}
