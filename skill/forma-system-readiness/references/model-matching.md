# Choosing viewer models

Goal: find the model documents whose element names match the asset names, so the viewer can highlight assets.

**Quick route (live build, October 2026 and later):** after one refresh, `py src\survey.py --models` does steps 1 and 2: it shows which systems have matchable asset names, ranks the most-linked models, checks they can be viewed, and prints a `VIEWER_MODELS=` line. Then `.\serve.ps1`, select a system, and read the line under the viewer: "Assets per model (whole project): A: 307 · B: 0". Keep the models with matches. The manual steps below are the fallback and explain what the tool does.

## 1. Rank candidate models

After a refresh (so `documents.json` and `relationships.json` exist for today), count how often each model document is referenced. Run from the project folder:

```powershell
py -c "
import json, config
from collections import Counter
D = config.snapshot_dir(config.snapshot_day())
d = json.load(open(D / 'documents.json', encoding='utf-8'))
docs = {x['id']: x for x in d['documents']}
edges = json.load(open(D / 'relationships.json', encoding='utf-8'))['edges'] + d['pinEdges']
c = Counter()
for e in edges:
    for k in (e['a'], e['b']):
        x = docs.get(k)
        if x and (x['name'] or '').lower().endswith(('.rvt', '.nwd', '.nwc', '.ifc', '.dwg', '.dgn')):
            c[(x['name'], x['urn'])] += 1
for (n, u), k in c.most_common(15): print(k, n, u)
"
```

(Run it with `src` as the working directory, or add `sys.path.insert(0, 'src')`, so `import config` works.)

Also look at asset names per system: names ending in `[number]` (Revit element ID) or `[hex]` (AutoCAD handle) can match. Plain names such as a road name or a signal code cannot be matched by name.

## 2. Resolve and check translation

Put up to about 10 candidate lineage URNs in `VIEWER_MODELS`, then:

```powershell
py src\fetch\models.py   # prints each model with v<version> and success / failed
py src\render.py
```

Models whose translation failed are skipped automatically.

## 3. Count matches in the browser

Start `.\serve.ps1`, wait until the viewer has loaded all models, then run this in the page (browser console, or the browser tool's JavaScript):

```javascript
({ready: viewerReady(), per: D.models.map((m, i) => {
  const map = V.nameMaps[i];
  const hits = map ? D.assets.filter(a => map.has(a.name.toLowerCase())) : [];
  const bySys = {}; hits.forEach(a => bySys[a.systemIds[0]] = (bySys[a.systemIds[0]] || 0) + 1);
  return [m.name, map ? map.size : "not loaded", hits.length, JSON.stringify(bySys)];
})})
```

Loading 10 models can take more than 45 seconds; if a script times out, wait and run the count again rather than reloading.

## 4. Keep only what matches

Set `VIEWER_MODELS` to the models with matches (drop duplicate copies that match the same assets), refresh models and render, and report coverage per system.

## Examples from past projects

| Project | Models kept | Coverage |
|---|---|---|
| Demo project A | Arch_demo.rvt v28, MEP-central.rvt v6, Struc.rvt v2 | 2,032 of 6,516 |
| Demo project B | MN_GC_0001.rvt (Tunnel 307 of 334), RidgeGate_Station_SITE.dwg (Light Poles 29 of 29) | 336 of 688 |

Next idea for unmatched assets: match by `IFCguid` / `Unique_ID` custom attribute against the model's external IDs (`model.getExternalIdMapping`). Not built yet.
