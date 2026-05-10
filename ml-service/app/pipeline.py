from app.catalog.repository import load_catalog
from app.generation.response_generator import generate_response
from app.models.recurrent import encode_text_sequence
from app.models.perceptron import choose_method
from app.planning.combined_template import build_combined_template
from app.semantic.extractor import extract_semantics


def analyze_task(task):
    text = " ".join(
        str(task.get(field, ""))
        for field in ("title", "description", "context")
    )
    catalog = load_catalog()
    sequence_state = encode_text_sequence(text)
    prediction = choose_method(task, sequence_state, catalog["methods"])
    selected_methods = prediction.get("selected_methods") or []
    template = build_combined_template(selected_methods, catalog["templates"])
    if not template.get("steps"):
        template = catalog["templates"].get(prediction["method_code"])
    if not template:
        raise RuntimeError(f"в БД нет шаблона плана для метода {prediction['method_code']}")
    semantic_structure = extract_semantics(task)
    generated = generate_response(task, prediction, template, semantic_structure=semantic_structure)

    return {
        "method_code": prediction["method_code"],
        "method_name": prediction["method_name"],
        "confidence": prediction["confidence"],
        "primary_method_code": prediction["method_code"],
        "primary_method_name": prediction["method_name"],
        "primary_method_confidence": prediction["confidence"],
        "legacy_method_note": "method_code/method_name оставлены для совместимости; итоговый план строится по selected_methods",
        "selection_mode": prediction["selection_mode"],
        "combination_confidence": prediction["combination_confidence"],
        "reason": prediction["reason"],
        "scores": prediction["scores"],
        "ranked_methods": prediction["ranked_methods"],
        "selected_methods": selected_methods,
        "explanation": prediction["explanation"],
        "planning_params": prediction["planning_params"],
        "planning_params_source": prediction["planning_params_source"],
        "summary": generated["summary"],
        "plan_draft": generated["plan_draft"],
        "schedule_hint": generated["schedule_hint"],
        "semantic_structure": semantic_structure,
    }
