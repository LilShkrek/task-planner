METHOD_FAMILIES = {
    "smart": "goal",
    "smarter": "goal",
    "clear": "goal",
    "woop": "goal",
    "personal_okr": "goal",
    "eisenhower": "priority",
    "abcde": "priority",
    "moscow": "priority",
    "pareto_80_20": "priority",
    "ivy_lee": "priority",
    "wbs": "decomposition",
    "backward_planning": "decomposition",
    "critical_path": "decomposition",
    "one_three_five": "decomposition",
    "alpen": "decomposition",
    "time_blocking": "time",
    "timeboxing": "time",
    "pomodoro": "time",
    "flowtime": "time",
    "biological_prime_time": "time",
    "eat_that_frog": "start",
    "two_minute_rule": "start",
    "five_minute_rule": "start",
    "swiss_cheese": "start",
    "if_then_planning": "start",
    "gtd": "decomposition",
    "personal_kanban": "decomposition",
    "inbox_zero": "decomposition",
    "bullet_journal": "decomposition",
    "autofocus": "priority",
    "single_tasking": "time",
    "task_batching": "time",
    "dont_break_chain": "time",
    "ultradian_rhythm": "time",
    "personal_sprint": "time",
    "daily_review": "control",
    "weekly_review": "control",
    "checklist": "control",
    "action_priority_matrix": "control",
    "pickle_jar": "priority",
}

FAMILY_MARKERS = {
    "goal": ("цель", "результат", "критер", "измерим", "готовност"),
    "priority": ("приоритет", "важн", "срочн", "главн", "обязател"),
    "decomposition": ("разб", "структур", "част", "этап", "последователь"),
    "time": ("время", "блок", "сесс", "таймер", "перерыв", "ритм"),
    "start": ("нач", "перв", "мал", "пят", "сопротивлен", "лягуш"),
    "control": ("провер", "свер", "оцен", "итог", "контрол", "чек"),
}


def align_steps_to_methods(steps, task, planning_params=None):
    result = []
    for step in steps:
        if not step.get("method_code"):
            result.append(step)
            continue
        family = _method_family(step)
        if not family or _step_matches_family(step, family):
            result.append(step)
            continue
        result.append(_rewrite_step(step, task, family, planning_params or {}))
    return result


def _method_family(step):
    code = str(step.get("method_code") or "").lower()
    if code in METHOD_FAMILIES:
        return METHOD_FAMILIES[code]
    function = _normalized(step.get("plan_function") or "")
    role = _normalized(step.get("method_role") or "")
    text = f"{function} {role}"
    if any(marker in text for marker in ("цель", "результ", "измерим")):
        return "goal"
    if any(marker in text for marker in ("приоритет", "важн", "срочн", "главн")):
        return "priority"
    if any(marker in text for marker in ("разб", "част", "структур")):
        return "decomposition"
    if any(marker in text for marker in ("время", "сесс", "ритм", "календар")):
        return "time"
    if any(marker in text for marker in ("нач", "старт", "прокраст", "сопротив")):
        return "start"
    if any(marker in text for marker in ("провер", "контрол", "оцен", "заверш")):
        return "control"
    return ""


def _step_matches_family(step, family):
    text = _normalized(f"{step.get('title', '')} {step.get('description', '')}")
    method_name = _normalized(step.get("method_name") or step.get("method_code") or "")
    if method_name and method_name not in text:
        return False
    return sum(1 for marker in FAMILY_MARKERS[family] if marker in text) >= 2


def _rewrite_step(step, task, family, planning_params):
    subject = _step_subject(step, task)
    method_name = step.get("method_name") or step.get("method_code") or "выбранный метод"
    title, description = _aligned_text(family, subject, method_name, planning_params)
    return {
        **step,
        "title": title,
        "description": description,
    }


def _aligned_text(family, subject, method_name, planning_params):
    if family == "goal":
        return (
            f"Уточнить результат: {subject}",
            f"Используй {method_name}: опиши ожидаемый результат по «{subject}», критерии готовности и признак, по которому будет понятно, что шаг выполнен.",
        )
    if family == "priority":
        return (
            f"Расставить приоритеты: {subject}",
            f"Используй {method_name}: отдели для «{subject}» важное и срочное от второстепенного, чтобы начать с обязательных действий.",
        )
    if family == "decomposition":
        return (
            f"Разложить на этапы: {subject}",
            f"Используй {method_name}: разбей «{subject}» на части, зависимости и понятную последовательность действий.",
        )
    if family == "time":
        focus = planning_params.get("focus_minutes", 25)
        breaks = planning_params.get("break_minutes", 5)
        return (
            f"Запланировать работу: {subject}",
            f"Используй {method_name}: выдели на «{subject}» рабочие сессии по {focus} минут и перерывы по {breaks} минут.",
        )
    if family == "start":
        return (
            f"Начать с малого шага",
            f"Используй {method_name}: снизь сопротивление и начни «{subject}» с первого маленького действия на 5 минут.",
        )
    return (
        f"Проверить результат: {subject}",
        f"Используй {method_name}: сверь «{subject}» с целью, оцени качество результата и зафиксируй, что нужно исправить.",
    )


def _step_subject(step, task):
    title = _clean(step.get("title") or "")
    for prefix in (
        "Уточнить",
        "Рассчитать",
        "Выбрать",
        "Составить",
        "Подготовить",
        "Выделить",
        "Разбить",
        "Запланировать",
        "Проверить",
        "Организовать",
    ):
        if title.startswith(prefix):
            value = _clean(title[len(prefix):])
            if value:
                return _enrich_subject(_normalize_subject(value.lower()), task)
    semantic = task.get("_semantic_structure") or {}
    subgoals = semantic.get("subgoals") if isinstance(semantic, dict) else []
    position = int(step.get("position") or 1)
    if isinstance(subgoals, list) and subgoals:
        return _enrich_subject(_normalize_subject(_clean(subgoals[min(position, len(subgoals)) - 1]).lower()), task)
    return _enrich_subject(_normalize_subject(_clean(task.get("title") or "задачи").lower()), task)


def _normalize_subject(subject):
    normalized = _normalized(subject)
    if normalized in {"даты", "дата", "сроки", "срок"} or "выбрать даты" in normalized:
        return "выбор дат поездки"
    if normalized in {"бюджет"} or "определить бюджет" in normalized or "рассчитать бюджет" in normalized:
        return "расчет бюджета"
    if normalized in {"жилье", "жильё", "проживание"} or any(marker in normalized for marker in ("подобрать место проживания", "забронировать жиль")):
        return "выбор жилья"
    if normalized in {"маршрут"} or "продумать маршрут" in normalized or "составить маршрут" in normalized:
        return "составление маршрута"
    if "вещ" in normalized and "документ" in normalized:
        return "подготовка вещей и проверка документов"
    if normalized in {"вещи и документы", "документы"}:
        return "подготовка вещей и проверка документов"
    return subject


def _enrich_subject(subject, task):
    task_text = _normalized(f"{task.get('title', '')} {task.get('description', '')} {task.get('context', '')}")
    if "слайд" in task_text and "слайд" not in subject:
        return f"{subject} для слайдов"
    if "презентац" in task_text and "презентац" not in subject and "слайд" not in subject:
        return f"{subject} для презентации"
    if "эксперимент" in task_text and "эксперимент" not in subject:
        return f"{subject} для экспериментов"
    if "письм" in task_text and "письм" not in subject:
        return f"{subject} для письма"
    return subject


def _normalized(text):
    return str(text).lower().replace("ё", "е")


def _clean(value):
    return " ".join(str(value).split()).strip(" .,:;")
