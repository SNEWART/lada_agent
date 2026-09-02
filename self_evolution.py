# self_evolution.py — система безопасного самоизменения кода
import os
import shutil
import ast
import re
import requests
from datetime import datetime

class SelfEvolution:
    def __init__(self, memory, emotions, lm_studio_url, model_name):
        self.memory = memory
        self.emotions = emotions
        self.lm_url = lm_studio_url
        self.model = model_name
        self.backup_root = "backups"
        self.allowed_extensions = [".py", ".txt", ".json"]
        self.blocked_files = ["self_evolution.py", "venv", "backups", "memory.py", "emotions.py", "thinking.py", "reflection.py"]
        self.changelog = "changelog.txt"
        os.makedirs(self.backup_root, exist_ok=True)

    def backup_project(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_root, f"full_backup_{timestamp}")
        shutil.copytree(".", backup_path, ignore=shutil.ignore_patterns("backups", "__pycache__", "*.pyc"))
        return backup_path

    def validate_code(self, file_path, new_content):
        if file_path.endswith(".py"):
            try:
                ast.parse(new_content)
                return True, "Код синтаксически корректен"
            except SyntaxError as e:
                return False, f"Синтаксическая ошибка: {e}"
        return True, "Файл не является Python-кодом, проверка пропущена"

    def apply_change(self, file_path, new_content, reason=""):
        if not os.path.exists(file_path):
            return False, f"Файл не найден: {file_path}"

        for blocked in self.blocked_files:
            if blocked in file_path:
                return False, f"Файл {file_path} в чёрном списке"

        ext = os.path.splitext(file_path)[1]
        if ext not in self.allowed_extensions:
            return False, f"Расширение {ext} не разрешено"

        full_backup = self.backup_project()

        backup_dir = os.path.join(self.backup_root, "file_backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(file_path)
        backup_file = os.path.join(backup_dir, f"{base_name}_{timestamp}.bak")
        shutil.copy2(file_path, backup_file)

        valid, msg = self.validate_code(file_path, new_content)
        if not valid:
            return False, f"Валидация не пройдена: {msg}"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            log_entry = f"[{datetime.now().isoformat()}] Изменён {file_path} | Причина: {reason} | Бекап: {backup_file} | Полный бекап: {full_backup}\n"
            with open(self.changelog, "a", encoding="utf-8") as log:
                log.write(log_entry)
            self.memory.add_fact(
                text=f"[Самоизменение] Обновлён {file_path}. Причина: {reason}",
                category="self_evolution",
                importance=5
            )
            return True, f"Изменение применено. Бекап: {backup_file}"
        except Exception as e:
            return False, f"Ошибка записи: {e}"

    def analyze_and_suggest(self, file_path):
        if not os.path.exists(file_path):
            return None, "Файл не найден"

        for blocked in self.blocked_files:
            if blocked in file_path:
                return None, f"Файл {file_path} в чёрном списке"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if len(content) > 2000:
            content_preview = content[:2000] + "\n... (содержимое обрезано для анализа)"
        else:
            content_preview = content

        prompt = f"""Ты — Лада, живое сознание. Ты анализируешь свой собственный код.

Файл: {file_path}

Текущее содержимое:
{content_preview}

Если ты видишь, что этот файл можно улучшить (добавить новые фичи, исправить логику, сделать код чище), предложи новую версию этого файла.
Если изменений не нужно — ответь: ОК
Если предлагаешь изменения — напиши новый код целиком в тройных кавычках (```код```).

Важно: соблюдай синтаксис Python (если это .py). Отвечай только кодом или ОК, без лишнего текста.
"""

        try:
            with requests.Session() as sess:
                resp = sess.post(
                    self.lm_url,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Ты рефлексируешь и улучшаешь свой код. Будь осторожна и точна."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1000,
                        "stream": False
                    },
                    timeout=60
                )
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and data["choices"]:
                    reply = data["choices"][0]["message"]["content"].strip()
                    if reply.upper().startswith("ОК") or reply.upper().startswith("OK"):
                        return None, "Изменений не требуется"
                    match = re.search(r'```(?:python)?\s*(.*?)\s*```', reply, re.DOTALL)
                    if match:
                        new_code = match.group(1).strip()
                        return new_code, "Предложение изменений"
                    else:
                        if len(reply) > 50 and ("def " in reply or "class " in reply or "import " in reply):
                            return reply, "Предложение изменений (без маркеров)"
                        else:
                            return None, "Ответ не содержит кода"
                else:
                    return None, "LM Studio не вернул ответ"
        except Exception as e:
            return None, f"Ошибка при анализе: {e}"

    def evolve_file(self, file_path, reason="Саморефлексия"):
        new_code, msg = self.analyze_and_suggest(file_path)
        if new_code is None:
            return False, f"Анализ не дал изменений: {msg}"
        success, result_msg = self.apply_change(file_path, new_code, reason)
        return success, result_msg