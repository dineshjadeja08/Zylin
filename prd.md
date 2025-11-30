# Zylin – MVP Build Guide (Step-by-Step, No Code)

## 1. Define the MVP Clearly

Before touching anything technical, be very clear on **what the first version should do**.

For Zylin MVP, your product should be able to:

1. **Answer a phone call automatically**
2. **Listen to the caller and understand what they said (speech → text)**
3. **Decide what they want (intent: FAQ or booking)**
4. **Respond with a helpful answer (text)**
5. **Speak back the answer (text → voice)** – this can be v2; in v1 even a WhatsApp/SMS reply is okay
6. **If they want an appointment, collect details and save it somewhere**
7. **Send a WhatsApp confirmation with the appointment details**
8. **Log the call: who called, what they said, what Zylin did**

That’s it.

No fancy dashboard, no payment system, no multi-tenant complexity yet.

---

## 2. Design the Core User Flows

Think like a user, not a developer. You need 2–3 crystal clear flows.

### 2.1. Call + FAQ Flow (Simple Question)

1. Customer calls the business number.
2. Zylin picks up.
3. Caller asks: “What are your working hours today?”
4. Zylin:
    - understands the speech
    - recognizes this as a FAQ
    - looks up the info (from a fixed data source or prompt context)
    - replies with the answer
5. Zylin ends the call or asks “Anything else?”
6. Zylin logs this call and marks it as `faq`.

---

### 2.2. Call + Appointment Booking Flow

1. Customer calls.
2. Zylin answers.
3. Caller says: “I want an appointment tomorrow at 4 PM.”
4. Zylin:
    - asks for name and phone number if needed
    - confirms the date and time
    - saves this as an appointment record
5. After the call, Zylin sends a **WhatsApp message** to the customer:
    
    “Your appointment is confirmed for [date][time].”
    
6. Zylin logs the call and marks it as `booking`.

---

### 2.3. Call + Escalation Flow (Optional for MVP)

1. Customer calls with an urgent or complex issue.
2. Zylin tries to help, but detects it’s urgent.
3. Zylin tells the caller: “I’ll ask the business owner to call you back.”
4. Zylin sends a **WhatsApp alert** to the business owner with a summary.

You can keep this for slightly later, but it’s a good mental model.

---

## 3. Decide the Building Blocks (Conceptually)

Now, you decompose Zylin into **modules** instead of thinking as one big mess.

### 3.1. Telephony Module

- Its job: **handle phone calls**.
- It connects the phone network to your backend.
- Example service: Twilio.
- It will:
    - receive incoming calls
    - send call audio to your backend
    - play back audio to the caller.

You will configure Twilio to send call events to an HTTP endpoint in your backend.

---

### 3.2. ASR Module (Speech → Text)

- Its job: **turn caller’s voice into text**.
- Zylin’s brain only works with text.
- Example engine: Whisper (via API or self-hosted).
- Input: audio from call.
- Output: text string (what the caller said).

---

### 3.3. LLM Module (Zylin Brain)

- Its job: **understand the text + decide what to do + generate a reply**.
- Powered by an LLM (like GPT).
- Uses a **system prompt** that defines Zylin’s personality and rules.
- Responsibilities:
    - classify intent (FAQ vs booking vs other)
    - generate natural replies
    - decide when to ask follow-up questions
    - decide when to call a “tool” (e.g., booking function).

You design this as a pure text-in → text-out brain.

---

### 3.4. Business Logic Module (Tools/Actions)

This is where “Zylin becomes useful,” beyond just chat.

- Handles concrete actions like:
    - create an appointment entry
    - send a WhatsApp message
    - mark a call as urgent
- Think of it as a set of “functions” the LLM can trigger.

Each **tool** is like:

> “Given some arguments, perform something in the real world and return a confirmation.”
> 

---

### 3.5. TTS Module (Text → Speech)

- Its job: **turn AI’s reply text back into audio**.
- This is what the caller will hear.
- Example: TTS service.
- Input: reply text.
- Output: audio stream/file.

For v1, you can even skip this and just send a WhatsApp message afterwards.

For v2, you make it speak live during the call.

---

### 3.6. Storage / Logging Module

- Its job: **remember what happened**.
- Stores:
    - call details
    - transcript
    - reply
    - type (faq / booking)
    - appointment details
- MVP storage can even be:
    - SQLite
    - or simple JSON files
    - then later PostgreSQL.

---

## 4. Plan the Order of Implementation

Most people fail by trying to do everything at once.

You won’t.

You’ll build in this order:

1. **LLM Brain** (Zylin as text-only assistant)
2. **ASR** (speech → text, offline test with files)
3. **TTS** (text → speech, offline test with files)
4. **Conversation Orchestrator** (connect ASR + LLM + TTS conceptually)
5. **Telephony integration** (but simple version)
6. **Business actions (appointments + WhatsApp)**
7. **Logging**

Below: how each of these is built conceptually.

---

## 5. Step-by-Step Build – In Detail (Concept, Not Code)

### Step 1: Make Zylin Smart with Text

**Goal:** Zylin can handle conversations in plain text.

You do this by:

- Designing a **system prompt** that defines:
    - Zylin is an assistant for SMEs
    - It can help with FAQs and bookings
    - It should ask follow-up questions if info is missing
    - It must answer briefly and clearly
- Deciding the **intents** Zylin cares about:
    - `faq` (simple information)
    - `booking` (appointments)
    - maybe `other` or `urgent`

You then manually test Zylin via terminal/chat:

- pretend you’re a caller
- see if Zylin:
    - understands you
    - asks missing questions
    - gives a good confirmation
    - can phrase things politely and naturally.

At this stage, you ignore voice and phones.

You’re just training “text Zylin” to behave correctly.

---

### Step 2: Teach Zylin to Understand Voice (ASR Concept)

**Goal:** Zylin can understand speech, not just text.

You plan:

- How audio is going to reach your backend:
    - For now, you can use a pre-recorded audio file (like `.wav` or `.mp3`).
    - Later this will be real phone call audio.
- How you will call your ASR engine:
    - You pass it audio data.
    - It gives you back text.

What matters conceptually:

- The transcription must be **good enough** for Zylin to understand.
- You may see some mistakes; that’s okay at MVP stage.
- You mentally test:
    
    “If it transcribes like this, can my LLM still figure out intent?”
    

You’re not yet worrying about callers.

You’re simulating “I have a voice recording → I get text → I send that text to Zylin.”

---

### Step 3: Teach Zylin to Talk Back (TTS Concept)

**Goal:** Zylin can speak.

You decide:

- What voice style fits your brand:
    - Friendly but professional
    - Neutral accent
    - Not too robotic
- Input: text reply from Zylin’s brain
- Output: an audio file or stream you can play.

Again, at MVP stage, you test:

- Take Zylin’s reply text
- Run it through TTS
- Listen to the result yourself
- Check:
    - is it clear?
    - is it too slow / too fast?
    - does it sound acceptable for real customers?

---

### Step 4: Orchestrate the Conversation (Core Pipeline)

Now you mentally assemble the pieces:

1. Caller speaks → **audio**
2. Audio → **ASR → text**
3. Text → **LLM → reply text**
4. Reply text → **TTS → audio**
5. Audio → **back to caller**

You also:

- Decide when to stop listening and when to respond
- Decide how many back-and-forth turns you allow for MVP
- Decide when to trigger actions (like booking)

Think of this as **a human receptionist’s brain**:

- Listening
- Thinking
- Speaking
- Acting
- Making notes.

Your “Conversation Orchestrator” is just a clean way to connect all those steps.

---

### Step 5: Connect the Phone System (Telephony)

Once the core “brain” works in isolation, you connect it to the phone network.

Conceptually:

- A customer dials your Twilio number.
- Twilio forwards the call to your backend via an HTTP endpoint you expose (a webhook).
- You decide what happens on each call:
    - Do you greet and record first?
    - Do you stream live audio? (more advanced)
    - For MVP, you can:
        - Let Twilio record part of the call
        - When recording ends, process that audio, generate reply, and either:
            - call them back with a message
            - or send reply via WhatsApp/SMS.

The simplest MVP version:

> Use the phone call to collect their question or request, then do your AI processing off-call and respond via WhatsApp.
> 

Later, you upgrade to real-time two-way speech.

---

### Step 6: Handle Bookings as a Real “Business Action”

Now you define **what a booking is**:

- customer name
- phone number
- date & time
- optional notes
- status: confirmed/pending

You decide:

- Where to store it (file or DB)
- What constitutes “enough info to confirm”:
    - If date/time is missing: Zylin asks.
    - If name is missing: Zylin asks.
- When to send confirmation:
    - Immediately after Zylin has all details.

Conceptually, booking is just:

**Collect parameters → store them → send confirmation → log it.**

You keep it simple at first:

- No calendars
- No conflict detection
- Just basic capture and confirm.

---

### Step 7: Add WhatsApp Notification Flow

Now you focus purely on communication flow after the call.

What should happen:

- If a **booking** was created:
    - Send WhatsApp to customer:
        
        “Hi [Name], your appointment is confirmed for [date][time]. – [Business Name] via Zylin”
        
- If the call was **urgent**:
    - Send WhatsApp to owner:
        
        “Urgent call from [Number]: [Short summary]. Please follow up.”
        

You define:

- For which events you send messages
- The exact message templates
- The phone number format you require (+91…)
- How you handle failures (message not sent, etc.)

---

### Step 8: Logging and Simpler Analytics

Now, think like an operator of the system.

For each call, you want to see:

- Who called
- When they called
- What they said (transcript)
- What Zylin replied
- What type of call it was (faq / booking / urgent)
- Whether any action was taken (appointment created? WhatsApp sent?)

You decide:

- How to store this:
    - a simple table / JSON list / DB
- What “stats” you want to derive:
    - number of calls per day
    - number of bookings
    - number of FAQs handled

You aren’t building a full analytics dashboard yet, but you’re planning the data model so you can.

---

### Step 9: Tie It Together as an MVP

At this point, your conceptual product should:

1. Accept a call via phone system
2. Capture user speech and convert to text
3. Ask more questions if needed (via LLM)
4. Detect whether this is a FAQ or booking
5. If FAQ, respond with the right info
6. If booking, collect details and store them
7. Send necessary WhatsApp confirmations
8. Log everything internally for you to inspect later

This is enough to:

- Show a demo
- Let a small clinic or salon try it
- Charge a basic subscription
- Collect feedback.

---

## 6. Testing the MVP (Conceptually)

You test each layer separately first:

1. **LLM** – test Zylin’s FAQ and booking logic in plain text.
2. **ASR** – test multiple accents, noisy audio, and check text output.
3. **TTS** – test how good replies sound.
4. **Telephony stub** – simulate calls using test tools or recorded audio.
5. **End-to-end call** – you call the number, talk, and see if:
    - Zylin understands
    - Zylin replies correctly (or via WhatsApp)
    - bookings are stored
    - logs are created.

---

## 7. What You *Should Not* Build in V1

To stay fast and focused, do **not** build yet:

- Full multi-tenant dashboard
- Complex role-based access
- Payment integration
- Admin analytics UI
- Perfect error messages
- Custom voice clones

MVP is about **proving the core works and businesses want it**, not perfection.

---

## 8. After MVP Works Once

Once you have:

- 2–3 successful test calls
- 1–2 internal test bookings created
- WhatsApp confirmations working

Then you’re ready to:

- Pitch it to a real clinic/salon
- Put a small price
- Get real-world usage feedback

From here, you iterate.