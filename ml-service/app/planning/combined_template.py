GROUP_STAGE_TITLES = {
    "формулировка цели": "Уточнить цель",
    "приоритизация": "Выбрать главное",
    "декомпозиция": "Разложить работу",
    "распределение времени": "Распределить время",
    "старт / борьба с прокрастинацией": "Начать выполнение",
    "организация потока задач": "Организовать поток задач",
    "выполнение": "Выполнить основной этап",
    "контроль / завершение": "Проверить результат",
}


def build_combined_template(selected_methods, templates):
    if not selected_methods:
        return {"steps": []}

    steps = []
    for index, method in enumerate(selected_methods, start=1):
        source_template = templates.get(method["code"]) or {}
        source_step = _pick_source_step(source_template.get("steps") or [], index)
        stage_title = GROUP_STAGE_TITLES.get(method.get("group"), f"Этап {index}")
        steps.append(
            {
                "title": stage_title,
                "description": _step_description(method, source_step),
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


def _step_description(method, source_step):
    source_title = source_step.get("title", "")
    source_description = source_step.get("description", "")
    parts = [
        f"Метод {method['name']} отвечает за этап: {method.get('role', 'работа над задачей')}.",
    ]
    if source_title or source_description:
        parts.append(f"Базовый шаг из шаблона БД: {source_title}. {source_description}".strip())
    return " ".join(parts)


def _schedule_hint(selected_methods):
    names = ", ".join(method["name"] for method in selected_methods[:5])
    return f"Выполнять план по этапам выбранной комбинации методов: {names}."
