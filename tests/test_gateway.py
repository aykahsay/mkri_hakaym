"""
Tests for Mkri Hakaym (ምኽሪ ሓካይም) RAG & Telephony Gateway.
Calls handlers directly for fast, reliable unit testing.
"""
from telephony.ivr_server import ask_doctor_api, ChatQueryRequest
from brain.rag_engine import MedicalRAGEngine
from brain.triage_rules import TriageEngine

def test_emergency_triage():
    triage = TriageEngine()
    res = triage.evaluate_query("ጥንስቲ እየ ደም ፈሲሱኒ እንታይ ክገብር?")
    assert res.is_emergency is True
    assert res.urgency_level == "CRITICAL"
    assert "ሆስፒታል" in res.triage_message_ti

def test_routine_pregnancy_advice():
    engine = MedicalRAGEngine()
    res = engine.answer_caller_query("ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?")
    assert res["is_emergency"] is False
    assert res["urgency_level"] == "ROUTINE"
    assert "12 ሰሙናት" in res["spoken_response_ti"]
    assert "ማዕዳ ሓካይም" in res["source_used"]

def test_api_ask_doctor():
    req = ChatQueryRequest(query_text="ጥንስቲ እንታይ ዓይነት ምግቢ ክትበልዕ ኣለዋ?")
    res = ask_doctor_api(req)
    assert res["query"] == req.query_text
    assert res["result"]["is_emergency"] is False
    assert "ዝተመጣጠነ" in res["result"]["spoken_response_ti"]

def test_fetal_distress_alert():
    engine = MedicalRAGEngine()
    res = engine.answer_caller_query("ዕሸል ምንቅስቓስ ኣቋሪጹኒ")
    assert res["is_emergency"] is True
    assert res["urgency_level"] == "HIGH"
    assert "ትርግታ" in res["spoken_response_ti"] or "ዕሸል" in res["spoken_response_ti"]

if __name__ == "__main__":
    test_emergency_triage()
    test_routine_pregnancy_advice()
    test_api_ask_doctor()
    test_fetal_distress_alert()
    print("ALL TESTS PASSED SUCCESSFULLY! ✅")
