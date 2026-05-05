import json
import re

from app.generation.service import get_text_generator


EMPTY_STRUCTURE = {
    "goal": "",
    "subgoals": [],
    "constraints": [],
    "domain": "",
}


def extract_semantics(task, text_generator=None):
    generator = text_generator or get_text_generator()
    prompt = build_semantic_prompt(task)
    try:
        generated = generator.generate(prompt, max_chars=180)
        structure = parse_semantic_json(generated)
        if useful_semantics(structure):
            return normalize_semantics(structure)
    except Exception as exc:
        print(f"semantic extraction не дал полезного результата: {exc}", flush=True)
    return fallback_semantics(task)


def build_semantic_prompt(task):
    title = _clean(task.get("title") or "")
    description = _clean(task.get("description") or "")
    context = _clean(task.get("context") or "")
    return "\n".join(
        [
            "semantic_json | Извлеки смысл задачи и верни только JSON без пояснений.",
            f"title: {title}",
            f"description: {description}",
            f"context: {context}",
            "Формат: {\"goal\":\"...\",\"subgoals\":[\"...\"],\"constraints\":[\"...\"],\"domain\":\"...\"}",
            "goal: главный ожидаемый результат.",
            "subgoals: 3-6 конкретных подцелей из текста задачи.",
            "constraints: сроки, бюджет, формат, документы, ограничения или условия.",
            "domain: короткая предметная область задачи.",
        ]
    )


def parse_semantic_json(text):
    payload = _extract_json_object(text)
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        return EMPTY_STRUCTURE.copy()
    return parsed


def normalize_semantics(value):
    goal = _clean(value.get("goal") or "")
    subgoals = _clean_list(value.get("subgoals"))
    constraints = _clean_list(value.get("constraints"))
    return {
        "goal": goal,
        "subgoals": subgoals,
        "constraints": constraints,
        "domain": normalize_domain(value.get("domain") or "", goal, subgoals, constraints),
    }


def useful_semantics(value):
    normalized = normalize_semantics(value)
    return bool(normalized["goal"] or normalized["subgoals"] or normalized["domain"])


def fallback_semantics(task):
    title = _clean(task.get("title") or "задача")
    description = _clean(task.get("description") or "")
    context = _clean(task.get("context") or "")
    subgoals = _extract_clauses(description) or _extract_clauses(title)
    constraints = []

    if context:
        constraints.append(context)
    if task.get("deadline"):
        constraints.append(f"дедлайн: {task['deadline']}")
    if task.get("estimated_minutes"):
        constraints.append(f"оценка времени: {task['estimated_minutes']} минут")

    return normalize_semantics(
        {
            "goal": title,
            "subgoals": subgoals,
            "constraints": constraints,
            "domain": _infer_domain(title, description, context),
        }
    )


def _extract_json_object(text):
    if not text:
        return "{}"
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return "{}"
    return text[start : end + 1]


def _extract_clauses(text):
    text = re.sub(r"^(нужно|надо|следует)\s+", "", _clean(text), flags=re.IGNORECASE)
    parts = re.split(r"[,.;]|\s+и\s+|\s+а также\s+", text)
    result = []
    for part in parts:
        part = _clean(part)
        if len(part) >= 4 and part.lower() not in {"нужно", "надо", "задача"}:
            result.append(part[:90])
    return result[:6]


def _infer_domain(title, description, context):
    return normalize_domain("", title, _extract_clauses(description), [context])


def normalize_domain(domain, goal="", subgoals=None, constraints=None):
    text = _clean(
        " ".join(
            [
                str(domain or ""),
                str(goal or ""),
                " ".join(subgoals or []),
                " ".join(constraints or []),
            ]
        )
    ).lower()
    if not text:
        return ""
    checks = (
        ("travel", ("отпуск", "поезд", "маршрут", "жиль", "бюджет", "документ", "билет")),
        ("presentation", ("презентац", "слайд", "выступлен", "доклад")),
        ("email", ("письм", "почт", "ответ", "адресат")),
        ("research", ("гипотез", "эксперимент", "критери", "исслед")),
        ("study", ("учеб", "глава", "конспект", "магистер", "диссертац")),
    )
    for code, markers in checks:
        if any(marker in text for marker in markers):
            return code
    raw = _clean(domain).lower()
    if raw in {"travel", "research", "presentation", "email", "study"}:
        return raw
    return "general"


def _clean_list(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        cleaned = _clean(item)
        if cleaned and cleaned not in result:
            result.append(cleaned[:120])
    return result[:7]


def _clean(value):
    return " ".join(str(value).split())
