from app.catalog.repository import load_catalog
from app.generation.response_generator import generate_response
from app.models.recurrent import encode_text_sequence
from app.models.perceptron import choose_method
from app.semantic.extractor import extract_semantics


def analyze_task(task):
    text = " ".join(
        str(task.get(field, ""))
        for field in ("title", "description", "context")
    )
    catalog = load_catalog()
    sequence_state = encode_text_sequence(text)
    prediction = choose_method(task, sequence_state, catalog["methods"])
    template = catalog["templates"].get(prediction["method_code"])
    if not template:
        raise RuntimeError(f"в БД нет шаблона плана для метода {prediction['method_code']}")
    semantic_structure = extract_semantics(task)
    generated = generate_response(task, prediction, template, semantic_structure=semantic_structure)

    return {
        "method_code": prediction["method_code"],
        "method_name": prediction["method_name"],
        "confidence": prediction["confidence"],
        "reason": prediction["reason"],
        "scores": prediction["scores"],
        "planning_params": prediction["planning_params"],
        "summary": generated["summary"],
        "plan_draft": generated["plan_draft"],
        "schedule_hint": generated["schedule_hint"],
        "semantic_structure": semantic_structure,
    }
