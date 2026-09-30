from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    # Токен выдаётся при регистрации, хранится только его хэш
    token_hash = db.Column(db.String(64), unique=True, nullable=False)


class Leader(db.Model):
    __tablename__ = "leaders"
    __table_args__ = (db.UniqueConstraint("user_id", "level"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)
    user = db.relationship(User)


class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(db.Integer, primary_key=True)
    main_text = db.Column(db.String(500), nullable=False)
    variant_1 = db.Column(db.String(200), nullable=False)
    variant_2 = db.Column(db.String(200), nullable=False)
    variant_3 = db.Column(db.String(200))
    variant_4 = db.Column(db.String(200))
    correct_answer = db.Column(db.Integer, nullable=False)  # 1..4
    level = db.Column(db.Integer, nullable=False, index=True)

    def public(self):
        """Вопрос без правильного ответа."""
        variants = [v for v in (self.variant_1, self.variant_2, self.variant_3, self.variant_4) if v]
        return {"id": self.id, "main_text": self.main_text, "variants": variants, "level": self.level}


class UserAnswer(db.Model):
    __tablename__ = "user_answer"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    level = db.Column(db.Integer, nullable=False)
    user_answer = db.Column(db.Integer, nullable=False)
    correctness = db.Column(db.Boolean, nullable=False, default=False)
    # Ответы текущего прохождения; после /done помечаются как учтённые
    counted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
