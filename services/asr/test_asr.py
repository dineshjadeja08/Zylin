"""
ASR Testing Script
Test audio transcription with various file formats and accents.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.asr.transcribe import ASRService, transcribe
import os


async def test_single_file(file_path: str, language: str = None):
    """Test transcription of a single audio file."""
    print(f"\n{'='*60}")
    print(f"📁 File: {Path(file_path).name}")
    print(f"{'='*60}")
    
    asr = ASRService()
    
    try:
        result = await asr.transcribe_file(file_path, language=language)
        
        print(f"\n✅ Transcription successful!")
        print(f"\n📝 Text:\n{result.text}")
        
        if result.language:
            print(f"\n🌐 Detected Language: {result.language}")
        
        if result.duration:
            print(f"\n⏱️  Duration: {result.duration:.2f} seconds")
        
        print(f"\n{'='*60}\n")
        
        return result
        
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        print(f"💡 Tip: Place test audio files in tests/audio/ directory")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def test_all_files_in_directory(directory: str = "tests/audio"):
    """Test all audio files in a directory."""
    audio_dir = Path(directory)
    
    if not audio_dir.exists():
        print(f"❌ Directory not found: {directory}")
        print(f"💡 Creating directory: {directory}")
        audio_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory created. Please add .wav or .mp3 files to test.")
        return
    
    # Supported audio formats
    audio_extensions = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"}
    audio_files = [
        f for f in audio_dir.iterdir()
        if f.is_file() and f.suffix.lower() in audio_extensions
    ]
    
    if not audio_files:
        print(f"⚠️  No audio files found in {directory}")
        print(f"💡 Supported formats: {', '.join(audio_extensions)}")
        print(f"💡 Add test recordings to: {audio_dir.absolute()}")
        return
    
    print(f"\n🎯 Testing {len(audio_files)} audio file(s)\n")
    
    results = []
    for audio_file in audio_files:
        result = await test_single_file(str(audio_file))
        if result:
            results.append({
                "file": audio_file.name,
                "text": result.text,
                "language": result.language,
                "duration": result.duration
            })
        
        # Small delay between files
        await asyncio.sleep(0.5)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 TRANSCRIPTION SUMMARY")
    print(f"{'='*60}\n")
    print(f"Total files processed: {len(results)}/{len(audio_files)}")
    print(f"Success rate: {len(results)/len(audio_files)*100:.1f}%\n")
    
    if results:
        print("Results:")
        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['file']}")
            print(f"   Text: {r['text'][:80]}..." if len(r['text']) > 80 else f"   Text: {r['text']}")
            if r['language']:
                print(f"   Language: {r['language']}")
    
    print(f"\n{'='*60}\n")


async def test_with_prompt():
    """Test transcription with prompt for better accuracy."""
    print("\n🎯 Testing with context prompt")
    print("This helps Whisper understand domain-specific terms.\n")
    
    # Example: Medical context
    prompt = "This is a call to a medical clinic about booking appointments and health services."
    
    audio_dir = Path("tests/audio")
    audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3"))
    
    if audio_files:
        file_path = str(audio_files[0])
        asr = ASRService()
        
        print("Without prompt:")
        result1 = await asr.transcribe_file(file_path)
        print(f"  {result1.text}\n")
        
        print("With prompt:")
        result2 = await asr.transcribe_file(file_path, prompt=prompt)
        print(f"  {result2.text}\n")
        
        if result1.text != result2.text:
            print("📊 Prompt changed the transcription (may be more accurate)")
        else:
            print("📊 Prompt didn't change transcription (text was already clear)")


async def interactive_mode():
    """Interactive mode for testing individual files."""
    print("\n" + "🎤 " + "="*58)
    print("   ASR INTERACTIVE TEST MODE")
    print("="*60)
    print("Commands:")
    print("  test <filename>   - Transcribe a specific file")
    print("  test all          - Transcribe all files in tests/audio/")
    print("  test prompt       - Test with context prompt")
    print("  quit              - Exit")
    print("="*60 + "\n")
    
    while True:
        try:
            cmd = input("🎤 ASR> ").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() == "quit":
                print("\n👋 Goodbye!\n")
                break
            
            parts = cmd.split(maxsplit=1)
            
            if parts[0].lower() == "test":
                if len(parts) == 1 or parts[1].lower() == "all":
                    await test_all_files_in_directory()
                elif parts[1].lower() == "prompt":
                    await test_with_prompt()
                else:
                    # Test specific file
                    file_path = parts[1]
                    if not file_path.startswith("tests/audio/"):
                        file_path = f"tests/audio/{file_path}"
                    await test_single_file(file_path)
            else:
                print("❌ Unknown command. Use: test <filename>, test all, test prompt, or quit")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            await test_all_files_in_directory()
        elif sys.argv[1] == "prompt":
            await test_with_prompt()
        else:
            # Test specific file
            await test_single_file(sys.argv[1])
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
