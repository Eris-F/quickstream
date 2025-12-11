# QuickStream Performance & Windows Architecture Proposal

## Current State Analysis

### Performance Bottlenecks (1.2 FPS → Target: 15+ FPS)

**Current Architecture:**
```
Capture → PIL Image → JPEG Encode → HTTP MJPEG Stream
  ↓          ↓            ↓              ↓
10-30ms   instant     40-80ms      Network
(mss)              (PIL.save)
```

**Total latency per frame: ~100-150ms → Max theoretical: 6-10 FPS**

### Identified Bottlenecks

1. **JPEG Encoding (40-80ms per frame)**
   - `PIL.Image.save(quality=75)` is CPU-intensive
   - Each frame is independently encoded (no inter-frame compression)
   - Quality 75 produces 50-200KB per frame @ 1080p

2. **MJPEG Protocol Inefficiency**
   - No inter-frame compression
   - High bandwidth: 15 FPS × 100KB = 1.5 MB/s = 12 Mbps
   - Not suitable for real-time streaming

3. **Wayland Screenshot Tools (200-500ms)**
   - spectacle, grim, gnome-screenshot designed for single captures
   - Theoretical max: 2-5 FPS
   - Already has worker scheduling fixes

4. **Windows: Not Supported**
   - No mss alternative
   - No capture implementation

---

## Proposed Architecture: Multi-Tier Approach

### Tier 1: Fast Platforms (Target: 20-30 FPS)
**Platforms:** Windows, Linux X11, macOS
**Method:** Direct screen capture with optimized encoding

```
Platform Capture → Resize (optional) → Fast Encode → WebSocket/WebRTC
      ↓                 ↓                   ↓              ↓
  5-15ms           2-5ms              10-20ms        Low latency
(mss/Windows)    (optional)         (turbo-jpeg)
```

### Tier 2: Medium Platforms (Target: 10-15 FPS)
**Platforms:** Linux Wayland (PipeWire, FFmpeg kmsgrab)
**Method:** Hardware-accelerated capture

```
FFmpeg/PipeWire → Native RGB → Fast Encode → WebSocket
      ↓              ↓             ↓             ↓
  10-20ms       instant        10-20ms      Low latency
```

### Tier 3: Fallback (Target: 5-10 FPS)
**Platforms:** All (when other methods fail)
**Method:** Screenshot tools with aggressive caching

```
Tool Capture → Aggressive Cache → Decode → Fast Encode
     ↓               ↓              ↓           ↓
 200-500ms      (reuse frames)   5-10ms     10-20ms
```

---

## Key Improvements

### 1. Windows Support

**Option A: mss (Recommended)**
- Already a dependency
- Works on Windows via ctypes + GDI
- 10-20ms capture time on Windows
- Code: `capture = ScreenCapture()` already works!

**Option B: Windows-specific (Alternative)**
```python
# Using pywin32
import win32gui, win32ui, win32con
# Or using Pillow ImageGrab (already works)
from PIL import ImageGrab
```

**Decision: Use mss** - It's cross-platform and already in requirements.txt!

### 2. Video Streaming Protocol

**Current: MJPEG (Motion JPEG)**
- ✗ No inter-frame compression
- ✗ High bandwidth
- ✓ Simple, works everywhere
- ✓ No client-side codec needed

**Option A: WebSocket + H.264 (Recommended for 15+ FPS)**
```
Pros:
- Inter-frame compression (P-frames, B-frames)
- 10-100x better compression than MJPEG
- 15 FPS @ 1080p = ~500KB/s = 4 Mbps (vs 12 Mbps MJPEG)
- Browser native support (<video> + Media Source Extensions)
- Low latency (<100ms)

Cons:
- More complex implementation
- Requires encoding library (ffmpeg-python or opencv)
- Slightly more CPU for encoding

Implementation:
- Server: Capture → H.264 encode → WebSocket chunks
- Client: WebSocket → MediaSource API → <video>
```

**Option B: WebRTC (Best for real-time, complex)**
```
Pros:
- Lowest latency (~20-50ms)
- Adaptive bitrate
- P2P capable
- Built-in congestion control

Cons:
- Very complex (STUN/TURN servers, signaling)
- Overkill for LAN streaming
```

**Option C: Improved MJPEG (Quick win for 10-15 FPS)**
```
Pros:
- Easy to implement
- Works now
- Can optimize encoding

Cons:
- Still limited to ~10-15 FPS @ 1080p on LAN
- High bandwidth

Optimizations:
- Use turbo-jpeg (6x faster than PIL)
- Lower resolution (720p → 30% less data)
- Lower quality (50 → 30% smaller files)
- Frame skipping / adaptive quality
```

**Recommendation: Start with Optimized MJPEG, add H.264 WebSocket as stretch goal**

### 3. Fast JPEG Encoding

**Current: PIL (40-80ms)**
```python
img.save(buffer, format='JPEG', quality=75, optimize=False)
```

**Improvement: turbo-jpeg (6-10ms)**
```python
from turbojpeg import TurboJPEG
jpeg = TurboJPEG()
data = jpeg.encode(img_array, quality=75)
# 6-8x faster than PIL!
```

**Benchmark (1920x1080):**
- PIL: 60ms
- turbo-jpeg: 10ms
- **Speedup: 6x = +50ms saved per frame = +12 FPS capacity!**

### 4. Resolution Scaling

**Current: Full resolution (1920x1080 or higher)**

**Improvement: Adaptive resolution**
```python
# Scale down for better FPS
if width > 1280:
    scale_factor = 1280 / width
    new_width = 1280
    new_height = int(height * scale_factor)
    img = img.resize((new_width, new_height), Image.BILINEAR)
# 1920x1080 → 1280x720: 44% fewer pixels = faster encode
```

**Savings:**
- Capture: Same speed
- Encode: 40% faster
- Bandwidth: 40% less
- **Result: Can push from 10 FPS to 15+ FPS**

---

## Proposed Implementation Plan

### Phase 1: Quick Wins (Target: 10-15 FPS) - 1-2 hours
1. ✅ Fix spectacle flags (DONE)
2. ✅ Fix worker scheduling (DONE)
3. **Add turbo-jpeg encoding**
   - Install: `pip install PyTurboJPEG`
   - Replace PIL.save() with turbo-jpeg
   - Fallback to PIL if turbo-jpeg unavailable
4. **Add resolution scaling**
   - Config option: `max_width = 1280`
   - Scale down if needed
5. **Lower default quality**
   - Change default from 75 → 60
   - Saves 20-30% bandwidth, minimal visual impact
6. **Add Windows detection**
   - Detect Windows OS
   - Use mss (already works!)
   - Test with Pillow ImageGrab fallback

### Phase 2: Video Streaming (Target: 15-25 FPS) - 2-4 hours
1. **Add WebSocket endpoint**
   - Flask-SocketIO or native WebSocket
   - Stream encoded frames
2. **Add H.264 encoding option**
   - Use ffmpeg-python or opencv
   - Encode with libx264 (fast preset)
   - Stream via WebSocket
3. **Update client HTML**
   - Add MediaSource API support
   - Fallback to MJPEG for older browsers
4. **Add adaptive quality**
   - Monitor FPS
   - Reduce quality/resolution if falling behind

### Phase 3: Testing & Optimization - 1-2 hours
1. **Add FPS performance tests**
   - Benchmark capture methods
   - Benchmark encoding methods
   - Test across platforms (Linux, Windows)
2. **Add integration tests**
   - Test full capture → encode → stream pipeline
   - Verify FPS targets met
3. **Optimize based on profiling**
   - Use cProfile to find hotspots
   - Optimize critical paths

---

## Performance Targets

### Tier 1: Optimized MJPEG (Phase 1)
| Platform | Capture Method | Resolution | Target FPS | Expected |
|----------|---------------|------------|------------|----------|
| Linux X11 | mss | 1280x720 | 15-20 FPS | ✓ Achievable |
| Linux X11 | mss | 1920x1080 | 10-15 FPS | ✓ Achievable |
| Windows | mss | 1280x720 | 15-20 FPS | ✓ Achievable |
| Wayland | PipeWire | 1280x720 | 10-15 FPS | ✓ Achievable |
| Wayland | kmsgrab | 1280x720 | 10-15 FPS | ✓ Achievable |
| Wayland | Tools | Any | 3-5 FPS | ⚠ Limited |

### Tier 2: H.264 WebSocket (Phase 2)
| Platform | Capture Method | Resolution | Target FPS | Expected |
|----------|---------------|------------|------------|----------|
| Linux X11 | mss | 1920x1080 | 20-30 FPS | ✓ Achievable |
| Windows | mss | 1920x1080 | 20-30 FPS | ✓ Achievable |
| Wayland | PipeWire | 1920x1080 | 15-25 FPS | ✓ Achievable |

---

## Technical Decisions Summary

### What to implement NOW (Phase 1):
1. ✅ turbo-jpeg encoding (6x speedup)
2. ✅ Resolution scaling (40% speedup)
3. ✅ Windows support via mss
4. ✅ Lower default quality
5. ✅ FPS performance tests

**Expected result: 10-15 FPS on all platforms (Tier 1)**

### What to implement NEXT (Phase 2):
1. WebSocket + H.264 streaming
2. Adaptive quality/resolution
3. Client-side MediaSource API

**Expected result: 20-30 FPS on fast platforms**

### What to skip for now:
1. ❌ WebRTC (too complex, overkill)
2. ❌ Custom codecs (H.265, VP9 - not worth complexity)
3. ❌ GPU acceleration (diminishing returns)

---

## Questions for You

1. **Priority: Quick wins (Phase 1) or full video streaming (Phase 2)?**
   - Phase 1 = 2 hours, gets you to 10-15 FPS
   - Phase 2 = 4-6 hours, gets you to 20-30 FPS

2. **Windows testing: Do you have a Windows machine to test on?**
   - mss should work out of the box
   - Need to verify

3. **Bandwidth: Is this LAN-only or need internet streaming?**
   - LAN: MJPEG is fine (gigabit = 1000 Mbps >> 12 Mbps)
   - Internet: Need H.264 compression

4. **Resolution: What's your primary target?**
   - 720p: Easier to hit 20+ FPS
   - 1080p: More challenging, 15 FPS realistic
   - 4K: Need H.264, 10-15 FPS max

---

## My Recommendation

**Start with Phase 1 (Quick Wins)**
- Implement turbo-jpeg + resolution scaling + Windows support
- Should get you from 1.2 FPS → 10-15 FPS in ~2 hours
- Test thoroughly with new FPS performance tests
- Then decide if Phase 2 (H.264) is needed

**Rationale:**
- Big gains with minimal complexity
- Cross-platform (Windows!) immediately
- Sets foundation for Phase 2
- Can always add H.264 later if needed

**What do you think? Should we proceed with Phase 1?**
