#!/usr/bin/env python3
"""
Comprehensive diagnostics for QuickStream capture methods.
Tests all capture methods and provides detailed feedback.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

print("=" * 70)
print("  QuickStream Capture Method Diagnostics")
print("=" * 70)

# Session information
print("\n📋 Session Information:")
print(f"  XDG_SESSION_TYPE: {os.environ.get('XDG_SESSION_TYPE', 'not set')}")
print(f"  WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', 'not set')}")
print(f"  XDG_CURRENT_DESKTOP: {os.environ.get('XDG_CURRENT_DESKTOP', 'not set')}")
print(f"  XDG_SESSION_DESKTOP: {os.environ.get('XDG_SESSION_DESKTOP', 'not set')}")
print(f"  DESKTOP_SESSION: {os.environ.get('DESKTOP_SESSION', 'not set')}")

# Check if Wayland
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
print(f"  → Wayland session: {'YES' if is_wayland else 'NO'}")

# Check if wlroots
desk = " ".join([
    os.environ.get("XDG_CURRENT_DESKTOP", ""),
    os.environ.get("XDG_SESSION_DESKTOP", ""),
    os.environ.get("DESKTOP_SESSION", "")
]).lower()
wlroots_keywords = ("sway", "hyprland", "wlroots", "river", "wayfire", "labwc", "niri")
is_wlroots = any(k in desk for k in wlroots_keywords)
print(f"  → wlroots compositor: {'YES' if is_wlroots else 'NO'}")

is_kde = "kde" in desk or "plasma" in desk
print(f"  → KDE/Plasma: {'YES' if is_kde else 'NO'}")

# Check capture methods
print("\n🔍 Checking Available Capture Methods:\n")

# 1. MSS (X11)
print("1. MSS (X11 capture)")
try:
    import mss
    test_sct = mss.mss()
    test_monitor = test_sct.monitors[1] if len(test_sct.monitors) > 1 else test_sct.monitors[0]
    test_sct.grab(test_monitor)
    test_sct.close()
    print("   ✓ MSS available and working")
except Exception as e:
    print(f"   ✗ MSS not available: {e}")

# 2. wl-screenrec
print("\n2. wl-screenrec (wlroots Wayland)")
try:
    result = subprocess.run(['which', 'wl-screenrec'], capture_output=True, timeout=1)
    if result.returncode == 0:
        wl_path = result.stdout.decode().strip()
        print(f"   ✓ wl-screenrec found: {wl_path}")

        # Try to get version
        try:
            ver_result = subprocess.run(['wl-screenrec', '--version'],
                                       capture_output=True, timeout=1, text=True)
            if ver_result.returncode == 0:
                print(f"   ✓ Version: {ver_result.stdout.strip()}")
        except:
            pass

        # Check if session is compatible
        if not is_wlroots:
            print("   ⚠ WARNING: wl-screenrec is designed for wlroots compositors")
            print("   ⚠ Your session is not wlroots - wl-screenrec may not work")
    else:
        print("   ✗ wl-screenrec not found")
        if is_wlroots:
            print("   → Install: flatpak install flathub com.github.russelltg.wl-screenrec")
except Exception as e:
    print(f"   ✗ Error checking wl-screenrec: {e}")

# 3. FFmpeg with kmsgrab
print("\n3. FFmpeg kmsgrab (DRM/KMS capture)")
try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=2, text=True)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0]
        print(f"   ✓ FFmpeg found: {version_line}")

        # Check if user is in video group
        try:
            groups_result = subprocess.run(['groups'], capture_output=True, timeout=1, text=True)
            groups = groups_result.stdout.strip().split()
            if 'video' in groups:
                print("   ✓ User is in 'video' group")
            else:
                print("   ✗ User NOT in 'video' group (required for kmsgrab)")
                print("   → Fix: sudo usermod -a -G video $USER && newgrp video")
        except:
            print("   ⚠ Could not check video group membership")

        # Check if /dev/dri exists
        if Path('/dev/dri').exists():
            dri_cards = list(Path('/dev/dri').glob('card*'))
            if dri_cards:
                print(f"   ✓ DRM devices available: {len(dri_cards)} card(s)")
            else:
                print("   ✗ No DRM cards found in /dev/dri")
        else:
            print("   ✗ /dev/dri not found")
    else:
        print("   ✗ FFmpeg not available")
        print("   → Install: sudo dnf install ffmpeg")
except Exception as e:
    print(f"   ✗ Error checking FFmpeg: {e}")

# 4. GStreamer PipeWire
print("\n4. GStreamer PipeWire")
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    print(f"   ✓ GStreamer available: version {Gst.version()}")

    # Check for PipeWire plugin
    registry = Gst.Registry.get()
    plugin = registry.find_plugin('pipewire')
    if plugin:
        print(f"   ✓ PipeWire plugin found: {plugin.get_description()}")
    else:
        print("   ✗ PipeWire plugin NOT found")
        print("   → Install: sudo dnf install pipewire-gstreamer")

    # Check for pipewiresrc element
    pipewiresrc = Gst.ElementFactory.make('pipewiresrc', None)
    if pipewiresrc:
        print("   ✓ pipewiresrc element available")
    else:
        print("   ✗ pipewiresrc element NOT available")

except ImportError as e:
    print(f"   ✗ GStreamer not available: {e}")
    print("   → Install: sudo dnf install python3-gobject gstreamer1-plugins-base pipewire-gstreamer")

# 5. Screenshot tools
print("\n5. Screenshot Tools (Fallback, slow)")

tools = [
    ('grim', 'wlroots Wayland'),
    ('spectacle', 'KDE/Plasma'),
    ('gnome-screenshot', 'GNOME'),
]

for tool, desc in tools:
    try:
        result = subprocess.run([tool, '--help'], capture_output=True, timeout=1)
        if result.returncode == 0:
            print(f"   ✓ {tool} available ({desc})")
        else:
            print(f"   ✗ {tool} not available ({desc})")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print(f"   ✗ {tool} not available ({desc})")

# 6. XDG Desktop Portal
print("\n6. XDG Desktop Portal")
try:
    result = subprocess.run(['which', 'xdg-desktop-portal'], capture_output=True, timeout=1)
    if result.returncode == 0:
        print("   ✓ xdg-desktop-portal found")

        # Check if portal is running
        try:
            ps_result = subprocess.run(['ps', 'aux'], capture_output=True, timeout=1, text=True)
            if 'xdg-desktop-portal' in ps_result.stdout:
                print("   ✓ xdg-desktop-portal is running")
            else:
                print("   ⚠ xdg-desktop-portal not running")
        except:
            pass

        # Check for KDE portal
        if is_kde:
            kde_result = subprocess.run(['which', 'xdg-desktop-portal-kde'],
                                       capture_output=True, timeout=1)
            if kde_result.returncode == 0:
                print("   ✓ xdg-desktop-portal-kde found")
            else:
                print("   ✗ xdg-desktop-portal-kde not found")
                print("   → Install: sudo dnf install xdg-desktop-portal-kde")
    else:
        print("   ✗ xdg-desktop-portal not found")
        print("   → Install: sudo dnf install xdg-desktop-portal")
except Exception as e:
    print(f"   ✗ Error checking portal: {e}")

# Recommendations
print("\n" + "=" * 70)
print("📊 RECOMMENDATIONS:")
print("=" * 70)

if not is_wayland:
    print("\n✓ You're on X11 - MSS should work great (30+ FPS)")
    print("  → Just run QuickStream and select 'Auto-detect' or 'MSS'")
elif is_wlroots:
    print("\n✓ You're on wlroots compositor")
    print("  → Install wl-screenrec for best performance:")
    print("    flatpak install flathub com.github.russelltg.wl-screenrec")
elif is_kde:
    print("\n⚠ You're on KDE/Plasma Wayland")
    print("  → BEST: Switch to X11 session (30+ FPS with MSS)")
    print("    - Log out → Select 'Plasma (X11)' at login screen")
    print("  → ALTERNATIVE: Use GStreamer PipeWire (if properly configured)")
    print("    - Requires portal handshake and proper permissions")
    print("  → FALLBACK: spectacle (1-5 FPS only)")
else:
    print("\n⚠ Wayland detected but compositor type unclear")
    print("  → Try GStreamer PipeWire or screenshot tools")

print("\n" + "=" * 70)
print("Done! Run 'python3 server.py' to start QuickStream")
print("=" * 70)
