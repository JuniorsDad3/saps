from app import app, db
from app import User
from werkzeug.security import generate_password_hash

with app.app_context():
    # Check if admin user already exists
    admin_user = User.query.filter_by(username="admin").first()

    if not admin_user:

        new_admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin123", method="pbkdf2:sha256")
        )
        db.session.add(new_admin)
        db.session.commit()
        print("✅ Admin user created successfully!")
    else:
        print("⚠️ Admin user already exists. No action taken.")
