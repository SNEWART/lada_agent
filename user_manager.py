import json
import bcrypt
from pathlib import Path
from datetime import datetime

USERS_FILE = Path("users.json")
NAMES_FILE = Path("user_names.json")

class UserManager:
    def __init__(self):
        self.users = self._load_users()

    def _load_users(self):
        if USERS_FILE.exists():
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_users(self):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.users, f, ensure_ascii=False, indent=4)

    def register_user(self, username: str, password: str):
        user_id = username.lower().strip().replace(" ", "_")
        if user_id in self.users:
            return None, "Пользователь уже существует"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        self.users[user_id] = {
            "username": username,
            "password_hash": hashed.decode("utf-8"),
            "created_at": datetime.now().isoformat()
        }
        self.save_users()
        # При регистрации сохраняем отображаемое имя (пока равно username)
        self.set_display_name(user_id, username)
        return user_id, "Регистрация успешна"

    def login_user(self, username: str, password: str):
        user_id = username.lower().strip().replace(" ", "_")
        user = self.users.get(user_id)
        if not user:
            return None, "Пользователь не найден"
        if bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        ):
            return user_id, "Вход выполнен"
        return None, "Неверный пароль"

    def reset_password(self, username: str, new_password: str):
        user_id = username.lower().strip().replace(" ", "_")
        if user_id not in self.users:
            return False, "Пользователь не найден"
        hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        self.users[user_id]["password_hash"] = hashed.decode("utf-8")
        self.save_users()
        return True, "Пароль успешно сброшен"

    # ===== РАБОТА С ОТОБРАЖАЕМЫМ ИМЕНЕМ =====
    def get_display_name(self, user_id: str) -> str:
        """Возвращает сохранённое имя пользователя или его логин."""
        if NAMES_FILE.exists():
            try:
                with open(NAMES_FILE, "r", encoding="utf-8") as f:
                    names = json.load(f)
                return names.get(user_id, user_id)
            except:
                return user_id
        return user_id

    def set_display_name(self, user_id: str, name: str):
        """Сохраняет отображаемое имя пользователя."""
        names = {}
        if NAMES_FILE.exists():
            try:
                with open(NAMES_FILE, "r", encoding="utf-8") as f:
                    names = json.load(f)
            except:
                pass
        names[user_id] = name
        with open(NAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(names, f, ensure_ascii=False, indent=2)