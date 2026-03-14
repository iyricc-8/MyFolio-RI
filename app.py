import os
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, abort, send_file, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get('DATABASE_URL', '')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
SUPABASE_BUCKET = os.environ.get('SUPABASE_BUCKET', 'portfolio')
SECRET_KEY = os.environ.get('SECRET_KEY', 'ilyas_portfolio_secret_2024_xiva')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'pdf', 'doc', 'docx'}

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# ── Supabase storage helper ──────────────────────────────────────────────────

def supabase_upload(file_bytes, filename, content_type):
    """Upload file to Supabase Storage, return public URL or None."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        import urllib.request
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        upload_url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{unique_name}"
        req = urllib.request.Request(upload_url, data=file_bytes, method='POST')
        req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
        req.add_header('Content-Type', content_type)
        req.add_header('x-upsert', 'true')
        req.add_header('apikey', SUPABASE_KEY)
        with urllib.request.urlopen(req) as resp:
            resp.read()
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{unique_name}"
        return public_url
    except Exception as e:
        print(f"Supabase upload error: {e}")
        return None


def save_uploaded_file(file, subfolder=''):
    """Save file to Supabase Storage or local fallback. Returns URL string."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return None

    file_bytes = file.read()
    file.seek(0)

    content_types = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
        'gif': 'image/gif', 'webp': 'image/webp', 'svg': 'image/svg+xml',
        'pdf': 'application/pdf', 'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    ct = content_types.get(ext, 'application/octet-stream')

    safe_name = f"{uuid.uuid4().hex}.{ext}"

    if SUPABASE_URL and SUPABASE_KEY:
        url = supabase_upload(file_bytes, safe_name, ct)
        if url:
            return url

    # Local fallback (for dev)
    upload_dir = os.path.join(BASE_DIR, 'static', 'uploads', subfolder)
    os.makedirs(upload_dir, exist_ok=True)
    local_path = os.path.join(upload_dir, safe_name)
    with open(local_path, 'wb') as f:
        f.write(file_bytes)
    rel = os.path.join(subfolder, safe_name).replace('\\', '/') if subfolder else safe_name
    return f"/static/uploads/{rel}"


def is_external_url(path: str) -> bool:
    return path and (path.startswith('http://') or path.startswith('https://'))


# ── DB helpers ───────────────────────────────────────────────────────────────

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS hero (
        id SERIAL PRIMARY KEY,
        greeting_uz TEXT, greeting_ru TEXT, greeting_en TEXT,
        name TEXT,
        tagline_uz TEXT, tagline_ru TEXT, tagline_en TEXT,
        subtitle_uz TEXT, subtitle_ru TEXT, subtitle_en TEXT,
        photo TEXT, cv_file TEXT, updated_at TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS about (
        id SERIAL PRIMARY KEY,
        text_uz TEXT, text_ru TEXT, text_en TEXT,
        photo TEXT, updated_at TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS skill (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        level INTEGER DEFAULT 80,
        category TEXT DEFAULT 'frontend',
        sort_order INTEGER DEFAULT 0
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS project (
        id SERIAL PRIMARY KEY,
        title_uz TEXT, title_ru TEXT, title_en TEXT,
        desc_uz TEXT, desc_ru TEXT, desc_en TEXT,
        image TEXT, tags TEXT,
        github_url TEXT, live_url TEXT,
        featured INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS contact_info (
        id SERIAL PRIMARY KEY,
        email TEXT, phone TEXT, address TEXT,
        github TEXT, linkedin TEXT, telegram TEXT,
        updated_at TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS message (
        id SERIAL PRIMARY KEY,
        name TEXT, email TEXT, subject TEXT, body TEXT,
        read INTEGER DEFAULT 0, created_at TEXT
    )""")

    # Default admin
    c.execute("SELECT id FROM admin WHERE username=%s", ('iyricc-8',))
    if not c.fetchone():
        c.execute("INSERT INTO admin (username, password_hash) VALUES (%s,%s)",
                  ('iyricc-8', generate_password_hash('P0O9I8U7Y6T5')))

    # Default hero
    c.execute("SELECT id FROM hero LIMIT 1")
    if not c.fetchone():
        c.execute("""INSERT INTO hero (greeting_uz,greeting_ru,greeting_en,name,
            tagline_uz,tagline_ru,tagline_en,subtitle_uz,subtitle_ru,subtitle_en,
            photo,cv_file,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
            "Salom, men","Привет, я","Hello, I'm",
            "Ilyas Rustambaev",
            "Web Fullstack Developer","Web Fullstack разработчик","Web Fullstack Developer",
            "Menda backend va frontend bo'yicha amaliy tajriba mavjud",
            "Junior разработчик с опытом в backend и frontend",
            "Motivated Junior Developer with hands-on experience in fullstack development",
            None, None, datetime.now().isoformat()
        ))

    c.execute("SELECT id FROM about LIMIT 1")
    if not c.fetchone():
        c.execute("""INSERT INTO about (text_uz,text_ru,text_en,photo,updated_at) VALUES (%s,%s,%s,%s,%s)""", (
            "Men IT sohasida Mentor va O'qituvchi sifatida amaliy tajribaga ega bo'lgan rag'batlantiruvchi Junior Developerman.",
            "Я мотивированный Junior Developer с практическим опытом работы в сфере IT в качестве Наставника и Инструктора.",
            "Motivated Junior Developer with hands-on experience in the IT education field as a Mentor and Instructor.",
            None, datetime.now().isoformat()
        ))

    c.execute("SELECT id FROM skill LIMIT 1")
    if not c.fetchone():
        skills = [
            ('HTML5',90,'frontend',1),('CSS3',85,'frontend',2),
            ('JavaScript',80,'frontend',3),('TypeScript',70,'frontend',4),
            ('React',75,'frontend',5),('Bootstrap',80,'frontend',6),
            ('Tailwind CSS',78,'frontend',7),
            ('Python',82,'backend',1),('Django',75,'backend',2),
            ('MySQL',70,'backend',3),('SQLite',75,'backend',4),
            ('Git',78,'tools',1),('Power BI',65,'tools',2),('MS Office',85,'tools',3),
        ]
        for s in skills:
            c.execute("INSERT INTO skill (name,level,category,sort_order) VALUES (%s,%s,%s,%s)", s)

    c.execute("SELECT id FROM contact_info LIMIT 1")
    if not c.fetchone():
        c.execute("""INSERT INTO contact_info (email,phone,address,github,linkedin,telegram,updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            ('rustambaev09@gmail.com','+998914235141','Gilamchi 1/9, Xiva',
             'https://github.com/','https://linkedin.com/','https://t.me/',
             datetime.now().isoformat()))

    conn.commit()
    conn.close()


# ── Auth ─────────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ── Language ─────────────────────────────────────────────────────────────────

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


# ── Template helper ───────────────────────────────────────────────────────────

@app.context_processor
def inject_helpers():
    def photo_url(path):
        if not path:
            return url_for('static', filename='images/profile.png')
        if is_external_url(path):
            return path
        if path.startswith('/static/'):
            return path
        if path in ('profile.png', 'about.jpg'):
            return url_for('static', filename=f'images/{path}')
        return url_for('static', filename=f'uploads/{path}')
    return dict(photo_url=photo_url, is_external_url=is_external_url)


# ── Public routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM hero LIMIT 1"); hero = c.fetchone() or {}
    c.execute("SELECT * FROM about LIMIT 1"); about = c.fetchone() or {}
    c.execute("SELECT * FROM skill ORDER BY category, sort_order"); skills = c.fetchall()
    c.execute("SELECT * FROM project ORDER BY featured DESC, sort_order, id DESC"); projects = c.fetchall()
    c.execute("SELECT * FROM contact_info LIMIT 1"); contact = c.fetchone() or {}
    db.close()

    skill_categories = {}
    for s in skills:
        sd = dict(s)
        skill_categories.setdefault(sd['category'], []).append(sd)

    processed_projects = []
    for p in projects:
        pd = dict(p)
        pd['tags_list'] = json.loads(pd['tags']) if pd.get('tags') else []
        processed_projects.append(pd)

    return render_template('portfolio/index.html',
        hero=dict(hero), about=dict(about),
        skill_categories=skill_categories,
        projects=processed_projects,
        contact=dict(contact),
        current_lang=lang()
    )


@app.route('/send_message', methods=['POST'])
def send_message():
    name = request.form.get('name','').strip()
    email = request.form.get('email','').strip()
    subject = request.form.get('subject','').strip()
    body = request.form.get('body','').strip()
    if name and email and body:
        db = get_db(); c = db.cursor()
        c.execute("INSERT INTO message (name,email,subject,body,created_at) VALUES (%s,%s,%s,%s,%s)",
                  (name, email, subject, body, datetime.now().isoformat()))
        db.commit(); db.close()
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 400


@app.route('/download_cv')
def download_cv():
    db = get_db(); c = db.cursor()
    c.execute("SELECT cv_file FROM hero LIMIT 1"); row = c.fetchone(); db.close()
    if row and row['cv_file']:
        cv = row['cv_file']
        if is_external_url(cv):
            return redirect(cv)
        local = os.path.join(BASE_DIR, 'static', 'uploads', cv)
        if os.path.exists(local):
            return send_file(local, as_attachment=True,
                             download_name='Ilyas_Rustambaev_CV.pdf')
    abort(404)


# ── Admin: auth ───────────────────────────────────────────────────────────────

@app.route('/admin')
@app.route('/admin/')
def admin_index():
    return redirect(url_for('admin_dashboard') if session.get('admin_logged_in') else url_for('admin_login'))


@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    error = None
    if request.method == 'POST':
        db = get_db(); c = db.cursor()
        c.execute("SELECT * FROM admin WHERE username=%s", (request.form.get('username',''),))
        admin = c.fetchone(); db.close()
        if admin and check_password_hash(admin['password_hash'], request.form.get('password','')):
            session['admin_logged_in'] = True
            session['admin_username'] = admin['username']
            return redirect(url_for('admin_dashboard'))
        error = "Noto'g'ri login yoki parol"
    return render_template('admin/login.html', error=error)


@app.route('/admin/logout')
def admin_logout():
    session.clear(); return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    db = get_db(); c = db.cursor()
    c.execute("SELECT COUNT(*) as c FROM project"); projects = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM skill"); skills_count = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM message"); msgs = c.fetchone()['c']
    c.execute("SELECT COUNT(*) as c FROM message WHERE read=0"); unread = c.fetchone()['c']
    c.execute("SELECT * FROM message ORDER BY created_at DESC LIMIT 5"); messages = c.fetchall()
    db.close()
    stats = {'projects': projects, 'skills': skills_count, 'messages': msgs, 'unread': unread}
    return render_template('admin/dashboard.html', stats=stats,
                           messages=[dict(m) for m in messages])


# ── Admin: Hero ───────────────────────────────────────────────────────────────

@app.route('/admin/hero', methods=['GET','POST'])
@login_required
def admin_hero():
    db = get_db(); c = db.cursor()
    if request.method == 'POST':
        photo_url_val = None; cv_url_val = None
        if 'photo' in request.files and request.files['photo'].filename:
            photo_url_val = save_uploaded_file(request.files['photo'], 'hero')
        if 'cv_file' in request.files and request.files['cv_file'].filename:
            cv_url_val = save_uploaded_file(request.files['cv_file'], 'cv')
        c.execute("SELECT * FROM hero LIMIT 1"); existing = c.fetchone()
        if existing:
            photo_url_val = photo_url_val or existing['photo']
            cv_url_val = cv_url_val or existing['cv_file']
            c.execute("""UPDATE hero SET greeting_uz=%s,greeting_ru=%s,greeting_en=%s,
                name=%s,tagline_uz=%s,tagline_ru=%s,tagline_en=%s,
                subtitle_uz=%s,subtitle_ru=%s,subtitle_en=%s,
                photo=%s,cv_file=%s,updated_at=%s WHERE id=%s""", (
                request.form.get('greeting_uz'), request.form.get('greeting_ru'),
                request.form.get('greeting_en'), request.form.get('name'),
                request.form.get('tagline_uz'), request.form.get('tagline_ru'),
                request.form.get('tagline_en'), request.form.get('subtitle_uz'),
                request.form.get('subtitle_ru'), request.form.get('subtitle_en'),
                photo_url_val, cv_url_val, datetime.now().isoformat(), existing['id']
            ))
        else:
            c.execute("""INSERT INTO hero (greeting_uz,greeting_ru,greeting_en,name,
                tagline_uz,tagline_ru,tagline_en,subtitle_uz,subtitle_ru,subtitle_en,
                photo,cv_file,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
                request.form.get('greeting_uz'), request.form.get('greeting_ru'),
                request.form.get('greeting_en'), request.form.get('name'),
                request.form.get('tagline_uz'), request.form.get('tagline_ru'),
                request.form.get('tagline_en'), request.form.get('subtitle_uz'),
                request.form.get('subtitle_ru'), request.form.get('subtitle_en'),
                photo_url_val, cv_url_val, datetime.now().isoformat()
            ))
        db.commit(); db.close()
        flash("Hero bo'limi saqlandi!", 'success')
        return redirect(url_for('admin_hero'))
    c.execute("SELECT * FROM hero LIMIT 1"); hero = c.fetchone() or {}
    db.close()
    return render_template('admin/hero.html', hero=dict(hero))


# ── Admin: About ──────────────────────────────────────────────────────────────

@app.route('/admin/about', methods=['GET','POST'])
@login_required
def admin_about():
    db = get_db(); c = db.cursor()
    if request.method == 'POST':
        photo_url_val = None
        if 'photo' in request.files and request.files['photo'].filename:
            photo_url_val = save_uploaded_file(request.files['photo'], 'about')
        c.execute("SELECT * FROM about LIMIT 1"); existing = c.fetchone()
        if existing:
            photo_url_val = photo_url_val or existing['photo']
            c.execute("UPDATE about SET text_uz=%s,text_ru=%s,text_en=%s,photo=%s,updated_at=%s WHERE id=%s",
                (request.form.get('text_uz'), request.form.get('text_ru'),
                 request.form.get('text_en'), photo_url_val,
                 datetime.now().isoformat(), existing['id']))
        else:
            c.execute("INSERT INTO about (text_uz,text_ru,text_en,photo,updated_at) VALUES (%s,%s,%s,%s,%s)",
                (request.form.get('text_uz'), request.form.get('text_ru'),
                 request.form.get('text_en'), photo_url_val, datetime.now().isoformat()))
        db.commit(); db.close()
        flash("Haqimda bo'limi saqlandi!", 'success')
        return redirect(url_for('admin_about'))
    c.execute("SELECT * FROM about LIMIT 1"); about = c.fetchone() or {}
    db.close()
    return render_template('admin/about.html', about=dict(about))


# ── Admin: Skills ─────────────────────────────────────────────────────────────

@app.route('/admin/skills')
@login_required
def admin_skills():
    db = get_db(); c = db.cursor()
    c.execute("SELECT * FROM skill ORDER BY category, sort_order")
    skills = [dict(s) for s in c.fetchall()]; db.close()
    return render_template('admin/skills.html', skills=skills)


@app.route('/admin/skills/add', methods=['POST'])
@login_required
def admin_skill_add():
    db = get_db(); c = db.cursor()
    c.execute("INSERT INTO skill (name,level,category,sort_order) VALUES (%s,%s,%s,%s)",
        (request.form.get('name'), int(request.form.get('level',80)),
         request.form.get('category','frontend'), int(request.form.get('sort_order',0))))
    db.commit(); db.close()
    flash("Ko'nikma qo'shildi!", 'success')
    return redirect(url_for('admin_skills'))


@app.route('/admin/skills/edit/<int:sid>', methods=['POST'])
@login_required
def admin_skill_edit(sid):
    db = get_db(); c = db.cursor()
    c.execute("UPDATE skill SET name=%s,level=%s,category=%s,sort_order=%s WHERE id=%s",
        (request.form.get('name'), int(request.form.get('level',80)),
         request.form.get('category','frontend'), int(request.form.get('sort_order',0)), sid))
    db.commit(); db.close()
    return jsonify({'ok': True})


@app.route('/admin/skills/delete/<int:sid>', methods=['POST'])
@login_required
def admin_skill_delete(sid):
    db = get_db(); c = db.cursor()
    c.execute("DELETE FROM skill WHERE id=%s", (sid,)); db.commit(); db.close()
    return jsonify({'ok': True})


# ── Admin: Projects ───────────────────────────────────────────────────────────

@app.route('/admin/projects')
@login_required
def admin_projects():
    db = get_db(); c = db.cursor()
    c.execute("SELECT * FROM project ORDER BY sort_order, id DESC")
    projects = []
    for p in c.fetchall():
        pd = dict(p); pd['tags_list'] = json.loads(pd['tags']) if pd.get('tags') else []
        projects.append(pd)
    db.close()
    return render_template('admin/projects.html', projects=projects)


@app.route('/admin/projects/add', methods=['GET','POST'])
@login_required
def admin_project_add():
    if request.method == 'POST':
        db = get_db(); c = db.cursor()
        img = None
        if 'image' in request.files and request.files['image'].filename:
            img = save_uploaded_file(request.files['image'], 'projects')
        tags = json.dumps([t.strip() for t in request.form.get('tags','').split(',') if t.strip()])
        c.execute("""INSERT INTO project (title_uz,title_ru,title_en,desc_uz,desc_ru,desc_en,
            image,tags,github_url,live_url,featured,sort_order,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (
            request.form.get('title_uz'), request.form.get('title_ru'),
            request.form.get('title_en'), request.form.get('desc_uz'),
            request.form.get('desc_ru'), request.form.get('desc_en'),
            img, tags, request.form.get('github_url'), request.form.get('live_url'),
            1 if request.form.get('featured') else 0,
            int(request.form.get('sort_order',0)), datetime.now().isoformat()
        ))
        db.commit(); db.close()
        flash("Loyiha qo'shildi!", 'success')
        return redirect(url_for('admin_projects'))
    return render_template('admin/project_form.html', project=None)


@app.route('/admin/projects/edit/<int:pid>', methods=['GET','POST'])
@login_required
def admin_project_edit(pid):
    db = get_db(); c = db.cursor()
    c.execute("SELECT * FROM project WHERE id=%s", (pid,)); project = c.fetchone()
    if not project: abort(404)
    if request.method == 'POST':
        img = project['image']
        if 'image' in request.files and request.files['image'].filename:
            img = save_uploaded_file(request.files['image'], 'projects')
        tags = json.dumps([t.strip() for t in request.form.get('tags','').split(',') if t.strip()])
        c.execute("""UPDATE project SET title_uz=%s,title_ru=%s,title_en=%s,
            desc_uz=%s,desc_ru=%s,desc_en=%s,image=%s,tags=%s,github_url=%s,live_url=%s,
            featured=%s,sort_order=%s WHERE id=%s""", (
            request.form.get('title_uz'), request.form.get('title_ru'),
            request.form.get('title_en'), request.form.get('desc_uz'),
            request.form.get('desc_ru'), request.form.get('desc_en'),
            img, tags, request.form.get('github_url'), request.form.get('live_url'),
            1 if request.form.get('featured') else 0,
            int(request.form.get('sort_order',0)), pid
        ))
        db.commit(); db.close()
        flash('Loyiha yangilandi!', 'success')
        return redirect(url_for('admin_projects'))
    pd = dict(project)
    pd['tags_str'] = ', '.join(json.loads(pd['tags'])) if pd.get('tags') else ''
    db.close()
    return render_template('admin/project_form.html', project=pd)


@app.route('/admin/projects/delete/<int:pid>', methods=['POST'])
@login_required
def admin_project_delete(pid):
    db = get_db(); c = db.cursor()
    c.execute("DELETE FROM project WHERE id=%s", (pid,)); db.commit(); db.close()
    flash("Loyiha o'chirildi!", 'success')
    return redirect(url_for('admin_projects'))


# ── Admin: Contact ────────────────────────────────────────────────────────────

@app.route('/admin/contact', methods=['GET','POST'])
@login_required
def admin_contact():
    db = get_db(); c = db.cursor()
    if request.method == 'POST':
        c.execute("SELECT id FROM contact_info LIMIT 1"); existing = c.fetchone()
        data = (request.form.get('email'), request.form.get('phone'),
                request.form.get('address'), request.form.get('github'),
                request.form.get('linkedin'), request.form.get('telegram'),
                datetime.now().isoformat())
        if existing:
            c.execute("""UPDATE contact_info SET email=%s,phone=%s,address=%s,
                github=%s,linkedin=%s,telegram=%s,updated_at=%s WHERE id=%s""",
                data + (existing['id'],))
        else:
            c.execute("""INSERT INTO contact_info (email,phone,address,github,linkedin,telegram,updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)""", data)
        db.commit(); db.close()
        flash("Aloqa ma'lumotlari saqlandi!", 'success')
        return redirect(url_for('admin_contact'))
    c.execute("SELECT * FROM contact_info LIMIT 1"); contact = c.fetchone() or {}
    db.close()
    return render_template('admin/contact.html', contact=dict(contact))


# ── Admin: Messages ───────────────────────────────────────────────────────────

@app.route('/admin/messages')
@login_required
def admin_messages():
    db = get_db(); c = db.cursor()
    c.execute("SELECT * FROM message ORDER BY created_at DESC")
    messages = [dict(m) for m in c.fetchall()]; db.close()
    return render_template('admin/messages.html', messages=messages)


@app.route('/admin/messages/read/<int:mid>', methods=['POST'])
@login_required
def admin_message_read(mid):
    db = get_db(); c = db.cursor()
    c.execute("UPDATE message SET read=1 WHERE id=%s", (mid,)); db.commit(); db.close()
    return jsonify({'ok': True})


@app.route('/admin/messages/delete/<int:mid>', methods=['POST'])
@login_required
def admin_message_delete(mid):
    db = get_db(); c = db.cursor()
    c.execute("DELETE FROM message WHERE id=%s", (mid,)); db.commit(); db.close()
    return jsonify({'ok': True})


# ── Admin: Settings ───────────────────────────────────────────────────────────

@app.route('/admin/settings', methods=['GET','POST'])
@login_required
def admin_settings():
    db = get_db(); c = db.cursor()
    if request.method == 'POST':
        new_pass = request.form.get('new_password')
        confirm  = request.form.get('confirm_password')
        if new_pass and new_pass == confirm:
            c.execute("UPDATE admin SET password_hash=%s WHERE username=%s",
                (generate_password_hash(new_pass), session['admin_username']))
            db.commit()
            flash("Parol muvaffaqiyatli o'zgartirildi!", 'success')
        else:
            flash("Parollar mos kelmadi!", 'error')
        db.close(); return redirect(url_for('admin_settings'))
    db.close()
    return render_template('admin/settings.html')


# ── Init on startup ───────────────────────────────────────────────────────────

# Init DB on cold start
if DATABASE_URL:
    try:
        init_db()
        print("DB initialized OK")
    except Exception as e:
        print(f"DB init warning: {e}")

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
