from app.planning.adapter import adapt_steps


def generate_plan(task, prediction, templates):
    method_code = prediction["method_code"]
    template = templates.get(method_code)
    if not template:
        raise RuntimeError(f"в БД нет шаблона плана для метода {method_code}")

    steps = template.get("steps") or []
    if not steps:
        raise RuntimeError(f"шаблон плана для метода {method_code} не содержит шагов")

    estimated = int(task.get("estimated_minutes") or 60)
    planning_params = prediction.get("planning_params", {})
    default_minutes = max(15, estimated // len(steps))

    built_steps = [
        _build_step(task, step, index + 1, default_minutes, planning_params, len(steps))
        for index, step in enumerate(steps)
    ]
    return adapt_steps(task, built_steps)


def _build_step(task, step, position, default_minutes, planning_params, total_steps):
    if isinstance(step, str):
        title = step
        description = _description(task, step)
        minutes = default_minutes
    else:
        title = step.get("title") or f"Шаг {position}"
        description = step.get("description") or _description(task, title)
        minutes = int(step.get("estimated_minutes") or default_minutes)

    if position == total_steps and planning_params.get("review_minutes"):
        minutes = planning_params["review_minutes"]

    return {
        "position": position,
        "title": title,
        "description": description.format(task_title=task.get("title") or "задача"),
        "estimated_minutes": max(15, minutes),
        "status": "pending",
    }


def _description(task, title):
    task_title = task.get("title") or "задача"
    return f"{title} для задачи: {task_title}."
