from app.planning.role_map import stage_definition, stage_for_method, stage_order_for_count


START_METHODS = {"eat_that_frog", "two_minute_rule", "five_minute_rule", "swiss_cheese", "if_then_planning"}
TIME_METHODS = {
    "time_blocking",
    "timeboxing",
    "pomodoro",
    "flowtime",
    "biological_prime_time",
    "single_tasking",
    "task_batching",
    "ultradian_rhythm",
    "personal_sprint",
}
LARGE_DOMAINS = {"travel", "research", "presentation", "study"}


def build_ranked_methods(methods, method_scores, probabilities):
    ranked = []
    for index, method in enumerate(methods):
        stage = stage_for_method(method)
        definition = stage_definition(stage)
        ranked.append(
            {
                "code": method["code"],
                "name": method["name"],
                "description": method.get("description", ""),
                "group": method.get("group") or method.get("method_group") or "не задана",
                "role": method.get("role") or "кандидат для планирования",
                "plan_stage": stage,
                "plan_function": definition["function"],
                "score": round(float(method_scores[index].item()), 4),
                "confidence": round(float(probabilities[index].item()), 4),
            }
        )
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def select_methods(ranked_methods, task=None, min_count=3, max_count=5):
    if not ranked_methods:
        return {
            "selected_methods": [],
            "combination_confidence": 0.0,
            "explanation": "методы не найдены",
        }

    ranked_methods = sorted(ranked_methods, key=lambda item: item["score"], reverse=True)
    target_count = _target_count(task or {}, min_count, max_count)
    stage_order = stage_order_for_count(target_count)
    selected = []

    for stage in stage_order:
        candidate = _best_candidate_for_stage(ranked_methods, stage, selected, task or {})
        if candidate:
            selected.append(_with_stage(candidate, stage, task or {}))
        if len(selected) >= target_count:
            break

    for candidate in ranked_methods:
        if len(selected) >= target_count:
            break
        if _can_add(candidate, selected):
            selected.append(_with_stage(candidate, stage_for_method(candidate), task or {}))

    if len(selected) < min_count:
        for candidate in ranked_methods:
            if len(selected) >= min_count:
                break
            if not _same_method(candidate, selected):
                selected.append(_with_stage(candidate, stage_for_method(candidate), task or {}))

    selected = selected[:target_count]
    confidence = _combination_confidence(selected)
    explanation = _build_explanation(selected, confidence)
    return {
        "selected_methods": selected,
        "combination_confidence": confidence,
        "explanation": explanation,
    }


def _target_count(task, min_count, max_count):
    estimated = int(task.get("estimated_minutes") or 60)
    priority = int(task.get("priority") or 3)
    if estimated <= 30 or priority >= 5:
        return min_count
    if estimated <= 90:
        return min(max_count, 4)
    return max_count


def _best_candidate_for_stage(ranked_methods, stage, selected, task):
    candidates = [
        candidate
        for candidate in ranked_methods
        if stage_for_method(candidate) == stage and _can_add(candidate, selected)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: _selection_score(candidate, stage, task))


def _can_add(candidate, selected):
    if _same_method(candidate, selected):
        return False
    if any(candidate["role"] == item["role"] for item in selected):
        return False
    candidate_stage = stage_for_method(candidate)
    return all(item.get("plan_stage") != candidate_stage for item in selected)


def _same_method(candidate, selected):
    return any(candidate["code"] == item["code"] for item in selected)


def _with_stage(candidate, stage, task=None):
    definition = stage_definition(stage)
    compatibility = _compatibility_score(candidate, stage, task or {})
    return {
        **candidate,
        "plan_stage": stage,
        "plan_function": definition["function"],
        "compatibility_score": compatibility,
        "selection_score": _selection_score(candidate, stage, task or {}),
    }


def _selection_score(candidate, stage, task):
    return float(candidate.get("score") or 0.0) + _compatibility_score(candidate, stage, task) * 2.0


def _compatibility_score(candidate, stage, task):
    code = candidate.get("code", "")
    context = _task_context(task)
    domain = context["domain"]
    estimated = context["estimated"]
    pressure = context["deadline_pressure"]
    text = context["text"]
    score = 0.5

    if stage == "goal_definition":
        if code in {"smart", "smarter", "personal_okr"}:
            score += 0.25
        if estimated >= 120:
            score += 0.1
    elif stage == "prioritization":
        if code in {"eisenhower", "abcde", "moscow", "pareto_80_20", "ivy_lee"}:
            score += 0.2
        if pressure >= 0.7 and code in {"eisenhower", "abcde", "ivy_lee"}:
            score += 0.2
        if domain in LARGE_DOMAINS and code in {"moscow", "pareto_80_20"}:
            score += 0.1
    elif stage == "decomposition":
        if code in {"wbs", "backward_planning", "critical_path", "alpen"}:
            score += 0.25
        if estimated >= 90 or domain in LARGE_DOMAINS:
            score += 0.15
        if "зависим" in text and code == "critical_path":
            score += 0.2
    elif stage == "execution_time":
        if code in TIME_METHODS:
            score += 0.2
        if code in START_METHODS:
            score += 0.1 if estimated <= 30 or pressure >= 0.8 else -0.35
        if domain in LARGE_DOMAINS and estimated >= 90:
            if code in {"time_blocking", "timeboxing", "flowtime", "pomodoro", "personal_sprint"}:
                score += 0.3
            if code in START_METHODS:
                score -= 0.25
        if domain == "travel" and code in {"time_blocking", "timeboxing"}:
            score += 0.2
        if domain in {"research", "presentation", "study"} and code in {"time_blocking", "flowtime", "pomodoro"}:
            score += 0.2
    elif stage == "review_control":
        if code in {"checklist", "daily_review", "weekly_review", "action_priority_matrix"}:
            score += 0.25
        if domain in LARGE_DOMAINS and code in {"checklist", "action_priority_matrix"}:
            score += 0.15

    return round(max(0.0, min(score, 1.0)), 3)


def _task_context(task):
    semantic = task.get("_semantic_structure") if isinstance(task, dict) else {}
    semantic = semantic if isinstance(semantic, dict) else {}
    raw_text = " ".join(
        [
            str(task.get("title", "")),
            str(task.get("description", "")),
            str(task.get("context", "")),
            str(semantic.get("goal", "")),
            " ".join(str(item) for item in semantic.get("subgoals", []) if str(item).strip()),
            " ".join(str(item) for item in semantic.get("constraints", []) if str(item).strip()),
        ]
    ).lower()
    estimated = int(task.get("estimated_minutes") or 60)
    return {
        "domain": _domain(task, semantic, raw_text),
        "estimated": estimated,
        "deadline_pressure": _deadline_pressure(task, raw_text),
        "text": raw_text,
    }


def _domain(task, semantic, text):
    domain = str(semantic.get("domain") or "").strip().lower()
    if domain:
        return domain
    checks = (
        ("travel", ("отпуск", "поезд", "маршрут", "жиль", "бюджет", "документ")),
        ("presentation", ("презентац", "слайд", "выступлен", "доклад")),
        ("research", ("гипотез", "эксперимент", "критери", "исслед")),
        ("email", ("письм", "почт", "ответ")),
        ("study", ("учеб", "глава", "конспект", "магистер")),
    )
    for code, markers in checks:
        if any(marker in text for marker in markers):
            return code
    return "general"


def _deadline_pressure(task, text):
    priority = int(task.get("priority") or 3)
    if priority >= 5 or "сроч" in text or "сегодня" in text:
        return 1.0
    if task.get("deadline"):
        return 0.7
    if priority >= 4:
        return 0.5
    return 0.0


def _combination_confidence(selected):
    if not selected:
        return 0.0
    confidence_sum = sum(float(item.get("confidence") or 0.0) for item in selected)
    compatibility_sum = sum(float(item.get("compatibility_score") or 0.0) for item in selected)
    stage_bonus = len({item.get("plan_stage") for item in selected}) / max(1, len(selected))
    value = (confidence_sum / len(selected)) * 0.55 + (compatibility_sum / len(selected)) * 0.25 + stage_bonus * 0.2
    return round(min(value, 1.0), 3)


def _build_explanation(selected, confidence):
    if not selected:
        return "не удалось выбрать комбинацию методов"
    parts = [
        f"{item['name']} отвечает за {item.get('plan_function', 'этап плана')}: {item['role']} "
        f"(semantic compatibility {item.get('compatibility_score', 0)})"
        for item in selected
    ]
    stages = ", ".join(dict.fromkeys(item.get("plan_function", item["group"]) for item in selected))
    return (
        "Комбинация выбрана по scores GRU/dense-модели, semantic compatibility и покрытию разных этапов работы. "
        f"Она лучше одного метода, потому что разделяет план на функции: {stages}. "
        f"Уверенность комбинации: {confidence}. Методы: {'; '.join(parts)}."
    )
