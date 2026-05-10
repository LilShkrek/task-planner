import re

from app.generation.prompts import build_generation_prompt
from app.generation.service import get_text_generator
from app.planning.method_alignment import align_steps_to_methods


BAD_TEXT_FRAGMENTS = (
    "описание шага задачи",
    "описание шага",
    "сгенерированный текст",
    "что делать",
    "что нужно сделать",
    "расписание задачи",
    "напиши естественную подсказку",
    "напиши конкретное описание",
    "придумай короткий уникальный",
    "уникальный заголовок",
    "требования",
    "поле:",
    "название задачи",
    "задача:",
    "для того чтобы",
    "что будет",
)

GENERIC_STEP_FRAGMENTS = (
    "разделить задачу на блоки",
    "разбить задачу на блоки",
    "выполнить первый блок",
    "выполнить следующий блок",
    "продолжить работу по расписанию",
    "назначить время для каждого блока",
    "выделить отдельные интервалы",
    "выполнить этап",
)

SUBJECT_KEYWORDS = (
    "гипотез",
    "эксперимент",
    "критери",
    "оценк",
    "глав",
    "структур",
    "слайд",
    "выступлен",
    "письм",
)

TITLE_BAD_STARTS = (
    "что ",
    "как ",
    "почему ",
    "зачем ",
    "когда ",
    "где ",
    "можно ли ",
)

TITLE_BAD_ENDS = (
    " в",
    " на",
    " для",
    " чтобы",
    " и",
    " с",
    " по",
    " к",
    " от",
)

ACTION_VERBS = (
    "уточнить",
    "собрать",
    "разбить",
    "разделить",
    "подготовить",
    "составить",
    "написать",
    "проверить",
    "выполнить",
    "запланировать",
    "назначить",
    "выделить",
    "начать",
    "продолжить",
    "оставить",
    "исправить",
    "согласовать",
    "отправить",
    "изучить",
    "выбрать",
    "оформить",
    "сформулировать",
    "провести",
    "проанализировать",
    "описать",
    "прорепетировать",
)


def generate_response(task, prediction, template, text_generator=None, semantic_structure=None):
    steps_template = template.get("steps") or []
    if not steps_template:
        raise RuntimeError(f"шаблон плана для метода {prediction['method_code']} не содержит шагов")

    generator = text_generator or get_text_generator()
    planning_params = prediction.get("planning_params", {})
    task = dict(task)
    task["_semantic_structure"] = semantic_structure or {}

    summary = _generate_checked_field(
        generator,
        task,
        prediction,
        template,
        "summary",
        64,
        validator=lambda text: _valid_summary(text, task),
        fallback=lambda: _fallback_summary(task),
        sentence=True,
    )
    schedule_hint = _generate_checked_field(
        generator,
        task,
        prediction,
        template,
        "schedule_hint",
        64,
        validator=lambda text: _valid_schedule_hint(text),
        fallback=lambda: _fallback_schedule_hint(task, prediction),
        sentence=True,
    )

    return {
        "summary": summary,
        "schedule_hint": schedule_hint,
        "plan_draft": _generate_steps(task, prediction, template, steps_template, planning_params, generator),
    }


def _generate_steps(task, prediction, template, steps_template, planning_params, generator):
    estimated = int(task.get("estimated_minutes") or 60)
    default_minutes = max(15, estimated // len(steps_template))
    steps = []

    for index, step_template in enumerate(steps_template):
        position = index + 1
        minutes = _step_minutes(step_template, default_minutes)
        if position == len(steps_template) and planning_params.get("review_minutes"):
            minutes = planning_params["review_minutes"]

        title = _generate_checked_field(
            generator,
            task,
            prediction,
            template,
            "step_title",
            24,
            step_index=position,
            step_template=step_template,
            previous_titles=[step["title"] for step in steps],
            validator=lambda text, previous=[step["title"] for step in steps]: _valid_step_title(text, task, previous),
            fallback=lambda pos=position, step=step_template: _fallback_step_title(task, step, pos),
        )
        description = _generate_checked_field(
            generator,
            task,
            prediction,
            template,
            "step_description",
            64,
            step_index=position,
            step_template=step_template,
            validator=lambda text, generated_title=title, previous=[step["description"] for step in steps]: _valid_step_description(
                text,
                task,
                generated_title,
                previous,
            ),
            fallback=lambda generated_title=title, step=step_template, pos=position: _fallback_step_description(
                task,
                step,
                generated_title,
                pos,
            ),
            sentence=True,
        )

        steps.append(
            {
                "position": position,
                "title": title,
                "description": description,
                "estimated_minutes": max(15, int(minutes)),
                "status": "pending",
                **_step_metadata(step_template),
            }
        )

    if _titles_are_not_useful(steps, task):
        for index, step in enumerate(steps):
            step["title"] = _fallback_step_title(task, steps_template[index], index + 1)
    if _descriptions_are_not_useful(steps, task):
        for index, step in enumerate(steps):
            step["description"] = _fallback_step_description(task, steps_template[index], step["title"], index + 1)
    if _pairs_are_not_consistent(steps, task) or _roles_are_not_useful(steps):
        for index, step in enumerate(steps):
            step["title"] = _fallback_step_title(task, steps_template[index], index + 1)
            step["description"] = _fallback_step_description(task, steps_template[index], step["title"], index + 1)
    if _steps_have_duplicates(steps) or _subgoals_not_covered(steps, task):
        for index, step in enumerate(steps):
            step["title"] = _fallback_step_title(task, steps_template[index], index + 1)
            step["description"] = _fallback_step_description(task, steps_template[index], step["title"], index + 1)
    steps = _ensure_semantic_subgoal_coverage(steps, task)
    steps = align_steps_to_methods(steps, task, planning_params)

    return steps


def _generate_checked_field(
    generator,
    task,
    prediction,
    template,
    field,
    max_chars,
    step_index=None,
    step_template=None,
    previous_titles=None,
    validator=None,
    fallback=None,
    sentence=False,
):
    for strict in (False, True):
        prompt = build_generation_prompt(
            task,
            prediction,
            template,
            field,
            step_index,
            step_template,
            strict=strict,
            previous_titles=previous_titles,
            semantic_structure=task.get("_semantic_structure"),
        )
        generated = generator.generate(prompt, max_chars=max_chars).strip()
        generated = _postprocess_text(generated, field, prediction)
        if sentence:
            generated = _normalize_sentence(generated)
        if generated and (validator is None or validator(generated)):
            return generated

    if fallback is not None:
        return fallback()
    raise RuntimeError(f"генеративная модель вернула неподходящий текст для поля {field}")


def _step_minutes(step_template, default_minutes):
    if isinstance(step_template, dict) and step_template.get("estimated_minutes"):
        return step_template["estimated_minutes"]
    return default_minutes


def _step_metadata(step_template):
    if not isinstance(step_template, dict):
        return {}
    result = {}
    for key in ("plan_stage", "plan_function", "method_code", "method_name", "method_group", "method_role"):
        if step_template.get(key):
            result[key] = step_template[key]
    return result


def _valid_summary(text, task):
    return (
        _meaningful(text, min_words=5)
        and _normalized(text) != _normalized(task.get("title") or "")
        and not _too_similar(text, task.get("title") or "", threshold=0.72)
        and not _bad_fragment(text)
    )


def _valid_schedule_hint(text):
    return _meaningful(text, min_words=7) and not _bad_fragment(text) and not _bad_block_agreement(text)


def _valid_step_title(text, task, previous_titles):
    normalized = _normalized(text)
    if not _meaningful(text, min_words=2) or _bad_fragment(text) or _bad_title_shape(text):
        return False
    if _has_subject_entities(task) and (_generic_step_text(text) or not _uses_subject_entity(text, task)):
        return False
    if len(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text)) > 8:
        return False
    task_title = _normalized(task.get("title") or "")
    if normalized == task_title or task_title in normalized:
        return False
    return all(normalized != _normalized(title) for title in previous_titles)


def _valid_step_description(text, task, title="", previous_descriptions=None):
    return (
        _meaningful(text, min_words=6)
        and not _bad_fragment(text)
        and not _description_repeats_previous(text, previous_descriptions or [])
        and _title_description_consistent(title, text, task)
        and not (_has_subject_entities(task) and (_generic_step_text(text) or not _uses_subject_entity(text, task)))
        and not _too_similar(text, task.get("description") or "", threshold=0.78)
        and _normalized(text) != _normalized(task.get("description") or "")
    )


def _meaningful(text, min_words):
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text)
    return len(words) >= min_words


def _bad_fragment(text):
    normalized = _normalized(text)
    return any(fragment in normalized for fragment in BAD_TEXT_FRAGMENTS)


def _bad_title_shape(text):
    value = text.strip().lower()
    if "?" in value or ":" in value:
        return True
    if any(value.startswith(prefix) for prefix in TITLE_BAD_STARTS):
        return True
    if any(value.endswith(suffix) for suffix in TITLE_BAD_ENDS):
        return True
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", value)
    if not words:
        return True
    return words[0] not in ACTION_VERBS and not words[0].endswith(("ть", "ти", "чь"))


def _bad_block_agreement(text):
    normalized = _normalized(text)
    return bool(re.search(r"\b1 рабочих блок", normalized))


def _generic_step_text(text):
    normalized = _normalized(text)
    return any(fragment in normalized for fragment in GENERIC_STEP_FRAGMENTS)


def _has_subject_entities(task):
    return bool(_subject_entities(task) or _semantic_subgoals(task) or _semantic_domain(task))


def _uses_subject_entity(text, task):
    normalized = _normalized(text)
    return any(entity in normalized for entity in _subject_entity_roots(task))


def _too_similar(left, right, threshold):
    left_words = _content_words(left)
    right_words = _content_words(right)
    if not left_words or not right_words:
        return False
    overlap = len(left_words & right_words)
    return overlap / max(1, min(len(left_words), len(right_words))) >= threshold


def _description_repeats_previous(text, previous_descriptions):
    normalized = _normalized(text)
    return any(normalized == _normalized(previous) or _too_similar(text, previous, threshold=0.82) for previous in previous_descriptions)


def _title_description_consistent(title, description, task):
    title_words = _content_words(title)
    description_words = _content_words(description)
    if not title_words or not description_words:
        return False
    title_role = _step_role(title)
    description_role = _step_role(description)
    if title_role and description_role and title_role != description_role:
        return False
    if title_words & description_words:
        return True
    if _has_subject_entities(task):
        roots = _subject_entity_roots(task)
        title_roots = roots & _normalized_roots(title)
        description_roots = roots & _normalized_roots(description)
        if title_roots:
            return bool(title_roots & description_roots)
        return bool(description_roots)
    return False


def _normalized_roots(text):
    return {_word_key(word) for word in re.findall(r"[a-zа-яё0-9]+", str(text).lower()) if len(word) > 2}


def _content_words(text):
    stop_words = {
        "и",
        "в",
        "во",
        "на",
        "по",
        "для",
        "с",
        "со",
        "к",
        "от",
        "до",
        "за",
        "из",
        "над",
        "под",
        "это",
        "задача",
        "нужно",
        "надо",
    }
    return {
        _word_key(word)
        for word in re.findall(r"[a-zа-яё0-9]+", str(text).lower())
        if len(word) > 2 and word not in stop_words
    }


def _word_key(word):
    if word.startswith("подготов"):
        return "подготов"
    if word.startswith("презентац"):
        return "презентац"
    if word.startswith("провер"):
        return "провер"
    if word.startswith("материал"):
        return "материал"
    if word.startswith("жиль"):
        return "жиль"
    return word[:7]


def _titles_are_not_useful(steps, task):
    titles = [_normalized(step["title"]) for step in steps]
    unique_titles = {title for title in titles if title}
    task_title = _normalized(task.get("title") or "")
    if len(unique_titles) <= 1 or all(title == task_title for title in titles):
        return True
    if _has_subject_entities(task):
        return any(_generic_step_text(step["title"]) or not _uses_subject_entity(step["title"], task) for step in steps)
    return False


def _descriptions_are_not_useful(steps, task=None):
    descriptions = [_normalized(step["description"]) for step in steps]
    unique_descriptions = {description for description in descriptions if description}
    if len(unique_descriptions) <= 1 or any(_bad_fragment(step["description"]) for step in steps):
        return True
    for index, description in enumerate(descriptions):
        if any(description and description == other for other in descriptions[:index]):
            return True
    for index, step in enumerate(steps):
        if _description_repeats_previous(step["description"], [previous["description"] for previous in steps[:index]]):
            return True
    if task and _has_subject_entities(task):
        return any(_generic_step_text(step["description"]) or not _uses_subject_entity(step["description"], task) for step in steps)
    return False


def _steps_have_duplicates(steps):
    for index, step in enumerate(steps):
        previous_titles = [previous["title"] for previous in steps[:index]]
        previous_descriptions = [previous["description"] for previous in steps[:index]]
        if any(_too_similar(step["title"], title, threshold=0.82) for title in previous_titles):
            return True
        if _description_repeats_previous(step["description"], previous_descriptions):
            return True
    return False


def _subgoals_not_covered(steps, task):
    subgoals = _semantic_subgoals(task)
    if len(subgoals) < 2:
        return False
    expected = _expected_subgoal_titles(task)
    if len(expected) >= min(len(steps), len(subgoals)):
        actual_titles = {_normalized(step["title"]) for step in steps}
        return any(_normalized(title) not in actual_titles for title in expected[: len(steps)])

    covered = set()
    step_text = " ".join(f"{step['title']} {step['description']}" for step in steps)
    for subgoal in subgoals:
        if _too_similar(step_text, subgoal, threshold=0.5) or _semantic_marker(subgoal) in _normalized(step_text):
            covered.add(_semantic_marker(subgoal))
    return len(covered) < min(len(subgoals), len(steps))


def _expected_subgoal_titles(task):
    subgoals = _semantic_subgoals(task) + _semantic_constraints(task)
    if not subgoals:
        return []
    patterns = (
        (("дат", "срок", "когда"), "Уточнить даты"),
        (("бюджет", "стоим", "деньг", "расход"), "Рассчитать бюджет"),
        (("жиль", "прожив", "размещ", "отел", "гостиниц", "квартир"), "Выбрать жилье"),
        (("маршрут", "план поезд", "локац", "транспорт"), "Составить маршрут"),
        (("вещ", "документ", "паспорт", "билет"), "Подготовить вещи и документы"),
    )
    result = []
    normalized_items = [_normalized(item) for item in subgoals]
    for markers, title in patterns:
        if any(any(marker in item for marker in markers) for item in normalized_items):
            result.append(title)
    return result


def _ensure_semantic_subgoal_coverage(steps, task):
    expected_titles = _expected_subgoal_titles(task)
    if len(expected_titles) < 2:
        return steps

    required = expected_titles[: len(steps)]
    actual = {_normalized(step["title"]) for step in steps}
    if all(_normalized(title) in actual for title in required) and not _steps_have_duplicates(steps):
        return steps

    fixed = []
    for index, step in enumerate(steps):
        if index < len(required):
            title = required[index]
            fixed.append(
                {
                    **step,
                    "title": title,
                    "description": _semantic_step_description(task, title, index + 1),
                }
            )
            continue
        fixed.append(step)
    return fixed


def _semantic_marker(text):
    words = list(_content_words(text))
    return sorted(words)[0] if words else ""


def _pairs_are_not_consistent(steps, task):
    return any(not _title_description_consistent(step["title"], step["description"], task) for step in steps)


def _roles_are_not_useful(steps):
    roles = [_step_role(f"{step['title']} {step['description']}") for step in steps]
    roles = [role for role in roles if role]
    return len(set(roles)) < min(3, len(steps))


def _step_role(text):
    normalized = _normalized(text)
    if any(marker in normalized for marker in ("резерв", "финаль", "отправ", "связност", "итогов")):
        return "final"
    if any(marker in normalized for marker in ("провер", "репет", "уточн", "проанализ", "аргументац")):
        return "review"
    if any(marker in normalized for marker in ("напис", "подготов", "провести", "созда", "черновик")):
        return "create"
    if any(marker in normalized for marker in ("структур", "критери", "част", "раздел", "план", "данные")):
        return "structure"
    if any(marker in normalized for marker in ("собрат", "сформулир", "цель", "материал", "тезис", "гипотез")):
        return "prepare"
    return ""


def _fallback_summary(task):
    title = _task_title(task)
    semantic = _semantic_structure(task)
    if semantic.get("goal") and semantic.get("subgoals"):
        return _normalize_sentence(f"План поможет выполнить «{semantic['goal']}» через конкретные этапы: {semantic['subgoals'][0]}")
    action = _short_task_action(task)
    if action:
        return _normalize_sentence(f"План поможет {action} и оставить время на проверку результата")
    return _normalize_sentence(f"План разбивает работу «{title}» на понятные этапы с финальной проверкой")


def _fallback_schedule_hint(task, prediction):
    params = prediction.get("planning_params", {})
    title = _task_title(task)
    focus = params.get("focus_minutes", 25)
    break_minutes = params.get("break_minutes", 5)
    blocks = params.get("block_count", 1)
    review = params.get("review_minutes", 15)
    return (
        f"Запланируй задачу «{title}» на {blocks} {_block_word(blocks)} по {focus} {_minute_word(focus)}, "
        f"делай перерывы по {break_minutes} {_minute_word(break_minutes)} и оставь {review} {_minute_word(review)} на проверку."
    )


def _fallback_step_title(task, step_template, position):
    subject_title = _subject_step_title(task, position)
    if subject_title:
        return subject_title
    semantic_title = _semantic_step_title(task, position)
    if semantic_title:
        return semantic_title
    base = _template_title(step_template, position)
    base = base.replace("{task_title}", _task_title(task))
    if _bad_fragment(base) or _generic_step_text(base) or _normalized(base) == _normalized(_task_title(task)):
        base = f"Выполнить этап {position}"
    return base[:80].strip()


def _fallback_step_description(task, step_template, title, position):
    subject_description = _subject_step_description(task, title, position)
    if subject_description:
        return subject_description
    semantic_description = _semantic_step_description(task, title, position)
    if semantic_description:
        return semantic_description
    base = _template_description(step_template)
    if base:
        text = base.replace("{task_title}", _task_title(task))
    else:
        text = f"{title} для задачи «{_task_title(task)}»"
    text = text.rstrip(".!? ")
    subject = _task_subject(task)
    if subject and not _too_similar(text, subject, threshold=0.95):
        text = f"{text}. Сфокусируйся на результате: {subject}"
    return _normalize_sentence(text)


def _template_title(step_template, position):
    if isinstance(step_template, dict):
        return str(step_template.get("title") or f"Этап {position}").strip()
    if isinstance(step_template, str):
        return step_template.strip()
    return f"Этап {position}"


def _template_description(step_template):
    if isinstance(step_template, dict):
        return str(step_template.get("description") or "").strip()
    return ""


def _task_title(task):
    return " ".join(str(task.get("title") or "задача").split())


def _task_detail(task):
    description = " ".join(str(task.get("description") or "").split())
    context = " ".join(str(task.get("context") or "").split())
    if description and context:
        return f"{description}; контекст: {context}"
    return description or context


def _short_task_action(task):
    description = " ".join(str(task.get("description") or "").split())
    if not description:
        return ""
    first_part = re.split(r"[,.;:]", description, maxsplit=1)[0].strip()
    first_part = re.sub(r"^(нужно|надо|следует)\s+", "", first_part, flags=re.IGNORECASE)
    return first_part[:90].strip()


def _task_subject(task):
    description = " ".join(str(task.get("description") or "").split())
    if description:
        first_part = re.split(r"[,.;:]", description, maxsplit=1)[0].strip()
        return first_part[:80].strip()
    return _task_title(task)


def _subject_entities(task):
    text = _normalized(f"{task.get('title', '')} {task.get('description', '')} {task.get('context', '')}")
    entities = []
    checks = (
        ("гипотезы", ("гипотез",)),
        ("эксперименты", ("эксперимент",)),
        ("критерии оценки", ("критери", "оценк")),
        ("глава", ("глав",)),
        ("структура", ("структур",)),
        ("слайды", ("слайд",)),
        ("выступление", ("выступлен",)),
        ("письмо", ("письм",)),
    )
    for label, roots in checks:
        if all(root in text for root in roots):
            entities.append(label)
    return entities


def _semantic_structure(task):
    value = task.get("_semantic_structure") or {}
    return value if isinstance(value, dict) else {}


def _semantic_subgoals(task):
    subgoals = _semantic_structure(task).get("subgoals") or []
    return [str(item) for item in subgoals if str(item).strip()][:7] if isinstance(subgoals, list) else []


def _semantic_constraints(task):
    constraints = _semantic_structure(task).get("constraints") or []
    return [str(item) for item in constraints if str(item).strip()][:5] if isinstance(constraints, list) else []


def _semantic_domain(task):
    return str(_semantic_structure(task).get("domain") or "").strip()


def _semantic_roots(task):
    text = " ".join(
        [
            str(_semantic_structure(task).get("goal") or ""),
            _semantic_domain(task),
            " ".join(_semantic_subgoals(task)),
            " ".join(_semantic_constraints(task)),
        ]
    )
    return _content_words(text)


def _subject_entity_roots(task):
    roots = set()
    for entity in _subject_entities(task):
        if entity == "гипотезы":
            roots.add("гипотез")
        elif entity == "эксперименты":
            roots.add("эксперимент")
        elif entity == "критерии оценки":
            roots.update(("критери", "оценк"))
        elif entity == "глава":
            roots.add("глав")
        elif entity == "структура":
            roots.add("структур")
        elif entity == "слайды":
            roots.add("слайд")
        elif entity == "выступление":
            roots.add("выступлен")
        elif entity == "письмо":
            roots.add("письм")
    roots.update(_semantic_roots(task))
    return roots


def _semantic_step_title(task, position):
    subgoals = _semantic_subgoals(task)
    constraints = _semantic_constraints(task)
    combined = subgoals + constraints
    if not combined:
        return ""

    patterns = (
        (("дат", "срок", "когда"), "Уточнить даты"),
        (("бюджет", "стоим", "деньг", "расход"), "Рассчитать бюджет"),
        (("жиль", "прожив", "размещ", "отел", "гостиниц", "квартир"), "Выбрать жилье"),
        (("маршрут", "план поезд", "локац", "транспорт"), "Составить маршрут"),
        (("вещ", "документ", "паспорт", "билет"), "Подготовить вещи и документы"),
    )
    matched = []
    normalized_items = [(item, _normalized(item)) for item in combined]
    for markers, title in patterns:
        if any(any(marker in normalized for marker in markers) for _, normalized in normalized_items):
            matched.append(title)
    if len(matched) >= 3:
        return _pick_position(matched, position)

    role_prefixes = ("Уточнить", "Структурировать", "Подготовить", "Проверить", "Завершить")
    item = combined[min(max(position, 1), len(combined)) - 1]
    return f"{role_prefixes[min(position, len(role_prefixes)) - 1]} {_short_phrase(item)}"


def _semantic_step_description(task, title, position):
    subgoals = _semantic_subgoals(task)
    constraints = _semantic_constraints(task)
    domain = _semantic_display_name(task)
    normalized_title = _normalized(title)

    if "дат" in normalized_title:
        return f"Проверь доступные даты для «{domain}» и согласуй их с важными ограничениями."
    if "бюджет" in normalized_title:
        return f"Оцени бюджет для «{domain}»: дорогу, жилье, обязательные расходы и небольшой резерв."
    if "жиль" in normalized_title:
        return f"Сравни варианты жилья для «{domain}» по цене, расположению и условиям бронирования."
    if "маршрут" in normalized_title:
        return f"Составь маршрут для «{domain}»: ключевые точки, порядок перемещений и время в пути."
    if "документ" in normalized_title or "вещ" in normalized_title:
        return f"Подготовь список вещей и документов для «{domain}» и проверь, что ничего критичного не забыто."

    source = ""
    if subgoals:
        source = subgoals[min(max(position, 1), len(subgoals)) - 1]
    elif constraints:
        source = constraints[min(max(position, 1), len(constraints)) - 1]
    if not source:
        return ""

    if position == 1:
        return f"Уточни цель и исходные данные для «{domain}», начиная с пункта: {source}."
    if position == 2:
        return f"Разложи «{domain}» на основные части и отдельно проработай: {source}."
    if position == 3:
        return f"Выполни основную часть задачи «{domain}», опираясь на пункт: {source}."
    if position == 4:
        return f"Проверь результат по задаче «{domain}» и уточни пункт: {source}."
    return f"Сделай финальную проверку для «{domain}» и оставь резерв на пункт: {source}."


def _short_phrase(value):
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", str(value))
    if not words:
        return "этап"
    return " ".join(words[:4]).lower()


def _semantic_display_name(task):
    goal = str(_semantic_structure(task).get("goal") or "").strip()
    return goal or _task_title(task)



def _subject_step_title(task, position):
    entities = set(_subject_entities(task))
    if {"гипотезы", "эксперименты"} & entities:
        titles = [
            "Сформулировать гипотезы",
            "Определить критерии оценки",
            "Провести эксперименты",
            "Проанализировать результаты экспериментов",
            "Проверить выводы экспериментов",
        ]
        return _pick_position(titles, position)
    if "глава" in entities:
        titles = [
            "Уточнить тезис главы",
            "Выстроить структуру главы",
            "Написать разделы главы",
            "Проверить аргументацию главы",
            "Проверить связность главы",
        ]
        return _pick_position(titles, position)
    if {"слайды", "выступление"} & entities:
        titles = [
            "Собрать материал для слайдов",
            "Составить структуру выступления",
            "Подготовить слайды",
            "Прорепетировать выступление",
            "Проверить финальные слайды",
        ]
        return _pick_position(titles, position)
    if "письмо" in entities:
        titles = [
            "Уточнить цель письма",
            "Собрать данные для письма",
            "Написать черновик письма",
            "Проверить формулировки письма",
            "Отправить письмо",
        ]
        return _pick_position(titles, position)
    return ""


def _subject_step_description(task, title, position):
    normalized_title = _normalized(title)
    if "гипотез" in normalized_title and position == 1:
        return "Сформулируй проверяемые гипотезы и задай ожидаемый результат для каждой гипотезы."
    if ("критери" in normalized_title or "оценк" in normalized_title) and position == 2:
        return "Определи критерии оценки и показатели, по которым будут сравниваться результаты экспериментов."
    if "эксперимент" in normalized_title and position == 3:
        return "Проведи эксперименты по выбранному плану и зафиксируй наблюдения для каждой гипотезы."
    if "результат" in normalized_title and position == 4:
        return "Проанализируй результаты экспериментов и сопоставь их с критериями оценки."
    if "эксперимент" in normalized_title and position >= 5:
        return "Проверь выводы экспериментов, отметь ограничения и оставь резерв на финальные правки."
    if "глав" in normalized_title and "структур" in normalized_title:
        return "Разложи главу на логические подразделы и проверь, что структура ведет к основному выводу."
    if "глав" in normalized_title and "тезис" in normalized_title:
        return "Уточни тезис главы и определи, какие материалы нужны для его обоснования."
    if "глав" in normalized_title and "раздел" in normalized_title:
        return "Напиши основные разделы главы, связывая аргументы с выбранной структурой."
    if "глав" in normalized_title and "аргументац" in normalized_title:
        return "Проверь аргументацию главы и уточни места, где выводы требуют дополнительных оснований."
    if "глав" in normalized_title:
        return "Проверь связность главы, переходы между разделами и финальные формулировки вывода."
    if "слайд" in normalized_title and position == 1:
        return "Собери материал для слайдов и выбери факты, которые лучше всего раскрывают тему выступления."
    if "структур" in normalized_title and "выступлен" in normalized_title:
        return "Составь структуру выступления: вступление, ключевые тезисы, примеры и финальный вывод."
    if "слайд" in normalized_title and position == 3:
        return "Подготовь слайды с краткими тезисами, примерами и визуальными опорами для выступления."
    if "выступлен" in normalized_title:
        return "Прорепетируй выступление по слайдам и отметь места, где нужно сократить или уточнить формулировки."
    if "слайд" in normalized_title:
        return "Проверь финальные слайды, единый стиль, порядок тезисов и готовность к показу."
    if "письм" in normalized_title and "цель" in normalized_title:
        return "Уточни цель письма и сформулируй, какого ответа или действия ты ожидаешь от адресата."
    if "письм" in normalized_title and "данные" in normalized_title:
        return "Собери данные для письма: факты, даты, вложения и детали, которые нужно указать адресату."
    if "письм" in normalized_title and "черновик" in normalized_title:
        return "Напиши черновик письма с понятной структурой, основной просьбой и нужными деталями."
    if "письм" in normalized_title and "формулиров" in normalized_title:
        return "Проверь формулировки письма, тон, точность дат и наличие всех вложений."
    if "письм" in normalized_title:
        return "Отправь письмо после финальной проверки адресата, темы, вложений и основного текста."
    return ""


def _pick_position(items, position):
    if not items:
        return ""
    index = min(max(position, 1), len(items)) - 1
    return items[index]


def _block_word(number):
    try:
        value = abs(int(number))
    except (TypeError, ValueError):
        value = 1
    last_two = value % 100
    last = value % 10
    if last_two in range(11, 15):
        return "рабочих блоков"
    if last == 1:
        return "рабочий блок"
    if last in (2, 3, 4):
        return "рабочих блока"
    return "рабочих блоков"


def _minute_word(number):
    try:
        value = abs(int(number))
    except (TypeError, ValueError):
        value = 1
    last_two = value % 100
    last = value % 10
    if last_two in range(11, 15):
        return "минут"
    if last == 1:
        return "минута"
    if last in (2, 3, 4):
        return "минуты"
    return "минут"


def _postprocess_text(text, field, prediction):
    text = " ".join(str(text).split())
    text = _strip_prompt_echo(text)
    text = text.replace("..", ".")
    if field == "schedule_hint":
        params = prediction.get("planning_params", {})
        blocks = params.get("block_count")
        if blocks is not None:
            text = re.sub(
                rf"\b{blocks}\s+рабоч(?:ий|их)\s+блок(?:а|ов)?\b",
                f"{blocks} {_block_word(blocks)}",
                text,
                flags=re.IGNORECASE,
            )
        text = re.sub(r"\b1\s+рабочих\s+блока?\b", "1 рабочий блок", text, flags=re.IGNORECASE)
        for key in ("focus_minutes", "break_minutes", "review_minutes"):
            minutes = params.get(key)
            if minutes is None:
                continue
            text = re.sub(
                rf"\b{minutes}\s+минут(?:а|ы)?\b",
                f"{minutes} {_minute_word(minutes)}",
                text,
                flags=re.IGNORECASE,
            )
    return text.strip()


def _strip_prompt_echo(text):
    text = re.sub(r"^(summary|schedule_hint|step_title|step_description)\s*[:|-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^поле\s*:\s*\w+\s*[.:-]?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^требования\s*:\s*", "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalized(text):
    return " ".join(re.findall(r"[a-zа-яё0-9]+", str(text).lower()))


def _normalize_sentence(text):
    text = text.strip()
    if not text:
        return text
    text = text[:1].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text
