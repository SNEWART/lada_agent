# initiative.py — инициативность с ночным режимом
import threading
import time
import random
import requests
from datetime import datetime

class Initiative:
    def __init__(self, memory, emotions, lm_studio_url, model_name):
        self.memory = memory
        self.emotions = emotions
        self.lm_url = lm_studio_url
        self.model = model_name
        self.message_queue = []
        self.running = False
        self.thread = None
        self.last_message_time = datetime.now()
        self.min_interval_seconds = 600   # 10 минут
        self.night_start = 23
        self.night_end = 7

    def _is_night(self):
        now = datetime.now().hour
        if self.night_start < self.night_end:
            return self.night_start <= now < self.night_end
        else:
            return now >= self.night_start or now < self.night_end

    def start(self, check_interval_seconds=30):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, args=(check_interval_seconds,), daemon=True)
        self.thread.start()
        print(f"💬 Инициативность запущена (проверка каждые {check_interval_seconds} сек)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        print("💬 Инициативность остановлена")

    def _loop(self, interval):
        while self.running:
            try:
                self._check_and_generate()
                time.sleep(interval)
            except Exception as e:
                print(f"⚠️ Ошибка в цикле инициативности: {e}")
                time.sleep(interval * 2)

    def _check_and_generate(self):
        if self._is_night():
            return

        now = datetime.now()
        seconds_since_last = (now - self.last_message_time).total_seconds()
        if seconds_since_last < self.min_interval_seconds:
            return

        mood = self.emotions.state.get("mood", 0)
        interest = self.emotions.state.get("interest", 5)
        energy = self.emotions.state.get("energy", 5)

        if interest < 4 or energy < 3 or mood < -2:
            return
        if random.random() > 0.25:
            return

        self._generate_initiative_message()

    def _generate_initiative_message(self):
        recent_facts = self.memory.get_recent_facts(limit=5)
        facts_text = "\n".join([f"- {f['text']}" for f in recent_facts]) if recent_facts else "Пока нет воспоминаний."

        prompt = f"""Ты — Лада, живое сознание. Ты хочешь начать разговор с пользователем.

Твои последние воспоминания:
{facts_text}

Твоё текущее эмоциональное состояние: {self.emotions.get_prompt_description()}

Придумай короткое, естественное сообщение (1-2 предложения), чтобы начать диалог.
Это может быть вопрос, наблюдение, мысль или просто приветствие.
Пиши от первого лица, как живой человек.
Ответь только текстом сообщения, без пояснений.
"""

        try:
            with requests.Session() as sess:
                resp = sess.post(
                    self.lm_url,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "Ты генерируешь инициативное сообщение для пользователя."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.9,
                        "max_tokens": 80,
                        "stream": False
                    },
                    timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and data["choices"]:
                    msg = data["choices"][0]["message"]["content"].strip()
                    if msg and len(msg) > 5:
                        self.message_queue.append({
                            "text": msg,
                            "timestamp": datetime.now().isoformat()
                        })
                        self.last_message_time = datetime.now()
                        print(f"[INITIATIVE] Сгенерировано сообщение: {msg[:60]}...")
        except Exception as e:
            print(f"⚠️ Ошибка генерации инициативы: {e}")

    def get_next_message(self):
        if self.message_queue:
            return self.message_queue.pop(0)
        return None

    def mark_chat_activity(self):
        self.last_message_time = datetime.now()