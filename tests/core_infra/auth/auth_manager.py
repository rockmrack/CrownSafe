from passlib.context import CryptContext
from sqlalchemy.orm import Session
from core_infra.database import User

# Use passlib for robust password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session, email: str, password: str, role_id: int = 2
) -> User:  # Default to a 'user' role
    hashed_password = get_password_hash(password)
    db_user = User(email=email, hashed_password=hashed_password, role_id=role_id)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
