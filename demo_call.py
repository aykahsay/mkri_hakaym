"""
Interactive Voice Call Simulator for Mkri Hakaym (ምኽሪ ሓካይም).
Demonstrates how a phone call from a 2G / basic phone ("small phone")
is received, evaluated for clinical emergencies, matched against verified
Tigrai TV 'ማዕዳ ሓካይም' doctor advice, and answered back in spoken Tigrinya.
"""
import time
from brain.rag_engine import MedicalRAGEngine

def simulate_phone_call():
    print("=" * 70)
    print("📞 MKRI HAKAYM (ምኽሪ ሓካይም) - 2G / BASIC PHONE VOICE SIMULATOR")
    print("=" * 70)
    print("Scenario: A mother or family member in a rural area dials in using")
    print("a basic button phone (no internet, no smartphone apps).\n")

    engine = MedicalRAGEngine()

    print("[RINGING...] 🔔 Inbound call detected from phone: +251 91 4XX XXXX")
    time.sleep(1)
    print("\n[CALL CONNECTED] 🟢 Audio Stream Established (8kHz G.711 Telephony)")
    
    welcome_msg = (
        "እንቋዕ ናብ 'ምኽሪ ሓካይም' ብደሓን መጻእኹም። "
        "ሕቶኹም ድሕሪ ድምጺ ምልክት ተዛረቡ። ዶክተር ክምልሰልኩም እዩ..."
    )
    print(f"\n[AI VOICE GREETING (Tigrinya)]:\n  📢 \"{welcome_msg}\"\n")

    test_scenarios = [
        {
            "description": "Routine Maternal Health Query",
            "spoken_audio_transcript": "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ወይ ጥዕና ጣብያ ክኸይድ ዝግብኣኒ?",
        },
        {
            "description": "Nutrition and Medication Query",
            "spoken_audio_transcript": "ጥንስቲ እንታይ ዓይነት ምግቢ ክትበልዕ ኣለዋ? ክኒን ሓጺን (Iron) ምውሳድ ኣገዳሲ ድዩ?",
        },
        {
            "description": "Critical Emergency / Red Flag Trigger",
            "spoken_audio_transcript": "ጥንስቲ እየ፤ ደም ፈሲሱኒ ኣሎ እንታይ ክገብር?",
        },
    ]

    for idx, sc in enumerate(test_scenarios, 1):
        print("-" * 70)
        print(f"Scenario {idx}: {sc['description']}")
        print(f"👤 Caller speaks into phone: \"{sc['spoken_audio_transcript']}\"")
        time.sleep(1)

        result = engine.answer_caller_query(sc["spoken_audio_transcript"])

        if result["is_emergency"]:
            print("\n🚨 [TRIAGE ALERT] RED FLAG DETECTED! (ቀይሕ ምልክት)")
            print(f"   Urgency Level: {result['urgency_level']}")
            print(f"   Clinical Protocol: {result['action']}")
        else:
            print("\n✅ [TRIAGE] Non-emergency routine educational guidance.")
            print(f"   Source Broadcast: {result['source_used']}")

        print(f"\n📢 [AI DOCTOR VOICE OVER PHONE LINE]:")
        print(f"   \"{result['spoken_response_ti']}\"")

        if result.get("bullet_points_ti"):
            print("\n   Key Clinical Takeaways (for SMS summary or clinic follow-up):")
            for b in result["bullet_points_ti"]:
                print(f"    • {b}")
        print()

    print("=" * 70)
    print("📞 Call Completed: Audio playback ended. Total duration: 3 min 12 sec.")
    print("=" * 70)


if __name__ == "__main__":
    simulate_phone_call()
