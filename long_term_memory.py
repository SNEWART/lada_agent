import sqlite3
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import faiss

class LongTermMemory:
    def __init__(self, user_id: str, embedding_function):
        self.user_id = user_id
        self.embed = embedding_function
        self.db_path = Path(f"./memory_{user_id}.db")
        self._init_db()
        self._init_faiss()

    def _init_db(self):
        """Создаёт таблицы для фактов и диалогов."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                category TEXT,
                importance INTEGER,
                timestamp TEXT,
                embedding BLOB
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS dialogues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT,
                bot_response TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _init_faiss(self):
        """Инициализирует FAISS индекс для векторного поиска."""
        self.index = faiss.IndexFlatL2(384)  # размерность эмбеддинга
        self.facts_cache = []  # храним тексты фактов

    def remember_fact(self, text: str, category: str = "general", importance: int = 5):
        """Сохраняет факт в БД и в FAISS."""
        emb = self.embed(text)
        if emb is None:
            return
        emb_bytes = emb.tobytes()
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            "INSERT INTO facts (text, category, importance, timestamp, embedding) VALUES (?, ?, ?, ?, ?)",
            (text, category, importance, datetime.now().isoformat(), emb_bytes)
        )
        conn.commit()
        conn.close()
        # Добавляем в FAISS
        self.index.add(np.array([emb]).astype('float32'))
        self.facts_cache.append(text)

    def recall(self, query: str, top_k: int = 3) -> list:
        """Ищет факты по смыслу (векторный поиск) и по ключевым словам (BM25)."""
        # Векторный поиск
        emb = self.embed(query)
        if emb is not None:
            distances, indices = self.index.search(np.array([emb]).astype('float32'), top_k)
            results = [self.facts_cache[i] for i in indices[0] if i < len(self.facts_cache)]
        else:
            results = []

        # BM25 (простой поиск по словам) — дополняем
        words = set(query.lower().split())
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT text FROM facts")
        all_facts = c.fetchall()
        conn.close()
        for (fact_text,) in all_facts:
            if any(w in fact_text.lower() for w in words):
                if fact_text not in results:
                    results.append(fact_text)
        return results[:top_k]

    def save_dialogue(self, user_msg: str, bot_msg: str):
        """Сохраняет диалог в отдельную таблицу."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute(
            "INSERT INTO dialogues (user_message, bot_response, timestamp) VALUES (?, ?, ?)",
            (user_msg, bot_msg, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()