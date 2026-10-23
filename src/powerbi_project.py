"""Write the Power BI project (.pbip): semantic model in TMDL plus a three-page report.

Called by export_powerbi.py. Everything is generated here so the model always matches the CSV columns.
Report format: PBIR-Legacy (report.json), which every recent Power BI Desktop opens.
Look and feel: an Autodesk-style theme (warm slate page, white panels, black header and tiles,
tertiary colours for status only), written as a custom theme file next to the report.
"""

import json
import shutil
import uuid
from pathlib import Path

NAME = "Forma System Readiness"
BASE_THEME = "CY24SU10"
THEME_DIR = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\WebView2Resources\minerva\SHAREDRESOURCES\BASETHEMES")
CUSTOM_THEME = "AutodeskReadiness.json"
NS = uuid.UUID("6b1f3c1e-2a7d-4f53-9a4e-5d1c0f6e8a11")

# Autodesk palette (same as the web dashboard). Tertiaries for status only.
BLACK, WHITE, YELLOW = "#000000", "#FFFFFF", "#FFFF00"
WARM_SLATE, WARM_SLATE_100, WARM_SLATE_300, SLATE = "#D5D5CB", "#F5F5F0", "#E4E4DB", "#666666"
MORNING, MORNING_100 = "#2AD0A9", "#D5F6EE"
DUSK, DUSK_100 = "#F2520A", "#FFDDCD"
DAWN, DAWN_100 = "#F09D4F", "#FFE9C5"
SLATE_100 = "#E8E8E8"


def tag(*parts):
    """Stable lineage tags, so regenerating the project does not look like a new model."""
    return str(uuid.uuid5(NS, "/".join(parts)))


# ---------- semantic model ----------

# table -> (csv file, [(csv column, tmdl type, m type, properties)]); "name" in properties = display name in Power BI
T = "string", "type text"
I = "int64", "Int64.Type"
B = "boolean", "type logical"
D = "dateTime", "type date"
HIDDEN = {"isHidden": True}
TABLES = {
    "Systems": ("systems.csv", [
        ("SystemId", *T, HIDDEN), ("System", *T, {}), ("Status", *T, HIDDEN),
        ("Readiness", *T, {"sortByColumn": "ReadinessOrder"}), ("ReadinessOrder", *I, HIDDEN),
        ("IsUnassigned", *B, HIDDEN), ("Assets", *I, {}), ("AssetsWithLinks", *I, {"name": "Assets with links"}),
        ("AssetsNotReady", *I, {"name": "Not ready"}), ("AssetsUnknown", *I, {"name": "Unknown"}),
        ("BlockingItems", *I, {"name": "Blocking"})]),
    "Assets": ("assets.csv", [
        ("AssetId", *T, HIDDEN), ("Asset", *T, {}), ("SystemId", *T, HIDDEN), ("Category", *T, {}),
        ("Barcode", *T, {}), ("AssetStatus", *T, {"name": "Forma status"}), ("Status", *T, HIDDEN),
        ("Readiness", *T, {"sortByColumn": "ReadinessOrder"}), ("ReadinessOrder", *I, HIDDEN),
        ("BlockingCount", *I, {"name": "Blocking"}), ("UnknownCount", *I, {"name": "Unknown"}),
        ("ReferenceCount", *I, {"name": "Links"}), ("LifecycleKey", *T, HIDDEN),
        ("FormaUrl", *T, {"name": "Forma link", "dataCategory": "WebUrl"})]),
    "References": ("references.csv", [
        ("AssetId", *T, HIDDEN), ("ItemKey", *T, HIDDEN), ("ItemType", *T, {"name": "Type"}), ("Item", *T, {}),
        ("State", *T, {"name": "State code", "isHidden": True}), ("StateLabel", *T, {"name": "State"}),
        ("Phase", *T, {"sortByColumn": "PhaseOrder"}), ("PhaseOrder", *I, HIDDEN),
        ("ItemStatus", *T, {"name": "Status"}), ("Detail", *T, {}), ("DueDate", *D, {"name": "Due"}),
        ("Depth", *I, HIDDEN), ("LinkPath", *T, {"name": "Why linked"}),
        ("FormaUrl", *T, {"name": "Forma link", "dataCategory": "WebUrl"})]),
    "Lifecycle": ("lifecycle.csv", [
        ("LifecycleKey", *T, HIDDEN), ("LifecycleSet", *T, {"name": "Lifecycle set"}), ("Step", *T, {}),
        ("StepNumber", *I, HIDDEN)]),
    "Meta": ("meta.csv", [
        ("Project", *T, {}), ("SnapshotDay", *T, {}), ("GeneratedAt", *T, {}), ("MaxDepth", *I, {}),
        ("IssueDoneStatuses", *T, {}), ("FormDoneStatuses", *T, {}), ("SystemGrouping", *T, {})]),
}


def colour_switch(column):
    return (f'SWITCH(SELECTEDVALUE({column}), "ready", "{MORNING_100}", "not_ready", "{DUSK_100}", '
            f'"unknown", "{DAWN_100}", "blocking", "{DUSK_100}", "done", "{MORNING_100}", "{SLATE_100}")')


MEASURES = {
    "Systems": [
        ("Systems total", "CALCULATE(COUNTROWS(Systems), Systems[IsUnassigned] = FALSE())", "0"),
        ("Systems ready", 'CALCULATE(COUNTROWS(Systems), Systems[Status] = "ready", Systems[IsUnassigned] = FALSE())', "0"),
        ("Systems not ready", 'CALCULATE(COUNTROWS(Systems), Systems[Status] = "not_ready", Systems[IsUnassigned] = FALSE())', "0"),
        ("Systems unknown", 'CALCULATE(COUNTROWS(Systems), Systems[Status] = "unknown", Systems[IsUnassigned] = FALSE())', "0"),
        ("System colour", colour_switch("Systems[Status]"), None),
    ],
    "Assets": [
        ("Asset count", "COUNTROWS(Assets)", "0"),
        ("Assets not ready", 'CALCULATE(COUNTROWS(Assets), Assets[Status] = "not_ready")', "0"),
        ("Asset colour", colour_switch("Assets[Status]"), None),
    ],
    "References": [
        ("Linked items", "DISTINCTCOUNT(References[ItemKey])", "0"),
        ("Blocking items", 'CALCULATE(DISTINCTCOUNT(References[ItemKey]), References[State code] = "blocking")', "0"),
        ("Open issues linked", 'CALCULATE(DISTINCTCOUNT(References[ItemKey]), References[State code] = "blocking", References[Type] = "Issue")', "0"),
        ("Open forms linked", 'CALCULATE(DISTINCTCOUNT(References[ItemKey]), References[State code] = "blocking", References[Type] = "Form")', "0"),
        ("State colour", colour_switch("References[State code]"), None),
    ],
    "Meta": [
        ("Project name", "SELECTEDVALUE(Meta[Project])", None),
        ("Data as of", '"Data as of " & SELECTEDVALUE(Meta[GeneratedAt])', None),
    ],
}

RELATIONSHIPS = [("Assets", "SystemId", "Systems", "SystemId"),
                 ("References", "AssetId", "Assets", "AssetId"),
                 ("Assets", "LifecycleKey", "Lifecycle", "LifecycleKey")]


def q(name):
    return f"'{name}'" if " " in name else name


def table_tmdl(table, csv_name, columns):
    lines = [f"table {table}", f"\tlineageTag: {tag(table)}", ""]
    for name, expr, fmt in MEASURES.get(table, []):
        lines.append(f"\tmeasure {q(name)} = {expr}")
        if fmt:
            lines.append(f"\t\tformatString: {fmt}")
        lines += [f"\t\tlineageTag: {tag(table, 'm', name)}", ""]
    for source, dtype, _mtype, props in columns:
        props = dict(props)
        name = props.pop("name", source)
        lines += [f"\tcolumn {q(name)}", f"\t\tdataType: {dtype}"]
        if dtype == "int64":
            lines.append("\t\tformatString: 0")
        if dtype == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd")
        lines += [f"\t\tlineageTag: {tag(table, source)}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {source}"]
        for key, value in props.items():
            lines.append(f"\t\t{key}" if value is True else f"\t\t{key}: {value}")
        lines.append("")
    types = ", ".join(f'{{"{s}", {m}}}' for s, _d, m, _p in columns)
    dates = [s for s, d, _m, _p in columns if d == "dateTime"]
    m = ["let",
         f'    Source = Csv.Document(File.Contents(DataFolder & "{csv_name}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),',
         "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),"]
    last = "Promoted"
    if dates:
        cols = ", ".join(f'"{d}"' for d in dates)
        m.append(f'    Blanks = Table.ReplaceValue({last}, "", null, Replacer.ReplaceValue, {{{cols}}}),')
        last = "Blanks"
    m += [f'    Typed = Table.TransformColumnTypes({last}, {{{types}}}, "en-GB")', "in", "    Typed"]
    lines += [f"\tpartition {table} = m", "\t\tmode: import", "\t\tsource ="]
    lines += ["\t\t\t\t" + line for line in m]
    lines += ["", "\tannotation PBI_ResultType = Table", ""]
    return "\n".join(lines)


def write_model(root, data_folder):
    sm = root / f"{NAME}.SemanticModel"
    d = sm / "definition"
    (d / "tables").mkdir(parents=True, exist_ok=True)
    (sm / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2), encoding="utf-8")
    (sm / ".platform").write_text(json.dumps(platform("SemanticModel"), indent=2), encoding="utf-8")
    (d / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1567\n", encoding="utf-8")
    model = ["model Model", "\tculture: en-GB", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-GB", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             "annotation PBI_QueryOrder = " + json.dumps(["DataFolder", *TABLES]), "",
             *[f"ref table {t}" for t in TABLES], ""]
    (d / "model.tmdl").write_text("\n".join(model), encoding="utf-8")
    folder = data_folder.replace('"', '""')
    (d / "expressions.tmdl").write_text(
        f'expression DataFolder = "{folder}" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
        f"\tlineageTag: {tag('DataFolder')}\n\n\tannotation PBI_ResultType = Text\n", encoding="utf-8")
    rels = []
    for ft, fc, tt, tc in RELATIONSHIPS:
        rels += [f"relationship {tag('rel', ft, fc, tt)}", f"\tfromColumn: {ft}.{fc}", f"\ttoColumn: {tt}.{tc}", ""]
    (d / "relationships.tmdl").write_text("\n".join(rels), encoding="utf-8")
    for table, (csv_name, columns) in TABLES.items():
        (d / "tables" / f"{table}.tmdl").write_text(table_tmdl(table, csv_name, columns), encoding="utf-8")


def platform(kind):
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": kind, "displayName": NAME},
            "config": {"version": "2.0", "logicalId": tag("platform", kind)}}


# ---------- theme ----------

def solid(colour):
    return {"solid": {"color": colour}}


def theme():
    font = "Segoe UI"  # installed on every Windows PC; Artifakt is not available to Power BI
    return {
        "name": "Autodesk readiness",
        "dataColors": [BLACK, DUSK, DAWN, MORNING, SLATE, WARM_SLATE, "#1D91D0", "#FEC681"],
        "background": WHITE, "foreground": BLACK, "tableAccent": BLACK,
        "good": MORNING, "neutral": DAWN, "bad": DUSK, "maximum": DUSK, "center": DAWN, "minimum": MORNING,
        "textClasses": {
            "callout": {"fontSize": 26, "fontFace": f"{font} Semibold", "color": BLACK},
            "title": {"fontSize": 12, "fontFace": f"{font} Semibold", "color": BLACK},
            "header": {"fontSize": 11, "fontFace": f"{font} Semibold", "color": BLACK},
            "label": {"fontSize": 10, "fontFace": font, "color": BLACK},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": solid(WHITE), "transparency": 0}],
                "border": [{"show": False}],
                "dropShadow": [{"show": False}],
                "title": [{"show": True, "fontColor": solid(BLACK), "fontSize": 12, "bold": True, "alignment": "left"}],
                "visualHeader": [{"show": True, "background": solid(WHITE), "foreground": solid(SLATE)}],
            }},
            "page": {"*": {
                "background": [{"color": solid(WARM_SLATE_100), "transparency": 0}],
                "outspace": [{"color": solid(WARM_SLATE_100), "transparency": 0}],
            }},
            "card": {"*": {
                "labels": [{"fontSize": 26, "color": solid(BLACK)}],
                "categoryLabels": [{"show": True, "fontSize": 10, "color": solid(SLATE)}],
            }},
            "tableEx": {"*": {
                "columnHeaders": [{"fontColor": solid(WHITE), "backColor": solid(BLACK), "fontSize": 10, "bold": True,
                                   "wordWrap": True}],
                "values": [{"fontColorPrimary": solid(BLACK), "backColorPrimary": solid(WHITE),
                            "fontColorSecondary": solid(BLACK), "backColorSecondary": solid(WARM_SLATE_100),
                            "fontSize": 10, "urlIcon": True}],
                "grid": [{"gridHorizontal": True, "gridHorizontalColor": solid(WARM_SLATE_300), "gridVertical": False,
                          "rowPadding": 4, "outlineColor": solid(BLACK)}],
                "total": [{"totals": False}],
            }},
            "slicer": {"*": {
                "header": [{"show": True, "fontColor": solid(SLATE), "textSize": 9}],
                "items": [{"fontColor": solid(BLACK), "textSize": 10}],
            }},
            "clusteredBarChart": {"*": {
                "categoryAxis": [{"color": solid(BLACK), "fontSize": 10, "showAxisTitle": False}],
                "valueAxis": [{"show": False, "gridlineShow": False, "showAxisTitle": False}],
                "labels": [{"show": True, "color": solid(BLACK), "fontSize": 10}],
                "dataPoint": [{"defaultColor": solid(DUSK)}],
            }},
            "clusteredColumnChart": {"*": {
                "categoryAxis": [{"color": solid(BLACK), "fontSize": 9, "showAxisTitle": False}],
                "valueAxis": [{"show": False, "gridlineShow": False, "showAxisTitle": False}],
                "labels": [{"show": True, "color": solid(BLACK), "fontSize": 9}],
                "dataPoint": [{"defaultColor": solid(BLACK)}],
            }},
        },
    }


# ---------- report ----------

def lit(value):
    """Power BI literal expression: strings in quotes, numbers with D, booleans as is."""
    if isinstance(value, bool):
        v = "true" if value else "false"
    elif isinstance(value, (int, float)):
        v = f"{value}D"
    else:
        v = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": v}}}


def colour(value):
    return {"solid": {"color": lit(value)}}


def field(entity, prop, measure=False):
    return {"entity": entity, "prop": prop, "measure": measure}


def visual(vid, vtype, x, y, w, h, roles, title=None, order=None, objects=None, vc=None):
    """roles: {role: [field, ...]}. Builds a PBIR-Legacy visual container."""
    sources, select, projections = {}, [], {}
    for role, fields in roles.items():
        projections[role] = []
        for f in fields:
            alias = sources.setdefault(f["entity"], f"t{len(sources)}")
            kind = "Measure" if f["measure"] else "Column"
            ref = f"{f['entity']}.{f['prop']}"
            item = {kind: {"Expression": {"SourceRef": {"Source": alias}}, "Property": f["prop"]}, "Name": ref}
            if not any(s["Name"] == ref for s in select):
                select.append(item)
            projections[role].append({"queryRef": ref})
    query = {"Version": 2, "From": [{"Name": a, "Entity": e, "Type": 0} for e, a in sources.items()], "Select": select}
    if order:
        f, direction = order
        kind = "Measure" if f["measure"] else "Column"
        query["OrderBy"] = [{"Direction": direction, "Expression": {
            kind: {"Expression": {"SourceRef": {"Source": sources[f["entity"]]}}, "Property": f["prop"]}}}]
    single = {"visualType": vtype, "projections": projections, "prototypeQuery": query, "drillFilterOtherVisuals": True}
    vco = dict(vc or {})
    vco["title"] = [{"properties": {"show": lit(bool(title)), **({"text": lit(title)} if title else {})}}]
    single["vcObjects"] = vco
    if objects:
        single["objects"] = objects
    config = {"name": vid, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": 0, "width": w, "height": h}}],
              "singleVisual": single}
    return {"x": x, "y": y, "z": 0, "width": w, "height": h, "config": json.dumps(config), "filters": "[]"}


def black_background():
    return {"background": [{"properties": {"show": lit(True), "color": colour(BLACK), "transparency": lit(0)}}]}


def header_card(vid, x, w, measure, size):
    """Text on the black header band, like the web dashboard."""
    return visual(vid, "card", x, 0, w, 64, {"Values": [field("Meta", measure, True)]}, vc=black_background(), objects={
        "labels": [{"properties": {"color": colour(WHITE), "fontSize": lit(size)}}],
        "categoryLabels": [{"properties": {"show": lit(False)}}]})


def kpi(vid, x, w, table, measure):
    return visual(vid, "card", x, 72, w, 96, {"Values": [field(table, measure, True)]}, vc=black_background(), objects={
        "labels": [{"properties": {"color": colour(WHITE), "fontSize": lit(28)}}],
        "categoryLabels": [{"properties": {"show": lit(True), "color": colour(WARM_SLATE), "fontSize": lit(10)}}]})


def status_fill(table, column, measure):
    """Conditional background on one table column, driven by a colour measure. Also hides the totals row."""
    return {"total": [{"properties": {"totals": lit(False)}}], "values": [{
        "properties": {"backColor": {"solid": {"color": {"expr": {
            "Measure": {"Expression": {"SourceRef": {"Entity": table}}, "Property": measure}}}}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"{table}.{column}"}}]}


def widths(table_widths, base=None):
    """Fixed column widths for a table visual, so every column fits without scrolling."""
    objects = dict(base or {})
    objects["columnWidth"] = [{"properties": {"value": lit(w)}, "selector": {"metadata": ref}} for ref, w in table_widths]
    return objects


def dropdown():
    return {"data": [{"properties": {"mode": lit("Dropdown")}}]}


def section(sid, name, ordinal, visuals):
    return {"name": sid, "displayName": name, "displayOption": 1, "width": 1280, "height": 720, "ordinal": ordinal,
            "config": "{}", "filters": "[]", "visualContainers": visuals}


def header():
    return [header_card("hdrProject", 0, 860, "Project name", 18), header_card("hdrAsOf", 860, 420, "Data as of", 12)]


def pages():
    S, A, R, L = "Systems", "Assets", "References", "Lifecycle"
    tiles = [(S, "Systems total"), (S, "Systems ready"), (S, "Systems not ready"), (S, "Systems unknown"),
             (R, "Open issues linked"), (R, "Open forms linked")]
    tile_w = (1280 - 32 - 5 * 8) // 6
    overview = header() + [kpi(f"kpi{i}", 16 + i * (tile_w + 8), tile_w, t, m) for i, (t, m) in enumerate(tiles)]
    overview += [
        visual("sysTable", "tableEx", 16, 180, 772, 524, {"Values": [
            field(S, "System"), field(S, "Readiness"), field(S, "Assets"), field(S, "Assets with links"),
            field(S, "Not ready"), field(S, "Unknown"), field(S, "Blocking")]},
            "Systems, not ready first", (field(S, "Readiness"), 1), objects=status_fill(S, "Readiness", "System colour")),
        visual("sysBar", "clusteredBarChart", 796, 180, 468, 524, {
            "Category": [field(S, "System")], "Y": [field(R, "Blocking items", True)]},
            "Blocking items per system", (field(R, "Blocking items", True), 2)),
    ]
    assets = header() + [
        visual("aSlicerSys", "slicer", 16, 72, 240, 300, {"Values": [field(S, "System")]}, "System"),
        visual("aSlicerReady", "slicer", 16, 380, 240, 130, {"Values": [field(A, "Readiness")]}, "Readiness"),
        visual("aSlicerSet", "slicer", 16, 518, 240, 80, {"Values": [field(L, "Lifecycle set")]}, "Lifecycle set",
               objects=dropdown()),
        visual("aLifecycle", "clusteredColumnChart", 264, 72, 1000, 228, {
            "Category": [field(L, "Step")], "Y": [field(A, "Asset count", True)]},
            "Assets per lifecycle step (pick a lifecycle set to compare like with like)", (field(L, "Step"), 1)),
        visual("aTable", "tableEx", 264, 308, 1000, 396, {"Values": [
            field(A, "Asset"), field(A, "Readiness"), field(A, "Category"), field(A, "Forma status"),
            field(A, "Blocking"), field(A, "Unknown"), field(A, "Links"), field(A, "Forma link")]},
            "Assets", (field(A, "Readiness"), 1), objects=status_fill(A, "Readiness", "Asset colour")),
    ]
    blocking = header() + [
        visual("bSlicerState", "slicer", 16, 72, 240, 160, {"Values": [field(R, "State")]}, "State"),
        visual("bSlicerPhase", "slicer", 16, 240, 240, 130, {"Values": [field(R, "Phase")]}, "Lifecycle phase"),
        visual("bSlicerSys", "slicer", 16, 378, 240, 326, {"Values": [field(S, "System")]}, "System"),
        visual("bPhase", "clusteredBarChart", 264, 72, 1000, 176, {
            "Category": [field(R, "Phase")], "Y": [field(R, "Blocking items", True)]},
            "Blocking items per lifecycle phase", (field(R, "Phase"), 1)),
        visual("bTable", "tableEx", 264, 256, 1000, 448, {"Values": [
            field(A, "Asset"), field(R, "Type"), field(R, "Item"), field(R, "State"), field(R, "Phase"),
            field(R, "Status"), field(R, "Due"), field(R, "Why linked"), field(R, "Forma link")]},
            "Linked issues, forms and other items", (field(R, "State"), 1),
            objects=widths([("Assets.Asset", 200), ("References.Type", 56), ("References.Item", 220),
                            ("References.State", 78), ("References.Phase", 104), ("References.Status", 80),
                            ("References.Due", 84), ("References.Why linked", 112), ("References.Forma link", 46)],
                           status_fill(R, "State", "State colour"))),
    ]
    return [section("overview", "Overview", 0, overview), section("assets", "Assets and lifecycle", 1, assets),
            section("blocking", "Blocking items", 2, blocking)]


def write_report(root, active_page=0):
    rp = root / f"{NAME}.Report"
    rp.mkdir(parents=True, exist_ok=True)
    (rp / ".platform").write_text(json.dumps(platform("Report"), indent=2), encoding="utf-8")
    (rp / "definition.pbir").write_text(json.dumps(
        {"version": "1.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}, "byConnection": None}},
        indent=2), encoding="utf-8")
    resources = []
    theme_src = THEME_DIR / f"{BASE_THEME}.JSON"
    if theme_src.exists():
        dst = rp / "StaticResources" / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(theme_src, dst)
        resources.append({"resourcePackage": {"name": "SharedResources", "type": 2, "disabled": False,
                                              "items": [{"type": 202, "path": f"BaseThemes/{BASE_THEME}.json", "name": BASE_THEME}]}})
    custom = rp / "StaticResources" / "RegisteredResources" / CUSTOM_THEME
    custom.parent.mkdir(parents=True, exist_ok=True)
    custom.write_text(json.dumps(theme(), indent=2), encoding="utf-8")
    resources.append({"resourcePackage": {"name": "RegisteredResources", "type": 1, "disabled": False,
                                          "items": [{"type": 201, "path": CUSTOM_THEME, "name": CUSTOM_THEME}]}})
    config = {"version": "5.59", "themeCollection": {
                  "baseTheme": {"name": BASE_THEME, "version": "5.59", "type": 2},
                  "customTheme": {"name": CUSTOM_THEME, "version": "5.59", "type": 1}},
              "activeSectionIndex": active_page, "defaultDrillFilterOtherVisuals": True}
    report = {"config": json.dumps(config), "layoutOptimization": 0, "resourcePackages": resources, "sections": pages()}
    (rp / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_project(root, data_folder, active_page=0):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    for old in (root / f"{NAME}.SemanticModel", root / f"{NAME}.Report"):
        if old.exists():
            shutil.rmtree(old)
    write_model(root, data_folder)
    write_report(root, active_page)
    pbip = root / f"{NAME}.pbip"
    pbip.write_text(json.dumps({"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                "settings": {"enableAutoRecovery": True}}, indent=2), encoding="utf-8")
    return pbip
