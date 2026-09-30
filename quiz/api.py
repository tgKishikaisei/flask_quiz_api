"""API викторины.

Что было не так в старой версии:
- приложение не запускалось: опечатки в моделях (db.Columnd, db.Colmn, db.Foreignkey,
  primery_key), импорт `..database` выше корня пакета, блюпринт не был зарегистрирован,
  ключ конфигурации SQLALCHEMY_DATABASE_URL вместо ..._URI;
- итоговый счёт присылал клиент: POST /done/<user_id>/<correct_answers> — любой мог
  начислить себе (или кому угодно) сколько угодно очков;
- регистрация по уже существующему номеру отдавала id чужого пользователя;
- /leaders всегда возвращал None, /get-questions вызывал несуществующее get_questions.db.
"""
import hashlib
import hmac
import re
import secrets
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func, select

from quiz.models import Leader, Question, User, UserAnswer, db

api_bp = Blueprint("api", __name__, url_prefix="/api")
PHONE_RE = re.compile(r"^\+?\d{9,15}$")
QUESTIONS_PER_TEST = 20


def error(message, status):
    return jsonify({"status": 0, "message": message}), status


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_user(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
        user = db.session.scalar(select(User).where(User.token_hash == token_hash(token))) if token else None
        if user is None:
            return error("Нужен токен: Authorization: Bearer <token>", 401)
        g.user = user
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("ADMIN_API_KEY") or ""
        given = request.headers.get("X-API-Key", "")
        if not expected or not hmac.compare_digest(given, expected):
            return error("Нужен заголовок X-API-Key", 401)
        return view(*args, **kwargs)
    return wrapper


@api_bp.post("/register")
def registration_api():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = re.sub(r"[\s()-]", "", str(data.get("phone_number", "")))
    if not 1 <= len(name) <= 100 or not PHONE_RE.match(phone):
        return error("Нужны name (1–100 символов) и phone_number (9–15 цифр)", 422)
    if db.session.scalar(select(User.id).where(User.phone_number == phone)):
        return error("Этот номер уже зарегистрирован", 409)
    token = secrets.token_urlsafe(32)
    user = User(name=name, phone_number=phone, token_hash=token_hash(token))
    db.session.add(user)
    db.session.commit()
    # Токен показывается один раз: в базе только его хэш
    return jsonify({"status": 1, "user_id": user.id, "token": token}), 201


@api_bp.get("/get-questions/<int:level>")
def get_questions(level: int):
    questions = db.session.scalars(select(Question).where(Question.level == level)
                                   .order_by(func.random()).limit(QUESTIONS_PER_TEST)).all()
    return jsonify({"status": 1, "questions": [q.public() for q in questions]})


@api_bp.post("/check-answer/<int:question_id>/<int:user_answer>")
@require_user
def check_answer(question_id: int, user_answer: int):
    question = db.session.get(Question, question_id)
    if question is None:
        return error("Вопрос не найден", 404)
    if not 1 <= user_answer <= 4:
        return error("Ответ — номер варианта от 1 до 4", 422)
    # В одном прохождении на вопрос засчитывается только первый ответ
    already = db.session.scalar(select(UserAnswer.id).where(
        UserAnswer.user_id == g.user.id, UserAnswer.question_id == question_id, UserAnswer.counted.is_(False)))
    if already:
        return error("На этот вопрос уже был ответ", 409)
    correct = question.correct_answer == user_answer
    db.session.add(UserAnswer(user_id=g.user.id, question_id=question_id, level=question.level,
                              user_answer=user_answer, correctness=correct))
    db.session.commit()
    return jsonify({"status": 1 if correct else 0})


@api_bp.post("/done/<int:level>")
@require_user
def commit_user_answers(level: int):
    # Счёт считает сервер по записанным ответам, а не берёт из URL
    answers = db.session.scalars(select(UserAnswer).where(
        UserAnswer.user_id == g.user.id, UserAnswer.level == level, UserAnswer.counted.is_(False))).all()
    correct = sum(1 for a in answers if a.correctness)
    for answer in answers:
        answer.counted = True
    leader = db.session.scalar(select(Leader).where(Leader.user_id == g.user.id, Leader.level == level))
    if leader is None:
        leader = Leader(user_id=g.user.id, level=level, score=0)
        db.session.add(leader)
    leader.score += correct
    db.session.commit()
    position = db.session.scalar(select(func.count()).select_from(Leader).where(
        Leader.level == level, Leader.score > leader.score)) + 1
    return jsonify({"status": 1, "correct_answer": correct, "total_score": leader.score, "position_on_top": position})


@api_bp.get("/leaders/<int:level>")
def get_top_5(level: int):
    rows = db.session.execute(select(User.name, Leader.score).join(Leader.user).where(Leader.level == level)
                              .order_by(Leader.score.desc(), Leader.id).limit(5)).all()
    return jsonify({"level": level, "leaders": [{"name": name, "score": score} for name, score in rows]})


@api_bp.post("/questions")
@require_admin
def add_question():
    data = request.get_json(silent=True) or {}
    try:
        variants = [str(data.get(f"variant_{i}") or "").strip() for i in range(1, 5)]
        question = Question(main_text=str(data["main_text"]).strip()[:500], level=int(data["level"]),
                            correct_answer=int(data["correct_answer"]),
                            **{f"variant_{i + 1}": (v[:200] or None) for i, v in enumerate(variants)})
    except (KeyError, TypeError, ValueError):
        return error("Нужны main_text, level, correct_answer и variant_1..variant_4", 422)
    filled = [v for v in variants if v]
    if not question.main_text or len(filled) < 2 or not variants[0] or not variants[1] \
            or not 1 <= question.correct_answer <= 4 or not variants[question.correct_answer - 1]:
        return error("Минимум 2 варианта, correct_answer указывает на заполненный вариант", 422)
    db.session.add(question)
    db.session.commit()
    return jsonify({"status": 1, "question_id": question.id}), 201
