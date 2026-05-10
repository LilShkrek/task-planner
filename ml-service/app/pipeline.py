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
    semantic_structure = extract_semantics(task)
    task_for_selection = dict(task)
    task_for_selection["_semantic_structure"] = semantic_structure
    prediction = choose_method(task_for_selection, sequence_state, catalog["methods"])
    selected_methods = prediction.get("selected_methods") or []
    template = build_combined_template(selected_methods, catalog["templates"])
    if not template.get("steps"):
        template = catalog["templates"].get(prediction["method_code"])
    if not template:
        raise RuntimeError(f"в БД нет шаблона плана для метода {prediction['method_code']}")
    generated = generate_response(task, prediction, template, semantic_structure=semantic_structure)
    compatibility = {
        "method_code": prediction["method_code"],
        "method_name": prediction["method_name"],
        "confidence": prediction["confidence"],
        "primary_method_code": prediction["method_code"],
        "primary_method_name": prediction["method_name"],
        "primary_method_confidence": prediction["confidence"],
        "note": "legacy поля сохранены для совместимости; пользовательская логика строится по selected_methods",
    }

    return {
        "selection_mode": prediction["selection_mode"],
        "user_facing_primary_strategy": f"Комбинированный план из {len(selected_methods)} методов",
        "selected_methods": selected_methods,
        "combination_confidence": prediction["combination_confidence"],
        "explanation": prediction["explanation"],
        "semantic_structure": semantic_structure,
        "planning_params": prediction["planning_params"],
        "planning_params_source": prediction["planning_params_source"],
        "summary": generated["summary"],
        "schedule_hint": generated["schedule_hint"],
        "plan_draft": generated["plan_draft"],
        "ranked_methods": prediction["ranked_methods"],
        "scores": prediction["scores"],
        "legacy_compatibility": compatibility,
        "method_code": prediction["method_code"],
        "method_name": prediction["method_name"],
        "confidence": prediction["confidence"],
        "primary_method_code": prediction["method_code"],
        "primary_method_name": prediction["method_name"],
        "primary_method_confidence": prediction["confidence"],
        "legacy_method_note": compatibility["note"],
        "reason": prediction["reason"],
    }
