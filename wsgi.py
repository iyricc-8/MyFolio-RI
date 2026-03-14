from app import app, init_db

try:
    init_db()
except Exception as e:
    print(f"DB init: {e}")

application = app

if __name__ == '__main__':
    app.run()
