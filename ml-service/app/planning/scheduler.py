def build_schedule_hint(task, prediction, templates):
    method_code = prediction["method_code"]
    template = templates.get(method_code)
    if not template:
        raise RuntimeError(f"в БД нет шаблона расписания для метода {method_code}")

    hint = template.get("schedule_hint")
    if not hint:
        raise RuntimeError(f"шаблон для метода {method_code} не содержит schedule_hint")

    values = {
        "task_title": task.get("title") or "задача",
        "estimated_minutes": int(task.get("estimated_minutes") or 60),
        **prediction.get("planning_params", {}),
    }
    return hint.format(**values)
