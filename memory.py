# memory.py — долговременная память на SQLite
import sqlite3
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional

class Memory:
    def __init__(self, user_id="default", db_path="memory.db"):
        self.user_id = user_id
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Создаёт таблицу facts, если её нет"""
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    importance INTEGER DEFAULT 5,
                    timestamp TEXT NOT NULL,
                    metadata TEXT  -- JSON
                )
            ''')
            # Индексы для скорости
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_category ON facts(user_id, category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON facts(timestamp)')
            conn.commit()
            conn.close()

    def add_fact(self, text: str, category: str = "general", importance: int = 5, metadata: dict = None) -> dict:
        """Добавляет факт в память. Возвращает сохранённый факт."""
        timestamp = datetime.now().isoformat()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO facts (user_id, text, category, importance, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.user_id, text, category, importance, timestamp, metadata_json))
            fact_id = cursor.lastrowid
            conn.commit()
            conn.close()
        return {
            "id": fact_id,
            "user_id": self.user_id,
            "text": text,
            "category": category,
            "importance": importance,
            "timestamp": timestamp,
            "metadata": metadata
        }

    def get_relevant_facts(self, query: str, top_k: int = 3, category_filter: Optional[str] = None) -> List[str]:
        """
        Ищет факты, содержащие слова из запроса (регистронезависимо).
        Если указан category_filter, ищет только в этой категории.
        Возвращает список текстов фактов.
        """
        if not query.strip():
            return []
        words = query.lower().split()
        if not words:
            return []

        # Строим условие LIKE для каждого слова
        like_conditions = " AND ".join(["(LOWER(text) LIKE ?)" for _ in words])
        params = [f"%{w}%" for w in words]

        sql = f'''
            SELECT text FROM facts
            WHERE user_id = ? AND {like_conditions}
        '''
        sql_params = [self.user_id] + params

        if category_filter:
            sql += " AND category = ?"
            sql_params.append(category_filter)

        sql += " ORDER BY importance DESC, timestamp DESC LIMIT ?"
        sql_params.append(top_k)

        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(sql, sql_params)
            rows = cursor.fetchall()
            conn.close()
        return [row[0] for row in rows]

    def get_recent_facts(self, limit: int = 10, category: Optional[str] = None) -> List[Dict]:
        """Возвращает последние факты (по времени) с указанной категорией (или без фильтра)."""
        sql = "SELECT id, user_id, text, category, importance, timestamp, metadata FROM facts WHERE user_id = ?"
        params = [self.user_id]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()

        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "user_id": row[1],
                "text": row[2],
                "category": row[3],
                "importance": row[4],
                "timestamp": row[5],
                "metadata": json.loads(row[6]) if row[6] else {}
            })
        return result

    def get_all_facts(self, category: Optional[str] = None) -> List[str]:
        """Возвращает все тексты фактов (опционально с фильтром по категории)."""
        sql = "SELECT text FROM facts WHERE user_id = ?"
        params = [self.user_id]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY timestamp DESC"

        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
        return [row[0] for row in rows]

    def delete_old_facts(self, days: int = 30, category: Optional[str] = None):
        """Удаляет факты старше указанного количества дней (опционально по категории)."""
        cutoff = datetime.now().timestamp() - days * 86400
        cutoff_iso = datetime.fromtimestamp(cutoff).isoformat()
        sql = "DELETE FROM facts WHERE user_id = ? AND timestamp < ?"
        params = [self.user_id, cutoff_iso]
        if category:
            sql += " AND category = ?"
            params.append(category)
        with self.lock:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
        return deleted

    # Для обратной совместимости со старым кодом (например, reflection.py использует self.memory.facts)
    @property
    def facts(self):
        """Возвращает последние 50 фактов как список словарей (для совместимости)"""
        return self.get_recent_facts(limit=50)