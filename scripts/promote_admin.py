import argparse

from app.db.base import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Promote an existing SafariDesk user to admin."
    )
    parser.add_argument("email", help="Existing user email to promote")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if not user:
            raise SystemExit(f"No user found for {args.email}")

        user.is_admin = True
        user.is_active = True
        user.is_verified = True
        db.commit()
        print(f"Promoted {user.email} to active verified admin.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
