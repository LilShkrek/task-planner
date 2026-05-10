TARGET_GROUPS = (
    "формулировка цели",
    "приоритизация",
    "декомпозиция",
    "распределение времени",
    "контроль / завершение",
    "выполнение",
)

COMPACT_GROUPS = (
    "приоритизация",
    "старт / борьба с прокрастинацией",
    "распределение времени",
    "контроль / завершение",
)


def build_ranked_methods(methods, method_scores, probabilities):
    ranked = []
    for index, method in enumerate(methods):
        ranked.append(
            {
                "code": method["code"],
                "name": method["name"],
                "description": method.get("description", ""),
                "group": method.get("group") or method.get("method_group") or "не задана",
                "role": method.get("role") or "кандидат для планирования",
                "score": round(float(method_scores[index].item()), 4),
                "confidence": round(float(probabilities[index].item()), 4),
            }
        )
    return sorted(ranked, key=lambda item: item["score"], reverse=True)


def select_methods(ranked_methods, task=None, min_count=3, max_count=5):
    if not ranked_methods:
        return {"selected_methods": [], "explanation": "методы не найдены"}

    ranked_methods = sorted(ranked_methods, key=lambda item: item["score"], reverse=True)
    target_count = _target_count(task or {}, min_count, max_count)
    groups = COMPACT_GROUPS if target_count <= 3 else TARGET_GROUPS
    selected = []

    for group in groups:
        candidate = _best_candidate_for_group(ranked_methods, group, selected)
        if candidate:
            selected.append(candidate)
        if len(selected) >= target_count:
            break

    for candidate in ranked_methods:
        if len(selected) >= target_count:
            break
        if _can_add(candidate, selected):
            selected.append(candidate)

    if len(selected) < min_count:
        for candidate in ranked_methods:
            if len(selected) >= min_count:
                break
            if not _same_method(candidate, selected):
                selected.append(candidate)

    selected = selected[:target_count]
    explanation = _build_explanation(selected)
    return {"selected_methods": selected, "explanation": explanation}


def _target_count(task, min_count, max_count):
    estimated = int(task.get("estimated_minutes") or 60)
    priority = int(task.get("priority") or 3)
    if estimated <= 30 or priority >= 5:
        return min_count
    if estimated <= 90:
        return min(max_count, 4)
    return max_count


def _best_candidate_for_group(ranked_methods, group, selected):
    for candidate in ranked_methods:
        if candidate["group"] == group and _can_add(candidate, selected):
            return candidate
    return None


def _can_add(candidate, selected):
    if _same_method(candidate, selected):
        return False
    if any(candidate["role"] == item["role"] for item in selected):
        return False
    group_count = sum(1 for item in selected if item["group"] == candidate["group"])
    return group_count == 0


def _same_method(candidate, selected):
    return any(candidate["code"] == item["code"] for item in selected)


def _build_explanation(selected):
    if not selected:
        return "не удалось выбрать комбинацию методов"
    parts = [f"{item['name']} - {item['role']}" for item in selected]
    groups = ", ".join(dict.fromkeys(item["group"] for item in selected))
    return (
        "Комбинация выбрана по высоким scores модели и разным ролям методов. "
        f"Она покрывает этапы: {groups}. Методы: {'; '.join(parts)}."
    )
