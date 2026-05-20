"""
Quick patch to add cleanup code to app.py
Run from repo root: python scripts/patch_cleanup.py
"""

import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_app = os.path.join(_ROOT, "app.py")

# Read the file
with open(_app, "r") as f:
    content = f.read()

# Find and replace the cleanup section
old_cleanup = '''    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        if stream_sid and stream_sid in gemini_sessions:
            if gemini_sessions[stream_sid]:
                await gemini_sessions[stream_sid].disconnect()
            del gemini_sessions[stream_sid]
        logger.info("🔌 Connection closed")'''

new_cleanup = '''    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        if call_sid:
            with get_db() as db:
                call_service.update_call_status(db, call_sid, "failed", error_message=str(e))
    finally:
        # Stop audio recording
        if audio_recorder:
            duration = audio_recorder.stop()
            logger.info(f"⏹ Recording stopped. Duration: {duration:.2f}s")
            if call_sid and audio_recorder.filepath:
                with get_db() as db:
                    call_service.set_recording_path(db, call_sid, audio_recorder.filepath, duration)
        
        # Update call status to completed
        if call_sid:
            with get_db() as db:
                call_service.update_call_status(db, call_sid, "completed")
        
        # Cleanup Gemini session
        if stream_sid and stream_sid in gemini_sessions:
            if gemini_sessions[stream_sid]:
                await gemini_sessions[stream_sid].disconnect()
            del gemini_sessions[stream_sid]
        logger.info("🔌 Connection closed")'''

if old_cleanup in content:
    content = content.replace(old_cleanup, new_cleanup)
    with open(_app, "w") as f:
        f.write(content)
    print("✅ Patch applied successfully!")
else:
    print("❌ Could not find the target section. May already be patched or different.")
