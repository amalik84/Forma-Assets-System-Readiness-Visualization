"""Place each reference in a lifecycle phase: design, execution or handover.

Forma has no phase field, so the phase is derived from the item type (docs/05, "Lifecycle").
The dashboard labels it as derived. Change the tables below to fit a project.
"""

PHASES = [
    {"id": "design", "label": "Design", "hint": "Models, drawings, design and coordination issues, RFIs"},
    {"id": "execution", "label": "Execution", "hint": "Quality, safety and daily forms, punch lists, schedule, meetings"},
    {"id": "handover", "label": "Handover and operations", "hint": "Commissioning issues and forms"},
]

# Issue type name (lower case) -> phase. Anything not listed counts as execution.
ISSUE_TYPES = {
    "design": "design", "coordination": "design", "interface queries": "design", "viewpoints": "design",
    "commissioning": "handover", "warranty": "handover", "handover": "handover",
}

# Form template type suffix (pg.template_type.<x>) -> phase. Anything not listed counts as execution.
FORM_TYPES = {"commissioning": "handover", "handover": "handover"}

# Other relationship types -> phase.
OTHER_TYPES = {
    "documentlineage": "design", "documentversion": "design", "sheetlineage": "design", "rfi": "design",
    "submittalitem": "design", "markup": "design", "markupdocument": "design", "markupsheethistory": "design",
    "specification": "design", "review": "design", "package": "design",
}


def phase_of(ref):
    """ref: a reference dict with 'type' plus 'itemType' (issue type) or 'templateType' (forms)."""
    typ = ref.get("type")
    if typ == "issue":
        return ISSUE_TYPES.get((ref.get("itemType") or "").strip().lower(), "execution")
    if typ == "form":
        suffix = (ref.get("templateType") or "").rsplit(".", 1)[-1].lower()
        return FORM_TYPES.get(suffix, "execution")
    return OTHER_TYPES.get(typ, "execution")
