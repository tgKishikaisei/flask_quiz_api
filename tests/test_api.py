import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# main.py создаёт приложение при импорте — не трогаем рабочую базу
os.environ["DATABASE_URL"] = "sqlite://"

from main import create_app  # noqa: E402

ADMIN = {"X-API-Key": "admin-key-for-tests-123456"}


@pytest.fixture()
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "ADMIN_API_KEY": ADMIN["X-API-Key"], "TESTING": True})
    with app.test_client() as test_client:
        yield test_client


def register(client, name, phone):
    r = client.post("/api/register", json={"name": name, "phone_number": phone})
    assert r.status_code == 201, r.get_json()
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def add_question(client, text, correct=2, level=1):
    r = client.post("/api/questions", headers=ADMIN, json={"main_text": text, "level": level, "correct_answer": correct,
                                                           "variant_1": "a", "variant_2": "b", "variant_3": "c"})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["question_id"]


def test_questions_hide_correct_answer(client):
    add_question(client, "2+2?")
    questions = client.get("/api/get-questions/1").get_json()["questions"]
    assert len(questions) == 1 and "correct_answer" not in questions[0]


def test_only_admin_adds_questions(client):
    assert client.post("/api/questions", json={"main_text": "x"}).status_code == 401
    assert client.post("/api/questions", headers=ADMIN, json={"main_text": "x", "level": 1, "correct_answer": 4,
                                                              "variant_1": "a", "variant_2": "b"}).status_code == 422


def test_score_is_computed_by_server(client):
    q1, q2 = add_question(client, "q1", correct=1), add_question(client, "q2", correct=2)
    alice = register(client, "Alice", "+998900000001")
    assert client.post(f"/api/check-answer/{q1}/1", headers=alice).get_json()["status"] == 1
    assert client.post(f"/api/check-answer/{q2}/3", headers=alice).get_json()["status"] == 0
    assert client.post(f"/api/check-answer/{q1}/1", headers=alice).status_code == 409  # повторный ответ
    done = client.post("/api/done/1", headers=alice).get_json()
    assert done["correct_answer"] == 1 and done["total_score"] == 1 and done["position_on_top"] == 1
    # старый способ накрутки: /done/<user_id>/<correct_answers> больше не существует
    assert client.post("/api/done/1/1000", headers=alice).status_code == 404


def test_answers_need_token(client):
    q = add_question(client, "q")
    assert client.post(f"/api/check-answer/{q}/2").status_code == 401
    assert client.post("/api/done/1", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_register_does_not_leak_existing_user(client):
    register(client, "Alice", "+998900000001")
    again = client.post("/api/register", json={"name": "Mallory", "phone_number": "+998900000001"})
    assert again.status_code == 409 and "user_id" not in again.get_json()


def test_leaderboard(client):
    q = add_question(client, "q", correct=1)
    for name, phone, answer in [("Alice", "+998900000001", 1), ("Bob", "+998900000002", 2)]:
        headers = register(client, name, phone)
        client.post(f"/api/check-answer/{q}/{answer}", headers=headers)
        client.post("/api/done/1", headers=headers)
    assert client.get("/api/leaders/1").get_json()["leaders"] == [{"name": "Alice", "score": 1}, {"name": "Bob", "score": 0}]
