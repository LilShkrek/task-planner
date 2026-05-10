from app.planning.role_map import stage_definition, stage_for_method


def build_combined_template(selected_methods, templates):
    if not selected_methods:
        return {"steps": []}

    steps = []
    for index, method in enumerate(selected_methods, start=1):
        source_template = templates.get(method["code"]) or {}
        source_step = _pick_source_step(source_template.get("steps") or [], index)
        stage = method.get("plan_stage") or stage_for_method(method)
        definition = stage_definition(stage)
        steps.append(
            {
                "title": definition["title"],
                "description": _step_description(method, source_step, definition),
                "plan_stage": stage,
                "plan_function": definition["function"],
                "method_code": method["code"],
                "method_name": method["name"],
                "method_group": method.get("group", ""),
                "method_role": method.get("role", ""),
            }
        )

    return {
        "method_code": "multi_method",
        "steps": steps,
        "schedule_hint": _schedule_hint(selected_methods),
    }


def _pick_source_step(steps, position):
    if not steps:
        return {}
    index = min(max(position, 1), len(steps)) - 1
    return steps[index] if isinstance(steps[index], dict) else {"title": str(steps[index])}


def _step_description(method, source_step, definition):
    source_title = source_step.get("title", "")
    source_description = source_step.get("description", "")
    parts = [
        f"Функция этапа: {definition['function']}.",
        f"Метод {method['name']} отвечает за этот этап: {method.get('role', 'работа над задачей')}.",
        f"Ожидаемый вклад метода: {definition['description']}.",
    ]
    if source_title or source_description:
        parts.append(f"Базовый шаг из шаблона БД: {source_title}. {source_description}".strip())
    return " ".join(parts)


def _schedule_hint(selected_methods):
    names = ", ".join(method["name"] for method in selected_methods[:5])
    return f"Выполнять план по этапам выбранной комбинации методов: {names}."
