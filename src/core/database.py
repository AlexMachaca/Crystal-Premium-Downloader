import os
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session, select

class Song(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    artist: str
    genre: str = "Sin categoría"
    duration: Optional[int] = None  # En segundos
    file_path: str
    thumbnail_url: Optional[str] = None
    date_added: datetime = Field(default_factory=datetime.utcnow)
    platform: str = "Desconocida"

# Path absoluto: src/core/ → src/ → project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sqlite_file_name = os.path.join(_PROJECT_ROOT, "database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"
engine = create_engine(sqlite_url, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
