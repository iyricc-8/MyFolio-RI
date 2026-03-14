# 🌿 Ilyas Rustambaev — Portfolio

Flask + PostgreSQL (Neon) + Supabase Storage

## 🚀 Локальный запуск

```bash
pip install -r requirements.txt
cp .env.example .env
# Заполните .env своими ключами
python run.py
```

## ☁️ Деплой на Vercel

### Шаг 1 — GitHub
1. Создайте репозиторий на github.com
2. Загрузите все файлы проекта (без `.env` и `instance/`)

### Шаг 2 — Vercel
1. Зайдите на **vercel.com** → New Project
2. Импортируйте ваш GitHub репозиторий
3. Framework Preset: **Other**
4. Нажмите **Deploy**

### Шаг 3 — Переменные окружения в Vercel
В настройках проекта (Settings → Environment Variables) добавьте:

| Ключ | Значение |
|------|---------|
| `DATABASE_URL` | `postgresql://neondb_owner:...@neon.tech/neondb?sslmode=require` |
| `SUPABASE_URL` | `https://xxxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | `eyJhbG...` (service_role key) |
| `SUPABASE_BUCKET` | `portfolio` |
| `SECRET_KEY` | любая длинная случайная строка |

### Шаг 4 — Supabase Storage
1. supabase.com → Storage → New Bucket
2. Название: `portfolio`
3. Включите **Public bucket**

## 🔐 Admin
- URL: `ваш-сайт.vercel.app/admin`
- Login: `iyricc-8`
- Password: `P0O9I8U7Y6T5`

## 📁 Структура
```
portfolio/
├── app.py              # Flask приложение
├── vercel.json         # Vercel конфиг
├── requirements.txt    # Зависимости
├── .env.example        # Пример переменных окружения
├── static/             # CSS, JS, изображения
└── templates/          # HTML шаблоны
```
