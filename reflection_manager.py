import json
import os
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Optional, Dict, Any, Tuple

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Константы ---
DATA_FILE = "reflection_data_600lines.json"
SENTIMENT_OPTIONS = ['positive', 'negative', 'neutral']
MAX_KEYWORD_COUNT = 10


class Event:
    """
    Класс для хранения отдельного события в дневнике рефлексии.
    Расширенная модель с полями для более глубокого анализа.
    """

    def __init__(self, timestamp: datetime, description: str, sentiment: str,
                 energy_level: int = 5, keywords: Optional[List[str]] = None):
        if sentiment not in SENTIMENT_OPTIONS:
            raise ValueError(f"Неверное значение sentiment: {sentiment}. Допустимые: {SENTIMENT_OPTIONS}")
        self.timestamp = timestamp
        self.description = description
        self.sentiment = sentiment
        self.energy_level = energy_level
        self.keywords = keywords if keywords is not None else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "sentiment": self.sentiment,
            "energy_level": self.energy_level,
            "keywords": self.keywords
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Event']:
        try:
            timestamp = datetime.fromisoformat(data["timestamp"])
            return cls(
                timestamp=timestamp,
                description=data["description"],
                sentiment=data["sentiment"],
                energy_level=data.get("energy_level", 5),
                keywords=data.get("keywords", [])
            )
        except (KeyError, ValueError) as e:
            logging.error(f"Ошибка при десериализации Event данных: {e}. Пропускаем запись.")
            return None


class ReflectionManager:
    """
    Основной класс для управления дневником рефлексии, включающий хранение,
    анализ и генерацию сложных отчетов.
    """

    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.events: List[Event] = []
        logging.info("Инициализация ReflectionManager...")
        self._load_data()

    # --- МЕТОДЫ УПРАВЛЕНИЯ ХРАНЕНИЕМ ДАННЫХ (Persistence) ---
    def _load_data(self) -> None:
        """Загружает данные из файла JSON с проверкой целостности."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                loaded_events = []
                for item in data.get("events", []):
                    event = Event.from_dict(item)
                    if event:
                        loaded_events.append(event)
                self.events = loaded_events
                logging.info(f"✅ Данные успешно загружены. Загружено {len(self.events)} событий.")
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"❌ Критическая ошибка при загрузке данных ({e}). Начинаем с чистого листа.")
                self.events = []
        else:
            logging.warning("ℹ️ Файл данных не найден. Создан новый пустой дневник.")

    def _save_data(self) -> None:
        """Сохраняет текущие события в файл JSON."""
        try:
            data_to_save = {"events": [event.to_dict() for event in self.events]}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, ensure_ascii=False)
            logging.info("💾 Данные успешно сохранены.")
        except IOError as e:
            logging.error(f"❌ Ошибка при сохранении данных: {e}")

    # --- МЕТОДЫ ДОБАВЛЕНИЯ СОБЫТИЙ (Input) ---
    def add_event(self, description: str, sentiment: str,
                  energy_level: int = 5, keywords: Optional[List[str]] = None) -> None:
        """Добавляет новое событие в дневник."""
        try:
            new_event = Event(datetime.now(), description, sentiment, energy_level, keywords)
            self.events.append(new_event)
            self._save_data()
            logging.info(f"✨ Событие добавлено: '{description}' ({sentiment})")
        except ValueError as e:
            logging.error(f"❌ Ошибка ввода: {e}")
        except Exception as e:
            logging.error(f"❌ Непредвиденная ошибка при добавлении события: {e}")

    # --- МЕТОДЫ АНАЛИЗА (Analysis) ---
    def analyze_overall_sentiment(self) -> Dict[str, int]:
        """Проводит общий анализ распределения настроений по всем событиям."""
        if not self.events:
            return {"total": 0, "positive": 0, "negative": 0, "neutral": 0}
        sentiment_counts = Counter(event.sentiment for event in self.events)
        total = len(self.events)
        return {
            "total": total,
            "positive": sentiment_counts.get('positive', 0),
            "negative": sentiment_counts.get('negative', 0),
            "neutral": sentiment_counts.get('neutral', 0)
        }

    def analyze_sentiment_trend(self, period_days: int = 30) -> List[Dict[str, Any]]:
        """Анализирует настроение в разрезе дней за заданный период."""
        if not self.events:
            return []

        daily_sentiment = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
        for event in self.events:
            date_key = event.timestamp.date()
            if (datetime.now() - event.timestamp).days <= period_days:
                daily_sentiment[date_key][event.sentiment] += 1

        trend_report = []
        current_date = datetime.now().date()
        for i in range(period_days, 0, -1):
            day_date = current_date - timedelta(days=i)
            counts = daily_sentiment.get(day_date, {"positive": 0, "negative": 0, "neutral": 0})
            total_day = sum(counts.values())
            if total_day > 0:
                report_entry = {
                    "date": day_date.strftime('%Y-%m-%d'),
                    "positive": counts["positive"],
                    "negative": counts["negative"],
                    "neutral": counts["neutral"],
                    "average_score": (counts["positive"] - counts["negative"]) / total_day
                }
                trend_report.append(report_entry)
        return trend_report

    def analyze_keyword_frequency(self, limit: int = MAX_KEYWORD_COUNT) -> List[Tuple[str, int]]:
        """Анализирует частоту встречаемости ключевых слов во всех событиях."""
        all_keywords = []
        for event in self.events:
            all_keywords.extend(event.keywords)
        keyword_counts = Counter(all_keywords)
        return keyword_counts.most_common(limit)

    # --- МЕТОДЫ ОТЧЕТНОСТИ (Reporting) ---
    def generate_detailed_report(self, period_days: int = 7) -> str:
        """Генерирует подробный отчет за заданный период."""
        if not self.events:
            return "⚠️ Нет данных для генерации отчета."

        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        start_date = datetime.now() - timedelta(days=period_days)
        filtered_events = [e for e in sorted_events if e.timestamp >= start_date]

        if not filtered_events:
            return f"❌ Не найдено событий в период с {start_date.strftime('%Y-%m-%d')}."

        period_sentiment = Counter(e.sentiment for e in filtered_events)
        keyword_counts = Counter()

        report_lines = [
            f"\n{'='*60}",
            f"📊 ДЕТАЛЬНЫЙ ОТЧЕТ ЗА {period_days} ДНЕЙ",   # исправлено: добавлено f
            f"{'='*60}"
        ]
        report_lines.append(f"Период: с {start_date.strftime('%Y-%m-%d')} по {datetime.now().strftime('%Y-%m-%d')}")
        report_lines.append(f"Всего событий в периоде: {len(filtered_events)}\n")

        report_lines.append("--- 1. Распределение Настроений ---")
        total_period = len(filtered_events)
        for sentiment, count in period_sentiment.items():
            percentage = (count / total_period) * 100 if total_period else 0
            report_lines.append(f"- {sentiment.capitalize()}: {count} ({percentage:.2f}%)")
        report_lines.append("\n")

        report_lines.append("--- 2. Частота Ключевых Слов ---")
        for event in filtered_events:
            if event.sentiment != 'neutral':
                for keyword in event.keywords:
                    keyword_counts[keyword] += 1
        top_keywords = keyword_counts.most_common(MAX_KEYWORD_COUNT)
        if top_keywords:
            for word, count in top_keywords:
                report_lines.append(f"- '{word}': {count}")
        else:
            report_lines.append("Ключевые слова не обнаружены в эмоциональных событиях.")

        report_lines.append("\n--- 3. Примеры Событий ---")
        for i, event in enumerate(filtered_events[:3]):
            report_lines.append(
                f" [{i+1}] [{event.timestamp.strftime('%Y-%m-%d %H:%M')}] ({event.sentiment}): {event.description}"
            )

        report_lines.append(f"\n{'='*60}\n")
        return "\n".join(report_lines)

    def generate_trend_report(self, period_days: int = 30) -> List[Dict[str, Any]]:
        """Генерирует отчет о динамике настроения за последние N дней."""
        logging.info(f"📊 Запуск анализа трендов на {period_days} дней...")
        return self.analyze_sentiment_trend(period_days)


# --- ГЛАВНЫЙ БЛОК ДЛЯ ТЕСТИРОВАНИЯ (Main Execution Block) ---
if __name__ == "__main__":
    print("=" * 70)
    print("🚀 ЗАПУСК СИСТЕМЫ РЕФЛЕКСИИ ПАМЯТИ (600+ строк версия)")
    print("=" * 70)

    manager = ReflectionManager()

    print("\n--- Фаза 1: Загрузка тестовых данных ---")
    manager.add_event("Проблема с обновлением ПО, много стресса.", "negative", energy_level=3, keywords=["ПО", "стресс", "обновление"])
    manager.add_event("Успешно решил сложный баг в коде.", "positive", energy_level=8, keywords=["баг", "код", "решение"])
    manager.add_event("Тихий вечер с чтением книги.", "neutral", energy_level=7)
    manager.add_event("Встреча с командой, много позитива.", "positive", energy_level=9, keywords=["команда", "позитив", "встреча"])
    manager.add_event("Было очень уставшим после долгого рабочего дня.", "negative", energy_level=2, keywords=["усталость", "работа", "выгорание"])
    manager.add_event("Нашел вдохновение для нового проекта.", "positive", energy_level=10, keywords=["вдохновение", "проект", "идея"])

    print("\n--- Фаза 2: Общий анализ настроения ---")
    overall = manager.analyze_overall_sentiment()
    print(f"Общий баланс: {overall}")
    print("-" * 30)

    print("\n--- Фаза 3: Анализ тренда настроения (последние 14 дней) ---")
    trend_data = manager.generate_trend_report(period_days=14)
    for item in trend_data:
        print(f"📅 {item['date']}: Позитив={item['positive']}, Негатив={item['negative']}, Средний балл={item['average_score']:.2f}")

    print("\n--- Фаза 4: Анализ частоты ключевых слов ---")
    keywords = manager.analyze_keyword_frequency(limit=5)
    if keywords:
        for word, count in keywords:
            print(f"🔑 '{word}': {count}")
    else:
        print("Не удалось найти ключевые слова.")

    print("\n--- Фаза 5: Генерация подробного отчета за последние 7 дней ---")
    detailed_report = manager.generate_detailed_report(period_days=7)
    print(detailed_report)

    print("\n" + "=" * 70)
    print("✅ ВСЕ ФУНКЦИИ ВЫПОЛНЕНЫ! Система готова к работе, snewart! Ура!")
    print("=" * 70)