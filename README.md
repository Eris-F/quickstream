# QuickStream

A simple, barebones, and reliable LAN screen streaming service. Think of it like a screensharing app for your local network.

## Features

- **Simple**: Minimal setup, just run and connect
- **Reliable**: Thoroughly tested with comprehensive test coverage
- **LAN-focused**: Optimized for local network streaming
- **Configurable**: Easy-to-edit configuration file
- **Custom Process Name**: Shows up as "quickstream" (or your custom name) in `top` and `ps`
- **Cross-platform**: Works on Linux, macOS, and Windows (X11 and Wayland supported)
- **Multiple Capture Methods**: Choose between MSS, Pillow ImageGrab, PyVips, or Wayland tools
- **Interactive Startup**: Select your preferred capture method at launch
- **Low Latency**: MJPEG streaming for minimal delay
- **Multiple Viewers**: Support for multiple simultaneous connections
- **Mouse Cursor Visible**: Cursor is captured and visible in the stream
- **Fullscreen Mode**: Built-in fullscreen button and double-click support

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd quickstream
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Server

Start the streaming server:
```bash
python server.py
```

When you start the server, you'll see an interactive menu to choose your preferred capture method:

```
============================================================
           QuickStream - Capture Method Selection
============================================================

Available capture methods:
  1. Auto-detect (recommended)
  2. PipeWire (Wayland real-time streaming)
  3. MSS (fast X11 capture)
  4. Pillow ImageGrab (cross-platform)
  5. PyVips (fast image processing)
  6. Spectacle (KDE Wayland screenshot tool)
  7. Grim (Sway/wlroots Wayland screenshot tool)
  8. GNOME Screenshot (GNOME Wayland screenshot tool)

Enter your choice (1-8):
```

**Capture Method Guide:**
- **Auto-detect** (recommended): Automatically selects the best method for your system
- **PipeWire**: Real-time Wayland screencasting (30+ FPS) - **Recommended for Wayland**
  - Requires: `python3-gobject`, `gstreamer1-plugins-base`, `gstreamer1-plugin-pipewire`
  - Achieves full 30 FPS real-time streaming on Wayland
  - Uses xdg-desktop-portal for screen sharing permission
- **MSS**: Fast, efficient capture for X11 systems (Linux/macOS/Windows)
- **Pillow ImageGrab**: Cross-platform option that works on most systems
- **PyVips**: Fast image processing library with Pillow ImageGrab backend (requires `libvips` installed)
- **Spectacle**: For KDE Plasma on Wayland (requires `spectacle` installed) - **Slow, 1-5 FPS max**
- **Grim**: For Sway/wlroots on Wayland (requires `grim` installed) - **Slow, 1-5 FPS max**
- **GNOME Screenshot**: For GNOME on Wayland (requires `gnome-screenshot` installed) - **Slow, 1-5 FPS max**

The server will:
- Start on `0.0.0.0:5000` (accessible from your LAN)
- Display as "quickstream" in system processes
- Print the connection URL

### Viewing the Stream

**On the same machine:**
```
http://localhost:5000
```

**From other devices on your LAN:**
```
http://YOUR_IP_ADDRESS:5000
```

To find your IP address:
- **Linux/macOS**: `ip addr` or `ifconfig`
- **Windows**: `ipconfig`

## Configuration

Edit `config.ini` to customize the server:

```ini
[server]
# Process name shown in top/ps
process_name = quickstream

# Server host (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)
host = 0.0.0.0

# Server port
port = 5000

# JPEG quality (1-100, higher is better quality but more bandwidth)
quality = 75

# Frame rate (frames per second)
fps = 30

# Monitor to capture (0 for primary, 1 for secondary, etc. -1 for all monitors)
monitor = 0
```

### Configuration Options

- **process_name**: The name that appears in `top`, `ps`, and other process monitors
- **host**:
  - `0.0.0.0` - Listen on all network interfaces (LAN accessible)
  - `127.0.0.1` - Listen only on localhost (local only)
- **port**: TCP port for the server (default: 5000)
- **quality**: JPEG quality (1-100). Higher values = better quality but more bandwidth
- **fps**: Target frames per second (10-60 recommended)
- **monitor**: Which monitor to capture
  - `0` - Primary monitor
  - `1` - Secondary monitor
  - `-1` - All monitors (combined)

## Development

### Running Tests

Run the comprehensive test suite:

```bash
pytest
```

Run tests with coverage report:

```bash
pytest --cov=server --cov-report=html
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Test Coverage

The test suite includes:
- Configuration loading and validation
- Screen capture functionality
- Frame generation and streaming
- Flask application routes
- Error handling and recovery
- Integration tests
- Concurrent viewer support

## Architecture

### Components

1. **ScreenCapture**: Handles screen grabbing and frame generation
   - Uses `mss` for fast, cross-platform screen capture
   - Converts frames to JPEG for efficient transmission
   - Rate-limited frame generation

2. **Config**: Manages configuration loading
   - INI file parsing
   - Default value fallback
   - Validation

3. **Flask App**: HTTP server and routing
   - Serves viewer HTML page
   - Streams MJPEG video feed
   - Health check endpoint

### Streaming Protocol

QuickStream uses MJPEG (Motion JPEG) streaming:
- Each frame is a complete JPEG image
- Sent via HTTP multipart/x-mixed-replace
- Simple, reliable, and widely supported
- Works in all modern browsers without plugins

## Troubleshooting

### Wayland Support (Fedora, Ubuntu 22.04+, etc.)

QuickStream **fully supports Wayland** with real-time streaming! It automatically detects your display server and uses the appropriate capture method.

**Supported capture methods:**
- **X11**: Uses `mss` library (fastest, built-in, 30+ FPS)
- **Wayland (PipeWire)**: Uses PipeWire screencasting (fast, real-time, 30+ FPS) - **RECOMMENDED**
- **Wayland (Screenshot tools)**: Fallback options (slow, 1-5 FPS max):
  - **KDE**: `spectacle` tool
  - **Sway/wlroots**: `grim` tool
  - **GNOME**: `gnome-screenshot` tool

#### For Real-Time Wayland Streaming (PipeWire - Recommended)

**Install PipeWire support:**

**Fedora:**
```bash
sudo dnf install python3-gobject gstreamer1-plugins-base gstreamer1-plugin-pipewire
```

**Ubuntu/Debian:**
```bash
sudo apt install python3-gi gstreamer1.0-plugins-base gstreamer1.0-pipewire
```

When you start QuickStream, select option **2 (PipeWire)** or use **1 (Auto-detect)** which will automatically use PipeWire on Wayland.

**First time setup:** When you start PipeWire capture, your desktop will show a permission dialog asking which screen to share. Select your screen and grant permission. This permission can be remembered for future sessions.

#### Fallback: Screenshot Tools (Slow, not recommended for streaming)

**If you see "No compatible capture method found" on Wayland:**

Install the appropriate tool for your desktop environment:

**For KDE Plasma:**
```bash
sudo dnf install spectacle  # Fedora
sudo apt install kde-spectacle  # Ubuntu/Debian
```

**For Sway/wlroots:**
```bash
sudo dnf install grim  # Fedora
sudo apt install grim  # Ubuntu/Debian
```

**For GNOME:**
```bash
sudo dnf install gnome-screenshot  # Fedora
sudo apt install gnome-screenshot  # Ubuntu/Debian
```

**Note:** These screenshot tools are **slow** (1-5 FPS max) and not suitable for real-time streaming. Use PipeWire for proper streaming performance.

To verify your session type:
```bash
echo $XDG_SESSION_TYPE
# Output: wayland or x11
```

### Port Already in Use

If port 5000 is already in use:
1. Edit `config.ini` and change `port = 5000` to another port (e.g., `port = 8080`)
2. Restart the server

### Cannot Connect from Other Devices

1. Check your firewall settings:
   ```bash
   # Linux - allow port 5000
   sudo ufw allow 5000/tcp

   # Check if port is listening
   netstat -tuln | grep 5000
   ```

2. Verify the server is listening on all interfaces:
   - In `config.ini`, ensure `host = 0.0.0.0`

3. Make sure both devices are on the same network

### Screen Capture Not Working

Linux users may need to install additional dependencies:
```bash
# Debian/Ubuntu
sudo apt-get install python3-dev

# Fedora
sudo dnf install python3-devel
```

### Process Name Not Changing

If the process name doesn't change in `top`/`ps`:
1. Ensure `setproctitle` is installed: `pip install setproctitle`
2. Some systems may not support process renaming

## Performance Tips

### For Better Quality
- Increase `quality` in config.ini (e.g., 90)
- Increase `fps` for smoother motion (e.g., 60)

### For Better Performance
- Decrease `quality` (e.g., 60)
- Decrease `fps` (e.g., 15-20)
- Use a specific monitor instead of all monitors

### For Lower Bandwidth
- Decrease `quality` to 50-60
- Decrease `fps` to 15-24
- Consider using only when needed

## Security Considerations

**Important**: QuickStream is designed for trusted LANs only.

- No authentication (anyone on your LAN can connect)
- No encryption (traffic is not encrypted)
- Not suitable for internet exposure

For security:
- Use only on trusted networks
- Don't expose to the internet
- Set `host = 127.0.0.1` if only local access is needed

## Requirements

- Python 3.7+
- flask
- mss
- Pillow
- pyvips (optional, requires libvips system library)
- setproctitle
- PyGObject (optional, for PipeWire support on Wayland)
- pydbus (optional, for PipeWire support on Wayland)

See `requirements.txt` for specific versions.

**Optional Dependencies:**

**For PyVips support:**
PyVips requires the `libvips` system library. To install:
- **Linux**: `sudo apt install libvips-dev` (Debian/Ubuntu) or `sudo dnf install vips-devel` (Fedora)
- **macOS**: `brew install vips`
- **Windows**: See [pyvips installation guide](https://github.com/libvips/pyvips#install)

**For PipeWire support (Wayland real-time streaming):**
PipeWire capture requires GStreamer and portal support:
- **Fedora**: `sudo dnf install python3-gobject gstreamer1-plugins-base gstreamer1-plugin-pipewire`
- **Ubuntu/Debian**: `sudo apt install python3-gi gstreamer1.0-plugins-base gstreamer1.0-pipewire`

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## FAQ

**Q: Can I use this over the internet?**
A: Not recommended. QuickStream is designed for LAN use only and lacks security features needed for internet exposure.

**Q: What's the latency?**
A: Typically 100-300ms on a good LAN connection, depending on your configuration.

**Q: Can multiple people watch simultaneously?**
A: Yes! QuickStream supports multiple concurrent viewers.

**Q: Does it capture audio?**
A: No, QuickStream only captures video. It's screen streaming only.

**Q: What happens if I disconnect?**
A: The viewer will automatically attempt to reconnect after 2 seconds.

**Q: How do I verify the process name changed?**
A: Run `ps aux | grep quickstream` or `top` and look for your configured process name.
