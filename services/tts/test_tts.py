"""
TTS Testing Script
Test text-to-speech synthesis with various voices and texts.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.tts.synthesize import TTSService, Voice
import os


# Test phrases for Zylin
TEST_PHRASES = {
    "greeting": "Hello! I'm Zylin, your AI receptionist. How can I help you today?",
    "hours": "We're open Monday to Friday from 9 AM to 6 PM, and Saturday from 10 AM to 2 PM. We're closed on Sundays.",
    "booking_confirm": "Perfect! I've booked your appointment for tomorrow at 3 PM. You'll receive a WhatsApp confirmation shortly.",
    "booking_collect": "I'd be happy to help you book an appointment. What date works best for you?",
    "urgent": "I understand this is urgent. I'm alerting the owner immediately, and they will call you back within the hour.",
    "farewell": "Thank you for calling. Have a wonderful day!",
    "clarification": "I'm sorry, I didn't quite understand that. Could you please rephrase your request?",
}


async def test_single_voice(voice: Voice, text: str, output_dir: str = "tests/tts"):
    """Test a single voice with given text."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    filename = f"{voice}_{list(TEST_PHRASES.keys())[list(TEST_PHRASES.values()).index(text)] if text in TEST_PHRASES.values() else 'custom'}.mp3"
    file_path = output_path / filename
    
    print(f"\n🔊 Generating: {voice}")
    print(f"📝 Text: {text[:80]}..." if len(text) > 80 else f"📝 Text: {text}")
    
    tts = TTSService(voice=voice)
    
    try:
        result = await tts.synthesize_to_file(
            text=text,
            output_path=str(file_path)
        )
        
        print(f"✅ Generated: {file_path.name}")
        if result.duration_estimate:
            print(f"⏱️  Estimated duration: {result.duration_estimate:.1f}s")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def test_all_voices():
    """Test all available voices with a sample phrase."""
    print("\n" + "🎙️ " + "="*58)
    print("   TESTING ALL VOICES")
    print("="*60 + "\n")
    
    voices: list[Voice] = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    test_text = TEST_PHRASES["greeting"]
    
    print(f"Testing {len(voices)} voices with greeting phrase\n")
    
    results = []
    for voice in voices:
        result = await test_single_voice(voice, test_text)
        if result:
            results.append(voice)
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully generated {len(results)}/{len(voices)} audio files")
    print(f"📁 Files saved to: tests/tts/")
    print(f"{'='*60}\n")


async def test_all_phrases(voice: Voice = "nova"):
    """Test all predefined phrases with a single voice."""
    print(f"\n🎙️  Testing all phrases with voice: {voice}\n")
    
    results = []
    for key, text in TEST_PHRASES.items():
        result = await test_single_voice(voice, text)
        if result:
            results.append(key)
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"✅ Generated {len(results)}/{len(TEST_PHRASES)} phrase variations")
    print(f"📁 Files saved to: tests/tts/")
    print(f"{'='*60}\n")


async def test_speed_variations():
    """Test different speech speeds."""
    print("\n🎙️  Testing speed variations\n")
    
    speeds = [0.75, 1.0, 1.25, 1.5]
    text = TEST_PHRASES["greeting"]
    voice: Voice = "nova"
    
    for speed in speeds:
        output_path = f"tests/tts/nova_speed_{speed}.mp3"
        
        print(f"\n🔊 Speed: {speed}x")
        
        tts = TTSService(voice=voice, speed=speed)
        result = await tts.synthesize_to_file(text, output_path)
        
        print(f"✅ Generated: {Path(output_path).name}")
        if result.duration_estimate:
            print(f"⏱️  Estimated duration: {result.duration_estimate:.1f}s")
        
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"✅ Generated {len(speeds)} speed variations")
    print(f"💡 Listen to compare: slower vs faster speech")
    print(f"{'='*60}\n")


async def interactive_mode():
    """Interactive mode for testing custom text."""
    print("\n" + "🎙️ " + "="*58)
    print("   TTS INTERACTIVE TEST MODE")
    print("="*60)
    print("Commands:")
    print("  synth <text>      - Synthesize custom text")
    print("  voice <name>      - Change voice (alloy, echo, fable, onyx, nova, shimmer)")
    print("  speed <number>    - Change speed (0.25-4.0)")
    print("  test voices       - Test all voices")
    print("  test phrases      - Test all predefined phrases")
    print("  test speed        - Test speed variations")
    print("  list              - List predefined phrases")
    print("  quit              - Exit")
    print("="*60 + "\n")
    
    current_voice: Voice = "nova"
    current_speed = 1.0
    counter = 1
    
    print(f"Current settings: voice={current_voice}, speed={current_speed}x\n")
    
    while True:
        try:
            cmd = input("🎙️  TTS> ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() == "quit":
                print("\n👋 Goodbye!\n")
                break
            
            parts = cmd.split(maxsplit=1)
            command = parts[0].lower()
            
            if command == "synth" and len(parts) > 1:
                text = parts[1]
                output_path = f"tests/tts/custom_{counter}.mp3"
                
                tts = TTSService(voice=current_voice, speed=current_speed)
                result = await tts.synthesize_to_file(text, output_path)
                
                print(f"✅ Generated: {Path(output_path).name}")
                print(f"🔊 Voice: {current_voice}, Speed: {current_speed}x")
                
                counter += 1
            
            elif command == "voice" and len(parts) > 1:
                new_voice = parts[1].lower()
                if new_voice in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
                    current_voice = new_voice  # type: ignore
                    print(f"✅ Voice changed to: {current_voice}")
                else:
                    print("❌ Invalid voice. Options: alloy, echo, fable, onyx, nova, shimmer")
            
            elif command == "speed" and len(parts) > 1:
                try:
                    new_speed = float(parts[1])
                    if 0.25 <= new_speed <= 4.0:
                        current_speed = new_speed
                        print(f"✅ Speed changed to: {current_speed}x")
                    else:
                        print("❌ Speed must be between 0.25 and 4.0")
                except ValueError:
                    print("❌ Invalid speed number")
            
            elif command == "test":
                if len(parts) > 1:
                    test_type = parts[1].lower()
                    if test_type == "voices":
                        await test_all_voices()
                    elif test_type == "phrases":
                        await test_all_phrases(current_voice)
                    elif test_type == "speed":
                        await test_speed_variations()
                    else:
                        print("❌ Unknown test type. Options: voices, phrases, speed")
                else:
                    print("❌ Specify test type: voices, phrases, or speed")
            
            elif command == "list":
                print("\n📝 Predefined Phrases:")
                for key, text in TEST_PHRASES.items():
                    print(f"  • {key}: {text[:60]}..." if len(text) > 60 else f"  • {key}: {text}")
                print()
            
            else:
                print("❌ Unknown command. Type 'help' to see available commands.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "voices":
            await test_all_voices()
        elif sys.argv[1] == "phrases":
            await test_all_phrases()
        elif sys.argv[1] == "speed":
            await test_speed_variations()
        else:
            print("❌ Unknown command")
            print("Usage: python test_tts.py [voices|phrases|speed]")
    else:
        # Interactive mode
        await interactive_mode()


if __name__ == "__main__":
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not set in environment")
        print("💡 Set it in .env file or export OPENAI_API_KEY=your-key")
        sys.exit(1)
    
    asyncio.run(main())
