from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ------------------------
# Configuration
# ------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'app.db')
CSS_DIR = os.path.join(BASE_DIR, 'CSS')
IMG_DIR = os.path.join(BASE_DIR, 'img')

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')



# ------------------------
# Database Helpers
# ------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist"""
    conn = get_db()
    cur = conn.cursor()

    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0
        )
    ''')

    # Candidates table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            image_path TEXT
        )
    ''')

    # Votes table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            candidate_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(candidate_id) REFERENCES candidates(id)
        )
    ''')

    conn.commit()
    conn.close()


def add_sample_data():
    """Insert sample candidates and a default admin user"""
    conn = get_db()
    cur = conn.cursor()

    # --- Sample Candidates ---
    cur.execute('SELECT COUNT(*) as c FROM candidates')
    if cur.fetchone()['c'] == 0:
        candidates = [
            ('HIM HEY', '/img/t.him.png'),
            ('RADY Y', '/img/t.rady.png'),
            ('YON YEN', '/img/t.yon.png'),
            ('MENGHEANG', '/img/t.mengheang.jpg'),
        ]
        cur.executemany('INSERT INTO candidates (name, image_path) VALUES (?, ?)', candidates)
        print("✅ Sample candidates added.")
    else:
        print("ℹ️ Candidates already exist — skipping.")

    # --- Default Admin User ---
    # Ensure the 'is_admin' column exists before inserting
    cur.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cur.fetchall()]
    if "is_admin" not in columns:
        print("⚙️ Adding 'is_admin' column to users table...")
        cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

    cur.execute("SELECT COUNT(*) as c FROM users WHERE email = ?", ('admin@email.com',))
    if cur.fetchone()['c'] == 0:
        admin_password = generate_password_hash('admin123')
        cur.execute(
            'INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)',
            ('admin@email.com', admin_password)
        )
        print("✅ Admin user created — email: admin@email.com, password: admin123")
    else:
        print("ℹ️ Admin already exists — skipping.")

    conn.commit()
    conn.close()



# ------------------------
# Routes for static files
# ------------------------
@app.route('/CSS/<path:filename>')
def css(filename):
    return send_from_directory(CSS_DIR, filename)


@app.route('/img/<path:filename>')
def images(filename):
    return send_from_directory(IMG_DIR, filename)


# ------------------------
# Core Routes
# ------------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        if not email or not password:
            flash('Email and password are required.', 'error')
            return redirect(url_for('register'))

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users(email, password_hash) VALUES(?, ?)',
                        (email, generate_password_hash(password)))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))

        user_id = cur.lastrowid
        conn.close()
        session['user_id'] = user_id
        session['user_email'] = email
        return redirect(url_for('voting'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['is_admin'] = bool(user['is_admin'])
            return redirect(url_for('voting'))

        flash('Invalid credentials.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# ------------------------
# Voting System
# ------------------------
@app.route('/voting')
def voting():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],))
    user = cur.fetchone()
    cur.execute('SELECT * FROM candidates')
    candidates = cur.fetchall()
    conn.close()

    return render_template('voting.html', candidates=candidates, user=user)


@app.route('/vote/<int:candidate_id>', methods=['POST'])
def vote(candidate_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db()
    cur = conn.cursor()

    # Check if already voted
    cur.execute('SELECT has_voted FROM users WHERE id = ?', (user_id,))
    user = cur.fetchone()
    if user and user['has_voted']:
        conn.close()
        flash('You have already voted.', 'error')
        return redirect(url_for('voting'))

    try:
        cur.execute('INSERT INTO votes(user_id, candidate_id, created_at) VALUES(?, ?, ?)',
                    (user_id, candidate_id, datetime.utcnow().isoformat()))
        cur.execute('UPDATE users SET has_voted = 1 WHERE id = ?', (user_id,))
        conn.commit()
        flash('Vote recorded successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('You have already voted.', 'error')
    finally:
        conn.close()

    return redirect(url_for('results'))


@app.route('/results')
def results():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        SELECT c.id, c.name, c.image_path, COUNT(v.id) AS votes
        FROM candidates c
        LEFT JOIN votes v ON v.candidate_id = c.id
        GROUP BY c.id, c.name, c.image_path
        ORDER BY votes DESC, c.name ASC
    ''')
    rows = cur.fetchall()
    conn.close()

    return render_template('result.html', results=rows)


# ------------------------
# Run App
# ------------------------
if __name__ == '__main__':
    os.makedirs(CSS_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)
    init_db()
    add_sample_data()
    app.run(host='0.0.0.0', port=5000, debug=True)
