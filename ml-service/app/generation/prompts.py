def build_generation_prompt(
    task,
    prediction,
    template,
    field,
    step_index=None,
    step_template=None,
    strict=False,
    previous_titles=None,
    semantic_structure=None,
):
    params = prediction.get("planning_params", {})
    title = _clean(task.get("title") or "задача")
    description = _clean(task.get("description") or "")
    context = _clean(task.get("context") or "")
    method = _method_hint(prediction)
    subject_entities = _subject_entities(title, description, context)
    entities_hint = ", ".join(subject_entities) if subject_entities else "не выделены"
    semantic_hint = _semantic_hint(semantic_structure)
    strict_hint = (
        "Строгий повтор: предыдущий вариант был слишком общим или повторял входные данные. "
        "Сделай текст предметным, без заглушек, вопросов и дословного копирования."
        if strict
        else ""
    )

    if field == "summary":
        return "\n".join(
            [
                "headline | Сформулируй краткий осмысленный итог задачи на русском языке.",
                "Поле: summary.",
                f"Задача: {title}.",
                f"Описание: {description}.",
                f"Контекст: {context}.",
                f"Предметные сущности: {entities_hint}.",
                f"Семантическая структура: {semantic_hint}.",
                f"Метод планирования: {method}.",
                "Требования: одно предложение до 16 слов; опиши смысл плана и ожидаемый результат; не перефразируй только название.",
                strict_hint,
            ]
        )

    if field == "schedule_hint":
        return "\n".join(
            [
                "assemble | Напиши естественную подсказку по расписанию для выполнения задачи.",
                "Поле: schedule_hint.",
                f"Задача: {title}.",
                f"Предметные сущности: {entities_hint}.",
                f"Семантическая структура: {semantic_hint}.",
                f"Метод: {method}.",
                f"Фокус-сессия: {params.get('focus_minutes', 25)} минут.",
                f"Перерыв: {params.get('break_minutes', 5)} минут.",
                f"Количество рабочих блоков: {params.get('block_count', 1)}.",
                f"Резерв на проверку: {params.get('review_minutes', 15)} минут.",
                "Требования: одно естественное предложение; правильно согласуй слово 'блок'; объясни, когда работать и когда проверять.",
                strict_hint,
            ]
        )

    step_text = _step_text(step_template, step_index or 1)
    if field == "step_title":
        used = "; ".join(previous_titles or []) or "нет"
        return "\n".join(
            [
                "headline | Придумай короткий уникальный заголовок шага плана.",
                "Поле: step_title.",
                f"Задача: {title}.",
                f"Предметные сущности: {entities_hint}.",
                f"Семантическая структура: {semantic_hint}.",
                f"Номер шага: {step_index}.",
                f"Базовый шаг из шаблона: {step_text}.",
                f"Уже использованные заголовки: {used}.",
                "Требования: 2-5 слов; начни с глагола действия; учитывай метод этапа; используй предметную сущность, если она есть; не пиши про блоки времени.",
                strict_hint,
            ]
        )

    if field == "step_description":
        return "\n".join(
            [
                "assemble | Напиши конкретное описание действия для одного шага плана.",
                "Поле: step_description.",
                f"Задача: {title}.",
                f"Описание задачи: {description}.",
                f"Контекст: {context}.",
                f"Предметные сущности: {entities_hint}.",
                f"Семантическая структура: {semantic_hint}.",
                f"Номер шага: {step_index}.",
                f"Базовый шаг из шаблона: {step_text}.",
                "Требования: 1 короткое предложение; свяжи действие с методом этапа и предметной сущностью; не повторяй описание задачи целиком.",
                strict_hint,
            ]
        )

    return f"headline | {title}. {description}"


def _method_hint(prediction):
    selected = prediction.get("selected_methods") or []
    if selected:
        parts = [
            f"{item.get('name', item.get('code', 'метод'))} ({item.get('group', 'этап')}: {item.get('role', 'роль')})"
            for item in selected[:5]
        ]
        return "комбинация методов: " + "; ".join(parts)
    return prediction.get("method_name") or prediction.get("method_code") or ""


def _clean(value):
    return " ".join(str(value).split())


def _subject_entities(title, description, context):
    text = f"{title} {description} {context}".lower()
    entities = []
    for keyword in (
        "гипотезы",
        "эксперименты",
        "критерии оценки",
        "глава",
        "структура",
        "слайды",
        "выступление",
        "письмо",
    ):
        if keyword in text:
            entities.append(keyword)
    return entities


def _semantic_hint(semantic_structure):
    if not isinstance(semantic_structure, dict):
        return "не выделена"
    goal = _clean(semantic_structure.get("goal") or "")
    domain = _clean(semantic_structure.get("domain") or "")
    subgoals = semantic_structure.get("subgoals") or []
    constraints = semantic_structure.get("constraints") or []
    parts = []
    if goal:
        parts.append(f"цель: {goal}")
    if domain:
        parts.append(f"область: {domain}")
    if subgoals:
        parts.append("подцели: " + "; ".join(_clean(item) for item in subgoals[:6]))
    if constraints:
        parts.append("ограничения: " + "; ".join(_clean(item) for item in constraints[:4]))
    return " | ".join(parts) if parts else "не выделена"


def _step_text(step_template, step_index):
    if isinstance(step_template, str):
        return step_template
    if isinstance(step_template, dict):
        title = step_template.get("title") or f"Шаг {step_index}"
        description = step_template.get("description") or ""
        method = step_template.get("method_name") or ""
        group = step_template.get("method_group") or ""
        role = step_template.get("method_role") or ""
        method_text = f" Метод этапа: {method}; группа: {group}; роль: {role}." if method else ""
        return f"{title}. {description}{method_text}"
    return f"Шаг {step_index}"
