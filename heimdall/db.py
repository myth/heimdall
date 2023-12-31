"""Heimdall database"""

from databases import Database
import sqlalchemy as sa

from heimdall import cfg

database = Database(cfg.DB_URI)
metadata = sa.MetaData()


def init_database():
    engine = sa.create_engine(cfg.DB_URI, connect_args={"check_same_thread": False})
    metadata.create_all(engine)
