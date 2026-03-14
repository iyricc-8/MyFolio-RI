import os
import sqlite3
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'portfolio.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf'}

app = Flask(__name__)
app.secret_key = 'ilyas_portfolio_secret_2024_xiva'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─── DB helpers ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS hero (
        id INTEGER PRIMARY KEY,
        greeting_uz TEXT, greeting_ru TEXT, greeting_en TEXT,
        name TEXT,
        tagline_uz TEXT, tagline_ru TEXT, tagline_en TEXT,
        subtitle_uz TEXT, subtitle_ru TEXT, subtitle_en TEXT,
        photo TEXT,
        cv_file TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS about (
        id INTEGER PRIMARY KEY,
        text_uz TEXT, text_ru TEXT, text_en TEXT,
        photo TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS skill (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        level INTEGER DEFAULT 80,
        category TEXT DEFAULT 'frontend',
        sort_order INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS project (
        id INTEGER PRIMARY KEY,
        title_uz TEXT, title_ru TEXT, title_en TEXT,
        desc_uz TEXT, desc_ru TEXT, desc_en TEXT,
        image TEXT,
        tags TEXT,
        github_url TEXT,
        live_url TEXT,
        featured INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS contact_info (
        id INTEGER PRIMARY KEY,
        email TEXT, phone TEXT, address TEXT,
        github TEXT, linkedin TEXT, telegram TEXT,
        updated_at TEXT
    );

    CREATE TABLE IF NOT EXISTS message (
        id INTEGER PRIMARY KEY,
        name TEXT, email TEXT,
        subject TEXT, body TEXT,
        read INTEGER DEFAULT 0,
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS site_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    # Default admin
    existing = c.execute("SELECT id FROM admin WHERE username=?", ('iyricc-8',)).fetchone()
    if not existing:
        c.execute("INSERT INTO admin (username, password_hash) VALUES (?,?)",
                  ('iyricc-8', generate_password_hash('P0O9I8U7Y6T5')))

    # Default hero
    if not c.execute("SELECT id FROM hero LIMIT 1").fetchone():
        c.execute("""INSERT INTO hero (greeting_uz,greeting_ru,greeting_en,name,
            tagline_uz,tagline_ru,tagline_en,subtitle_uz,subtitle_ru,subtitle_en,
            photo,cv_file,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            "Salom, men", "Привет, я", "Hello, I'm",
            "Ilyas Rustambaev",
            "Web Fullstack Developer",
            "Web Fullstack разработчик",
            "Web Fullstack Developer",
            "Menda backend va frontend bo'yicha amaliy tajriba mavjud",
            "Junior разработчик с опытом в backend и frontend",
            "Motivated Junior Developer with hands-on experience in fullstack development",
            "profile.png", None, datetime.now().isoformat()
        ))

    if not c.execute("SELECT id FROM about LIMIT 1").fetchone():
        c.execute("""INSERT INTO about (text_uz,text_ru,text_en,photo,updated_at) VALUES (?,?,?,?,?)""", (
            "Men IT sohasida Mentor va O'qituvchi sifatida amaliy tajribaga ega bo'lgan rag'batlantiruvchi Junior Developerman. Backend va frontend ishlanmalar bo'yicha mustahkam asos mavjud bo'lib, Fullstack Dasturchi bo'lish yo'lida bilimlarni kengaytirib bormoqdaman.",
            "Я мотивированный Junior Developer с практическим опытом работы в сфере IT в качестве Наставника и Инструктора. Имею прочную базу в backend и frontend разработке и непрерывно расширяю знания, стремясь стать Fullstack разработчиком.",
            "Motivated Junior Developer with hands-on experience in the IT education field as a Mentor and Instructor. Possess a strong foundation in backend and frontend development and continuously expanding knowledge toward becoming a Fullstack Developer.",
            "profile.png", datetime.now().isoformat()
        ))

    default_skills = [
        ('HTML5', 90, 'frontend', 1), ('CSS3', 85, 'frontend', 2),
        ('JavaScript', 80, 'frontend', 3), ('TypeScript', 70, 'frontend', 4),
        ('React', 75, 'frontend', 5), ('Bootstrap', 80, 'frontend', 6),
        ('Tailwind CSS', 78, 'frontend', 7),
        ('Python', 82, 'backend', 1), ('Django', 75, 'backend', 2),
        ('MySQL', 70, 'backend', 3), ('SQLite', 75, 'backend', 4),
        ('Git', 78, 'tools', 1), ('Power BI', 65, 'tools', 2),
        ('MS Office', 85, 'tools', 3),
    ]
    if not c.execute("SELECT id FROM skill LIMIT 1").fetchone():
        for s in default_skills:
            c.execute("INSERT INTO skill (name,level,category,sort_order) VALUES (?,?,?,?)", s)

    if not c.execute("SELECT id FROM contact_info LIMIT 1").fetchone():
        c.execute("""INSERT INTO contact_info (email,phone,address,github,linkedin,telegram,updated_at)
            VALUES (?,?,?,?,?,?,?)""",
            ('rustambaev09@gmail.com', '+998914235141', 'Gilamchi 1/9, Xiva',
             'https://github.com/', 'https://linkedin.com/', 'https://t.me/',
             datetime.now().isoformat()))

    conn.commit()
    conn.close()


# ─── Auth ──────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file, subfolder=''):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        dest = os.path.join(UPLOAD_FOLDER, subfolder)
        os.makedirs(dest, exist_ok=True)
        file.save(os.path.join(dest, filename))
        return os.path.join(subfolder, filename).replace('\\', '/') if subfolder else filename
    return None


# ─── Language ──────────────────────────────────────────────────────────────────

@app.before_request
def set_lang():
    if 'lang' not in session:
        session['lang'] = 'uz'


@app.route('/set_lang/<lang>')
def set_language(lang):
    if lang in ('uz', 'ru', 'en'):
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))


def lang():
    return session.get('lang', 'uz')


# ─── Public routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    hero = db.execute("SELECT * FROM hero LIMIT 1").fetchone()
    about = db.execute("SELECT * FROM about LIMIT 1").fetchone()
    skills = db.execute("SELECT * FROM skill ORDER BY category, sort_order").fetchall()
    projects = db.execute("SELECT * FROM project ORDER BY featured DESC, sort_order, id DESC").fetchall()
    contact = db.execute("SELECT * FROM contact_info LIMIT 1").fetchone()
    db.close()

    skill_categories = {}
    for s in skills:
        cat = s['category']
        skill_categories.setdefault(cat, []).append(dict(s))

    processed_projects = []
    for p in projects:
        pd = dict(p)
        pd['tags_list'] = json.loads(pd['tags']) if pd['tags'] else []
        processed_projects.append(pd)

    return render_template('portfolio/index.html',
        hero=dict(hero) if hero else {},
        about=dict(about) if about else {},
        skill_categories=skill_categories,
        projects=processed_projects,
        contact=dict(contact) if contact else {},
        current_lang=lang()
    )


@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    if name and email and body:
        db = get_db()
        db.execute(
            "INSERT INTO message (name,email,subject,body,created_at) VALUES (?,?,?,?,?)",
            (name, email, subject, body, datetime.now().isoformat())
        )
        db.commit()
        db.close()
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Missing fields'}), 400


@app.route('/download_cv')
def download_cv():
    db = get_db()
    hero = db.execute("SELECT cv_file FROM hero LIMIT 1").fetchone()
    db.close()
    if hero and hero['cv_file']:
        cv_path = hero['cv_file']
        # Check uploads folder
        full_path = os.path.join(UPLOAD_FOLDER, cv_path)
        if os.path.exists(full_path):
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            return send_from_directory(directory, filename, as_attachment=True,
                                       download_name='Ilyas_Rustambaev_CV.pdf')
    abort(404)


# ─── Admin routes ──────────────────────────────────────────────────────────────

@app.route('/admin')
@app.route('/admin/')
def admin_index():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        admin = db.execute("SELECT * FROM admin WHERE username=?", (username,)).fetchone()
        db.close()
        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
        error = 'Noto\'g\'ri login yoki parol / Неверный логин или пароль'
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    db = get_db()
    stats = {
        'projects': db.execute("SELECT COUNT(*) as c FROM project").fetchone()['c'],
        'skills': db.execute("SELECT COUNT(*) as c FROM skill").fetchone()['c'],
        'messages': db.execute("SELECT COUNT(*) as c FROM message").fetchone()['c'],
        'unread': db.execute("SELECT COUNT(*) as c FROM message WHERE read=0").fetchone()['c'],
    }
    messages = db.execute("SELECT * FROM message ORDER BY created_at DESC LIMIT 5").fetchall()
    db.close()
    return render_template('admin/dashboard.html', stats=stats,
                           messages=[dict(m) for m in messages])


# ─── Admin: Hero ───────────────────────────────────────────────────────────────

@app.route('/admin/hero', methods=['GET', 'POST'])
@login_required
def admin_hero():
    db = get_db()
    if request.method == 'POST':
        photo_name = None
        cv_name = None
        if 'photo' in request.files and request.files['photo'].filename:
            photo_name = save_file(request.files['photo'], 'hero')
        if 'cv_file' in request.files and request.files['cv_file'].filename:
            cv_name = save_file(request.files['cv_file'], 'cv')

        existing = db.execute("SELECT * FROM hero LIMIT 1").fetchone()
        if existing:
            photo_name = photo_name or existing['photo']
            cv_name = cv_name or existing['cv_file']
            db.execute("""UPDATE hero SET greeting_uz=?,greeting_ru=?,greeting_en=?,
                name=?,tagline_uz=?,tagline_ru=?,tagline_en=?,
                subtitle_uz=?,subtitle_ru=?,subtitle_en=?,
                photo=?,cv_file=?,updated_at=? WHERE id=?""", (
                request.form.get('greeting_uz'), request.form.get('greeting_ru'),
                request.form.get('greeting_en'), request.form.get('name'),
                request.form.get('tagline_uz'), request.form.get('tagline_ru'),
                request.form.get('tagline_en'), request.form.get('subtitle_uz'),
                request.form.get('subtitle_ru'), request.form.get('subtitle_en'),
                photo_name, cv_name, datetime.now().isoformat(), existing['id']
            ))
        else:
            db.execute("""INSERT INTO hero (greeting_uz,greeting_ru,greeting_en,name,
                tagline_uz,tagline_ru,tagline_en,subtitle_uz,subtitle_ru,subtitle_en,
                photo,cv_file,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                request.form.get('greeting_uz'), request.form.get('greeting_ru'),
                request.form.get('greeting_en'), request.form.get('name'),
                request.form.get('tagline_uz'), request.form.get('tagline_ru'),
                request.form.get('tagline_en'), request.form.get('subtitle_uz'),
                request.form.get('subtitle_ru'), request.form.get('subtitle_en'),
                photo_name, cv_name, datetime.now().isoformat()
            ))
        db.commit()
        flash('Hero bo\'limi saqlandi!', 'success')
        db.close()
        return redirect(url_for('admin_hero'))

    hero = db.execute("SELECT * FROM hero LIMIT 1").fetchone()
    db.close()
    return render_template('admin/hero.html', hero=dict(hero) if hero else {})


# ─── Admin: About ──────────────────────────────────────────────────────────────

@app.route('/admin/about', methods=['GET', 'POST'])
@login_required
def admin_about():
    db = get_db()
    if request.method == 'POST':
        photo_name = None
        if 'photo' in request.files and request.files['photo'].filename:
            photo_name = save_file(request.files['photo'], 'about')
        existing = db.execute("SELECT * FROM about LIMIT 1").fetchone()
        if existing:
            photo_name = photo_name or existing['photo']
            db.execute("""UPDATE about SET text_uz=?,text_ru=?,text_en=?,photo=?,updated_at=? WHERE id=?""",
                (request.form.get('text_uz'), request.form.get('text_ru'),
                 request.form.get('text_en'), photo_name,
                 datetime.now().isoformat(), existing['id']))
        else:
            db.execute("""INSERT INTO about (text_uz,text_ru,text_en,photo,updated_at) VALUES (?,?,?,?,?)""",
                (request.form.get('text_uz'), request.form.get('text_ru'),
                 request.form.get('text_en'), photo_name, datetime.now().isoformat()))
        db.commit()
        flash('Haqimda bo\'limi saqlandi!', 'success')
        db.close()
        return redirect(url_for('admin_about'))

    about = db.execute("SELECT * FROM about LIMIT 1").fetchone()
    db.close()
    return render_template('admin/about.html', about=dict(about) if about else {})


# ─── Admin: Skills ─────────────────────────────────────────────────────────────

@app.route('/admin/skills')
@login_required
def admin_skills():
    db = get_db()
    skills = db.execute("SELECT * FROM skill ORDER BY category, sort_order").fetchall()
    db.close()
    return render_template('admin/skills.html', skills=[dict(s) for s in skills])


@app.route('/admin/skills/add', methods=['POST'])
@login_required
def admin_skill_add():
    db = get_db()
    db.execute("INSERT INTO skill (name,level,category,sort_order) VALUES (?,?,?,?)",
        (request.form.get('name'), int(request.form.get('level', 80)),
         request.form.get('category', 'frontend'), int(request.form.get('sort_order', 0))))
    db.commit()
    db.close()
    flash('Ko\'nikma qo\'shildi!', 'success')
    return redirect(url_for('admin_skills'))


@app.route('/admin/skills/edit/<int:sid>', methods=['POST'])
@login_required
def admin_skill_edit(sid):
    db = get_db()
    db.execute("UPDATE skill SET name=?,level=?,category=?,sort_order=? WHERE id=?",
        (request.form.get('name'), int(request.form.get('level', 80)),
         request.form.get('category', 'frontend'), int(request.form.get('sort_order', 0)), sid))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/admin/skills/delete/<int:sid>', methods=['POST'])
@login_required
def admin_skill_delete(sid):
    db = get_db()
    db.execute("DELETE FROM skill WHERE id=?", (sid,))
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ─── Admin: Projects ───────────────────────────────────────────────────────────

@app.route('/admin/projects')
@login_required
def admin_projects():
    db = get_db()
    projects = db.execute("SELECT * FROM project ORDER BY sort_order, id DESC").fetchall()
    db.close()
    plist = []
    for p in projects:
        pd = dict(p)
        pd['tags_list'] = json.loads(pd['tags']) if pd['tags'] else []
        plist.append(pd)
    return render_template('admin/projects.html', projects=plist)


@app.route('/admin/projects/add', methods=['GET', 'POST'])
@login_required
def admin_project_add():
    if request.method == 'POST':
        db = get_db()
        image_name = None
        if 'image' in request.files and request.files['image'].filename:
            image_name = save_file(request.files['image'], 'projects')
        tags_raw = request.form.get('tags', '')
        tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
        db.execute("""INSERT INTO project (title_uz,title_ru,title_en,desc_uz,desc_ru,desc_en,
            image,tags,github_url,live_url,featured,sort_order,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            request.form.get('title_uz'), request.form.get('title_ru'),
            request.form.get('title_en'), request.form.get('desc_uz'),
            request.form.get('desc_ru'), request.form.get('desc_en'),
            image_name, json.dumps(tags_list),
            request.form.get('github_url'), request.form.get('live_url'),
            1 if request.form.get('featured') else 0,
            int(request.form.get('sort_order', 0)), datetime.now().isoformat()
        ))
        db.commit()
        db.close()
        flash('Loyiha qo\'shildi!', 'success')
        return redirect(url_for('admin_projects'))
    return render_template('admin/project_form.html', project=None)


@app.route('/admin/projects/edit/<int:pid>', methods=['GET', 'POST'])
@login_required
def admin_project_edit(pid):
    db = get_db()
    project = db.execute("SELECT * FROM project WHERE id=?", (pid,)).fetchone()
    if not project:
        abort(404)
    if request.method == 'POST':
        image_name = project['image']
        if 'image' in request.files and request.files['image'].filename:
            image_name = save_file(request.files['image'], 'projects')
        tags_raw = request.form.get('tags', '')
        tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]
        db.execute("""UPDATE project SET title_uz=?,title_ru=?,title_en=?,
            desc_uz=?,desc_ru=?,desc_en=?,image=?,tags=?,github_url=?,live_url=?,
            featured=?,sort_order=? WHERE id=?""", (
            request.form.get('title_uz'), request.form.get('title_ru'),
            request.form.get('title_en'), request.form.get('desc_uz'),
            request.form.get('desc_ru'), request.form.get('desc_en'),
            image_name, json.dumps(tags_list),
            request.form.get('github_url'), request.form.get('live_url'),
            1 if request.form.get('featured') else 0,
            int(request.form.get('sort_order', 0)), pid
        ))
        db.commit()
        db.close()
        flash('Loyiha yangilandi!', 'success')
        return redirect(url_for('admin_projects'))
    pd = dict(project)
    pd['tags_str'] = ', '.join(json.loads(pd['tags'])) if pd['tags'] else ''
    db.close()
    return render_template('admin/project_form.html', project=pd)


@app.route('/admin/projects/delete/<int:pid>', methods=['POST'])
@login_required
def admin_project_delete(pid):
    db = get_db()
    db.execute("DELETE FROM project WHERE id=?", (pid,))
    db.commit()
    db.close()
    flash('Loyiha o\'chirildi!', 'success')
    return redirect(url_for('admin_projects'))


# ─── Admin: Contact ────────────────────────────────────────────────────────────

@app.route('/admin/contact', methods=['GET', 'POST'])
@login_required
def admin_contact():
    db = get_db()
    if request.method == 'POST':
        existing = db.execute("SELECT id FROM contact_info LIMIT 1").fetchone()
        data = (request.form.get('email'), request.form.get('phone'),
                request.form.get('address'), request.form.get('github'),
                request.form.get('linkedin'), request.form.get('telegram'),
                datetime.now().isoformat())
        if existing:
            db.execute("""UPDATE contact_info SET email=?,phone=?,address=?,
                github=?,linkedin=?,telegram=?,updated_at=? WHERE id=?""",
                data + (existing['id'],))
        else:
            db.execute("""INSERT INTO contact_info (email,phone,address,github,linkedin,telegram,updated_at)
                VALUES (?,?,?,?,?,?,?)""", data)
        db.commit()
        flash('Aloqa ma\'lumotlari saqlandi!', 'success')
        db.close()
        return redirect(url_for('admin_contact'))
    contact = db.execute("SELECT * FROM contact_info LIMIT 1").fetchone()
    db.close()
    return render_template('admin/contact.html', contact=dict(contact) if contact else {})


# ─── Admin: Messages ───────────────────────────────────────────────────────────

@app.route('/admin/messages')
@login_required
def admin_messages():
    db = get_db()
    messages = db.execute("SELECT * FROM message ORDER BY created_at DESC").fetchall()
    db.close()
    return render_template('admin/messages.html', messages=[dict(m) for m in messages])


@app.route('/admin/messages/read/<int:mid>', methods=['POST'])
@login_required
def admin_message_read(mid):
    db = get_db()
    db.execute("UPDATE message SET read=1 WHERE id=?", (mid,))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/admin/messages/delete/<int:mid>', methods=['POST'])
@login_required
def admin_message_delete(mid):
    db = get_db()
    db.execute("DELETE FROM message WHERE id=?", (mid,))
    db.commit()
    db.close()
    return jsonify({'ok': True})


# ─── Admin: Change password ────────────────────────────────────────────────────

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    db = get_db()
    if request.method == 'POST':
        new_pass = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        if new_pass and new_pass == confirm:
            db.execute("UPDATE admin SET password_hash=? WHERE username=?",
                (generate_password_hash(new_pass), session['admin_username']))
            db.commit()
            flash('Parol muvaffaqiyatli o\'zgartirildi!', 'success')
        else:
            flash('Parollar mos kelmadi!', 'error')
        db.close()
        return redirect(url_for('admin_settings'))
    db.close()
    return render_template('admin/settings.html')


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
