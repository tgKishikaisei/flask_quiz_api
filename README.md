# Quiz API

API викторины на Flask: вопросы по уровням сложности, проверка ответов на сервере и таблица лидеров. Правильные ответы клиенту не уходят, а счёт считает сервер, поэтому очки не накрутить.

[![License](https://img.shields.io/github/license/tgKishikaisei/flask_quiz_api)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/tgKishikaisei/flask_quiz_api/ci.yml?branch=main&label=CI)](https://github.com/tgKishikaisei/flask_quiz_api/actions/workflows/ci.yml)

## API

| Метод | Путь | Доступ | Что делает |
|---|---|---|---|
| POST | `/api/register` | все | `{"name", "phone_number"}` → `user_id` и токен, токен показывается один раз |
| GET | `/api/get-questions/<level>` | все | до 20 случайных вопросов уровня без правильных ответов |
| POST | `/api/check-answer/<question_id>/<answer>` | `Authorization: Bearer <token>` | засчитывает ответ, повторный ответ не считается |
| POST | `/api/done/<level>` | токен | завершает прохождение и считает счёт по сохранённым ответам |
| GET | `/api/leaders/<level>` | все | топ-5 уровня |
| POST | `/api/questions` | `X-API-Key` | добавляет вопрос |

## Стек

Python 3.12, Flask 3, Flask-SQLAlchemy, SQLite по умолчанию.

## Запуск

```bash
git clone https://github.com/tgKishikaisei/flask_quiz_api.git
cd flask_quiz_api
python -m venv venv
venv\Scripts\activate               # Linux и macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # ADMIN_API_KEY нужен, чтобы добавлять вопросы
flask --app main run
```

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

## Живая версия

Публичного стенда нет, проект запускается локально.

## Лицензия

[MIT](LICENSE) © 2023-2026 Behruz Avezmatov
