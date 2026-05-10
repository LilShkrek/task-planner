from app.planning.role_map import stage_definition, stage_for_method, stage_order_for_count


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
        candidate = _best_candidate_for_stage(ranked_methods, stage, selected)
        if candidate:
            selected.append(_with_stage(candidate, stage))
        if len(selected) >= target_count:
            break

    for candidate in ranked_methods:
        if len(selected) >= target_count:
            break
        if _can_add(candidate, selected):
            selected.append(_with_stage(candidate, stage_for_method(candidate)))

    if len(selected) < min_count:
        for candidate in ranked_methods:
            if len(selected) >= min_count:
                break
            if not _same_method(candidate, selected):
                selected.append(_with_stage(candidate, stage_for_method(candidate)))

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


def _best_candidate_for_stage(ranked_methods, stage, selected):
    for candidate in ranked_methods:
        if stage_for_method(candidate) == stage and _can_add(candidate, selected):
            return candidate
    return None


def _can_add(candidate, selected):
    if _same_method(candidate, selected):
        return False
    if any(candidate["role"] == item["role"] for item in selected):
        return False
    candidate_stage = stage_for_method(candidate)
    return all(item.get("plan_stage") != candidate_stage for item in selected)


def _same_method(candidate, selected):
    return any(candidate["code"] == item["code"] for item in selected)


def _with_stage(candidate, stage):
    definition = stage_definition(stage)
    return {
        **candidate,
        "plan_stage": stage,
        "plan_function": definition["function"],
    }


def _combination_confidence(selected):
    if not selected:
        return 0.0
    confidence_sum = sum(float(item.get("confidence") or 0.0) for item in selected)
    stage_bonus = len({item.get("plan_stage") for item in selected}) / max(1, len(selected))
    value = (confidence_sum / len(selected)) * 0.75 + stage_bonus * 0.25
    return round(min(value, 1.0), 3)


def _build_explanation(selected, confidence):
    if not selected:
        return "не удалось выбрать комбинацию методов"
    parts = [
        f"{item['name']} отвечает за {item.get('plan_function', 'этап плана')}: {item['role']}"
        for item in selected
    ]
    stages = ", ".join(dict.fromkeys(item.get("plan_function", item["group"]) for item in selected))
    return (
        "Комбинация выбрана по scores GRU/dense-модели и покрытию разных этапов работы. "
        f"Она лучше одного метода, потому что разделяет план на функции: {stages}. "
        f"Уверенность комбинации: {confidence}. Методы: {'; '.join(parts)}."
    )
