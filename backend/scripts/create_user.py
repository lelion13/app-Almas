"""
Crea un usuario (ejecutar desde carpeta backend con PYTHONPATH=.):

  set PYTHONPATH=.
  python -m scripts.create_user admin@local.test secretpassword admin
"""
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    if len(sys.argv) < 4:
        print("Uso: python -m scripts.create_user <email> <password> <role>")
        sys.exit(1)
    email, password, role = sys.argv[1], sys.argv[2], sys.argv[3]
    db = SessionLocal()
    try:
        existing = db.scalars(select(User).where(User.email == email.lower().strip())).first()
        if existing:
            print("El usuario ya existe.")
            sys.exit(1)
        u = User(email=email.lower().strip(), password_hash=hash_password(password), role=role)
        db.add(u)
        db.commit()
        print("Usuario creado:", u.email, u.role)
    finally:
        db.close()


if __name__ == "__main__":
    main()
