# 🌿 Ilyas Rustambaev — Portfolio

Flask + SQLite asosidagi shaxsiy portfolio va admin panel.

## Ishga tushurish

```bash
# 1. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 2. Ishga tushurish
python run.py
```

Sayt: http://localhost:5000  
Admin: http://localhost:5000/admin

## Admin kirish

- **Login:** iyricc-8  
- **Parol:** P0O9I8U7Y6T5

## Loyiha tuzilishi

```
portfolio/
├── app.py              # Asosiy Flask ilovasi
├── run.py              # Ishga tushurish fayli
├── requirements.txt    # Kutubxonalar
├── instance/
│   └── portfolio.db    # SQLite ma'lumotlar bazasi
├── static/
│   ├── css/
│   │   ├── style.css   # Portfolio CSS
│   │   └── admin.css   # Admin CSS
│   ├── js/
│   │   └── main.js     # JavaScript
│   ├── images/         # Statik rasmlar
│   └── uploads/        # Yuklangan fayllar
└── templates/
    ├── portfolio/
    │   └── index.html  # Asosiy sahifa
    └── admin/
        ├── base.html   # Admin asosi
        ├── login.html  # Kirish sahifasi
        ├── dashboard.html
        ├── hero.html
        ├── about.html
        ├── skills.html
        ├── projects.html
        ├── project_form.html
        ├── contact.html
        ├── messages.html
        └── settings.html
```

## Tillar

- 🇺🇿 O'zbek (lotin)
- 🇷🇺 Русский
- 🇬🇧 English

## Asosiy ranglar

- `#2c6e49` — To'q yashil
- `#4c956c` — O'rta yashil  
- `#fefee3` — Krem
- `#ffc9b9` — Shaftoli
- `#d68c45` — Oltin
