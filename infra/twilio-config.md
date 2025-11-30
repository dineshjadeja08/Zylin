# Twilio Configuration Guide

## Overview

This guide explains how to configure Twilio to work with Zylin for handling phone calls and WhatsApp notifications.

---

## Prerequisites

1. **Twilio Account** - Sign up at https://www.twilio.com
2. **Phone Number** - Purchase a Twilio phone number with voice capabilities
3. **WhatsApp Sandbox** (for testing) or approved WhatsApp number
4. **Public URL** - Your Zylin API must be publicly accessible (use ngrok for local testing)

---

## Step 1: Get Twilio Credentials

1. Log in to Twilio Console: https://console.twilio.com
2. Find your Account SID and Auth Token on the dashboard
3. Copy these to your `.env` file:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

---

## Step 2: Purchase Phone Number

1. Go to **Phone Numbers** → **Buy a Number**
2. Search for a number in your desired country
3. Ensure it has **Voice** capabilities
4. Purchase the number
5. Copy the number to your `.env`:

```env
TWILIO_PHONE_NUMBER=+1234567890
```

---

## Step 3: Configure Voice Webhooks

1. Go to **Phone Numbers** → **Manage** → **Active Numbers**
2. Click on your purchased number
3. Scroll to **Voice & Fax** section
4. Configure webhooks:

### A Call Comes In
- **Webhook**: `https://your-domain.com/api/twilio/voice`
- **Method**: `HTTP POST`

### Call Status Changes
- **Status Callback URL**: `https://your-domain.com/api/twilio/status`
- **Method**: `HTTP POST`

5. Click **Save**

---

## Step 4: Configure WhatsApp (Testing)

### Using WhatsApp Sandbox (for testing):

1. Go to **Messaging** → **Try it out** → **Send a WhatsApp message**
2. Follow instructions to connect your WhatsApp to the sandbox
3. Send the code (e.g., "join example-word") to the sandbox number
4. Use the sandbox number in your `.env`:

```env
TWILIO_WHATSAPP_NUMBER=+14155238886
```

### For Production (requires approval):

1. Go to **Messaging** → **Senders** → **WhatsApp senders**
2. Click **New WhatsApp Sender**
3. Follow Facebook Business verification process
4. Submit your WhatsApp message templates for approval
5. Once approved, use your approved number

---

## Step 5: Set Up Public URL (Local Development)

### Using ngrok:

1. Install ngrok: https://ngrok.com/download

```powershell
# Install via chocolatey
choco install ngrok

# Or download and add to PATH
```

2. Start your Zylin API:

```powershell
python main.py
```

3. In another terminal, start ngrok:

```powershell
ngrok http 8000
```

4. Copy the HTTPS forwarding URL (e.g., `https://abc123.ngrok.io`)

5. Update your Twilio webhook URLs:
   - Voice webhook: `https://abc123.ngrok.io/api/twilio/voice`
   - Status callback: `https://abc123.ngrok.io/api/twilio/status`

**Note:** ngrok URLs change each restart. Use ngrok paid plan for static URLs, or deploy to a permanent server.

---

## Step 6: Test the Integration

### Test Voice Call:

1. Ensure your server is running and ngrok is connected
2. Call your Twilio phone number from your mobile
3. You should hear: "Hello! I'm Zylin, your AI receptionist..."
4. Speak your message (e.g., "I need an appointment tomorrow at 3 PM")
5. Check your WhatsApp for a response from Zylin

### Test WhatsApp Notifications:

```python
from services.notifications.whatsapp import WhatsAppService

whatsapp = WhatsAppService()
whatsapp.send_message(
    to_phone="+919876543210",
    message="Test message from Zylin!"
)
```

---

## Webhook Flow

### Incoming Call Flow:

```
1. Customer calls Twilio number
   ↓
2. Twilio POSTs to /api/twilio/voice
   ↓
3. Zylin creates session and returns TwiML
   ↓
4. Twilio plays greeting and records caller
   ↓
5. Twilio POSTs recording to /api/twilio/recording/{call_sid}
   ↓
6. Zylin processes in background:
   - Download recording
   - Transcribe with ASR
   - Process with LLM brain
   - Create booking if needed
   - Send WhatsApp response
   - Log call
   ↓
7. Customer receives WhatsApp with reply
```

---

## TwiML Reference

### Greeting Response:

```xml
<Response>
    <Say voice="Polly.Joanna">
        Hello! I'm Zylin, your AI receptionist. How can I help you today?
    </Say>
    <Record 
        action="/api/twilio/recording/{CallSid}"
        maxLength="30"
        playBeep="true"
        timeout="5"
    />
    <Hangup/>
</Response>
```

### Available Voices:
- `Polly.Joanna` (Female, US English)
- `Polly.Matthew` (Male, US English)
- `Polly.Amy` (Female, British English)
- `Polly.Brian` (Male, British English)
- `Polly.Aditi` (Female, Indian English)

---

## Environment Variables Summary

```env
# Twilio Credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token

# Twilio Phone Numbers
TWILIO_PHONE_NUMBER=+1234567890
TWILIO_WHATSAPP_NUMBER=+14155238886  # or your approved number

# OpenAI (for ASR/LLM/TTS)
OPENAI_API_KEY=sk-your-key

# Business Info
BUSINESS_NAME=Your Business Name
BUSINESS_PHONE=+911234567890
OWNER_PHONE=+919876543210
```

---

## Security Considerations

### 1. Validate Twilio Requests

Add signature validation (production):

```python
from twilio.request_validator import RequestValidator

validator = RequestValidator(os.getenv("TWILIO_AUTH_TOKEN"))

def validate_twilio_request(request: Request):
    signature = request.headers.get("X-Twilio-Signature")
    url = str(request.url)
    params = await request.form()
    
    if not validator.validate(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")
```

### 2. Use HTTPS Only

Never use HTTP webhooks in production. Twilio requires HTTPS.

### 3. Rate Limiting

Implement rate limiting to prevent abuse:

```python
from fastapi_limiter import FastAPILimiter

@router.post("/voice")
@limiter.limit("10/minute")
async def handle_incoming_call(...):
    ...
```

### 4. Secure Environment Variables

- Never commit `.env` to git
- Use secret management in production (AWS Secrets Manager, Azure Key Vault)
- Rotate credentials regularly

---

## Troubleshooting

### "Webhook returned invalid TwiML"

- Check your XML is valid (no unclosed tags)
- Ensure Content-Type is `application/xml`
- Check Twilio error logs in console

### "Recording URL returns 401 Unauthorized"

- Include Twilio credentials when downloading
- Check Account SID and Auth Token are correct

### "WhatsApp message not delivered"

- Verify recipient joined sandbox (for testing)
- Check phone number format (+country code)
- Ensure WhatsApp number has `whatsapp:` prefix

### "Webhook not triggered"

- Verify ngrok is running and URL is correct
- Check webhook URL in Twilio console
- Look at Twilio debugger logs
- Ensure your server is running

### "Audio quality poor"

- Twilio recordings are 8kHz by default (phone quality)
- Whisper handles this well
- For better quality, use Twilio Media Streams (advanced)

---

## Production Deployment

### 1. Deploy to Cloud

Use AWS, Azure, GCP, or similar:

```bash
# Example: Deploy to AWS EC2
ssh ec2-user@your-instance
git clone your-repo
cd Zylin
pip install -r requirements.txt
python main.py
```

### 2. Use Process Manager

```bash
# Using systemd
sudo nano /etc/systemd/system/zylin.service

[Unit]
Description=Zylin AI Receptionist
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Zylin
ExecStart=/home/ubuntu/Zylin/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable zylin
sudo systemctl start zylin
```

### 3. Set Up SSL/TLS

Use Let's Encrypt with nginx:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Update Twilio Webhooks

Replace ngrok URL with your production domain:
- `https://your-domain.com/api/twilio/voice`
- `https://your-domain.com/api/twilio/status`

---

## Cost Estimates

### Twilio Pricing (as of 2025):

- **Phone number**: ~$1/month
- **Incoming calls**: $0.0085/minute
- **Outgoing calls**: $0.013/minute (if you call back)
- **WhatsApp messages**: $0.005/message

### Example: 100 calls/day, 2 min avg

- Phone number: $1/month
- Incoming calls: 100 × 2 min × $0.0085 × 30 days = $51/month
- WhatsApp messages: 100 × $0.005 × 30 days = $15/month
- **Total Twilio: ~$67/month**

Combined with OpenAI (~$100/month), total ~$170/month for 3000 calls.

---

## Advanced: Real-Time Streaming

For real-time two-way conversations (post-MVP):

See `docs/streaming_plan.md` for implementation guide.

Uses Twilio Media Streams to stream audio in real-time rather than recording first.

---

## Support

- **Twilio Docs**: https://www.twilio.com/docs
- **Twilio Support**: https://support.twilio.com
- **Zylin Issues**: https://github.com/dineshjadeja08/Zylin/issues

---

**Last Updated:** November 30, 2025
