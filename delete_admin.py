from app import app, db
from app import User  # Import your User model

# Set up the application context
with app.app_context():
    # Find the existing admin user
    admin_user = User.query.filter_by(email="admin@example.com").first()

    # If it exists, delete it
    if admin_user:
        db.session.delete(admin_user)
        db.session.commit()
        print("✅ Duplicate admin user deleted!")
    else:
        print("⚠️ No duplicate admin user found.")
