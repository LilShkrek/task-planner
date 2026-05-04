from app.catalog.repository import load_catalog
from app.planning.generator import generate_plan
from app.planning.scheduler import build_schedule_hint
from app.models.recurrent import encode_text_sequence
from app.models.perceptron import choose_method


def analyze_task(task):
    text = " ".join(
        str(task.get(field, ""))
        for field in ("title", "description", "context")
    )
    catalog = load_catalog()
    sequence_state = encode_text_sequence(text)
    prediction = choose_method(task, sequence_state, catalog["methods"])
    plan_draft = generate_plan(task, prediction, catalog["templates"])
    schedule_hint = build_schedule_hint(task, prediction, catalog["templates"])

    return {
        "method_code": prediction["method_code"],
        "method_name": prediction["method_name"],
        "confidence": prediction["confidence"],
        "reason": prediction["reason"],
        "scores": prediction["scores"],
        "planning_params": prediction["planning_params"],
        "plan_draft": plan_draft,
        "schedule_hint": schedule_hint,
    }
