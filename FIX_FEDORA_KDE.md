# Fix for Fedora 42 KDE Wayland - Achieve 15+ FPS

## Current Status (from diagnostic)

**Working:**
- ✅ GStreamer 1.0 (v1.26.6)
- ✅ PipeWire services (all active)
- ✅ PipeWire socket exists
- ✅ simplejpeg encoding (10ms - FAST!)
- ✅ spectacle (1.2 FPS - TOO SLOW)

**Not Working:**
- ❌ mss: XGetImage failed (needs X11, you're on Wayland)
- ❌ FFmpeg kmsgrab: DRM capabilities issue
- ❌ pydbus: NOT INSTALLED (critical!)

## Solution 1: Install pydbus (RECOMMENDED - Will give 10-20 FPS)

### Step 1: Install pydbus

```bash
# Fedora 42
sudo dnf install python3-pydbus

# OR via pip
pip3 install --user pydbus
```

### Step 2: Verify Installation

```bash
python3 -c "import pydbus; print('pydbus installed!')"
```

### Step 3: Test QuickStream

```bash
cd ~/PycharmProjects/quickstream
python3 server.py
```

You should see:
```
INFO - Using GStreamer PipeWire for screen capture (Wayland - Fast, Real-time)
```

**Expected FPS: 10-20 FPS** ✅

---

## Solution 2: Fix FFmpeg kmsgrab (ADVANCED - May give 15-30 FPS)

The error shows FFmpeg needs CAP_SYS_ADMIN capability to access DRM framebuffers.

### Option A: Add Capabilities to FFmpeg

```bash
# Give FFmpeg the capability to access DRM
sudo setcap cap_sys_admin+ep /usr/bin/ffmpeg

# Verify
getcap /usr/bin/ffmpeg
```

**Warning:** This gives FFmpeg elevated privileges. Only do this if you trust FFmpeg.

### Option B: Run as Root (NOT RECOMMENDED)

```bash
sudo python3 server.py
```

### Option C: Add yourself to video/render groups

```bash
# Add to groups
sudo usermod -a -G video,render $USER

# Logout and login again, then verify
groups | grep -E 'video|render'
```

---

## Solution 3: Switch to X11 Session (FALLBACK - Will give 100+ FPS)

If PipeWire doesn't work, you can temporarily use X11:

1. Logout
2. At login screen, click the gear icon (⚙️)
3. Select "Plasma (X11)"
4. Login

Then QuickStream will use mss and get **100+ FPS**.

---

## Recommended Approach

**Try in this order:**

1. **Install pydbus** (5 minutes, should work immediately)
   ```bash
   sudo dnf install python3-pydbus
   python3 server.py
   ```

2. **If that doesn't work,** try FFmpeg capabilities:
   ```bash
   sudo setcap cap_sys_admin+ep /usr/bin/ffmpeg
   python3 server.py
   ```

3. **If still not working,** switch to X11 session temporarily

---

## Expected Results

| Method | Expected FPS | Pros | Cons |
|--------|-------------|------|------|
| **PipeWire + GStreamer** | 10-20 FPS | Native Wayland, good FPS | Need pydbus |
| **FFmpeg kmsgrab** | 15-30 FPS | High FPS, direct DRM | Needs capabilities |
| **X11 + mss** | 100+ FPS | VERY FAST | Need to switch session |
| **spectacle (current)** | 1.2 FPS | Works now | WAY too slow ❌ |

---

## Diagnostic Output Summary

From your system:
- **OS:** Fedora 42 KDE Plasma
- **Session:** Wayland
- **Resolution:** 2560x1600
- **Current FPS:** 1.2 (spectacle)
- **Target FPS:** 15+
- **Blocker:** Missing pydbus package

---

## After Fix - Test Performance

Once pydbus is installed, run this to verify FPS:

```bash
cd ~/PycharmProjects/quickstream
python3 diagnostic_ultimate.py 2>&1 | grep -A 5 "Multi-Frame Performance"
```

You should see:
```
Average FPS: 15+ ✅
```

---

## Troubleshooting

### If PipeWire still doesn't work after installing pydbus:

Check if GStreamer PipeWire plugin is installed:

```bash
# Check for pipewiresrc plugin
gst-inspect-1.0 pipewiresrc

# If not found, install
sudo dnf install gstreamer1-plugins-base gstreamer1-plugins-good pipewire-gstreamer
```

### Check PipeWire is actually running:

```bash
# Should show active services
systemctl --user status pipewire pipewire-pulse wireplumber

# Should show PipeWire socket
ls -la /run/user/$UID/pipewire-0
```

---

## Contact

If you still have issues after trying these fixes, paste:

```bash
python3 diagnostic_ultimate.py 2>&1 > diagnostic_after_fix.txt
```

And share the output!
