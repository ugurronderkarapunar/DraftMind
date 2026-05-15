from abc import ABC, abstractmethod
from db_utils import get_connection
import streamlit as st
from logger_config import logger

class ChampionRepository(ABC):
    @abstractmethod
    def get_all(self):
        pass

class SQLiteChampionRepository(ChampionRepository):
    @st.cache_data(ttl=3600)
    def get_all(_self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM champions").fetchall()
        conn.close()
        logger.debug(f"{len(rows)} şampiyon veritabanından çekildi.")
        return [dict(r) for r in rows]

# Singleton kullanımı
repo = SQLiteChampionRepository()
