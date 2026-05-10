STAGE_DEFINITIONS = {
    "goal_definition": {
        "title": "Уточнить цель",
        "function": "постановка цели",
        "description": "сформулировать ожидаемый результат и критерии готовности",
    },
    "prioritization": {
        "title": "Выделить главное",
        "function": "приоритизация",
        "description": "отделить обязательные действия от второстепенных",
    },
    "decomposition": {
        "title": "Разложить работу",
        "function": "декомпозиция",
        "description": "разбить задачу на понятные части и порядок выполнения",
    },
    "execution_time": {
        "title": "Организовать выполнение",
        "function": "распределение времени и выполнение",
        "description": "задать рабочий ритм и выполнить основные действия",
    },
    "review_control": {
        "title": "Проверить результат",
        "function": "контроль и завершение",
        "description": "сверить итог с целью и оставить резерв на исправления",
    },
}

GROUP_TO_STAGE = {
    "формулировка цели": "goal_definition",
    "приоритизация": "prioritization",
    "декомпозиция": "decomposition",
    "распределение времени": "execution_time",
    "старт / борьба с прокрастинацией": "execution_time",
    "организация потока задач": "execution_time",
    "выполнение": "execution_time",
    "контроль / завершение": "review_control",
}

FULL_STAGE_ORDER = (
    "goal_definition",
    "prioritization",
    "decomposition",
    "execution_time",
    "review_control",
)

COMPACT_STAGE_ORDER = (
    "prioritization",
    "execution_time",
    "review_control",
)


def stage_for_method(method):
    return GROUP_TO_STAGE.get(method.get("group") or method.get("method_group") or "", "execution_time")


def stage_definition(stage):
    return STAGE_DEFINITIONS.get(stage, STAGE_DEFINITIONS["execution_time"])


def stage_order_for_count(count):
    return COMPACT_STAGE_ORDER if count <= 3 else FULL_STAGE_ORDER
