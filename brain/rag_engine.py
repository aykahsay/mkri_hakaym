"""
Retrieval-Augmented Generation (RAG) Engine for Mkri Hakaym.
Searches verified clinical advice from Tigrai TV "ማዕዳ ሓካይም" and generates
spoken, culturally aligned Tigrinya responses for phone callers.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import KB_DIR
from brain.triage_rules import TriageEngine, TriageAssessment

logger = logging.getLogger("RAG")


class MedicalRAGEngine:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.kb_dir = kb_dir
        self.triage = TriageEngine()
        self.knowledge_entries: List[Dict[str, Any]] = []
        self.load_knowledge_base()

    def load_knowledge_base(self):
        """Loads all verified medical Q&A entries from JSON files."""
        self.knowledge_entries.clear()
        for json_file in self.kb_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    entries = json.load(f)
                    if isinstance(entries, list):
                        self.knowledge_entries.extend(entries)
                    elif isinstance(entries, dict):
                        self.knowledge_entries.append(entries)
            except Exception as e:
                logger.error(f"Error loading {json_file}: {e}")
        logger.info(f"Loaded {len(self.knowledge_entries)} medical knowledge entries.")

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant doctor advice entries by matching query terms
        against questions, tags, topics, and answers.
        """
        query_words = set(query.strip().lower().split())
        scored_entries = []

        for entry in self.knowledge_entries:
            score = 0
            # Check question
            q_text = entry.get("question_ti", "").lower()
            for w in query_words:
                if w in q_text:
                    score += 5

            # Check tags
            tags = [t.lower() for t in entry.get("tags", [])]
            for w in query_words:
                if any(w in tag for tag in tags):
                    score += 4

            # Check topic
            topic = entry.get("topic", "").lower()
            for w in query_words:
                if w in topic:
                    score += 3

            # Check answer
            ans = entry.get("answer_ti", "").lower()
            for w in query_words:
                if w in ans:
                    score += 1

            if score > 0:
                scored_entries.append((score, entry))

        # Sort by relevance score descending
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored_entries[:top_k]]

    def answer_caller_query(self, query_text: str) -> Dict[str, Any]:
        """
        Primary entry point for voice phone callers:
        1. Triage scan for Red Flags (ቀያሕቲ ምልክታት).
        2. If emergency, return immediate hospital alert.
        3. Otherwise, retrieve verified doctor guidance from "ማዕዳ ሓካይም".
        4. Compose clear, spoken Tigrinya audio response for basic phones.
        """
        # Step 1: Emergency Triage Check
        assessment: TriageAssessment = self.triage.evaluate_query(query_text)
        if assessment.is_emergency:
            return {
                "is_emergency": True,
                "urgency_level": assessment.urgency_level,
                "spoken_response_ti": assessment.triage_message_ti,
                "bullet_points_ti": [
                    "ብቕጽበት ናብ ዝቐረበ ጥዕና ጣብያ ወይ ሆስፒታል ምኻድ",
                    "ኣብ ገዛ ደው ዘይምባል",
                ],
                "action": assessment.recommended_action,
                "source_used": "Emergency Triage Protocol",
            }

        # Step 2: Retrieve Relevant Doctor Guidance
        matches = self.search(query_text, top_k=1)
        if matches:
            best = matches[0]
            # Spoken response tuned for audio telephone clarity
            greeting = "ሰላም ጥዕና ይሃበለይ። ንሕቶኹም ብዝምልከት ዶክተር ኣብ 'ማዕዳ ሓካይም' ከምዚ ክብል ይምዕድ፦ "
            spoken_text = f"{greeting}{best['answer_ti']}"

            return {
                "is_emergency": False,
                "urgency_level": "ROUTINE",
                "spoken_response_ti": spoken_text,
                "bullet_points_ti": best.get("key_advice_bullets_ti", []),
                "action": "Educational Guidance",
                "source_used": best.get("source_title", "ማዕዳ ሓካይም - ቴሌቪዥን ትግራይ"),
                "entry_id": best.get("id"),
            }

        # Fallback if no specific match
        fallback_msg = (
            "ሕቶኹም ተሰሚዑ ኣሎ። ይቕሬታ፣ ኣብዚ እዋን እዚ ንዝሓተትኩምዎ ሕቶ ፍሉይ ዝርዝር ኣይተረኸበን። "
            "ዝኾነ ናይ ጥዕና ጸገም እንተሃልዩኩም ናብ ዝቐረበ ጥዕና ጣብያ ብምኻድ ምስ ሓኪም ክትመያየጡ ንምዕድ። "
            "ምስ ሰብ ወይ ሓኪም ብቐጥታ ንምዝርራብ ዜሮ (0) ጸቕጡ።"
        )
        return {
            "is_emergency": False,
            "urgency_level": "UNKNOWN",
            "spoken_response_ti": fallback_msg,
            "bullet_points_ti": ["ናብ ዝቐረበ ጥዕና ጣብያ ምኻድ"],
            "action": "Consult Local Clinic / Transfer to Human Operator",
            "source_used": "General Health Advisory",
        }


if __name__ == "__main__":
    engine = MedicalRAGEngine()
    print("=== Testing Medical RAG Engine ===")

    test_inquiries = [
        "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?",
        "ምግቢ ጥንስቲ እንታይ ክኸውን ኣለዎ?",
        "ደም ፈሲሱኒ እንታይ ክገብር?",
    ]

    for q in test_inquiries:
        print(f"\n[Caller Query]: {q}")
        res = engine.answer_caller_query(q)
        print(f"Emergency: {res['is_emergency']} ({res['urgency_level']})")
        print(f"Voice Response:\n{res['spoken_response_ti']}")
        print(f"Source: {res['source_used']}")
