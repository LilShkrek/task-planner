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
    title_subgoals = _title_first_subgoals(title, context, domain)
    task_archetypes = _detect_task_archetypes(title, context, domain)
    base_subgoals = _archetype_base_subgoals(title, context, domain, title_subgoals, task_archetypes)
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
        "task_archetypes": task_archetypes,
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


def _detect_task_archetypes(title, context, domain):
    text = _clean(f"{title} {context}").lower()
    checks = (
        ("event_planning", ("мероприят", "событи", "праздник", "день рожден", "сюрприз", "вечерин")),
        ("social_coordination", ("друг", "участник", "гост", "команд", "согласоват", "договорит")),
        ("career_planning", ("карьер", "профес", "направлен", "работ", "год")),
        ("decision_making", ("разобрат", "выбрать", "решить", "сравнит", "вариант", "направлен")),
        ("creative_project", ("придумат", "концепц", "youtube", "ютуб", "канал", "контент", "творчес")),
        ("logistics", ("переезд", "перевез", "логист", "собрать вещи", "транспорт", "документ")),
        ("personal_organization", ("дедлайн", "не завал", "успеть", "организоват", "расписан", "порядок")),
        ("self_reflection", ("разобрат", "осмысл", "понять", "цели", "приоритет", "ближайший год")),
    )
    result = []
    for code, markers in checks:
        if any(marker in text for marker in markers):
            result.append(code)
    if domain == "study" and any(marker in text for marker in ("дедлайн", "учеб", "не завал")):
        result.append("personal_organization")
    return _dedupe(result)


def _archetype_base_subgoals(title, context, domain, title_subgoals, archetypes):
    if not archetypes:
        return title_subgoals
    if domain in {"travel", "presentation", "research", "email"}:
        return title_subgoals

    title_details = _extract_title_details(title, context)
    archetype_subgoals = []
    for archetype in archetypes:
        archetype_subgoals.extend(_subgoals_for_archetype(archetype))

    if not archetype_subgoals:
        return title_subgoals
    if _is_generic_decomposition(title_subgoals) or domain in {"general", "study"}:
        return _merge_subgoals(title_details, archetype_subgoals)
    return _merge_subgoals(title_subgoals, title_details + archetype_subgoals)


def _subgoals_for_archetype(archetype):
    templates = {
        "event_planning": [
            "определить формат события",
            "рассчитать бюджет",
            "выбрать место и время",
            "согласовать участников и детали",
            "подготовить подарок или сценарий",
            "проверить готовность",
        ],
        "social_coordination": [
            "уточнить ожидания участников",
            "согласовать роли и договоренности",
            "подготовить сообщение или приглашение",
            "проверить важные детали",
        ],
        "decision_making": [
            "уточнить цель решения",
            "собрать варианты",
            "определить критерии выбора",
            "сравнить варианты",
            "выбрать следующий шаг",
        ],
        "creative_project": [
            "определить аудиторию и тему",
            "собрать идеи формата",
            "сформулировать концепцию",
            "набросать первые рубрики или элементы",
            "проверить реалистичность первого результата",
        ],
        "logistics": [
            "определить дату и объем переезда",
            "составить список вещей",
            "организовать транспорт и помощь",
            "проверить документы и ключи",
        ],
        "personal_organization": [
            "собрать все дедлайны и обязательства",
            "расставить приоритеты",
            "разнести дела по дням",
            "оставить резерв на учебные задачи",
            "проверить календарь и напоминания",
        ],
        "career_planning": [
            "уточнить карьерную цель на год",
            "собрать возможные направления",
            "определить критерии выбора",
            "сравнить направления по реалистичности",
            "выбрать ближайший практический шаг",
        ],
        "self_reflection": [
            "зафиксировать текущие ожидания",
            "выделить важные критерии",
            "сравнить возможные сценарии",
            "выбрать направление для проверки",
        ],
    }
    return templates.get(archetype, [])


def _extract_title_details(title, context):
    text = _clean(f"{title} {context}").lower()
    details = []
    if "youtube" in text or "ютуб" in text:
        details.append("сформулировать концепцию YouTube-канала")
    if "день рожден" in text or "сюрприз" in text:
        details.append("подготовить сюрприз для друга")
    if "карьер" in text:
        details.append("выбрать карьерное направление")
    if "переезд" in text:
        details.append("подготовить переезд")
    if "учеб" in text or "дедлайн" in text:
        details.append("сохранить учебные дедлайны")
    return details


def _is_generic_decomposition(subgoals):
    generic = {
        "уточнить результат",
        "разбить задачу на этапы",
        "выполнить основной этап",
        "проверить итог",
        "проверить результат",
    }
    normalized = {_clean(item).lower() for item in subgoals or []}
    return len(normalized & generic) >= 2


def _description_hints(description):
    return [_normalize_subgoal(clause) for clause in _extract_clauses(description) if not _looks_like_constraint(clause)]


def _normalize_subgoal(value):
    text = _clean(value).lower()
    text = re.sub(r"^(нужно|надо|следует|важно)\s+", "", text, flags=re.IGNORECASE)
    if "дат" in text and "сдач" in text:
        return "уточнить дату сдачи"
    if "дедлайн" in text and ("учеб" in text or "сохран" in text):
        return "сохранить учебные дедлайны"
    if "день рожден" in text or "сюрприз" in text:
        return "подготовить сюрприз для друга"
    if "формат собы" in text or "формат мероприят" in text:
        return "определить формат события"
    if "мест" in text and "врем" in text:
        return "выбрать место и время"
    if "участник" in text or "гост" in text or "договор" in text:
        return "согласовать участников и детали"
    if "подар" in text or "сценар" in text:
        return "подготовить подарок или сценарий"
    if "готовност" in text:
        return "проверить готовность"
    if "собрат" in text and "направлен" in text:
        return "собрать возможные направления"
    if "сравн" in text and ("вариант" in text or "направлен" in text or "сценар" in text):
        return "сравнить варианты"
    if "вариант" in text and ("собрат" in text or "возможн" in text):
        return "собрать варианты"
    if "критери" in text and ("выбор" in text or "вариант" in text):
        return "определить критерии выбора"
    if "карьер" in text and ("цель" in text or "год" in text):
        return "уточнить карьерную цель на год"
    if "карьер" in text or "направлен" in text:
        return "выбрать карьерное направление"
    if "следующ" in text and "шаг" in text:
        return "выбрать следующий шаг"
    if "youtube" in text or "ютуб" in text:
        return "сформулировать концепцию YouTube-канала"
    if "аудитор" in text or "тем" in text:
        return "определить аудиторию и тему"
    if "формат" in text and ("иде" in text or "контент" in text):
        return "собрать идеи формата"
    if "концепц" in text:
        return "сформулировать концепцию"
    if "рубр" in text or "элемент" in text:
        return "набросать первые рубрики или элементы"
    if "перв" in text and ("результ" in text or "выпуск" in text):
        return "проверить реалистичность первого результата"
    if "переезд" in text and ("дат" in text or "объем" in text):
        return "определить дату и объем переезда"
    if "переезд" in text:
        return "подготовить переезд"
    if "список вещей" in text:
        return "составить список вещей"
    if "транспорт" in text or "помощ" in text:
        return "организовать транспорт и помощь"
    if "ключ" in text:
        return "проверить документы и ключи"
    if "календар" in text or "напоминан" in text:
        return "проверить календарь и напоминания"
    if "приоритет" in text:
        return "расставить приоритеты"
    if "по дням" in text:
        return "разнести дела по дням"
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


def _dedupe(values):
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


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
