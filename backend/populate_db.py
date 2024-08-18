# create_tony_user.py
from app import app, db, User
from werkzeug.security import generate_password_hash
import sys

def create_tony_user(password):
    with app.app_context():
        # Create the database tables
        db.create_all()

        # Create or update the "tony" user
        tony_user = User.query.filter_by(username="tony").first()
        if not tony_user:
            tony_user = User(username="tony")
            db.session.add(tony_user)
            print("Created new user 'tony'.")
        else:
            print("User 'tony' already exists. Updating password.")

        # Set or update the password
        tony_user.password_hash = generate_password_hash(password)
        db.session.commit()

        print("User 'tony' has been created or updated successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_tony_user.py <password for user 'tony'>")
        sys.exit(1)
    
    password = sys.argv[1]
    create_tony_user(password)