# 📞 Real Phone Line Deployment Guide (ምኽሪ ሓካይም)
### Connect Real Physical Phones (2G Dumbphones & Smartphones) to Mkri Hakaym

This guide walks you step-by-step through setting up a **real, dialable telephone number** that anyone can call from any small phone.

---

## 🚀 Option 1: Quick Cloud Phone Setup (Twilio) — *Works in 5 Minutes*

With Twilio, you can get a live phone number that anyone in the world can dial right now.

### Step 1: Start your local IVR Telephony Server
In PowerShell:
```powershell
.venv\Scripts\python -m uvicorn telephony.ivr_server:app --port 8000
```

### Step 2: Expose your server to the Internet using a Tunnel
To let telephone networks connect to your local server, run a free tunnel (like `ngrok` or `cloudflared`):
```bash
# Using ngrok
ngrok http 8000
```
*Note your public HTTPS URL, for example:* `https://abc1234.ngrok-free.app`

### Step 3: Configure your Twilio Phone Number
1. Log into your [Twilio Console](https://console.twilio.com/).
2. Go to **Phone Numbers** ➔ **Manage** ➔ **Active Numbers**.
3. Click on your phone number.
4. Scroll down to the **Voice Configuration** section:
   * **A CALL COMES IN**: Select `Webhook`.
   * **URL**: Paste your public tunnel URL:
     ```
     https://abc1234.ngrok-free.app/voice/inbound
     ```
   * **HTTP Method**: `HTTP POST`
5. Click **Save Configuration**.

### Step 4: Pick up ANY phone and dial!
* Call the phone number from your mobile phone or landline.
* **What you will hear:**
  1. The phone answers and speaks in Tigrinya: *"እንቋዕ ናብ ምኽሪ ሓካይም ብደሓን መጻእኹም። ሕቶኹም ድሕሪ ድምጺ ምልክት ተዛረቡ..."*
  2. Speak your health question (e.g. *"ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?"*).
  3. The AI replies with verified doctor advice from Tigrai TV's *"ማዕዳ ሓካይም"*.

---

## 🇪🇹 Option 2: Local Ethio Telecom SIM Deployment (Zero-Internet 2G Access in Ethiopia)

For rural or local deployment in Tigrai and Ethiopia without internet dependencies, you can route calls through a real **Ethio Telecom SIM card**:

```
[Rural 2G Button Phone]
          │ (Local 2G GSM cellular call: 0914XXXXXX)
          ▼
[Ethio Telecom Cellular Tower]
          │
          ▼
[GSM Gateway / USB Dongle with Ethio Telecom SIM] (e.g., GoIP-1 or Huawei E3372)
          │ (SIP / Local Network)
          ▼
[Asterisk PBX / FreePBX Server]
          │ (HTTP Webhook)
          ▼
[Mkri Hakaym IVR Gateway (localhost:8000)]
```

### Required Hardware (Low Cost):
1. **1-Port GSM Gateway** (e.g., *GoIP-1*, *Dinstar*, or a *Huawei USB GSM Dongle*): ~$25 - $45.
2. **Local Ethio Telecom SIM card** (e.g. `0914...` or `09...`).
3. **Local Computer / Mini PC / Raspberry Pi** running Asterisk and Mkri Hakaym.

### Asterisk Dialplan Configuration (`/etc/asterisk/extensions.conf`):
```ini
[from-gsm-gateway]
exten => s,1,NoOp(Incoming Medical Call from Ethio Telecom SIM)
 same => n,Answer()
 same => n,Set(CALLER_ID=${CALLERID(num)})
 ; Play Tigrinya greeting audio
 same => n,Playback(/mkri_hakaym/data/audio_cache/welcome)
 ; Record caller inquiry (30 seconds limit)
 same => n,Record(/tmp/caller_query:wav,3,30)
 ; Trigger Mkri Hakaym Brain via CURL
 same => n,System(/mkri_hakaym/.venv/bin/python /mkri_hakaym/process_call.py /tmp/caller_query.wav)
 ; Play back doctor response audio
 same => n,Playback(/tmp/doctor_response)
 same => n,Hangup()
```

---

## 🧪 Testing the Live Telephony Webhooks Locally Right Now

You can simulate an incoming call from a telecom carrier using `curl` or PowerShell:

```powershell
# 1. Test Inbound Call Pickup
Invoke-RestMethod -Uri "http://127.0.0.1:8000/voice/inbound" -Method Post

# 2. Test Voice Input Processing
Invoke-RestMethod -Uri "http://127.0.0.1:8000/voice/process_audio" -Method Post -Body @{
    SpeechResult = "ጥንሲ ምስ ሓዝኩ መዓስ እየ ናብ ሓኪም ክኸይድ?"
    From = "+251914000000"
}
```

Both return standard **TwiML XML** ready to stream audio back into the caller's telephone receiver!
