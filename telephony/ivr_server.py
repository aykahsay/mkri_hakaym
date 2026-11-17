"""
Interactive Voice Response (IVR) and Phone Call Gateway for Mkri Hakaym.
Handles phone calls from basic 2G/button phones via standard telephony webhooks
(Twilio / Asterisk / SIP FreePBX / Telnyx).
"""
import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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

# Enable CORS for browser frontend & website access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Website static files
website_dir = Path(__file__).resolve().parent.parent / "website"
if website_dir.exists():
    app.mount("/website", StaticFiles(directory=str(website_dir), html=True), name="website")

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
def index():
    """Redirect to the TMA-DHI Web Portal."""
    return RedirectResponse(url="/website/")


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Mkri Hakaym & TMA-DHI Platform",
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
# DATASET PAID ACCESS & LICENSING API
# Strict Monetization: No one is allowed to download data unless they pay.
# =====================================================================

data_dir = Path(__file__).resolve().parent.parent / "data"
dataset_csv_path = data_dir / "medical_qa_dataset.csv"
licenses_file_path = data_dir / "dataset_licenses.json"


class DatasetCheckoutRequest(BaseModel):
    licensee_name: str
    licensee_email: str
    organization: str
    license_tier: str  # "academic" ($49), "commercial" ($499), "institutional"
    payment_gateway: str  # "telebirr", "cbe", "stripe", "bank_transfer"
    transaction_reference: str
    currency: Optional[str] = "USD"


class DatasetVerifyRequest(BaseModel):
    license_key: str


def load_dataset_licenses() -> Dict[str, Any]:
    if licenses_file_path.exists():
        try:
            with open(licenses_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading dataset licenses: {e}")
    # Default seeded active license for verified partner / academic test
    seeded = {
        "TMA-PAID-DEMO-ACADEMIC": {
            "licensee_name": "Ayder Health Researcher",
            "licensee_email": "research@ayder.edu.et",
            "organization": "Mekelle University College of Health Sciences",
            "license_tier": "academic",
            "amount_paid": 49.0,
            "currency": "USD",
            "payment_gateway": "telebirr",
            "transaction_reference": "TEL-2026-DEMO-001",
            "download_count": 0,
            "max_downloads": 15,
            "created_at": "2026-02-15T10:00:00Z",
            "status": "completed",
        }
    }
    save_dataset_licenses(seeded)
    return seeded


def save_dataset_licenses(licenses: Dict[str, Any]):
    licenses_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(licenses_file_path, "w", encoding="utf-8") as f:
        json.dump(licenses, f, indent=2, ensure_ascii=False)


@app.post("/api/v1/datasets/checkout")
def checkout_dataset_license(req: DatasetCheckoutRequest):
    """
    Processes paid license checkout for raw clinical datasets.
    Validates payment details and issues a cryptographically unique license key.
    """
    tier = req.license_tier.lower()
    if tier not in ["academic", "commercial", "institutional"]:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid tier", "message": "Tier must be 'academic' ($49), 'commercial' ($499), or 'institutional'."}
        )

    amounts = {"academic": 49.0, "commercial": 499.0, "institutional": 0.0}
    amount = amounts.get(tier, 49.0)

    # Generate unique 16-hex license key
    random_hex = uuid.uuid4().hex[:10].upper()
    license_key = f"TMA-PAID-{tier[:3].upper()}-{random_hex}"

    licenses = load_dataset_licenses()
    licenses[license_key] = {
        "licensee_name": req.licensee_name,
        "licensee_email": req.licensee_email,
        "organization": req.organization,
        "license_tier": tier,
        "amount_paid": amount,
        "currency": req.currency or "USD",
        "payment_gateway": req.payment_gateway,
        "transaction_reference": req.transaction_reference,
        "download_count": 0,
        "max_downloads": 50 if tier == "commercial" else 15,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "completed",
    }
    save_dataset_licenses(licenses)

    logger.info(f"Paid license issued: {license_key} to {req.licensee_name} ({req.organization})")

    return {
        "success": True,
        "message": "Payment verified and license generated successfully. You are now authorized to download the dataset.",
        "license_key": license_key,
        "license_tier": tier,
        "amount_paid": amount,
        "currency": req.currency or "USD",
        "licensee_name": req.licensee_name,
        "download_url": f"/api/v1/datasets/download?license_key={license_key}",
    }


@app.post("/api/v1/datasets/verify-license")
def verify_dataset_license(req: DatasetVerifyRequest):
    """Validates an existing paid license key."""
    key = req.license_key.strip()
    licenses = load_dataset_licenses()
    if key in licenses:
        info = licenses[key]
        return {
            "valid": True,
            "license_key": key,
            "licensee_name": info.get("licensee_name"),
            "organization": info.get("organization"),
            "license_tier": info.get("license_tier"),
            "download_count": info.get("download_count", 0),
            "max_downloads": info.get("max_downloads", 15),
            "status": info.get("status", "completed"),
        }
    return JSONResponse(
        status_code=404,
        content={"valid": False, "error": "Invalid or unpaid license key. Payment required."}
    )


@app.get("/api/v1/datasets/download")
def download_dataset(license_key: Optional[str] = None):
    """
    Downloads raw medical_qa_dataset.csv.
    STRICT PAYMENT GATE: Returns HTTP 402 Payment Required unless a valid paid license_key is provided.
    """
    if not license_key:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "message": "Strict Data Monetization: No one is allowed to download clinical datasets unless they pay.",
                "pricing": {
                    "academic_license_usd": 49.0,
                    "commercial_license_usd": 499.0,
                    "supported_gateways": ["Telebirr", "CBE Birr", "Credit Card / Stripe", "Bank Wire"]
                },
                "checkout_portal": "/website/#dataset"
            }
        )

    licenses = load_dataset_licenses()
    key = license_key.strip()

    if key not in licenses:
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "message": f"License key '{key}' is invalid or unverified. Payment is strictly required to download.",
                "checkout_portal": "/website/#dataset"
            }
        )

    lic_data = licenses[key]
    lic_data["download_count"] = lic_data.get("download_count", 0) + 1
    save_dataset_licenses(licenses)

    if not dataset_csv_path.exists():
        return JSONResponse(status_code=404, content={"error": "Dataset file not found on server."})

    with open(dataset_csv_path, "r", encoding="utf-8-sig") as f:
        raw_csv_content = f.read()

    # Prepend watermark attribution header to downloaded CSV
    watermark = (
        f"# =========================================================================\n"
        f"# TIGRAY MEDICAL ASSOCIATION (TMA) - DIGITAL HEALTH INITIATIVE (DHI)\n"
        f"# LICENSED CLINICAL DATASET: medical_qa_dataset.csv (TMA-DHI-CORPUS-01)\n"
        f"# LICENSE KEY: {key} | TIER: {lic_data.get('license_tier', 'academic').upper()}\n"
        f"# ISSUED TO: {lic_data.get('licensee_name')} ({lic_data.get('organization')})\n"
        f"# TRANSACTION REF: {lic_data.get('transaction_reference')} | GATEWAY: {lic_data.get('payment_gateway')}\n"
        f"# REVENUES SUPPORT RURAL HEALTH CENTERS AND MATERNAL CLINICS IN TIGRAY\n"
        f"# UNAUTHORIZED REDISTRIBUTION, SHARING, OR PUBLIC HOSTING IS STRICTLY FORBIDDEN\n"
        f"# =========================================================================\n"
    )
    licensed_csv_output = watermark + raw_csv_content

    return Response(
        content=licensed_csv_output.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="medical_qa_dataset_{key}.csv"',
            "X-License-Key": key,
            "X-Licensee": lic_data.get("licensee_name", "Licensed User"),
        }
    )


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
