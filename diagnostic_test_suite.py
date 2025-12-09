#!/usr/bin/env python3
"""
Comprehensive QuickStream Diagnostic Test Suite
Run this and send the complete output for analysis.

Usage: python3 diagnostic_test_suite.py > diagnostic_output.txt 2>&1
"""

import os
import sys
import subprocess
import tempfile
import time
import platform
from pathlib import Path
from datetime import datetime

# Color output for terminal (will be plain in redirected output)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_subheader(text):
    """Print a subsection header."""
    print(f"\n--- {text} ---")

def run_command(cmd, description, timeout=5, capture_output=True, check_return=False):
    """Run a command and report results verbosely."""
    print(f"\n🔍 Testing: {description}")
    print(f"   Command: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    try:
        start = time.time()
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        elapsed = time.time() - start

        print(f"   ✓ Completed in {elapsed:.2f}s")
        print(f"   Return code: {result.returncode}")

        if result.stdout and result.stdout.strip():
            print(f"   STDOUT ({len(result.stdout)} chars):")
            for line in result.stdout.strip().split('\n')[:20]:  # First 20 lines
                print(f"      {line}")
            if len(result.stdout.strip().split('\n')) > 20:
                print(f"      ... ({len(result.stdout.strip().split('\n')) - 20} more lines)")

        if result.stderr and result.stderr.strip():
            print(f"   STDERR ({len(result.stderr)} chars):")
            for line in result.stderr.strip().split('\n')[:20]:  # First 20 lines
                print(f"      {line}")
            if len(result.stderr.strip().split('\n')) > 20:
                print(f"      ... ({len(result.stderr.strip().split('\n')) - 20} more lines)")

        if check_return and result.returncode != 0:
            print(f"   ⚠ WARNING: Non-zero return code")
            return False

        return result

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        print(f"   ✗ TIMEOUT after {elapsed:.2f}s")
        return None
    except FileNotFoundError:
        print(f"   ✗ COMMAND NOT FOUND")
        return None
    except Exception as e:
        print(f"   ✗ ERROR: {type(e).__name__}: {e}")
        return None

def test_file_permissions(path):
    """Test file/directory permissions."""
    print(f"\n📁 Testing path: {path}")

    try:
        p = Path(path)
        print(f"   Exists: {p.exists()}")

        if p.exists():
            stat = p.stat()
            print(f"   Type: {'Directory' if p.is_dir() else 'File'}")
            print(f"   Permissions: {oct(stat.st_mode)[-3:]}")
            print(f"   Owner UID: {stat.st_uid}")
            print(f"   Group GID: {stat.st_gid}")
            print(f"   Readable: {os.access(path, os.R_OK)}")
            print(f"   Writable: {os.access(path, os.W_OK)}")
            print(f"   Executable: {os.access(path, os.X_OK)}")

            if p.is_dir():
                try:
                    contents = list(p.iterdir())
                    print(f"   Contents: {len(contents)} items")
                except PermissionError:
                    print(f"   ✗ Cannot list directory contents (permission denied)")

        return p.exists()

    except Exception as e:
        print(f"   ✗ ERROR: {e}")
        return False

# Start diagnostic
print("╔" + "=" * 78 + "╗")
print("║" + " " * 78 + "║")
print("║" + "  QuickStream Comprehensive Diagnostic Test Suite".center(78) + "║")
print("║" + " " * 78 + "║")
print("╚" + "=" * 78 + "╝")

print(f"\nTimestamp: {datetime.now().isoformat()}")
print(f"Hostname: {platform.node()}")
print(f"Platform: {platform.platform()}")
print(f"Python: {sys.version}")
print(f"User: {os.environ.get('USER', 'unknown')}")
print(f"Home: {os.environ.get('HOME', 'unknown')}")
print(f"Shell: {os.environ.get('SHELL', 'unknown')}")
print(f"Current directory: {os.getcwd()}")

# ============================================================================
# SECTION 1: ENVIRONMENT ANALYSIS
# ============================================================================

print_header("SECTION 1: ENVIRONMENT ANALYSIS")

print_subheader("1.1 Display Server Detection")

env_vars = [
    'DISPLAY',
    'WAYLAND_DISPLAY',
    'XDG_SESSION_TYPE',
    'XDG_CURRENT_DESKTOP',
    'XDG_SESSION_DESKTOP',
    'DESKTOP_SESSION',
    'XDG_RUNTIME_DIR',
    'DBUS_SESSION_BUS_ADDRESS'
]

for var in env_vars:
    value = os.environ.get(var, '<not set>')
    print(f"   {var}: {value}")

# Determine session type
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
is_x11 = bool(os.environ.get("DISPLAY"))
print(f"\n   → Session Type: {'Wayland' if is_wayland else 'X11' if is_x11 else 'Unknown/Headless'}")

# Check desktop environment
desk = " ".join([
    os.environ.get("XDG_CURRENT_DESKTOP", ""),
    os.environ.get("XDG_SESSION_DESKTOP", ""),
    os.environ.get("DESKTOP_SESSION", "")
]).lower()

print(f"   → Desktop Environment: {desk if desk.strip() else 'Unknown'}")

wlroots_keywords = ("sway", "hyprland", "wlroots", "river", "wayfire", "labwc", "niri")
is_wlroots = any(k in desk for k in wlroots_keywords)
is_kde = "kde" in desk or "plasma" in desk
is_gnome = "gnome" in desk

print(f"   → wlroots compositor: {is_wlroots}")
print(f"   → KDE/Plasma: {is_kde}")
print(f"   → GNOME: {is_gnome}")

print_subheader("1.2 User Groups and Permissions")

result = run_command(['groups'], "User group memberships")
if result:
    groups = result.stdout.strip().split()
    print(f"   User groups: {', '.join(groups)}")
    print(f"   → In 'video' group: {'video' in groups}")
    print(f"   → In 'input' group: {'input' in groups}")
    print(f"   → In 'render' group: {'render' in groups}")

result = run_command(['id'], "User ID information")

print_subheader("1.3 System Information")

run_command(['uname', '-a'], "Kernel information")
run_command(['cat', '/etc/os-release'], "OS release info", timeout=2)

# ============================================================================
# SECTION 2: DIRECTORY AND FILE SYSTEM CHECKS
# ============================================================================

print_header("SECTION 2: DIRECTORY AND FILE SYSTEM CHECKS")

print_subheader("2.1 Temporary Directory")

temp_dir = tempfile.gettempdir()
print(f"   System temp dir: {temp_dir}")
test_file_permissions(temp_dir)

# Try to create a test file
try:
    with tempfile.NamedTemporaryFile(mode='w', prefix='quickstream_test_', delete=False) as f:
        test_path = f.name
        f.write("test data")

    print(f"\n   ✓ Can create temp files")
    print(f"   Test file: {test_path}")

    # Check if we can read it back
    with open(test_path, 'r') as f:
        data = f.read()
        print(f"   ✓ Can read back: '{data}'")

    # Delete it
    os.unlink(test_path)
    print(f"   ✓ Can delete temp files")

except Exception as e:
    print(f"   ✗ ERROR with temp files: {e}")

print_subheader("2.2 XDG Runtime Directory")

xdg_runtime = os.environ.get('XDG_RUNTIME_DIR')
if xdg_runtime:
    test_file_permissions(xdg_runtime)
else:
    print("   ⚠ XDG_RUNTIME_DIR not set")

print_subheader("2.3 DRM/KMS Devices")

drm_path = Path('/dev/dri')
test_file_permissions(drm_path)

if drm_path.exists():
    try:
        for device in sorted(drm_path.iterdir()):
            print(f"\n   Device: {device}")
            test_file_permissions(device)
    except Exception as e:
        print(f"   ✗ Error listing DRM devices: {e}")

# ============================================================================
# SECTION 3: CAPTURE TOOLS AVAILABILITY
# ============================================================================

print_header("SECTION 3: CAPTURE TOOLS AVAILABILITY")

print_subheader("3.1 MSS (Python library)")

try:
    import mss
    print(f"   ✓ mss module imported: version {mss.__version__ if hasattr(mss, '__version__') else 'unknown'}")

    try:
        sct = mss.mss()
        monitors = sct.monitors
        print(f"   ✓ MSS initialized successfully")
        print(f"   Monitors detected: {len(monitors) - 1}")  # -1 because monitors[0] is all
        for i, mon in enumerate(monitors):
            print(f"      Monitor {i}: {mon}")
        sct.close()
    except Exception as e:
        print(f"   ✗ MSS initialization failed: {e}")

except ImportError as e:
    print(f"   ✗ mss not available: {e}")

print_subheader("3.2 wl-screenrec")

result = run_command(['which', 'wl-screenrec'], "Locate wl-screenrec")
if result and result.returncode == 0:
    wl_path = result.stdout.strip()
    run_command(['wl-screenrec', '--version'], "wl-screenrec version", timeout=2)
    run_command(['wl-screenrec', '--help'], "wl-screenrec help", timeout=2)
else:
    print("   ⚠ wl-screenrec not found in PATH")

print_subheader("3.3 FFmpeg")

result = run_command(['which', 'ffmpeg'], "Locate ffmpeg")
if result and result.returncode == 0:
    ffmpeg_path = result.stdout.strip()
    run_command(['ffmpeg', '-version'], "ffmpeg version", timeout=2)
    run_command(['ffmpeg', '-formats'], "ffmpeg formats (first 50 lines)", timeout=3)
    run_command(['ffmpeg', '-devices'], "ffmpeg devices", timeout=2)
else:
    print("   ⚠ ffmpeg not found in PATH")

print_subheader("3.4 Screenshot Tools")

screenshot_tools = [
    ('spectacle', ['spectacle', '--help']),
    ('spectacle', ['spectacle', '--version']),
    ('grim', ['grim', '--help']),
    ('gnome-screenshot', ['gnome-screenshot', '--help']),
    ('scrot', ['scrot', '--version']),
    ('maim', ['maim', '--version']),
]

for tool_name, cmd in screenshot_tools:
    result = run_command(cmd, f"{tool_name} - {cmd[1]}", timeout=2)

print_subheader("3.5 Portal and D-Bus")

run_command(['which', 'xdg-desktop-portal'], "Locate xdg-desktop-portal")
run_command(['which', 'xdg-desktop-portal-kde'], "Locate xdg-desktop-portal-kde")
run_command(['ps', 'aux'], "Check if xdg-desktop-portal is running", timeout=2)

# Check D-Bus
dbus_addr = os.environ.get('DBUS_SESSION_BUS_ADDRESS')
print(f"\n   DBUS_SESSION_BUS_ADDRESS: {dbus_addr}")

# ============================================================================
# SECTION 4: PYTHON DEPENDENCIES
# ============================================================================

print_header("SECTION 4: PYTHON DEPENDENCIES")

print_subheader("4.1 Required Modules")

modules_to_test = [
    'flask',
    'mss',
    'PIL',
    'pyvips',
    'setproctitle',
    'pytest',
    'gi',
    'pydbus',
]

for module_name in modules_to_test:
    try:
        if module_name == 'gi':
            import gi
            print(f"   ✓ {module_name}: imported")
            try:
                gi.require_version('Gst', '1.0')
                from gi.repository import Gst
                Gst.init(None)
                print(f"      → GStreamer: {Gst.version()}")
            except Exception as e:
                print(f"      ✗ GStreamer init failed: {e}")
        else:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"   ✓ {module_name}: {version}")
    except ImportError as e:
        print(f"   ✗ {module_name}: NOT AVAILABLE ({e})")

# ============================================================================
# SECTION 5: ACTUAL CAPTURE TESTING
# ============================================================================

print_header("SECTION 5: ACTUAL CAPTURE TESTING")

print_subheader("5.1 Test Spectacle Screenshot (Detailed)")

if is_wayland or is_kde:
    # Create a unique temp directory for this test
    test_dir = tempfile.mkdtemp(prefix='quickstream_spectacle_test_')
    print(f"\n   Test directory: {test_dir}")
    test_file_permissions(test_dir)

    test_output = os.path.join(test_dir, 'screenshot.png')
    print(f"   Output file: {test_output}")

    # Try multiple spectacle command variations
    spectacle_commands = [
        (['spectacle', '-bno', test_output], 'background, no-notify, output'),
        (['spectacle', '-bn', '-o', test_output], 'background, no-notify, -o'),
        (['spectacle', '-b', '-n', '-o', test_output], 'background -n -o (separate flags)'),
        (['spectacle', '-f', '-b', '-o', test_output], 'fullscreen, background, output'),
        (['spectacle', '-o', test_output], 'just output'),
        (['spectacle', test_output], 'just filename'),
    ]

    for cmd, desc in spectacle_commands:
        print(f"\n   Trying: {desc}")
        print(f"   Command: {' '.join(cmd)}")

        # Remove output file if it exists
        if os.path.exists(test_output):
            os.unlink(test_output)
            print(f"   Cleaned up previous output file")

        result = run_command(cmd, f"spectacle {desc}", timeout=5)

        # Wait a moment for file to be written
        time.sleep(0.5)

        # Check if file was created
        if os.path.exists(test_output):
            print(f"   ✓ SUCCESS! File created: {test_output}")
            file_stat = os.stat(test_output)
            print(f"   File size: {file_stat.st_size} bytes")
            print(f"   File mode: {oct(file_stat.st_mode)}")

            # Try to identify file type
            try:
                result = subprocess.run(['file', test_output], capture_output=True, text=True, timeout=1)
                print(f"   File type: {result.stdout.strip()}")
            except:
                pass

            # This command worked!
            print(f"\n   ✓✓✓ WORKING COMMAND FOUND: {' '.join(cmd)}")
            break
        else:
            print(f"   ✗ File NOT created")
            print(f"   Expected at: {test_output}")

            # List directory contents
            try:
                contents = os.listdir(test_dir)
                print(f"   Directory contents: {contents if contents else '(empty)'}")
            except Exception as e:
                print(f"   ✗ Cannot list directory: {e}")

    # Clean up
    try:
        import shutil
        shutil.rmtree(test_dir)
        print(f"\n   Cleaned up test directory")
    except Exception as e:
        print(f"   ⚠ Failed to clean up: {e}")

else:
    print("   ⊘ Skipping (not Wayland/KDE)")

print_subheader("5.2 Test Grim Screenshot")

if is_wayland:
    test_dir = tempfile.mkdtemp(prefix='quickstream_grim_test_')
    print(f"\n   Test directory: {test_dir}")
    test_output = os.path.join(test_dir, 'screenshot.png')

    result = run_command(['grim', test_output], "grim capture", timeout=3)

    time.sleep(0.5)

    if os.path.exists(test_output):
        print(f"   ✓ File created: {test_output}")
        print(f"   File size: {os.stat(test_output).st_size} bytes")
    else:
        print(f"   ✗ File NOT created")

    # Clean up
    try:
        import shutil
        shutil.rmtree(test_dir)
    except:
        pass
else:
    print("   ⊘ Skipping (not Wayland)")

print_subheader("5.3 Test MSS Capture")

try:
    import mss
    from PIL import Image
    import io

    print(f"\n   Attempting MSS capture...")
    sct = mss.mss()
    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
    print(f"   Capturing from monitor: {monitor}")

    screenshot = sct.grab(monitor)
    print(f"   ✓ Screenshot captured: {screenshot.size}")

    # Convert to PIL
    img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
    print(f"   ✓ Converted to PIL Image: {img.size} {img.mode}")

    # Encode to JPEG
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    jpeg_size = len(buffer.getvalue())
    print(f"   ✓ Encoded to JPEG: {jpeg_size} bytes")

    sct.close()
    print(f"   ✓ MSS capture SUCCESSFUL")

except Exception as e:
    print(f"   ✗ MSS capture failed: {type(e).__name__}: {e}")

# ============================================================================
# SECTION 6: REAL CAPTURE METHOD TESTING
# ============================================================================

print_header("SECTION 6: REAL CAPTURE METHOD TESTING")

print_subheader("6.1 Test FFmpeg kmsgrab (ACTUAL ATTEMPT)")

print("\n   This tests the EXACT command QuickStream uses for FFmpeg kmsgrab")
print("   If this fails, we'll see the real error message\n")

# Test if we can actually use kmsgrab
ffmpeg_cmd = [
    'ffmpeg',
    '-device', '/dev/dri/card0',
    '-f', 'kmsgrab',
    '-i', '-',
    '-vf', 'hwdownload,format=rgb24,scale=1920:1080',
    '-f', 'rawvideo',
    '-pix_fmt', 'rgb24',
    '-r', '30',
    '-frames:v', '1',  # Just capture 1 frame for testing
    '-'
]

print(f"   Command: {' '.join(ffmpeg_cmd)}")
print(f"   (Capturing 1 frame to stdout)\n")

result = subprocess.run(
    ffmpeg_cmd,
    capture_output=True,
    timeout=5
)

print(f"   Return code: {result.returncode}")
print(f"   Stdout length: {len(result.stdout)} bytes")
print(f"   Stderr length: {len(result.stderr)} bytes")

if result.returncode == 0:
    expected_frame_size = 1920 * 1080 * 3  # RGB24
    print(f"   ✓ FFmpeg kmsgrab WORKS!")
    print(f"   Expected frame size: {expected_frame_size} bytes")
    print(f"   Got: {len(result.stdout)} bytes")
    if len(result.stdout) == expected_frame_size:
        print(f"   ✓✓ FRAME SIZE MATCHES! FFmpeg kmsgrab is FUNCTIONAL")
    else:
        print(f"   ⚠ Frame size mismatch")
else:
    print(f"   ✗ FFmpeg kmsgrab FAILED")

print(f"\n   FFmpeg stderr output:")
for line in result.stderr.decode('utf-8', errors='replace').split('\n')[:30]:
    print(f"      {line}")

print_subheader("6.2 Test wl-screenrec (ACTUAL ATTEMPT)")

if is_wayland and is_wlroots:
    print("\n   This tests the EXACT command QuickStream uses for wl-screenrec")
    print("   We'll try to capture a few frames\n")

    wl_cmd = [
        'wl-screenrec',
        '--no-damage',
        '--encode-pixfmt', 'rgb24',
        '-f', 'rawvideo',
        '-'
    ]

    print(f"   Command: {' '.join(wl_cmd)}")
    print(f"   (Will timeout after 2 seconds)\n")

    try:
        proc = subprocess.Popen(
            wl_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait a bit
        time.sleep(2)

        # Check if still running
        poll_result = proc.poll()

        if poll_result is None:
            print(f"   ✓ wl-screenrec is running")

            # Try to read some data
            try:
                # Try to read with timeout
                import select
                ready = select.select([proc.stdout], [], [], 0.5)
                if ready[0]:
                    data = proc.stdout.read(1024)
                    print(f"   ✓ Got {len(data)} bytes of data")
                    print(f"   ✓✓ wl-screenrec IS PRODUCING OUTPUT!")
                else:
                    print(f"   ⚠ No data ready yet")
            except Exception as e:
                print(f"   ⚠ Error reading data: {e}")

            # Kill it
            proc.terminate()
            proc.wait(timeout=2)
            print(f"   Process terminated")

        else:
            print(f"   ✗ wl-screenrec exited with code {poll_result}")
            stderr = proc.stderr.read().decode('utf-8', errors='replace')
            print(f"   Stderr: {stderr}")

    except FileNotFoundError:
        print(f"   ✗ wl-screenrec command not found")
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")

else:
    print(f"   ⊘ Skipping (not wlroots session)")

print_subheader("6.3 Test GStreamer PipeWire (ACTUAL ATTEMPT)")

print("\n   This tests if GStreamer can actually connect to PipeWire")
print("   Testing pipewiresrc element\n")

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)

    print(f"   ✓ GStreamer initialized")

    # Try to create a simple pipeline
    pipeline_str = "pipewiresrc ! video/x-raw ! fakesink"
    print(f"   Pipeline: {pipeline_str}")

    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print(f"   ✓ Pipeline created")

        # Try to set to PLAYING
        ret = pipeline.set_state(Gst.State.PLAYING)
        print(f"   Pipeline set_state returned: {ret}")

        if ret == Gst.StateChangeReturn.FAILURE:
            print(f"   ✗ Pipeline failed to start")
        else:
            print(f"   ✓ Pipeline started")

            # Wait a bit
            time.sleep(1)

            # Check state
            ret, state, pending = pipeline.get_state(Gst.CLOCK_TIME_NONE)
            print(f"   Pipeline state: {state}")

            if state == Gst.State.PLAYING:
                print(f"   ✓✓ GStreamer PipeWire IS WORKING!")
            else:
                print(f"   ⚠ Pipeline not in PLAYING state")

            # Get any error messages
            bus = pipeline.get_bus()
            while True:
                msg = bus.pop()
                if not msg:
                    break
                if msg.type == Gst.MessageType.ERROR:
                    err, debug = msg.parse_error()
                    print(f"   ✗ Error: {err}")
                    print(f"   Debug: {debug}")

        # Stop pipeline
        pipeline.set_state(Gst.State.NULL)

    except Exception as e:
        print(f"   ✗ Pipeline error: {type(e).__name__}: {e}")

except ImportError as e:
    print(f"   ✗ GStreamer not available: {e}")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")

print_subheader("6.4 Test QuickStream's Actual Capture Logic")

print("\n   This tests QuickStream's actual capture initialization")
print("   This is the MOST IMPORTANT test - it runs the real code\n")

try:
    import server

    print(f"   Testing FFmpegPipeWireCapture...")

    # Try to initialize FFmpeg capture
    try:
        ffmpeg_capture = server.FFmpegPipeWireCapture()
        print(f"   ✓ FFmpegPipeWireCapture instance created")

        try:
            ffmpeg_capture.initialize()
            print(f"   ✓✓✓ FFmpegPipeWireCapture.initialize() SUCCEEDED!")
            print(f"   This should work in QuickStream!")

            # Try to capture a frame
            frame = ffmpeg_capture.capture_frame()
            print(f"   ✓✓✓ Captured frame: {frame.size if hasattr(frame, 'size') else 'unknown size'}")

            ffmpeg_capture.stop()

        except Exception as e:
            print(f"   ✗ FFmpegPipeWireCapture.initialize() failed: {type(e).__name__}: {e}")
            print(f"\n   This is why FFmpeg capture fails in QuickStream!")

    except Exception as e:
        print(f"   ✗ Cannot create FFmpegPipeWireCapture: {e}")

    print(f"\n   Testing PipeWirePortalCapture...")

    # Try to initialize PipeWire portal capture
    try:
        pipewire_capture = server.PipeWirePortalCapture()
        print(f"   ✓ PipeWirePortalCapture instance created")

        try:
            pipewire_capture.initialize()
            print(f"   ✓✓✓ PipeWirePortalCapture.initialize() SUCCEEDED!")

            # Try to capture a frame
            frame = pipewire_capture.capture_frame()
            print(f"   ✓✓✓ Captured frame: {frame.size if hasattr(frame, 'size') else 'unknown size'}")

            pipewire_capture.stop()

        except Exception as e:
            print(f"   ✗ PipeWirePortalCapture.initialize() failed: {type(e).__name__}: {e}")
            print(f"\n   This is why PipeWire capture fails in QuickStream!")

    except Exception as e:
        print(f"   ✗ Cannot create PipeWirePortalCapture: {e}")

except ImportError as e:
    print(f"   ✗ Cannot import server module: {e}")
except Exception as e:
    print(f"   ✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# SECTION 7: QUICKSTREAM SERVER IMPORT TEST
# ============================================================================

print_header("SECTION 7: QUICKSTREAM SERVER IMPORT TEST")

try:
    print("   Attempting to import server module...")
    import server
    print(f"   ✓ server module imported successfully")

    print("\n   Testing session helpers:")
    print(f"      is_wayland(): {server.is_wayland()}")
    print(f"      is_wlroots_session(): {server.is_wlroots_session()}")
    print(f"      is_kde_session(): {server.is_kde_session()}")

    print("\n   Testing Config:")
    config = server.Config('nonexistent.ini')
    print(f"      Config loaded: {config.get('process_name')}")

except Exception as e:
    print(f"   ✗ Import failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header("DIAGNOSTIC COMPLETE")

print("""
═════════════════════════════════════════════════════════════════════════════════

📋 INSTRUCTIONS:

1. Save this output to a file:
   python3 diagnostic_test_suite.py > diagnostic_output.txt 2>&1

2. Review the output for any obvious issues

3. Send the diagnostic_output.txt file back for analysis

4. Look for these key sections:
   - Section 1: Environment variables and session type
   - Section 3: Which capture tools are available
   - Section 5: Actual capture testing results (especially spectacle)

═════════════════════════════════════════════════════════════════════════════════
""")

print(f"\nDiagnostic completed at: {datetime.now().isoformat()}")
print("\n" + "=" * 80)
