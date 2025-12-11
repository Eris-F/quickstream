#!/usr/bin/env python3
"""
ULTIMATE QuickStream Diagnostic Suite
Ultra-comprehensive system diagnostics that catch EVERYTHING across all platforms.
Run this and paste the output to identify any issues!
"""

import os
import sys
import time
import platform
import subprocess
import json
from pathlib import Path

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

def print_subheader(text):
    print(f"\n{BOLD}{YELLOW}>>> {text}{RESET}")
    print(f"{YELLOW}{'-' * 80}{RESET}")

def print_success(text):
    print(f"{GREEN}   ✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}   ✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}   ⚠ {text}{RESET}")

def print_info(text):
    print(f"   → {text}")

def run_command(cmd, timeout=5, check=False):
    """Run command and return result."""
    try:
        result = subprocess.run(
            cmd if isinstance(cmd, list) else cmd.split(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=check
        )
        return result
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        return None

# ============================================================================
# SECTION 1: SYSTEM INFORMATION
# ============================================================================

print_header("SECTION 1: SYSTEM INFORMATION")

print_subheader("1.1 Platform Details")
print_info(f"System: {platform.system()}")
print_info(f"Release: {platform.release()}")
print_info(f"Version: {platform.version()}")
print_info(f"Machine: {platform.machine()}")
print_info(f"Processor: {platform.processor()}")
print_info(f"Python: {sys.version}")

# Detect Linux distro
if platform.system() == 'Linux':
    print_subheader("1.2 Linux Distribution")

    # Try /etc/os-release
    if Path('/etc/os-release').exists():
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('NAME=') or line.startswith('VERSION=') or line.startswith('ID='):
                    print_info(line.strip())

    # Try lsb_release
    result = run_command(['lsb_release', '-a'])
    if result and result.returncode == 0:
        print_info("lsb_release output:")
        for line in result.stdout.split('\n'):
            if line.strip():
                print(f"      {line}")

print_subheader("1.3 Session Type Detection")
session_vars = {
    'XDG_SESSION_TYPE': os.environ.get('XDG_SESSION_TYPE', '<not set>'),
    'WAYLAND_DISPLAY': os.environ.get('WAYLAND_DISPLAY', '<not set>'),
    'DISPLAY': os.environ.get('DISPLAY', '<not set>'),
    'XDG_CURRENT_DESKTOP': os.environ.get('XDG_CURRENT_DESKTOP', '<not set>'),
    'XDG_SESSION_DESKTOP': os.environ.get('XDG_SESSION_DESKTOP', '<not set>'),
    'DESKTOP_SESSION': os.environ.get('DESKTOP_SESSION', '<not set>'),
}

for var, val in session_vars.items():
    if val != '<not set>':
        print_success(f"{var} = {val}")
    else:
        print_warning(f"{var} = {val}")

# Determine session type
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
is_x11 = bool(os.environ.get("DISPLAY")) and not is_wayland

desk = " ".join([
    os.environ.get("XDG_CURRENT_DESKTOP", ""),
    os.environ.get("XDG_SESSION_DESKTOP", ""),
    os.environ.get("DESKTOP_SESSION", "")
]).lower()

is_kde = "kde" in desk or "plasma" in desk
is_gnome = "gnome" in desk
is_wlroots = any(k in desk for k in ("sway", "hyprland", "wlroots", "river", "wayfire", "labwc", "niri"))

print_info("")
print_info(f"Detected: {'Wayland' if is_wayland else 'X11' if is_x11 else 'Unknown'}")
print_info(f"Desktop: {'KDE/Plasma' if is_kde else 'GNOME' if is_gnome else 'wlroots' if is_wlroots else 'Other'}")

# ============================================================================
# SECTION 2: PYTHON DEPENDENCIES
# ============================================================================

print_header("SECTION 2: PYTHON DEPENDENCIES")

print_subheader("2.1 Required Libraries")

required_libs = {
    'flask': 'Flask web framework',
    'mss': 'Screen capture (X11)',
    'PIL': 'Image processing (Pillow)',
    'simplejpeg': 'Fast JPEG encoding (NEW!)',
    'numpy': 'Array processing',
}

for lib, desc in required_libs.items():
    try:
        if lib == 'PIL':
            import PIL
            version = PIL.__version__
        else:
            mod = __import__(lib)
            version = getattr(mod, '__version__', 'unknown')
        print_success(f"{lib:<15} v{version:<10} - {desc}")
    except ImportError:
        print_error(f"{lib:<15} {'NOT INSTALLED':<10} - {desc}")

print_subheader("2.2 Optional Libraries (Linux Wayland)")

optional_libs = {
    'pydbus': 'DBus communication',
    'gi.repository.Gst': 'GStreamer (PipeWire)',
    'gi.repository.GLib': 'GLib (PipeWire)',
}

for lib, desc in optional_libs.items():
    try:
        if '.' in lib:
            parts = lib.split('.')
            mod = __import__(parts[0])
            for part in parts[1:]:
                mod = getattr(mod, part)
        else:
            mod = __import__(lib)
        print_success(f"{lib:<25} AVAILABLE - {desc}")
    except ImportError as e:
        print_warning(f"{lib:<25} NOT AVAILABLE - {desc}")

# ============================================================================
# SECTION 3: SCREEN CAPTURE TOOLS
# ============================================================================

print_header("SECTION 3: SCREEN CAPTURE TOOLS AVAILABILITY")

print_subheader("3.1 X11 Tools")

x11_tools = {
    'xdotool': 'Cursor position detection',
    'xrandr': 'Resolution detection',
}

for tool, desc in x11_tools.items():
    result = run_command(['which', tool])
    if result and result.returncode == 0:
        path = result.stdout.strip()
        print_success(f"{tool:<15} {path:<40} - {desc}")
    else:
        print_warning(f"{tool:<15} {'NOT FOUND':<40} - {desc}")

print_subheader("3.2 Wayland Screenshot Tools")

wayland_tools = {
    'spectacle': 'KDE screenshot tool',
    'grim': 'wlroots screenshot tool',
    'gnome-screenshot': 'GNOME screenshot tool',
    'kscreen-doctor': 'KDE resolution detection',
    'wlr-randr': 'wlroots resolution detection',
}

for tool, desc in wayland_tools.items():
    result = run_command(['which', tool])
    if result and result.returncode == 0:
        path = result.stdout.strip()
        print_success(f"{tool:<20} {path:<35} - {desc}")

        # Test if tool actually works
        if tool == 'spectacle':
            test_result = run_command(['spectacle', '--help'], timeout=2)
            if test_result and test_result.returncode == 0:
                print_info(f"  {tool} --help works ✓")
            else:
                print_warning(f"  {tool} --help FAILED")
    else:
        print_warning(f"{tool:<20} {'NOT FOUND':<35} - {desc}")

print_subheader("3.3 PipeWire/FFmpeg Tools")

pipewire_tools = {
    'ffmpeg': 'Video encoding/kmsgrab',
    'wl-screenrec': 'Wayland screen recording',
    'pw-cli': 'PipeWire CLI',
    'wpctl': 'WirePlumber control',
}

for tool, desc in pipewire_tools.items():
    result = run_command(['which', tool])
    if result and result.returncode == 0:
        path = result.stdout.strip()
        # Get version
        if tool == 'ffmpeg':
            ver_result = run_command(['ffmpeg', '-version'], timeout=2)
            if ver_result:
                ver_line = ver_result.stdout.split('\n')[0]
                print_success(f"{tool:<15} {path:<35} - {desc}")
                print_info(f"  {ver_line}")
        else:
            print_success(f"{tool:<15} {path:<35} - {desc}")
    else:
        print_warning(f"{tool:<15} {'NOT FOUND':<35} - {desc}")

# ============================================================================
# SECTION 4: ACTUAL CAPTURE TESTS
# ============================================================================

print_header("SECTION 4: ACTUAL CAPTURE TESTS (REAL ATTEMPTS)")

print_subheader("4.1 Test mss Library (X11)")
try:
    import mss
    print_info("Attempting mss screen capture...")

    try:
        with mss.mss() as sct:
            monitors = sct.monitors
            print_success(f"mss works! Found {len(monitors)} monitors")
            for i, mon in enumerate(monitors):
                print_info(f"  Monitor {i}: {mon}")

            # Try to capture
            screenshot = sct.grab(monitors[1] if len(monitors) > 1 else monitors[0])
            print_success(f"Captured screen: {screenshot.size}, {len(screenshot.rgb)} bytes")

            # Measure speed
            start = time.time()
            for _ in range(10):
                sct.grab(monitors[1] if len(monitors) > 1 else monitors[0])
            elapsed = time.time() - start
            fps = 10 / elapsed
            print_success(f"mss speed: {fps:.1f} FPS (10 captures in {elapsed:.2f}s)")

    except Exception as e:
        print_error(f"mss capture FAILED: {e}")
        print_info(f"Error type: {type(e).__name__}")
        if "XGetImage" in str(e):
            print_warning("XGetImage failed - you're likely on Wayland, mss needs X11")

except ImportError:
    print_error("mss library not installed")

print_subheader("4.2 Test Pillow ImageGrab")
try:
    from PIL import ImageGrab
    print_info("Attempting Pillow ImageGrab...")

    try:
        img = ImageGrab.grab()
        print_success(f"ImageGrab works! Size: {img.size}, mode: {img.mode}")

        # Measure speed
        start = time.time()
        for _ in range(10):
            ImageGrab.grab()
        elapsed = time.time() - start
        fps = 10 / elapsed
        print_success(f"ImageGrab speed: {fps:.1f} FPS (10 captures in {elapsed:.2f}s)")

    except Exception as e:
        print_error(f"ImageGrab FAILED: {e}")

except ImportError:
    print_error("Pillow not installed")

print_subheader("4.3 Test Spectacle (KDE)")
if is_kde:
    result = run_command(['which', 'spectacle'])
    if result and result.returncode == 0:
        print_info("Attempting spectacle capture...")

        test_file = '/tmp/quickstream_diag_spectacle.png'
        start = time.time()

        result = run_command(
            ['spectacle', '-b', '-n', '-o', test_file],
            timeout=5
        )

        elapsed = time.time() - start

        if result and result.returncode == 0:
            if Path(test_file).exists():
                size = Path(test_file).stat().st_size
                print_success(f"spectacle works! File: {size} bytes, time: {elapsed*1000:.0f}ms")
                print_warning(f"spectacle speed: {1/elapsed:.1f} FPS (very slow for streaming!)")
                Path(test_file).unlink()
            else:
                print_error("spectacle returned 0 but file not created")
        else:
            print_error(f"spectacle FAILED (exit: {result.returncode if result else 'timeout'})")
            if result:
                print_info(f"stdout: {result.stdout[:200]}")
                print_info(f"stderr: {result.stderr[:200]}")
    else:
        print_warning("spectacle not found")
else:
    print_info("Not KDE, skipping spectacle test")

print_subheader("4.4 Test FFmpeg kmsgrab (DRM)")
result = run_command(['which', 'ffmpeg'])
if result and result.returncode == 0:
    print_info("Attempting FFmpeg kmsgrab capture...")

    # Find DRM device
    dri_path = Path('/dev/dri')
    if dri_path.exists():
        cards = sorted(dri_path.glob('card[0-9]*'))
        print_info(f"Found DRM devices: {[str(c) for c in cards]}")

        if cards:
            drm_device = str(cards[0])
            print_info(f"Testing with {drm_device}")

            # Check permissions
            readable = os.access(drm_device, os.R_OK)
            writable = os.access(drm_device, os.W_OK)
            print_info(f"  Permissions: readable={readable}, writable={writable}")

            if not (readable and writable):
                print_warning(f"  No access to {drm_device}! Need to be in 'video' group")
                print_info(f"  Run: sudo usermod -a -G video $USER && newgrp video")

            # Try capture
            cmd = [
                'ffmpeg',
                '-device', drm_device,
                '-f', 'kmsgrab',
                '-i', '-',
                '-vframes', '1',
                '-f', 'null',
                '-'
            ]

            print_info(f"Running: {' '.join(cmd)}")
            start = time.time()
            result = run_command(cmd, timeout=10)
            elapsed = time.time() - start

            if result and result.returncode == 0:
                print_success(f"FFmpeg kmsgrab works! Time: {elapsed*1000:.0f}ms")
            else:
                print_error(f"FFmpeg kmsgrab FAILED (exit: {result.returncode if result else 'timeout'})")
                if result and result.stderr:
                    print_info("Last 10 lines of stderr:")
                    for line in result.stderr.split('\n')[-10:]:
                        if line.strip():
                            print(f"      {line}")
        else:
            print_warning("No DRM card devices found")
    else:
        print_warning("/dev/dri does not exist")
else:
    print_warning("ffmpeg not found")

# ============================================================================
# SECTION 5: PIPEWIRE STATUS
# ============================================================================

print_header("SECTION 5: PIPEWIRE STATUS")

print_subheader("5.1 PipeWire Services")
if platform.system() == 'Linux':
    services = ['pipewire.service', 'pipewire-pulse.service', 'wireplumber.service']

    for service in services:
        result = run_command(['systemctl', '--user', 'is-active', service], timeout=2)
        if result:
            status = result.stdout.strip()
            if status == 'active':
                print_success(f"{service}: {status}")
            else:
                print_warning(f"{service}: {status}")
        else:
            print_error(f"{service}: could not check")

print_subheader("5.2 PipeWire Socket")
runtime_dir = os.environ.get('XDG_RUNTIME_DIR', '')
if runtime_dir:
    pw_socket = Path(runtime_dir) / 'pipewire-0'
    if pw_socket.exists():
        print_success(f"PipeWire socket exists: {pw_socket}")
    else:
        print_error(f"PipeWire socket NOT found: {pw_socket}")
else:
    print_error("XDG_RUNTIME_DIR not set")

print_subheader("5.3 PipeWire Node Detection")
result = run_command(['pw-cli', 'list-objects'], timeout=3)
if result and result.returncode == 0:
    lines = result.stdout.split('\n')
    node_count = sum(1 for line in lines if 'type = "PipeWire:Interface:Node"' in line)
    print_success(f"pw-cli works! Found ~{node_count} nodes")
    print_info(f"Output lines: {len(lines)}")
else:
    print_warning("pw-cli not available or failed")

# ============================================================================
# SECTION 6: QUICKSTREAM IMPORT TEST
# ============================================================================

print_header("SECTION 6: QUICKSTREAM SERVER TEST")

print_subheader("6.1 Import Test")
try:
    sys.path.insert(0, str(Path(__file__).parent))
    import server
    print_success("server.py imported successfully")

    print_info(f"Platform detection:")
    print_info(f"  IS_WINDOWS: {server.IS_WINDOWS}")
    print_info(f"  IS_LINUX: {server.IS_LINUX}")
    print_info(f"  IS_MACOS: {server.IS_MACOS}")
    print_info(f"  SIMPLEJPEG_AVAILABLE: {server.SIMPLEJPEG_AVAILABLE}")
    print_info(f"  XLIB_AVAILABLE: {server.XLIB_AVAILABLE}")
    print_info(f"  PYVIPS_AVAILABLE: {server.PYVIPS_AVAILABLE}")
    print_info(f"  PYDBUS_AVAILABLE: {server.PYDBUS_AVAILABLE}")
    print_info(f"  GST_AVAILABLE: {server.GST_AVAILABLE}")

    print_subheader("6.2 ScreenCapture Initialization Test")
    try:
        capture = server.ScreenCapture(
            quality=60,
            fps=30,
            max_width=1920,
            max_height=1080,
            fast_encoding=True
        )
        print_success(f"ScreenCapture initialized successfully!")
        print_info(f"  Capture method: {capture.capture_method}")
        print_info(f"  Fast encoding: {capture.fast_encoding}")
        print_info(f"  Quality: {capture.quality}")
        print_info(f"  Max resolution: {capture.max_width}x{capture.max_height}")

        # Try to capture one frame
        print_subheader("6.3 Single Frame Capture Test")
        try:
            start = time.time()
            frame = capture.capture_frame()
            elapsed = time.time() - start

            print_success(f"Frame captured successfully!")
            print_info(f"  Frame size: {len(frame)/1024:.1f} KB")
            print_info(f"  Capture time: {elapsed*1000:.0f}ms")
            print_info(f"  Estimated FPS: {1/elapsed:.1f}")

            if elapsed > 0.1:  # More than 100ms per frame
                print_warning(f"Frame capture is SLOW ({elapsed*1000:.0f}ms)!")
                print_warning(f"Expected FPS: Only {1/elapsed:.1f} FPS (target: 15+)")
            elif elapsed > 0.033:  # More than 33ms per frame
                print_warning(f"Frame capture is moderate ({elapsed*1000:.0f}ms)")
                print_info(f"Expected FPS: ~{1/elapsed:.1f} FPS (target: 15+)")
            else:
                print_success(f"Frame capture is FAST ({elapsed*1000:.0f}ms)!")
                print_success(f"Expected FPS: {1/elapsed:.1f} FPS ✓")

            # Capture multiple frames for average
            print_subheader("6.4 Multi-Frame Performance Test")
            print_info("Capturing 20 frames...")

            frame_times = []
            for i in range(20):
                start = time.time()
                frame = capture.capture_frame()
                elapsed = time.time() - start
                frame_times.append(elapsed)

                if (i + 1) % 5 == 0:
                    avg_fps = (i + 1) / sum(frame_times)
                    print_info(f"  {i+1}/20 frames, avg: {avg_fps:.1f} FPS")

            avg_time = sum(frame_times) / len(frame_times)
            min_time = min(frame_times)
            max_time = max(frame_times)
            avg_fps = 1 / avg_time

            print_info(f"\nResults:")
            print_info(f"  Avg frame time: {avg_time*1000:.1f}ms")
            print_info(f"  Min frame time: {min_time*1000:.1f}ms")
            print_info(f"  Max frame time: {max_time*1000:.1f}ms")
            print_info(f"  Average FPS: {avg_fps:.1f}")

            if avg_fps >= 15:
                print_success(f"✓ MEETS TARGET: {avg_fps:.1f} >= 15 FPS")
            else:
                print_error(f"✗ BELOW TARGET: {avg_fps:.1f} < 15 FPS")

        except Exception as e:
            print_error(f"Frame capture failed: {e}")
            import traceback
            traceback.print_exc()

        capture.stop()

    except Exception as e:
        print_error(f"ScreenCapture initialization failed: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print_error(f"Failed to import server.py: {e}")
except Exception as e:
    print_error(f"Error during import: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header("DIAGNOSTIC COMPLETE - SUMMARY")

print("\nThis comprehensive diagnostic tested:")
print("  1. System and platform information")
print("  2. Python dependencies")
print("  3. Screen capture tools availability")
print("  4. Actual capture tests with timing")
print("  5. PipeWire status")
print("  6. QuickStream server functionality")
print("  7. Real-world performance measurement")

print(f"\n{BOLD}PLEASE SHARE THE COMPLETE OUTPUT ABOVE{RESET}")
print("This will help identify exactly what's working and what needs fixing!\n")
