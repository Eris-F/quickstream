#!/usr/bin/env python3
"""
Diagnostic script to check PipeWire/GStreamer availability.
"""

import sys

print("=" * 60)
print("PipeWire/GStreamer Diagnostic Check")
print("=" * 60)

# Check pydbus
print("\n1. Checking pydbus...")
try:
    import pydbus
    print("   ✓ pydbus installed")
except ImportError as e:
    print(f"   ✗ pydbus NOT available: {e}")

# Check PyGObject
print("\n2. Checking PyGObject...")
try:
    import gi
    print("   ✓ gi (PyGObject) module found")
except ImportError as e:
    print(f"   ✗ PyGObject NOT available: {e}")
    sys.exit(1)

# Check GStreamer
print("\n3. Checking GStreamer...")
try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    print(f"   ✓ GStreamer available: version {Gst.version()}")
except Exception as e:
    print(f"   ✗ GStreamer NOT available: {e}")
    print("\n   FIX: Install GStreamer with:")
    print("   sudo dnf install gstreamer1 gstreamer1-plugins-base python3-gobject")
    sys.exit(1)

# Check PipeWire GStreamer plugin
print("\n4. Checking PipeWire GStreamer plugin...")
try:
    registry = Gst.Registry.get()
    plugin = registry.find_plugin('pipewire')
    if plugin:
        print(f"   ✓ PipeWire plugin found: {plugin.get_description()}")
    else:
        print("   ✗ PipeWire plugin NOT found")
        print("\n   FIX: Install with:")
        print("   sudo dnf install pipewire-gstreamer")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error checking PipeWire plugin: {e}")

# Check pipewiresrc element
print("\n5. Checking pipewiresrc element...")
try:
    pipewiresrc = Gst.ElementFactory.make('pipewiresrc', None)
    if pipewiresrc:
        print("   ✓ pipewiresrc element available")
    else:
        print("   ✗ pipewiresrc element NOT available")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error creating pipewiresrc: {e}")

# Check portal availability
print("\n6. Checking xdg-desktop-portal...")
import subprocess
try:
    result = subprocess.run(['which', 'xdg-desktop-portal'], capture_output=True, timeout=1)
    if result.returncode == 0:
        print("   ✓ xdg-desktop-portal found")
    else:
        print("   ✗ xdg-desktop-portal NOT found")
        print("\n   FIX: Install with:")
        print("   sudo dnf install xdg-desktop-portal xdg-desktop-portal-kde")
except Exception as e:
    print(f"   ✗ Error checking portal: {e}")

print("\n" + "=" * 60)
print("All checks passed! PipeWire should work.")
print("=" * 60)
