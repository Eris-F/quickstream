# PipeWire Setup Guide for Fedora 42 KDE

The PipeWire implementation requires properly functioning Python GObject bindings. Here's how to set it up on your actual Fedora 42 system (not in Docker).

## Option 1: Fix GStreamer Python Bindings (Recommended)

On your **actual Fedora system** (not Docker), run:

```bash
# Install required system packages
sudo dnf install \
    python3-gobject \
    gstreamer1 \
    gstreamer1-plugins-base \
    gstreamer1-plugins-good \
    gstreamer1-plugin-pipewire \
    xdg-desktop-portal \
    xdg-desktop-portal-kde \
    pipewire \
    wireplumber

# Verify installation
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print('GStreamer OK:', Gst.version())"

# Run the diagnostic
python3 check_pipewire.py
```

If the diagnostic passes, QuickStream's PipeWire capture will work and give you 30+ FPS.

## Option 2: Alternative FFmpeg-based Approach

If GStreamer still doesn't work, you can use ffmpeg with PipeWire (I can implement this if needed):

```bash
# Install ffmpeg with PipeWire support
sudo dnf install ffmpeg

# This approach uses ffmpeg to capture from PipeWire and pipes frames to Python
# Achieves ~20-30 FPS (slower than direct GStreamer but faster than Spectacle)
```

## Option 3: Use X11 Session (Easiest)

The fastest solution if you need streaming NOW:

1. Log out of your KDE session
2. At login screen, click the gear icon
3. Select "Plasma (X11)" instead of "Plasma (Wayland)"
4. Log in
5. Run QuickStream - it will use mss (30+ FPS, no setup needed)

## Why Docker/Container Doesn't Work

The Python GObject bindings require C extensions (`_gi.so`) that depend on:
- GObject introspection typelibs
- Properly configured GI_TYPELIB_PATH
- DBus session bus access
- Access to /dev/dri for hardware acceleration

These are often not available or misconfigured in containers.

## Current Status on Your System

You're getting 556ms/frame because QuickStream is falling back to Spectacle, which is a screenshot tool not designed for streaming. The solution is either:

1. **Best**: Fix GObject on your real Fedora system (follow Option 1)
2. **Good**: Switch to X11 session temporarily (follow Option 3)
3. **Alternative**: I can implement ffmpeg-based capture (Option 2)

Which would you prefer?
