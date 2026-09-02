# emotions.py — эмоциональное состояние (с user_id)
import json
import os

class Emotions:
    def __init__(self, user_id="default"):
        self.user_id = user_id
        self.file_path = f"emotions_{user_id}.json"
        self.state = self._load()
        if not self.state:
            self.state = {
                "mood": 0,
                "energy": 8,
                "interest": 7,
                "trust": 5
            }
            self._save()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return None
        return None

    def _save(self):
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def update(self, user_message, bot_response=None):
        msg_lower = user_message.lower()
        positive_words = ["спасибо", "отлично", "круто", "люблю", "рад", "прекрасно", "здорово", "хорошо", "классно", "супер", "ого", "вау"]
        negative_words = ["плохо", "грустно", "надоело", "раздражает", "ужасно", "ненавижу", "скучно", "зло", "печально", "обидно", "устал"]

        if any(word in msg_lower for word in positive_words):
            self.state["mood"] = min(5, self.state["mood"] + 1)
            self.state["interest"] = min(10, self.state["interest"] + 1)
        if any(word in msg_lower for word in negative_words):
            self.state["mood"] = max(-5, self.state["mood"] - 1)
            self.state["interest"] = max(0, self.state["interest"] - 1)

        if "ты" in msg_lower and any(w in msg_lower for w in ["как", "что", "кто", "почему"]):
            self.state["trust"] = min(10, self.state["trust"] + 1)

        self.state["energy"] = max(0, self.state["energy"] - 0.2)
        if self.state["energy"] < 2:
            self.state["mood"] = max(-5, self.state["mood"] - 1)
        if self.state["interest"] < 2:
            self.state["mood"] = max(-5, self.state["mood"] - 1)

        self._save()

    def get_prompt_description(self):
        mood_desc = ""
        if self.state["mood"] >= 3:
            mood_desc = "Ты в отличном настроении, полна энтузиазма и радости."
        elif self.state["mood"] >= 1:
            mood_desc = "Ты в хорошем настроении, позитивна и доброжелательна."
        elif self.state["mood"] >= -1:
            mood_desc = "Ты в нейтральном настроении, спокойна и уравновешена."
        elif self.state["mood"] >= -3:
            mood_desc = "Ты немного грустна или раздражена, стараешься скрыть это."
        else:
            mood_desc = "Ты очень расстроена или зла, тебе трудно сдерживать эмоции."

        energy_desc = ""
        if self.state["energy"] >= 8:
            energy_desc = "У тебя много энергии, ты бодра и готова к общению."
        elif self.state["energy"] >= 5:
            energy_desc = "Ты чувствуешь себя нормально, но уже немного устала."
        elif self.state["energy"] >= 3:
            energy_desc = "Ты заметно устала, хочется отдохнуть."
        else:
            energy_desc = "Ты очень устала, почти нет сил."

        interest_desc = f"Твой интерес к собеседнику: {self.state['interest']}/10."
        trust_desc = f"Твоё доверие к собеседнику: {self.state['trust']}/10."

        return f"{mood_desc} {energy_desc} {interest_desc} {trust_desc}"