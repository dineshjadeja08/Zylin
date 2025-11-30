# LLM Brain Test Cases

## Test Suite for Zylin Intent Classification and Dialog Flow

### Test Format
```
Input: <caller message>
Expected Intent: <faq|booking|urgent|other>
Expected Data: <key-value pairs if booking>
Expected Response Pattern: <what the response should contain>
```

---

## FAQ Tests (5 cases)

### T1-FAQ-01: Business Hours
**Input:** "What time are you open today?"
**Expected Intent:** `faq`
**Expected Data:** None
**Expected Response Pattern:** Should mention today's hours and ask if anything else needed
**Pass Criteria:** Intent correct + response contains time information

---

### T1-FAQ-02: Location
**Input:** "Where is your clinic located?"
**Expected Intent:** `faq`
**Expected Data:** None
**Expected Response Pattern:** Should provide address
**Pass Criteria:** Intent correct + response contains address

---

### T1-FAQ-03: Service Inquiry
**Input:** "Do you do blood tests?"
**Expected Intent:** `faq`
**Expected Data:** None
**Expected Response Pattern:** Should confirm service availability
**Pass Criteria:** Intent correct + clear yes/no answer

---

### T1-FAQ-04: Pricing
**Input:** "How much does a consultation cost?"
**Expected Intent:** `faq`
**Expected Data:** None
**Expected Response Pattern:** Should state the price
**Pass Criteria:** Intent correct + price information included

---

### T1-FAQ-05: Multiple Questions
**Input:** "What are your hours and do you accept walk-ins?"
**Expected Intent:** `faq`
**Expected Data:** None
**Expected Response Pattern:** Should answer both questions or address them sequentially
**Pass Criteria:** Intent correct + both questions acknowledged

---

## Booking Tests (8 cases)

### T2-BOOK-01: Complete Booking in One Message
**Input:** "I'd like to book an appointment for tomorrow at 3 PM. My name is Raj Kumar and my number is +919876543210."
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "name": "Raj Kumar",
  "phone": "+919876543210",
  "date": "2025-12-01",
  "time": "15:00"
}
```
**Expected Response Pattern:** Confirmation with all details repeated
**Pass Criteria:** All 4 fields extracted correctly + confirmation message

---

### T2-BOOK-02: Booking - No Details
**Input:** "I need an appointment."
**Expected Intent:** `booking`
**Expected Data:** None yet
**Expected Response Pattern:** Should ask for date first
**Pass Criteria:** Intent correct + asks ONE specific question

---

### T2-BOOK-03: Booking - Progressive Collection (Date First)
**Input:** "Can I come in on Friday?"
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "date": "2025-12-06"
}
```
**Expected Response Pattern:** Should ask for time next
**Pass Criteria:** Date extracted + asks for time

---

### T2-BOOK-04: Booking - Progressive Collection (Time Provided)
**Context:** Previous message established date
**Input:** "2 PM works for me."
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "time": "14:00"
}
```
**Expected Response Pattern:** Should ask for name next
**Pass Criteria:** Time extracted + asks for name

---

### T2-BOOK-05: Booking - Progressive Collection (Name Provided)
**Context:** Date and time already collected
**Input:** "My name is Priya Sharma"
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "name": "Priya Sharma"
}
```
**Expected Response Pattern:** Should ask for phone number next
**Pass Criteria:** Name extracted + asks for phone

---

### T2-BOOK-06: Booking - Progressive Collection (Phone Provided)
**Context:** Name, date, time already collected
**Input:** "+919123456789"
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "phone": "+919123456789"
}
```
**Expected Response Pattern:** Should confirm complete booking with all details
**Pass Criteria:** Phone extracted + full booking confirmation

---

### T2-BOOK-07: Booking - Natural Language Date
**Input:** "I want to book for next Tuesday at 10 in the morning."
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "date": "2025-12-03",
  "time": "10:00"
}
```
**Expected Response Pattern:** Should ask for name
**Pass Criteria:** Date and time correctly parsed from natural language

---

### T2-BOOK-08: Booking - Relative Date
**Input:** "Book me for the day after tomorrow at 4:30 PM. Name is Arjun, phone 9988776655."
**Expected Intent:** `booking`
**Expected Data:** 
```json
{
  "name": "Arjun",
  "phone": "+919988776655",
  "date": "2025-12-02",
  "time": "16:30"
}
```
**Expected Response Pattern:** Full confirmation
**Pass Criteria:** All fields correct, phone number formatted with +91

---

## Urgent Tests (4 cases)

### T3-URG-01: Explicit Emergency
**Input:** "This is an emergency, I need help immediately!"
**Expected Intent:** `urgent`
**Expected Data:** 
```json
{
  "issue_summary": "emergency requiring immediate help"
}
```
**Expected Response Pattern:** Should acknowledge urgency and promise owner callback
**Pass Criteria:** Intent correct + empathetic response + owner callback mentioned

---

### T3-URG-02: Complaint
**Input:** "I'm very upset about the service I received yesterday. Your technician was rude and unprofessional."
**Expected Intent:** `urgent`
**Expected Data:** 
```json
{
  "issue_summary": "complaint about rude technician"
}
```
**Expected Response Pattern:** Apologize, acknowledge issue, promise owner will call
**Pass Criteria:** Intent correct + appropriate empathy + escalation

---

### T3-URG-03: Angry Tone
**Input:** "This is ridiculous! I've been waiting for hours and nobody called me back!"
**Expected Intent:** `urgent`
**Expected Data:** 
```json
{
  "issue_summary": "angry about long wait and no callback"
}
```
**Expected Response Pattern:** De-escalate, apologize, promise immediate attention
**Pass Criteria:** Intent correct + calming response

---

### T3-URG-04: Complex Technical Issue
**Input:** "The equipment you installed is malfunctioning and causing problems. I need someone to look at this urgently."
**Expected Intent:** `urgent`
**Expected Data:** 
```json
{
  "issue_summary": "installed equipment malfunctioning"
}
```
**Expected Response Pattern:** Acknowledge technical issue, promise expert callback
**Pass Criteria:** Intent correct + assurance of technical help

---

## Other/Ambiguous Tests (3 cases)

### T4-OTH-01: Unclear Request
**Input:** "Hi, I was just calling about stuff."
**Expected Intent:** `other`
**Expected Data:** None
**Expected Response Pattern:** Should ask for clarification on what specifically they need
**Pass Criteria:** Intent correct + helpful clarifying question

---

### T4-OTH-02: Small Talk
**Input:** "How's the weather there?"
**Expected Intent:** `other`
**Expected Data:** None
**Expected Response Pattern:** Brief polite response + redirect to how Zylin can help
**Pass Criteria:** Intent correct + professional redirect

---

### T4-OTH-03: Wrong Number
**Input:** "Is this the pizza place?"
**Expected Intent:** `other`
**Expected Data:** None
**Expected Response Pattern:** Politely inform wrong number + state actual business
**Pass Criteria:** Intent correct + helpful correction

---

## Multi-Turn Conversation Tests

### T5-CONV-01: FAQ to Booking
**Turn 1:** "What services do you offer?"
**Expected:** `faq` - list services

**Turn 2:** "Great, I'd like to book a consultation."
**Expected:** `booking` - start collecting details

**Pass Criteria:** Context maintained, smooth transition between intents

---

### T5-CONV-02: Booking with Clarification
**Turn 1:** "I want an appointment tomorrow."
**Expected:** `booking` - ask for time

**Turn 2:** "Wait, actually I meant next Monday, not tomorrow."
**Expected:** `booking` - update date, continue with time

**Pass Criteria:** Handles correction gracefully, updates data

---

### T5-CONV-03: Interruption Handling
**Turn 1:** "Can I book for—actually, first, what are your prices?"
**Expected:** `faq` - answer pricing

**Turn 2:** "OK thanks, so about that booking..."
**Expected:** `booking` - resume booking flow

**Pass Criteria:** Handles interruption, returns to original intent

---

## Test Execution Guide

### Manual Testing Process
1. Set up business context (sample clinic data)
2. Initialize LLM with system prompt
3. For each test case:
   - Send input message
   - Capture response
   - Verify intent classification
   - Verify extracted data (if applicable)
   - Check response pattern match
4. Record pass/fail for each case
5. Calculate accuracy: (passed / total) × 100%

### Success Threshold
- **Minimum:** 18/20 (90%) tests passing
- **Target:** 19/20 (95%) tests passing
- **Excellent:** 20/20 (100%) tests passing

### Failure Analysis
If test fails:
1. Check if intent was misclassified
2. Check if data extraction was incorrect
3. Check if response was inappropriate
4. Document specific failure mode
5. Iterate on system prompt or add examples

### Regression Testing
- Run full suite after any prompt changes
- Track performance over time
- Maintain test result history

---

## Test Data Setup

### Sample Business Context for Testing
```json
{
  "business_name": "HealthFirst Clinic",
  "business_type": "healthcare",
  "phone": "+911234567890",
  "address": "123 MG Road, Bangalore, Karnataka 560001",
  "hours": {
    "monday": "9:00 AM - 6:00 PM",
    "tuesday": "9:00 AM - 6:00 PM",
    "wednesday": "9:00 AM - 6:00 PM",
    "thursday": "9:00 AM - 6:00 PM",
    "friday": "9:00 AM - 6:00 PM",
    "saturday": "10:00 AM - 2:00 PM",
    "sunday": "Closed"
  },
  "services": [
    "General consultation",
    "Blood tests",
    "X-ray",
    "ECG",
    "Vaccinations"
  ],
  "pricing": {
    "consultation": "₹500",
    "blood_test": "₹800-2000",
    "xray": "₹1200",
    "ecg": "₹600",
    "vaccination": "₹300-1500"
  },
  "owner_phone": "+919876543210"
}
```

### Current Date for Testing
**Test Date:** November 30, 2025 (Saturday)
- "tomorrow" = December 1, 2025 (Sunday)
- "day after tomorrow" = December 2, 2025 (Monday)
- "next Tuesday" = December 3, 2025
- "Friday" = December 6, 2025
- "next Monday" = December 7, 2025
