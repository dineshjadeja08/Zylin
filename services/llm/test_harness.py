"""
Test harness for Zylin LLM brain.
Run text-only conversations to validate intent classification and response quality.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.llm.brain import ZylinBrain, ConversationResponse
from datetime import datetime


class TestHarness:
    """Interactive test harness for the LLM brain."""
    
    def __init__(self):
        self.brain = ZylinBrain()
        self.conversation_history: list[dict] = []
        self.test_results: list[dict] = []
    
    def display_response(self, response: ConversationResponse):
        """Display response in a formatted way."""
        print("\n" + "="*60)
        print(f"🤖 ZYLIN: {response.message}")
        print(f"\n📊 Intent: {response.intent}")
        
        if response.extracted_data.model_dump(exclude_none=True):
            print(f"📝 Extracted Data:")
            for key, value in response.extracted_data.model_dump(exclude_none=True).items():
                print(f"   • {key}: {value}")
        
        if response.booking_complete:
            print("✅ Booking Complete!")
        
        if response.needs_escalation:
            print("🚨 Needs Escalation!")
        
        print("="*60 + "\n")
    
    async def run_interactive(self):
        """Run interactive chat session."""
        print("\n" + "🎯 " + "="*58)
        print("   ZYLIN INTERACTIVE TEST HARNESS")
        print("="*60)
        print("Type your messages as a caller. Type 'quit' to exit.")
        print("Type 'reset' to start a new conversation.")
        print("Type 'history' to see conversation history.")
        print("="*60 + "\n")
        
        while True:
            user_input = input("👤 YOU: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!\n")
                break
            
            if user_input.lower() == 'reset':
                self.conversation_history = []
                print("\n🔄 Conversation reset.\n")
                continue
            
            if user_input.lower() == 'history':
                print("\n📜 Conversation History:")
                for msg in self.conversation_history:
                    role = "YOU" if msg["role"] == "user" else "ZYLIN"
                    print(f"   {role}: {msg['content']}")
                print()
                continue
            
            # Process message
            response = await self.brain.process_message(
                user_input,
                self.conversation_history
            )
            
            # Update history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response.message
            })
            
            # Display response
            self.display_response(response)
    
    async def run_test_case(
        self,
        test_id: str,
        input_message: str,
        expected_intent: str,
        expected_data: dict = None,
        conversation_context: list[dict] = None
    ) -> bool:
        """
        Run a single test case.
        
        Returns:
            True if test passes, False otherwise
        """
        print(f"\n🧪 Running Test: {test_id}")
        print(f"   Input: {input_message}")
        
        response = await self.brain.process_message(
            input_message,
            conversation_context or []
        )
        
        # Check intent
        intent_match = response.intent == expected_intent
        
        # Check extracted data if provided
        data_match = True
        if expected_data:
            extracted = response.extracted_data.model_dump(exclude_none=True)
            for key, expected_value in expected_data.items():
                actual_value = extracted.get(key)
                if actual_value != expected_value:
                    data_match = False
                    print(f"   ❌ Data mismatch - {key}: expected '{expected_value}', got '{actual_value}'")
        
        # Overall pass/fail
        passed = intent_match and data_match
        
        if passed:
            print(f"   ✅ PASSED")
        else:
            print(f"   ❌ FAILED")
            if not intent_match:
                print(f"      Expected intent: {expected_intent}, got: {response.intent}")
        
        print(f"   Response: {response.message}\n")
        
        self.test_results.append({
            "test_id": test_id,
            "passed": passed,
            "expected_intent": expected_intent,
            "actual_intent": response.intent,
            "response": response.message
        })
        
        return passed
    
    async def run_automated_tests(self):
        """Run all automated test cases from test_llm_brain.md."""
        print("\n" + "🧪 " + "="*58)
        print("   RUNNING AUTOMATED TEST SUITE")
        print("="*60 + "\n")
        
        # FAQ Tests
        await self.run_test_case(
            "T1-FAQ-01",
            "What time are you open today?",
            "faq"
        )
        
        await self.run_test_case(
            "T1-FAQ-02",
            "Where is your clinic located?",
            "faq"
        )
        
        await self.run_test_case(
            "T1-FAQ-03",
            "Do you do blood tests?",
            "faq"
        )
        
        await self.run_test_case(
            "T1-FAQ-04",
            "How much does a consultation cost?",
            "faq"
        )
        
        # Booking Tests
        await self.run_test_case(
            "T2-BOOK-01",
            "I'd like to book an appointment for tomorrow at 3 PM. My name is Raj Kumar and my number is +919876543210.",
            "booking",
            {
                "name": "Raj Kumar",
                "phone": "+919876543210",
                "time": "15:00"
            }
        )
        
        await self.run_test_case(
            "T2-BOOK-02",
            "I need an appointment.",
            "booking"
        )
        
        await self.run_test_case(
            "T2-BOOK-08",
            "Book me for the day after tomorrow at 4:30 PM. Name is Arjun, phone 9988776655.",
            "booking",
            {
                "name": "Arjun",
                "phone": "+919988776655",
                "time": "16:30"
            }
        )
        
        # Urgent Tests
        await self.run_test_case(
            "T3-URG-01",
            "This is an emergency, I need help immediately!",
            "urgent"
        )
        
        await self.run_test_case(
            "T3-URG-02",
            "I'm very upset about the service I received yesterday. Your technician was rude and unprofessional.",
            "urgent"
        )
        
        # Other Tests
        await self.run_test_case(
            "T4-OTH-01",
            "Hi, I was just calling about stuff.",
            "other"
        )
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        accuracy = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Accuracy: {accuracy:.1f}%\n")
        
        if accuracy >= 90:
            print("✅ SUCCESS: Brain passes acceptance criteria (≥90%)")
        else:
            print("❌ FAILURE: Brain needs improvement")
        
        print("\nFailed Tests:")
        for result in self.test_results:
            if not result["passed"]:
                print(f"  • {result['test_id']}: Expected {result['expected_intent']}, got {result['actual_intent']}")
        
        print("="*60 + "\n")


async def main():
    """Main entry point."""
    harness = TestHarness()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run automated tests
        await harness.run_automated_tests()
    else:
        # Run interactive mode
        await harness.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())
