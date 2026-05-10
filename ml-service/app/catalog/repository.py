import json
import os
from functools import lru_cache

import psycopg


def database_url():
    return os.getenv(
        "ML_DATABASE_URL",
        os.getenv("DATABASE_URL", "postgres://task_planner:task_planner@localhost:5432/task_planner?sslmode=disable"),
    )


@lru_cache(maxsize=1)
def load_catalog():
    with psycopg.connect(database_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id,
                    m.code,
                    m.name,
                    m.description,
                    m.best_for,
                    m.method_group,
                    m.role,
                    t.template
                FROM time_management_methods m
                JOIN LATERAL (
                    SELECT template
                    FROM plan_templates
                    WHERE method_id = m.id
                    ORDER BY id DESC
                    LIMIT 1
                ) t ON true
                ORDER BY m.id
                """
            )
            rows = cur.fetchall()

    if not rows:
        raise RuntimeError("в БД нет методов тайм-менеджмента с шаблонами планов")

    methods = []
    templates = {}
    for row in rows:
        method = {
            "id": row[0],
            "code": row[1],
            "name": row[2],
            "description": row[3],
            "best_for": row[4],
            "group": row[5],
            "role": row[6],
        }
        methods.append(method)
        templates[method["code"]] = _decode_template(row[7])

    return {"methods": methods, "templates": templates}


def _decode_template(value):
    if isinstance(value, str):
        return json.loads(value)
    return value
