import os
from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Auto-create tables if they don't exist yet
        db.create_all()

    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'True').lower() in ['true', '1', 'yes']
    print(f"🚀 PG Finder Bengaluru running at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
