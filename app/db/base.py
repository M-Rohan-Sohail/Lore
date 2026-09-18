import secrets
from typing import Any
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

def generate_short_code() -> str:
    """Generates an 8-character hex short code."""
    return secrets.token_hex(4)
