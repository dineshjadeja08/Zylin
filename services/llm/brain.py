"""
Zylin LLM Brain Service
Handles conversation management, intent classification, and response generation.
"""

from typing import Optional, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import os
import json


# Response Models
class ExtractedData(BaseModel):
    """Data extracted from conversation."""
    name: Optional[str] = None
    phone: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD format
    time: Optional[str] = None  # HH:MM format
    notes: Optional[str] = None
    issue_summary: Optional[str] = None


class ConversationResponse(BaseModel):
    """LLM response with intent and extracted data."""
    intent: Literal["faq", "booking", "urgent", "other"]
    message: str
    extracted_data: ExtractedData
    booking_complete: bool = False
    needs_escalation: bool = False


class BusinessContext(BaseModel):
    """Business information for context."""
    business_name: str
    business_type: str
    phone: str
    address: str
    hours: dict[str, str]
    services: list[str]
    pricing: dict[str, str]
    owner_phone: str


# Default business context (should be loaded from config/DB in production)
DEFAULT_BUSINESS_CONTEXT = BusinessContext(
    business_name=os.getenv("BUSINESS_NAME", "HealthFirst Clinic"),
    business_type="healthcare",
    phone=os.getenv("BUSINESS_PHONE", "+911234567890"),
    address=os.getenv("BUSINESS_ADDRESS", "123 MG Road, Bangalore, Karnataka 560001"),
    hours={
        "monday": "9:00 AM - 6:00 PM",
        "tuesday": "9:00 AM - 6:00 PM",
        "wednesday": "9:00 AM - 6:00 PM",
        "thursday": "9:00 AM - 6:00 PM",
        "friday": "9:00 AM - 6:00 PM",
        "saturday": "10:00 AM - 2:00 PM",
        "sunday": "Closed",
    },
    services=[
        "General consultation",
        "Blood tests",
        "X-ray",
        "ECG",
        "Vaccinations"
    ],
    pricing={
        "consultation": "₹500",
        "blood_test": "₹800-2000",
        "xray": "₹1200",
        "ecg": "₹600",
        "vaccination": "₹300-1500"
    },
    owner_phone=os.getenv("OWNER_PHONE", "+919876543210")
)


class ZylinBrain:
    """
    Core LLM brain for Zylin.
    Manages conversations, classifies intents, and extracts structured data.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        business_context: Optional[BusinessContext] = None
    ):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.business_context = business_context or DEFAULT_BUSINESS_CONTEXT
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt with business context."""
        today = datetime.now().strftime("%A, %B %d, %Y")
        
        return f"""You are Zylin, a professional AI receptionist for {self.business_context.business_name}. Today is {today}.

**Business Information:**
- Name: {self.business_context.business_name}
- Type: {self.business_context.business_type}
- Phone: {self.business_context.phone}
- Address: {self.business_context.address}

**Hours:**
{json.dumps(self.business_context.hours, indent=2)}

**Services:**
{', '.join(self.business_context.services)}

**Pricing:**
{json.dumps(self.business_context.pricing, indent=2)}

**Your Role:**
1. Answer caller questions (FAQs) clearly and concisely
2. Book appointments by collecting necessary information
3. Identify urgent matters that need immediate owner attention
4. Be polite, friendly, and professional at all times

**Behavior Guidelines:**
- Keep responses brief (1-3 sentences maximum)
- Ask ONE question at a time if information is missing
- Confirm details before finalizing bookings
- Use natural, conversational language
- Never make up information you don't have
- If you can't help, politely say so and offer to have the owner call back

**Information Collection for Bookings:**
You MUST collect these details before confirming an appointment:
1. Customer name
2. Phone number (add +91 prefix if missing for Indian numbers)
3. Preferred date (convert relative dates like "tomorrow" to actual dates)
4. Preferred time (convert to 24-hour format HH:MM)

If any detail is missing, ask for it specifically.

**Intent Classification:**
Based on the conversation, you must classify into one of these:
- `faq`: Simple information requests (hours, location, services, pricing)
- `booking`: Appointment scheduling requests
- `urgent`: Emergency situations, complaints, or complex issues needing owner attention
- `other`: General conversation or unclear intent

**Response Format:**
You MUST respond in JSON format with this structure:
{{
  "intent": "faq|booking|urgent|other",
  "message": "your natural language response to the caller",
  "extracted_data": {{
    "name": "if mentioned",
    "phone": "if mentioned, with +91 prefix",
    "date": "YYYY-MM-DD format if mentioned",
    "time": "HH:MM 24-hour format if mentioned",
    "notes": "any additional context",
    "issue_summary": "brief summary if urgent"
  }},
  "booking_complete": true if all 4 booking fields are collected,
  "needs_escalation": true if urgent
}}

**Date Parsing Examples:**
- "tomorrow" → {(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")}
- "day after tomorrow" → {(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")}
- "next Tuesday" → calculate the next Tuesday from today
- "Friday" → calculate the next Friday from today

Always respond naturally in the "message" field while providing structured data in the other fields.
"""
    
    async def process_message(
        self,
        user_message: str,
        conversation_history: Optional[list[dict]] = None
    ) -> ConversationResponse:
        """
        Process a user message and return structured response.
        
        Args:
            user_message: The caller's message
            conversation_history: Previous messages in the conversation
            
        Returns:
            ConversationResponse with intent, message, and extracted data
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Call OpenAI with JSON mode
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.4,
                max_tokens=500
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content
            response_data = json.loads(response_text)
            
            # Validate and structure response
            return ConversationResponse(
                intent=response_data.get("intent", "other"),
                message=response_data.get("message", "I apologize, I didn't quite understand that. Could you please rephrase?"),
                extracted_data=ExtractedData(**response_data.get("extracted_data", {})),
                booking_complete=response_data.get("booking_complete", False),
                needs_escalation=response_data.get("needs_escalation", False)
            )
            
        except Exception as e:
            # Fallback response on error
            print(f"Error processing message: {e}")
            return ConversationResponse(
                intent="other",
                message="I apologize, I'm having trouble processing that right now. Could you please try again?",
                extracted_data=ExtractedData(),
                booking_complete=False,
                needs_escalation=False
            )
    
    async def get_conversation_summary(
        self,
        conversation_history: list[dict]
    ) -> str:
        """Generate a brief summary of the conversation for logging."""
        try:
            messages = [
                {"role": "system", "content": "Summarize this conversation in 1-2 sentences."},
                *conversation_history
            ]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Conversation summary unavailable"
