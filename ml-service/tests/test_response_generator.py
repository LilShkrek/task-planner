import unittest

from app.generation.response_generator import generate_response


class FakeTextGenerator:
    def generate(self, prompt, max_chars=220):
        title = _title_from_prompt(prompt)
        field = _field_from_prompt(prompt)
        step_index = _step_index_from_prompt(prompt)

        if field == "summary":
            return f"Нужно осмысленно выполнить задачу: {title}"
        if field == "schedule_hint":
            return f"Лучше выполнить задачу {title} несколькими рабочими блоками с короткими перерывами"
        if field == "step_title":
            return f"Шаг {step_index} для {title}"
        if field == "step_description":
            return f"Выполнить действие шага {step_index} с учетом содержания задачи {title}"
        return "Сгенерированный текст"


class SubjectAwareFakeTextGenerator:
    def generate(self, prompt, max_chars=220):
        title = _title_from_prompt(prompt)
        field = _field_from_prompt(prompt)

        if "презентац" in title.lower():
            subject = "слайды по базам данных"
        elif "письмо" in title.lower():
            subject = "письмо преподавателю"
        else:
            subject = "учебный конспект главы"

        if field == "summary":
            return f"План про {subject}"
        if field == "schedule_hint":
            return f"Расписание учитывает {subject}"
        if field == "step_title":
            return f"Подготовить {subject}"
        return f"Подробно выполнить работу про {subject}"


class BadThenGoodTextGenerator:
    def generate(self, prompt, max_chars=220):
        field = _field_from_prompt(prompt)
        strict = "Строгий повтор" in prompt
        step_index = _step_index_from_prompt(prompt)

        if not strict:
            if field == "summary":
                return _title_from_prompt(prompt)
            if field == "schedule_hint":
                return "Расписание задачи."
            if field == "step_title":
                return _title_from_prompt(prompt)
            if field == "step_description":
                return "Описание шага задачи."

        if field == "summary":
            return "Нужно подготовить материалы и получить проверяемый результат"
        if field == "schedule_hint":
            return "Разбей работу на фокус-блоки и оставь отдельное время на финальную проверку"
        if field == "step_title":
            return f"Конкретный этап {step_index}"
        if field == "step_description":
            return f"Выполни конкретное действие этапа {step_index} с учетом деталей задачи"
        return "Конкретный текст"


class AlwaysBadTextGenerator:
    def generate(self, prompt, max_chars=220):
        field = _field_from_prompt(prompt)
        if field == "schedule_hint":
            return "Расписание задачи."
        if field == "step_description":
            return "Описание шага задачи."
        return _title_from_prompt(prompt)


class QualityProblemTextGenerator:
    def generate(self, prompt, max_chars=220):
        field = _field_from_prompt(prompt)
        step_index = _step_index_from_prompt(prompt)

        if field == "summary":
            return "Подготовка презентации"
        if field == "schedule_hint":
            return "Запланируй работу на 1 рабочих блока и оставь время на проверку"
        if field == "step_title":
            if step_index == "1":
                return "Что будет делать для"
            return "Собрать материалы"
        if field == "step_description":
            return _description_from_prompt(prompt)
        return "Плохой текст"


class GenericSubjectTextGenerator:
    def generate(self, prompt, max_chars=220):
        field = _field_from_prompt(prompt)
        if field == "summary":
            return "План поможет получить предметный результат"
        if field == "schedule_hint":
            return "Запланируй работу на 21 рабочих блока по 21 минут и оставь 22 минут на проверку"
        if field == "step_title":
            step_index = _step_index_from_prompt(prompt)
            if step_index == "1":
                return "Разделить задачу на блоки"
            if step_index == "2":
                return "Выполнить первый блок"
            return "Выполнить следующий блок"
        if field == "step_description":
            return "Продолжить работу по расписанию без смешивания этапов"
        return "Общий текст"


class RepeatedDescriptionTextGenerator:
    def generate(self, prompt, max_chars=220):
        field = _field_from_prompt(prompt)
        step_index = _step_index_from_prompt(prompt)
        if field == "summary":
            return "План поможет выполнить предметную задачу с проверкой результата"
        if field == "schedule_hint":
            return "Запланируй работу на 3 рабочих блока по 35 минут и оставь 15 минут на проверку"
        if field == "step_title":
            titles = {
                "1": "Сформулировать гипотезы",
                "2": "Определить критерии оценки",
                "3": "Провести эксперименты",
                "4": "Проанализировать результаты экспериментов",
                "5": "Проверить выводы экспериментов",
            }
            return titles.get(step_index, "Проверить выводы экспериментов")
        if field == "step_description":
            return "Опиши ход экспериментов, нужные данные и ожидаемые наблюдения для проверки гипотез"
        return "Общий текст"


class ResponseGeneratorTest(unittest.TestCase):
    def test_generate_response_keeps_step_count_from_database_template(self):
        result = generate_response(
            task={
                "title": "Проверить настройки приложения",
                "description": "Проверить параметры приложения",
                "estimated_minutes": 90,
            },
            prediction={
                "method_code": "pomodoro",
                "method_name": "Pomodoro",
                "planning_params": {"review_minutes": 20},
            },
            template={
                "steps": [
                    {"title": "Шаг 1", "description": "Базовое действие для \"{task_title}\"."},
                    {"title": "Шаг 2", "description": "Проверка для \"{task_title}\"."},
                ],
                "schedule_hint": "Работать по {focus_minutes} минут.",
            },
            text_generator=FakeTextGenerator(),
        )

        self.assertEqual(len(result["plan_draft"]), 2)
        self.assertEqual(result["summary"], "План поможет Проверить параметры приложения и оставить время на проверку результата.")
        self.assertEqual(result["plan_draft"][1]["estimated_minutes"], 20)
        self.assertEqual(result["plan_draft"][0]["title"], "Шаг 1")

    def test_generate_response_requires_template_steps(self):
        with self.assertRaisesRegex(RuntimeError, "не содержит шагов"):
            generate_response(
                {"title": "Задача", "estimated_minutes": 60},
                {"method_code": "pomodoro", "method_name": "Pomodoro", "planning_params": {}},
                {"steps": []},
                text_generator=FakeTextGenerator(),
            )

    def test_generate_response_makes_different_subject_outputs(self):
        generator = SubjectAwareFakeTextGenerator()
        presentation = generate_response(
            task={
                "title": "Подготовить презентацию по базам данных",
                "description": "Нужны слайды и выступление",
                "context": "учебная задача",
                "estimated_minutes": 120,
            },
            prediction={
                "method_code": "time_blocking",
                "method_name": "Time Blocking",
                "planning_params": {"focus_minutes": 40, "review_minutes": 20},
            },
            template=_template(),
            text_generator=generator,
        )
        email = generate_response(
            task={
                "title": "Ответить на письмо преподавателю",
                "description": "Уточнить дату сдачи и приложить файл",
                "context": "почта",
                "estimated_minutes": 45,
            },
            prediction={
                "method_code": "pomodoro",
                "method_name": "Pomodoro",
                "planning_params": {"focus_minutes": 25, "review_minutes": 15},
            },
            template=_template(),
            text_generator=generator,
        )

        self.assertNotEqual(presentation["plan_draft"][0]["title"], email["plan_draft"][0]["title"])
        self.assertIn("слайд", presentation["plan_draft"][0]["title"].lower())
        self.assertIn("письм", email["plan_draft"][0]["title"].lower())

    def test_generate_response_retries_bad_generated_text(self):
        result = generate_response(
            task={
                "title": "Подготовить презентацию",
                "description": "Собрать материалы и сделать слайды",
                "estimated_minutes": 90,
            },
            prediction={
                "method_code": "time_blocking",
                "method_name": "Time Blocking",
                "planning_params": {"focus_minutes": 35, "review_minutes": 15},
            },
            template=_template(),
            text_generator=BadThenGoodTextGenerator(),
        )

        self.assertNotEqual(result["summary"], "Подготовить презентацию.")
        self.assertEqual(result["plan_draft"][0]["title"], "Собрать материал для слайдов")
        self.assertNotIn("Описание шага задачи", result["plan_draft"][0]["description"])

    def test_generate_response_uses_template_fallback_after_failed_validation(self):
        result = generate_response(
            task={
                "title": "Подготовить презентацию",
                "description": "Собрать материалы и сделать слайды",
                "context": "учебная задача",
                "estimated_minutes": 90,
            },
            prediction={
                "method_code": "time_blocking",
                "method_name": "Time Blocking",
                "planning_params": {"focus_minutes": 35, "break_minutes": 5, "block_count": 2, "review_minutes": 15},
            },
            template=_template(),
            text_generator=AlwaysBadTextGenerator(),
        )

        titles = [step["title"] for step in result["plan_draft"]]
        self.assertEqual(len(set(titles)), len(titles))
        self.assertNotEqual(result["summary"], "Подготовить презентацию.")
        self.assertIn("Собрать материалы", result["summary"])
        self.assertNotIn("Описание шага задачи", result["plan_draft"][0]["description"])

    def test_generate_response_filters_quality_problems(self):
        result = generate_response(
            task={
                "title": "Подготовить презентацию",
                "description": "Собрать материалы и сделать слайды",
                "context": "учебная задача",
                "estimated_minutes": 60,
            },
            prediction={
                "method_code": "time_blocking",
                "method_name": "Time Blocking",
                "planning_params": {"focus_minutes": 30, "break_minutes": 5, "block_count": 1, "review_minutes": 10},
            },
            template=_template(),
            text_generator=QualityProblemTextGenerator(),
        )

        self.assertNotEqual(result["summary"], "Подготовка презентации.")
        self.assertNotIn("1 рабочих блока", result["schedule_hint"])
        self.assertIn("1 рабочий блок", result["schedule_hint"])
        self.assertNotIn("Что будет делать", result["plan_draft"][0]["title"])
        self.assertNotEqual(result["plan_draft"][0]["description"], "Собрать материалы и сделать слайды.")

    def test_subject_experiment_task_rejects_generic_steps(self):
        semantic = {
            "goal": "проверить исследовательские гипотезы",
            "subgoals": ["сформулировать гипотезы", "определить критерии оценки", "провести эксперименты"],
            "constraints": ["исследовательская задача"],
            "domain": "эксперименты и гипотезы",
        }
        result = generate_response(
            task={
                "title": "Спланировать эксперименты для проверки гипотез",
                "description": "Нужно сформулировать гипотезы, провести эксперименты и определить критерии оценки",
                "context": "исследовательская задача",
                "estimated_minutes": 120,
            },
            prediction=_prediction(blocks=21, focus=21, review=22),
            template=_generic_time_blocking_template(),
            text_generator=GenericSubjectTextGenerator(),
            semantic_structure=semantic,
        )

        titles = [step["title"] for step in result["plan_draft"]]
        self.assertIn("Сформулировать гипотезы", titles)
        self.assertIn("Определить критерии оценки", titles)
        self.assertIn("Провести эксперименты", titles)
        self.assertNotIn("Разделить задачу на блоки", titles)
        _assert_unique_descriptions(self, result)
        _assert_title_description_consistency(self, result)
        self.assertIn("21 рабочий блок", result["schedule_hint"])
        self.assertIn("21 минута", result["schedule_hint"])
        self.assertIn("22 минуты", result["schedule_hint"])

    def test_subject_chapter_task_gets_chapter_specific_steps(self):
        result = generate_response(
            task={
                "title": "Дописать главу магистерской работы",
                "description": "Нужно уточнить структуру главы и связать выводы с критериями оценки",
                "context": "магистерская диссертация",
                "estimated_minutes": 180,
            },
            prediction=_prediction(blocks=4),
            template=_generic_time_blocking_template(),
            text_generator=GenericSubjectTextGenerator(),
        )

        titles = [step["title"] for step in result["plan_draft"]]
        self.assertIn("Уточнить тезис главы", titles)
        self.assertIn("Выстроить структуру главы", titles)
        self.assertTrue(all("блок" not in title.lower() for title in titles))
        self.assertTrue(any("глав" in step["description"].lower() for step in result["plan_draft"]))
        _assert_unique_descriptions(self, result)
        _assert_title_description_consistency(self, result)

    def test_subject_presentation_task_gets_slide_and_speech_steps(self):
        semantic = {
            "goal": "подготовить презентацию для защиты проекта",
            "subgoals": ["собрать материал для слайдов", "продумать структуру", "прорепетировать выступление"],
            "constraints": ["учебный проект"],
            "domain": "презентация",
        }
        result = generate_response(
            task={
                "title": "Подготовить презентацию для защиты проекта",
                "description": "Нужно сделать слайды, продумать структуру и прорепетировать выступление",
                "context": "учебный проект",
                "estimated_minutes": 150,
            },
            prediction=_prediction(blocks=5),
            template=_generic_time_blocking_template(),
            text_generator=GenericSubjectTextGenerator(),
            semantic_structure=semantic,
        )

        titles = [step["title"] for step in result["plan_draft"]]
        self.assertIn("Составить структуру выступления", titles)
        self.assertIn("Подготовить слайды", titles)
        self.assertIn("Прорепетировать выступление", titles)
        self.assertNotIn("Выполнить следующий блок", titles)
        _assert_unique_descriptions(self, result)
        _assert_title_description_consistency(self, result)

    def test_repeated_descriptions_fallback_to_position_roles(self):
        result = generate_response(
            task={
                "title": "Спланировать эксперименты для проверки гипотез",
                "description": "Нужно сформулировать гипотезы, провести эксперименты и определить критерии оценки",
                "context": "исследовательская задача",
                "estimated_minutes": 120,
            },
            prediction=_prediction(),
            template=_generic_time_blocking_template(),
            text_generator=RepeatedDescriptionTextGenerator(),
        )

        _assert_unique_descriptions(self, result)
        _assert_title_description_consistency(self, result)
        self.assertIn("Сформулируй проверяемые гипотезы", result["plan_draft"][0]["description"])
        self.assertIn("критерии оценки", result["plan_draft"][1]["description"])
        self.assertIn("Проведи эксперименты", result["plan_draft"][2]["description"])
        self.assertIn("Проанализируй результаты", result["plan_draft"][3]["description"])
        self.assertIn("Проверь выводы", result["plan_draft"][4]["description"])

    def test_email_task_uses_different_position_roles(self):
        semantic = {
            "goal": "ответить на письмо преподавателю",
            "subgoals": ["уточнить цель письма", "собрать данные", "написать черновик", "проверить формулировки"],
            "constraints": ["приложить файл"],
            "domain": "письмо",
        }
        result = generate_response(
            task={
                "title": "Ответить на письмо преподавателю",
                "description": "Нужно уточнить дату сдачи и приложить файл",
                "context": "почта",
                "estimated_minutes": 45,
            },
            prediction=_prediction(blocks=2),
            template=_generic_time_blocking_template(),
            text_generator=GenericSubjectTextGenerator(),
            semantic_structure=semantic,
        )

        titles = [step["title"] for step in result["plan_draft"]]
        self.assertEqual(
            titles,
            [
                "Уточнить цель письма",
                "Собрать данные для письма",
                "Написать черновик письма",
                "Проверить формулировки письма",
                "Отправить письмо",
            ],
        )
        _assert_unique_descriptions(self, result)
        _assert_title_description_consistency(self, result)

    def test_vacation_trip_uses_semantic_structure_for_concrete_steps(self):
        semantic = {
            "goal": "организовать отпуск и поездку в Казань",
            "subgoals": [
                "выбрать даты поездки",
                "рассчитать бюджет",
                "забронировать жилье",
                "составить маршрут",
                "подготовить вещи и документы",
            ],
            "constraints": ["не выйти за бюджет", "проверить документы"],
            "domain": "отпуск и поездка",
        }
        result = generate_response(
            task={
                "title": "Организовать отпуск и поездку в Казань",
                "description": "Нужно выбрать даты, рассчитать бюджет, забронировать жилье, составить маршрут и собрать документы",
                "context": "личная поездка",
                "estimated_minutes": 180,
            },
            prediction=_prediction(blocks=5),
            template=_generic_time_blocking_template(),
            text_generator=GenericSubjectTextGenerator(),
            semantic_structure=semantic,
        )

        titles = [step["title"] for step in result["plan_draft"]]
        self.assertEqual(
            titles,
            [
                "Уточнить даты",
                "Рассчитать бюджет",
                "Выбрать жилье",
                "Составить маршрут",
                "Подготовить вещи и документы",
            ],
        )
        self.assertIn("даты", result["plan_draft"][0]["description"])
        self.assertIn("бюджет", result["plan_draft"][1]["description"])
        self.assertIn("жиль", result["plan_draft"][2]["description"])
        self.assertIn("маршрут", result["plan_draft"][3]["description"])
        self.assertIn("документ", result["plan_draft"][4]["description"])
        _assert_unique_descriptions(self, result)
        _assert_title_description_consistency(self, result)


def _template():
    return {
        "steps": [
            {"title": "Уточнить результат", "description": "Уточнить результат для \"{task_title}\"."},
            {"title": "Разбить работу", "description": "Разбить работу для \"{task_title}\"."},
            {"title": "Выполнить", "description": "Выполнить основные действия для \"{task_title}\"."},
        ],
        "schedule_hint": "Запланировать работу по {focus_minutes} минут и оставить {review_minutes} минут на проверку.",
    }


def _generic_time_blocking_template():
    return {
        "steps": [
            {"title": "Разделить задачу на блоки", "description": "Разложить задачу \"{task_title}\" на логические части."},
            {"title": "Назначить время для каждого блока", "description": "Выделить отдельные интервалы времени под каждый блок."},
            {"title": "Выполнить первый блок", "description": "Начать с блока, который сильнее всего продвигает результат."},
            {"title": "Выполнить следующий блок", "description": "Продолжить работу по расписанию без смешивания этапов."},
            {"title": "Оставить резерв на проверку", "description": "Проверить результат и исправить недочеты."},
        ],
        "schedule_hint": "Запланировать работу блоками.",
    }


def _prediction(blocks=3, focus=35, review=15):
    return {
        "method_code": "time_blocking",
        "method_name": "Time Blocking",
        "planning_params": {
            "focus_minutes": focus,
            "break_minutes": 5,
            "block_count": blocks,
            "review_minutes": review,
        },
    }


def _assert_unique_descriptions(test_case, result):
    descriptions = [step["description"] for step in result["plan_draft"]]
    test_case.assertEqual(len(descriptions), len(set(descriptions)))


def _assert_title_description_consistency(test_case, result):
    for step in result["plan_draft"]:
        title_words = _content_words(step["title"])
        description_words = _content_words(step["description"])
        test_case.assertTrue(
            title_words & description_words,
            f"title и description не согласованы: {step['title']} / {step['description']}",
        )


def _content_words(text):
    return {
        _word_key(word)
        for word in text.lower().replace("ё", "е").replace(",", " ").replace(".", " ").split()
        if len(word) > 3
    }


def _word_key(word):
    if word.startswith("жиль"):
        return "жиль"
    if word.startswith("документ"):
        return "документ"
    return word[:7]


def _title_from_prompt(prompt):
    if "Задача: " in prompt:
        return prompt.split("Задача: ", 1)[1].split(".", 1)[0]
    return ""


def _step_index_from_prompt(prompt):
    if "Номер шага: " not in prompt:
        return ""
    return prompt.split("Номер шага: ", 1)[1].split(".", 1)[0]


def _description_from_prompt(prompt):
    if "Описание задачи: " not in prompt:
        return ""
    return prompt.split("Описание задачи: ", 1)[1].split(".", 1)[0]


def _field_from_prompt(prompt):
    if "Поле: summary." in prompt:
        return "summary"
    if "Поле: schedule_hint." in prompt:
        return "schedule_hint"
    if "Поле: step_title." in prompt:
        return "step_title"
    if "Поле: step_description." in prompt:
        return "step_description"
    return ""


if __name__ == "__main__":
    unittest.main()
