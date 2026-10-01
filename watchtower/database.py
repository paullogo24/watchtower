# Database — SQLite connection setup and initialization.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path

Base = declarative_base()

class Database:
    # Manages SQLite connection and table creation.

    def __init__(self, db_path: str = "data/watchtower.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False  # Set to True for SQL logging
        )
        self.Session = sessionmaker(bind=self.engine)

    def create_tables(self):
        # Create all tables if they don't exist.
        Base.metadata.create_all(self.engine)

    def get_session(self):
        # Get a new database session.
        return self.Session()

    def drop_tables(self):
        #Drop all tables (careful: this will delete all data).
        Base.metadata.drop_all(self.engine)
