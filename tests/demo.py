"""
End-to-End Demo Script
Demonstrates full Zylin pipeline: Audio → ASR → LLM → TTS → Booking → WhatsApp
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.orchestrator.session_manager import ConversationOrchestrator
from services.bookings.store import BookingTool
from services.notifications.whatsapp import WhatsAppService
from services.logging.log_store import CallLogStore, create_log_from_session
import os


async def demo_faq_scenario():
    """Demo: Simple FAQ about hours."""
    print("\n" + "🎬 " + "="*58)
    print("   DEMO 1: FAQ SCENARIO")
    print("="*60 + "\n")
    
    orchestrator = ConversationOrchestrator(generate_audio=False)
    session = orchestrator.create_session(caller_phone="+919876543210")
    
    # Simulate conversation
    print("📞 Caller asks about business hours\n")
    
    result = await orchestrator.process_text_turn(
        "What time are you open today?",
        session.session_id
    )
    
    print(f"\n✅ Intent: {result.intent}")
    print(f"🤖 Response: {result.bot_text}")
    
    # Log the call
    log_store = CallLogStore()
    session_data = orchestrator.get_session_summary(session.session_id)
    log = create_log_from_session(session_data, summary="Customer asked about hours")
    log_store.create_log(log)
    
    print(f"\n📝 Call logged: {log.session_id}")
    print("\n✅ Demo 1 Complete!\n")


async def demo_booking_scenario():
    """Demo: Complete booking flow."""
    print("\n" + "🎬 " + "="*58)
    print("   DEMO 2: BOOKING SCENARIO")
    print("="*60 + "\n")
    
    orchestrator = ConversationOrchestrator(generate_audio=False)
    booking_tool = BookingTool()
    whatsapp = WhatsAppService(dry_run=True)
    
    session = orchestrator.create_session(caller_phone="+919123456789")
    
    # Multi-turn booking conversation
    print("📞 Caller wants to book appointment\n")
    
    # Turn 1
    print("--- Turn 1 ---")
    result = await orchestrator.process_text_turn(
        "I need an appointment tomorrow at 3 PM",
        session.session_id
    )
    print(f"🤖 {result.bot_text}\n")
    
    # Turn 2
    print("--- Turn 2 ---")
    result = await orchestrator.process_text_turn(
        "My name is Priya Sharma",
        session.session_id
    )
    print(f"🤖 {result.bot_text}\n")
    
    # Turn 3
    print("--- Turn 3 ---")
    result = await orchestrator.process_text_turn(
        "+919123456789",
        session.session_id
    )
    print(f"🤖 {result.bot_text}\n")
    
    # Check if booking is complete
    if result.booking_complete:
        print("✅ Booking complete! Creating appointment...")
        
        # Create booking
        booking_data = result.extracted_data
        booking = booking_tool.create_booking_from_conversation(
            booking_data,
            session.session_id
        )
        
        print(f"📅 Booking created: ID={booking.booking_id}")
        print(f"   Customer: {booking.customer_name}")
        print(f"   Date: {booking.appointment_date}")
        print(f"   Time: {booking.appointment_time}")
        
        # Send WhatsApp confirmation
        whatsapp.send_booking_confirmation(
            customer_name=booking.customer_name,
            customer_phone=booking.customer_phone,
            appointment_date=booking.appointment_date,
            appointment_time=booking.appointment_time,
            business_name="HealthFirst Clinic"
        )
        
        # Log the call
        log_store = CallLogStore()
        session_data = orchestrator.get_session_summary(session.session_id)
        log = create_log_from_session(
            session_data,
            booking_id=booking.booking_id,
            summary="Customer booked appointment"
        )
        log_store.create_log(log)
        
        print(f"\n📝 Call logged: {log.session_id}")
    
    print("\n✅ Demo 2 Complete!\n")


async def demo_urgent_scenario():
    """Demo: Urgent escalation."""
    print("\n" + "🎬 " + "="*58)
    print("   DEMO 3: URGENT ESCALATION")
    print("="*60 + "\n")
    
    orchestrator = ConversationOrchestrator(generate_audio=False)
    whatsapp = WhatsAppService(dry_run=True)
    
    session = orchestrator.create_session(caller_phone="+919988776655")
    
    print("📞 Caller has an urgent issue\n")
    
    result = await orchestrator.process_text_turn(
        "This is an emergency! I need immediate help with a serious problem.",
        session.session_id
    )
    
    print(f"\n✅ Intent: {result.intent}")
    print(f"🤖 Response: {result.bot_text}")
    
    if result.needs_escalation:
        print("\n🚨 Escalating to owner...")
        
        # Send alert to owner
        whatsapp.send_urgent_alert(
            owner_phone="+919876543210",
            caller_phone="+919988776655",
            issue_summary="Emergency - serious problem requiring immediate attention",
            business_name="HealthFirst Clinic"
        )
        
        # Log the call
        log_store = CallLogStore()
        session_data = orchestrator.get_session_summary(session.session_id)
        log = create_log_from_session(session_data, summary="Urgent escalation")
        log_store.create_log(log)
        
        print(f"\n📝 Call logged: {log.session_id}")
    
    print("\n✅ Demo 3 Complete!\n")


async def demo_with_audio():
    """Demo: Full pipeline with audio files (if available)."""
    print("\n" + "🎬 " + "="*58)
    print("   DEMO 4: FULL AUDIO PIPELINE")
    print("="*60 + "\n")
    
    # Check if audio files exist
    audio_dir = Path("tests/audio")
    audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3"))
    
    if not audio_files:
        print("⚠️  No audio files found in tests/audio/")
        print("💡 Add .wav or .mp3 files to test full audio pipeline")
        print("   Skipping audio demo.\n")
        return
    
    print(f"Found {len(audio_files)} audio file(s)\n")
    
    orchestrator = ConversationOrchestrator(generate_audio=True)
    
    # Use first audio file
    audio_file = str(audio_files[0])
    print(f"🎤 Processing: {Path(audio_file).name}\n")
    
    session = orchestrator.create_session(caller_phone="+919876543210")
    
    try:
        result = await orchestrator.process_audio_turn(
            audio_file,
            session.session_id,
            output_audio_dir="tests/tts"
        )
        
        print(f"\n✅ Audio pipeline complete!")
        print(f"📝 Transcription: {result.user_text}")
        print(f"🤖 Response: {result.bot_text}")
        print(f"📊 Intent: {result.intent}")
        if result.bot_audio_path:
            print(f"🔊 Audio saved: {result.bot_audio_path}")
        
    except Exception as e:
        print(f"❌ Error in audio pipeline: {e}")
    
    print("\n✅ Demo 4 Complete!\n")


async def show_analytics():
    """Show analytics summary."""
    print("\n" + "📊 " + "="*58)
    print("   ANALYTICS SUMMARY")
    print("="*60 + "\n")
    
    from datetime import date
    log_store = CallLogStore()
    
    stats = log_store.get_daily_stats(date.today().isoformat())
    
    print(f"Today's Stats:")
    print(f"  • Total Calls: {stats['total_calls']}")
    print(f"  • FAQ: {stats['faq_count']}")
    print(f"  • Bookings: {stats['booking_count']}")
    print(f"  • Urgent: {stats['urgent_count']}")
    print(f"  • Bookings Created: {stats['bookings_created']}")
    print(f"  • Escalations: {stats['escalations']}")
    
    # Show bookings
    from services.bookings.store import BookingStore
    booking_store = BookingStore()
    bookings = booking_store.list_bookings(limit=10)
    
    if bookings:
        print(f"\n📅 Recent Bookings:")
        for booking in bookings[:5]:
            print(f"  • {booking.customer_name} - {booking.appointment_date} at {booking.appointment_time}")
    
    print("\n" + "="*60 + "\n")


async def main():
    """Run all demos."""
    print("\n" + "🎯 " + "="*58)
    print("   ZYLIN END-TO-END DEMO")
    print("   Demonstrating complete MVP functionality")
    print("="*60)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not set")
        print("💡 Set it in .env file first")
        return
    
    try:
        # Run all scenarios
        await demo_faq_scenario()
        await asyncio.sleep(1)
        
        await demo_booking_scenario()
        await asyncio.sleep(1)
        
        await demo_urgent_scenario()
        await asyncio.sleep(1)
        
        await demo_with_audio()
        await asyncio.sleep(1)
        
        # Show analytics
        await show_analytics()
        
        print("\n🎉 All demos completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Check data/zylin.db for stored data")
        print("   2. Run: python scripts/daily_report.py")
        print("   3. Test API: python main.py")
        print("   4. Add real audio files to tests/audio/")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
