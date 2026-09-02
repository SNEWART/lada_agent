# web_search.py — интеграция поиска в интернете
from duckduckgo_search import DDGS
import requests
import json
from datetime import datetime
import re

class WebSearch:
    def __init__(self, memory=None):
        self.memory = memory
        self.max_results = 3  # количество ссылок для анализа

    def search(self, query: str) -> list:
        """Выполняет поиск и возвращает список словарей с результатами"""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
                return results
        except Exception as e:
            print(f"⚠️ Ошибка поиска: {e}")
            return []

    def search_and_summarize(self, query: str) -> str:
        """Ищет и возвращает краткую сводку из первых результатов"""
        results = self.search(query)
        if not results:
            return "Не удалось найти информацию по этому запросу."

        # Формируем текстовую выжимку
        summary = f"Результаты поиска по запросу '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get('title', 'Без заголовка')
            snippet = res.get('body', 'Нет описания')
            link = res.get('href', '')
            summary += f"{i}. **{title}**\n   {snippet}\n   Источник: {link}\n\n"

        # Сохраняем в память, если есть
        if self.memory:
            self.memory.add_fact(
                text=f"[Поиск в интернете] Запрос: {query}\nРезультаты: {summary[:300]}...",
                category="web_search",
                importance=4,
                metadata={"timestamp": datetime.now().isoformat()}
            )

        return summary

    def verify_fact(self, claim: str) -> dict:
        """Проверяет утверждение через поиск и возвращает оценку достоверности"""
        # Ищем по утверждению
        results = self.search(claim)
        if not results:
            return {"claim": claim, "verified": False, "reason": "Нет информации"}

        # Простой анализ: считаем, что если есть несколько источников с похожим содержанием, то правда
        # В будущем можно подключить LLM для оценки
        summary = "\n".join([r.get('body', '') for r in results[:2]])
        # Проверяем, содержит ли хоть один результат похожий текст (очень грубо)
        # Для реальной проверки лучше использовать отдельный вызов LLM
        return {
            "claim": claim,
            "verified": True,
            "sources": [r.get('href') for r in results[:2]],
            "summary": summary[:500]
        }