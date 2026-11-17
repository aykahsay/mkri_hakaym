"""
Interactive Voice Response (IVR) and Phone Call Gateway for Mkri Hakaym.
Handles phone calls from basic 2G/button phones via standard telephony webhooks
(Twilio / Asterisk / SIP FreePBX / Telnyx).
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, FileResponse
from pydantic import BaseModel

from brain.rag_engine import MedicalRAGEngine
from telephony.audio_service import TigrinyaAudioService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("IVRServer")

app = FastAPI(
    title="Mkri Hakaym (ምኽሪ ሓካይም) Voice Gateway",
    description="Telephony Voice Gateway for 2G / Basic Feature Phones in Tigrinya",
    version="1.0.0",
)

rag_engine = MedicalRAGEngine()
audio_service = TigrinyaAudioService()


class ChatQueryRequest(BaseModel):
    query_text: str
    caller_phone: Optional[str] = "Anonymous"


async def parse_telephony_params(request: Request) -> Dict[str, str]:
    """Helper to parse form or query params from telephone carriers."""
    params = dict(request.query_params)
    body_bytes = await request.body()
    if body_bytes:
        try:
            body_str = body_bytes.decode("utf-8")
            parsed = parse_qs(body_str)
            for k, v in parsed.items():
                if v:
                    params[k] = v[0]
        except Exception:
            pass
    return params


@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "Mkri Hakaym Telephony Gateway",
        "language": "Tigrinya (ትግርኛ)",
        "knowledge_entries": len(rag_engine.knowledge_entries),
    }


@app.get("/audio/{filename}")
def serve_audio(filename: str):
    """Serves real voice WAV/MP3 files directly to telephone carriers during a call."""
    audio_path = audio_service.get_audio_path(filename)
    if audio_path and audio_path.exists():
        return FileResponse(path=str(audio_path), media_type="audio/wav")
    return JSONResponse(status_code=404, content={"error": f"Audio file '{filename}' not found."})


@app.post("/api/ask")
def ask_doctor_api(req: ChatQueryRequest):
    """JSON API for testing, mobile apps, SMS, or Telegram bots."""
    result = rag_engine.answer_caller_query(req.query_text)
    return {
        "query": req.query_text,
        "caller": req.caller_phone,
        "result": result,
    }


# =====================================================================
# Telephony Webhooks (Twilio / Asterisk Voice XML)
# =====================================================================

@app.post("/voice/inbound", response_class=Response)
@app.get("/voice/inbound", response_class=Response)
async def inbound_call_handler(request: Request):
    """
    Triggered when a user dials the phone number from any small phone.
    Greets the caller in Tigrinya with real spoken audio.
    """
    logger.info("Inbound phone call received!")

    # Check if we have audio generated for welcome, else fallback to Say tag
    twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <!-- Welcome Greeting in Spoken Tigrinya -->
    <Play>/audio/welcome.wav</Play>
    <!-- Record the caller's spoken question -->
    <Record action="/voice/process_audio" 
            maxLength="30" 
            finishOnKey="#" 
            playBeep="true" 
            transcribe="false"/>
    <!-- Fallback if silence -->
    <Say language="am-ET">ድምጺ ኣይተሰምዐን። በይዞም ደጊምኩም ደውሉ።</Say>
    <Hangup/>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")


@app.post("/voice/process_audio", response_class=Response)
@app.get("/voice/process_audio", response_class=Response)
async def process_audio_handler(request: Request):
    """
    Receives caller's speech audio/transcript from the telephone network.
    Queries the Medical Brain and speaks back the advice in Tigrinya.
    """
    params = await parse_telephony_params(request)
    caller = params.get("From", "Unknown")
    speech_result = params.get("SpeechResult")
    recording_url = params.get("RecordingUrl")

    logger.info(f"Processing phone voice input from {caller}. Speech: '{speech_result}' | Recording: {recording_url}")

    query = speech_result or "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?"

    # Run through clinical triage and knowledge retrieval
    answer_data = rag_engine.answer_caller_query(query)
    spoken_reply = answer_data["spoken_response_ti"]

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="am-ET">{spoken_reply}</Say>
    <Pause length="1"/>
    <Say language="am-ET">ተወሳኺ ሕቶ እንተሃልዩኩም ድሕሪ ድምጺ ምልክት ተዛረቡ። ንምዝዛም ዓጽዉዎ።</Say>
    <Record action="/voice/process_audio" maxLength="30" finishOnKey="#" playBeep="true"/>
    <Hangup/>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")


# =====================================================================
# DTMF Touch-Tone Fallback (For 2G Keypad Navigation)
# =====================================================================

@app.post("/voice/menu", response_class=Response)
@app.get("/voice/menu", response_class=Response)
async def keypad_menu_handler():
    """Touch-Tone (DTMF) menu for callers with keypad button navigation."""
    twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="1" action="/voice/menu_select" timeout="10">
        <Say language="am-ET">
            ንናይ ጥንሲ ክትትልን ጥዕና ኣዴታትን ቁጽሪ ሓደ ጸቕጡ።
            ንናይ ህጻናት ጥዕናን ክታበትን ቁጽሪ ክልተ ጸቕጡ።
            ንሓፈሻዊ ሕክምናን ቀያሕቲ ምልክታትን ቁጽሪ ሰለስተ ጸቕጡ።
            ምስ ሓኪም ብቐጥታ ንምዝርራብ ቁጽሪ ዜሮ ጸቕጡ።
        </Say>
    </Gather>
    <Say language="am-ET">ምርጫ ኣይተቐበልናን። ደጊምኩም ይደውሉልና።</Say>
    <Hangup/>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")


@app.post("/voice/menu_select", response_class=Response)
@app.get("/voice/menu_select", response_class=Response)
async def keypad_selection_handler(request: Request):
    """Routes caller based on pressed button on their basic phone keypad."""
    params = await parse_telephony_params(request)
    digits = params.get("Digits", "1")

    if digits == "1":
        query = "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?"
    elif digits == "2":
        query = "ናይ ህጻናት ክታበትን ተምላስን ውጽኣትን"
    elif digits == "3":
        query = "ቀያሕቲ ምልክታት ኣብ ጥንሲ"
    elif digits == "0":
        twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="am-ET">ናብ ናይ ጥዕና ሰራሕተኛ ነመሓላልፈኩም ኣለና። በይዞም ኣብ መስመር ጽንሑ።</Say>
</Response>
"""
        return Response(content=twiml_response, media_type="application/xml")
    else:
        query = "ሓፈሻዊ ናይ ጥዕና ምኽሪ"

    answer_data = rag_engine.answer_caller_query(query)
    spoken_reply = answer_data["spoken_response_ti"]

    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="am-ET">{spoken_reply}</Say>
    <Pause length="2"/>
    <Redirect>/voice/menu</Redirect>
</Response>
"""
    return Response(content=twiml_response, media_type="application/xml")
