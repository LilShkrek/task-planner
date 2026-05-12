import json
import re

from app.generation.service import get_text_generator


EMPTY_STRUCTURE = {
    "goal": "",
    "subgoals": [],
    "constraints": [],
    "domain": "",
    "base_subgoals_from_title": [],
    "description_hints": [],
    "merged_subgoals": [],
    "decomposition_confidence": 0.0,
}


def extract_semantics(task, text_generator=None):
    generator = text_generator or get_text_generator()
    autonomous = autonomous_decomposition(task)
    prompt = build_semantic_prompt(task)
    try:
        generated = generator.generate(prompt, max_chars=180)
        structure = parse_semantic_json(generated)
        if useful_semantics(structure):
            return finalize_semantics(task, structure, autonomous)
    except Exception as exc:
        print(f"semantic extraction не дал полезного результата: {exc}", flush=True)
    return finalize_semantics(task, {}, autonomous)


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
    base_subgoals = _clean_list(value.get("base_subgoals_from_title"))
    description_hints = _clean_list(value.get("description_hints"))
    merged_subgoals = _clean_list(value.get("merged_subgoals")) or subgoals
    return {
        "goal": goal,
        "subgoals": merged_subgoals,
        "constraints": constraints,
        "domain": normalize_domain(value.get("domain") or "", goal, merged_subgoals, constraints),
        "base_subgoals_from_title": base_subgoals,
        "description_hints": description_hints,
        "merged_subgoals": merged_subgoals,
        "decomposition_confidence": float(value.get("decomposition_confidence") or 0.0),
    }


def useful_semantics(value):
    normalized = normalize_semantics(value)
    return bool(normalized["goal"] or normalized["subgoals"] or normalized["domain"])


def fallback_semantics(task):
    return finalize_semantics(task, {}, autonomous_decomposition(task))


def autonomous_decomposition(task):
    title = _clean(task.get("title") or "задача")
    description = _clean(task.get("description") or "")
    context = _clean(task.get("context") or "")
    domain = _infer_domain(title, "", context)
    base_subgoals = _title_first_subgoals(title, context, domain)
    description_hints = _description_hints(description)
    constraints = _constraints(task, context)
    merged_subgoals = _merge_subgoals(base_subgoals, description_hints)

    return {
        "goal": title,
        "base_subgoals_from_title": base_subgoals,
        "description_hints": description_hints,
        "merged_subgoals": merged_subgoals,
        "constraints": constraints,
        "domain": domain,
        "decomposition_confidence": _decomposition_confidence(base_subgoals, description_hints),
    }


def finalize_semantics(task, generated_structure, autonomous):
    title = _clean(task.get("title") or "задача")
    description = _clean(task.get("description") or "")
    context = _clean(task.get("context") or "")
    generated = normalize_semantics(generated_structure)

    base_subgoals = autonomous["base_subgoals_from_title"]
    description_hints = _merge_subgoals(
        autonomous["description_hints"],
        _description_hints(" ".join(generated.get("subgoals") or [])),
    )
    merged_subgoals = _merge_subgoals(base_subgoals, description_hints)
    constraints = _merge_constraints(autonomous["constraints"], _clean_list(generated_structure.get("constraints")))
    domain = normalize_domain(generated.get("domain") or autonomous["domain"], title, merged_subgoals, constraints)

    return normalize_semantics(
        {
            "goal": generated.get("goal") or title,
            "subgoals": merged_subgoals,
            "constraints": constraints,
            "domain": domain or _infer_domain(title, description, context),
            "base_subgoals_from_title": base_subgoals,
            "description_hints": description_hints,
            "merged_subgoals": merged_subgoals,
            "decomposition_confidence": _decomposition_confidence(base_subgoals, description_hints),
        }
    )


def _constraints(task, context):
    constraints = []
    if context:
        constraints.append(context)
    if task.get("deadline"):
        constraints.append(f"дедлайн: {task['deadline']}")
    if task.get("estimated_minutes"):
        constraints.append(f"оценка времени: {task['estimated_minutes']} минут")
    return constraints


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


def _title_first_subgoals(title, context, domain):
    text = _clean(f"{title} {context}").lower()
    if domain == "travel":
        return [
            "выбрать даты поездки",
            "рассчитать бюджет",
            "подобрать жилье",
            "составить маршрут",
            "подготовить вещи и документы",
        ]
    if domain == "presentation":
        return [
            "уточнить цель выступления",
            "собрать материалы",
            "составить структуру презентации",
            "подготовить слайды",
            "проверить и отрепетировать выступление",
        ]
    if domain == "research":
        return [
            "сформулировать гипотезы",
            "определить критерии оценки",
            "спланировать эксперименты",
            "проанализировать результаты",
            "проверить выводы",
        ]
    if domain == "email":
        return [
            "уточнить цель письма",
            "собрать нужные данные",
            "написать черновик ответа",
            "проверить формулировки и вложения",
            "отправить письмо",
        ]
    if domain == "study":
        return [
            "уточнить цель учебной работы",
            "собрать материалы",
            "составить структуру",
            "подготовить основной текст",
            "проверить результат",
        ]
    clauses = _extract_clauses(title)
    if len(clauses) >= 3:
        return [_normalize_subgoal(clause) for clause in clauses[:5]]
    if any(marker in text for marker in ("убрать", "убор", "дом", "квартир", "быт")):
        return ["определить объем работы", "разделить дела по зонам", "выполнить основные действия", "проверить результат"]
    return ["уточнить результат", "разбить задачу на этапы", "выполнить основной этап", "проверить итог"]


def _description_hints(description):
    return [_normalize_subgoal(clause) for clause in _extract_clauses(description) if not _looks_like_constraint(clause)]


def _normalize_subgoal(value):
    text = _clean(value).lower()
    text = re.sub(r"^(нужно|надо|следует|важно)\s+", "", text, flags=re.IGNORECASE)
    if "дат" in text and "сдач" in text:
        return "уточнить дату сдачи"
    if any(marker in text for marker in ("дат", "срок поезд")):
        return "выбрать даты поездки"
    if any(marker in text for marker in ("бюджет", "расход", "стоим")):
        return "рассчитать бюджет"
    if any(marker in text for marker in ("жиль", "прожив", "отел", "гостиниц", "квартир")):
        return "подобрать жилье"
    if "маршрут" in text:
        return "составить маршрут"
    if "вещ" in text or "документ" in text or "паспорт" in text or "билет" in text:
        return "подготовить вещи и документы"
    if "слайд" in text:
        return "подготовить слайды"
    if "структур" in text:
        return "составить структуру"
    if "материал" in text:
        return "собрать материалы"
    if "репет" in text or "выступлен" in text:
        return "проверить и отрепетировать выступление"
    if "гипотез" in text:
        return "сформулировать гипотезы"
    if "критери" in text or "оценк" in text:
        return "определить критерии оценки"
    if "эксперимент" in text:
        return "спланировать эксперименты"
    if "результат" in text or "вывод" in text:
        return "проверить результаты и выводы"
    if "цель" in text and "письм" in text:
        return "уточнить цель письма"
    if "чернов" in text and "письм" in text:
        return "написать черновик письма"
    if "формулиров" in text and "письм" in text:
        return "проверить формулировки письма"
    if "письм" in text or "ответ" in text:
        return "подготовить ответ"
    return _clean(value)[:90]


def _merge_subgoals(base_subgoals, hints):
    result = []
    for item in list(base_subgoals or []) + list(hints or []):
        normalized = _normalize_subgoal(item)
        if not normalized or _looks_like_constraint(normalized):
            continue
        if not any(_too_similar_subgoals(normalized, existing) for existing in result):
            result.append(normalized)
        if len(result) >= 7:
            break
    return result


def _merge_constraints(base_constraints, hints):
    result = []
    for item in list(base_constraints or []) + list(hints or []):
        cleaned = _clean(item)
        if cleaned and cleaned not in result:
            result.append(cleaned[:120])
    return result[:7]


def _looks_like_constraint(value):
    text = _clean(value).lower()
    return (
        text.startswith("дедлайн:")
        or text.startswith("оценка времени:")
        or bool(re.search(r"\b\d+\s*(минут|час|дн)", text))
    )


def _too_similar_subgoals(left, right):
    left_words = _word_set(left)
    right_words = _word_set(right)
    if not left_words or not right_words:
        return False
    return len(left_words & right_words) / max(1, min(len(left_words), len(right_words))) >= 0.7


def _word_set(text):
    return {
        word[:8]
        for word in re.findall(r"[а-яёa-z0-9]+", str(text).lower())
        if len(word) > 3 and word not in {"нужно", "надо", "задача", "этап"}
    }


def _decomposition_confidence(base_subgoals, description_hints):
    if len(base_subgoals) >= 4:
        value = 0.75
    elif len(base_subgoals) >= 2:
        value = 0.6
    else:
        value = 0.45
    if description_hints:
        value += 0.1
    return round(min(value, 0.95), 2)


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
