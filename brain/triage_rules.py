"""
Triage Rules & Red-Flag Detector (ቀያሕቲ ምልክታት) for Mkri Hakaym.
Linguistically tuned for Tigrinya morphological inflections (e.g. ርእሰይ, ይሓመኒ, ይፈሰኒ).
Ensures clear separation between 'ጸቕጢ ደም' (blood pressure) and 'ምፍሳስ ደም' (bleeding).
"""
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class TriageAssessment(BaseModel):
    is_emergency: bool
    urgency_level: str  # "CRITICAL", "HIGH", "MEDIUM", "ROUTINE"
    matched_condition: Optional[str] = None
    triage_message_ti: str
    triage_message_en: str
    recommended_action: str


RED_FLAGS = {
    "maternal_hemorrhage": {
        "title": "Maternal Vaginal Bleeding (ምፍሳስ ደም ኣብ ጥንሲ)",
        "terms": ["ምፍሳስ ደም", "ደም ምፍሳስ", "ደም ይፈሰኒ", "ደም ፈሲሱኒ", "ደም ኣሎኒ"],
        "regex_patterns": [
            r"ምፍሳስ ደም",
            r"ደም ምፍሳስ",
            r"ደም ይፈሰ[ኒካኪ]",
            r"ደም ፈሲሱ[ኒካኪ]",
            r"ደም ኣሎ[ኒኪ]",
            r"ደም መጺኡ[ኒኪ]",
            r"ደም ርእየ",
        ],
        "level": "CRITICAL",
        "msg_ti": "ኣድህቡ! ኣብ እዋን ጥንሲ ምፍሳስ ደም ቀይሕ ምልክት (ሓደጋ) እዩ። ብቕጽበት ናብ ዝቐረበ ሆስፒታል ወይ ጥዕና ጣብያ ኪዱ! ኣብ ገዛ ደው ኣይትበሉ!",
        "msg_en": "Immediate Emergency: Vaginal bleeding during pregnancy is a critical red flag. Go to the nearest hospital immediately.",
        "action": "Immediate Emergency Referral to Emergency Obstetric Care.",
    },
    "preeclampsia_eclampsia": {
        "title": "Pre-eclampsia / Severe Hypertension in Pregnancy (ጸቕጢ ደም ጥንሲ)",
        "terms": ["ብርቱዕ ርእሲ ሕማም", "ዓይኒ ምፍዛዝ", "ሕበጥ ገጽ", "ሕበጥ ኣእጋር", "መንቀጥቀጥ"],
        "regex_patterns": [
            r"ብርቱዕ.*(ርእሲ|ርእሰይ)",
            r"(ርእሲ|ርእሰይ).*ብርቱዕ",
            r"(ርእሲ|ርእሰይ).*(ሕማም|ይሓመኒ|ቃንዛ).*(ዓይኒ|ይፈዝዝ|ምፍዛዝ)",
            r"ዓይኒ.*(ምፍዛዝ|ዘይምርኣይ|ምዕዋር)",
            r"ሕበጥ.*(ገጽ|ኣእጋር)",
            r"መንቀጥቀጥ",
        ],
        "level": "CRITICAL",
        "msg_ti": "ብርቱዕ ርእሲ ሕማም ምስ ዓይኒ ምፍዛዝ ኣብ ጥንሲ ምልክት ልዑል ጸቕጢ ደም (Pre-eclampsia) ክኸውን ስለዝኽእል ቀጥታ ናብ ጥዕና ጣብያ ብምኻድ ጸቕጢ ደምኩም ተመርመሩ።",
        "msg_en": "Critical Emergency: Severe headache, visual disturbance, or sudden facial edema in pregnancy indicates possible pre-eclampsia.",
        "action": "Immediate Blood Pressure check and emergency clinic evaluation.",
    },
    "fetal_distress": {
        "title": "Reduced Fetal Movement (ምንቅስቓስ ዕሸል ምቁራጽ)",
        "terms": ["ዕሸል ምንቅስቓስ ምቁራጽ", "ምንቅስቓስ ዕሸል ምቕናስ", "ዕሸል ኣይተንቀሳቐሰን"],
        "regex_patterns": [
            r"ዕሸል.*(ምንቅስቓስ|ምንቅስቃስ)",
            r"ምንቅስቓስ.*ዕሸል",
            r"ዕሸል.*ኣይተንቀሳቐሰን",
            r"ምንቅስቓስ.*(ምቁራጽ|ምቕናስ|ኣቋሪጹ|ቀኒሱ)",
        ],
        "level": "HIGH",
        "msg_ti": "ዕሸል ምንቅስቓሱ እንተቋሪጹ ወይ ብርቱዕ እንተቀኒሱ፣ ብህጹጽ ናብ ጥዕና ጣብያ ብምኻድ ናይ ልቢ ትርግታ ዕሸል (Fetal Heartbeat) ክረጋገጽ ኣለዎ።",
        "msg_en": "Urgent: Reduced or absent fetal movement requires immediate fetal heartbeat auscultation.",
        "action": "Urgent Clinic Visit for Fetal Monitoring.",
    },
    "respiratory_distress": {
        "title": "Severe Respiratory Distress (ምሕጻር እስትንፋስ)",
        "terms": ["ምሕጻር እስትንፋስ", "ምትንፋስ ምእባይ", "ሕማም ደረት"],
        "regex_patterns": [
            r"ምሕጻር እስትንፋስ",
            r"ምትንፋስ.*(ኣብዩ|ምእባይ)",
            r"እስትንፋስ.*(ምቁራጽ|ምሕጻር)",
            r"ሕማም ደረት",
        ],
        "level": "CRITICAL",
        "msg_ti": "ምሕጻር እስትንፋስን ሕማም ደረትን ህጹጽ ሕክምናዊ ሓገዝ ዘድልዮ እዩ። ቀጥታ ናብ ህጹጽ ረድኤት (Emergency) ኪዱ።",
        "msg_en": "Critical Emergency: Severe shortness of breath or chest pain requires immediate emergency care.",
        "action": "Immediate Emergency Transport.",
    },
    "severe_dehydration_pediatric": {
        "title": "Pediatric/General Severe Dehydration (ተምላስን ውጽኣትን)",
        "terms": ["ውጽኣትን ተምላስን", "ማይ ምውዳእ", "ልሕሉሕ ምዃን"],
        "regex_patterns": [
            r"ውጽኣት.*ተምላስ",
            r"ተምላስ.*ውጽኣት",
            r"ውጽኣትን ተምላስን",
            r"ማይ ምውዳእ",
        ],
        "level": "HIGH",
        "msg_ti": "ተምላስን ውጽኣትን ማይ ኣብ ውሽጢ ሰብነት ስለዘውድእ፣ ብቕጽበት ኦ.ኣር.ኤስ (ORS) ወይ ማይ ብጨው እናሃብኩም ናብ ጥዕና ጣብያ ውሰድዎ።",
        "msg_en": "Urgent: Dehydration from vomiting or diarrhea requires immediate ORS rehydration and clinic visit.",
        "action": "ORS Rehydration + Urgent Clinic Visit.",
    },
}


class TriageEngine:
    def __init__(self, custom_rules: Optional[Dict[str, Any]] = None):
        self.rules = custom_rules or RED_FLAGS

    def evaluate_query(self, user_query: str) -> TriageAssessment:
        query_text = user_query.strip().lower()

        for condition_key, rule in self.rules.items():
            for pattern in rule.get("regex_patterns", []):
                if re.search(pattern, query_text):
                    return TriageAssessment(
                        is_emergency=True,
                        urgency_level=rule["level"],
                        matched_condition=condition_key,
                        triage_message_ti=rule["msg_ti"],
                        triage_message_en=rule["msg_en"],
                        recommended_action=rule["action"],
                    )

        # Routine inquiry
        return TriageAssessment(
            is_emergency=False,
            urgency_level="ROUTINE",
            matched_condition=None,
            triage_message_ti="ሕቶኹም ተቐቢልናዮ ኣለና። ዶክተር ምኽሪ ንምሃብ ኣብ ምድላው ኣሎ።",
            triage_message_en="Inquiry received. Preparing verified clinical guidance.",
            recommended_action="Provide standard educational and preventive counseling.",
        )
