#!/usr/bin/env python3
"""
QuickStream - Simple LAN Screen Streaming Service
A barebones, reliable screen sharing application for local networks.
"""

import io
import os
import time
import configparser
import logging
import subprocess
import tempfile
from pathlib import Path
from threading import Thread, Event, local

try:
    import setproctitle
except ImportError:
    setproctitle = None

import mss
import mss.exception
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, Response, render_template_string


class ScreenCapture:
    """Handles screen capture functionality."""

    def __init__(self, monitor=0, quality=75, fps=30):
        """
        Initialize screen capture.

        Args:
            monitor: Monitor index to capture (0 for primary, -1 for all)
            quality: JPEG quality (1-100)
            fps: Target frames per second
        """
        self.capture_method = None  # 'mss', 'grim', 'spectacle', 'gnome-screenshot', or 'headless'
        # Use thread-local storage for mss instances (mss uses thread-local display connections)
        self._thread_local = local()
        self._temp_dir = tempfile.mkdtemp(prefix='quickstream_')

        self.monitor = monitor
        self.quality = quality
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self._stop_event = Event()
        self._frame_count = 0
        self._last_fps_log = time.time()
        self._fps_frame_count = 0

        # Detect best capture method
        self._detect_capture_method()

    def _detect_capture_method(self):
        """Detect the best available screen capture method."""
        # Try mss first (works on X11, fastest)
        try:
            test_sct = mss.mss()
            test_monitor = test_sct.monitors[1] if len(test_sct.monitors) > 1 else test_sct.monitors[0]
            test_sct.grab(test_monitor)
            test_sct.close()
            self.capture_method = 'mss'
            logging.info("Using mss for screen capture (X11)")
            return
        except (mss.exception.ScreenShotError, Exception) as e:
            logging.warning(f"mss not available: {e}")

        # Try Wayland screenshot tools
        session_type = os.environ.get('XDG_SESSION_TYPE', 'unknown')
        if session_type == 'wayland' or 'wayland' in os.environ.get('WAYLAND_DISPLAY', '').lower():
            logging.info("Wayland session detected, trying Wayland screenshot tools...")

            # Try grim (sway/wlroots)
            if self._try_tool(['grim', '--help'], 'grim'):
                return

            # Try spectacle (KDE)
            if self._try_tool(['spectacle', '--help'], 'spectacle'):
                return

            # Try gnome-screenshot (GNOME)
            if self._try_tool(['gnome-screenshot', '--help'], 'gnome-screenshot'):
                return

            logging.error("╔════════════════════════════════════════════════════════════════╗")
            logging.error("║  WAYLAND DETECTED - No compatible screenshot tool found!      ║")
            logging.error("╠════════════════════════════════════════════════════════════════╣")
            logging.error("║  Please install one of the following:                         ║")
            logging.error("║                                                                ║")
            logging.error("║  For KDE Plasma:                                               ║")
            logging.error("║    sudo dnf install spectacle                                  ║")
            logging.error("║                                                                ║")
            logging.error("║  For Sway/wlroots compositors:                                ║")
            logging.error("║    sudo dnf install grim                                       ║")
            logging.error("║                                                                ║")
            logging.error("║  For GNOME:                                                    ║")
            logging.error("║    sudo dnf install gnome-screenshot                           ║")
            logging.error("║                                                                ║")
            logging.error("║  Falling back to test pattern mode...                         ║")
            logging.error("╚════════════════════════════════════════════════════════════════╝")

        # Fallback to test pattern
        self.capture_method = 'headless'
        logging.warning("Running in HEADLESS mode with test pattern")

    def _try_tool(self, test_cmd, tool_name):
        """Try if a screenshot tool is available."""
        try:
            result = subprocess.run(test_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
            self.capture_method = tool_name
            logging.info(f"Using {tool_name} for screen capture (Wayland)")
            logging.warning(f"Performance note: {tool_name} is slower than native X11 capture. "
                          f"Expect ~5-15 FPS max. For better performance, use X11 session.")
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False

    def _get_sct(self):
        """Get or create thread-local mss instance."""
        if self.capture_method != 'mss':
            return None

        if not hasattr(self._thread_local, 'sct'):
            self._thread_local.sct = mss.mss()
        return self._thread_local.sct

    def get_monitor(self):
        """Get the monitor to capture (for mss)."""
        if self.capture_method != 'mss':
            return None

        sct = self._get_sct()
        if self.monitor == -1:
            # Capture all monitors
            return sct.monitors[0]
        elif 0 <= self.monitor < len(sct.monitors) - 1:
            # Capture specific monitor (monitors[0] is all, monitors[1+] are individual)
            return sct.monitors[self.monitor + 1]
        else:
            # Default to primary monitor
            return sct.monitors[1]

    def _get_cursor_position(self):
        """Get cursor position on X11 using xdotool."""
        try:
            result = subprocess.run(
                ['xdotool', 'getmouselocation', '--shell'],
                capture_output=True,
                text=True,
                timeout=0.1
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                pos = {}
                for line in lines:
                    if '=' in line:
                        key, value = line.split('=', 1)
                        pos[key] = int(value)
                return pos.get('X', 0), pos.get('Y', 0)
        except:
            pass
        return None

    def _draw_cursor(self, img, x, y):
        """Draw a simple cursor on the image."""
        draw = ImageDraw.Draw(img)
        # Draw a simple arrow cursor
        cursor_size = 20
        # Arrow points
        points = [
            (x, y),
            (x, y + cursor_size),
            (x + cursor_size//3, y + cursor_size*2//3),
            (x + cursor_size*2//3, y + cursor_size//3)
        ]
        # Draw cursor with black outline
        draw.polygon(points, fill='white', outline='black')

    def _capture_with_mss(self):
        """Capture screen using mss library."""
        sct = self._get_sct()
        monitor = self.get_monitor()
        screenshot = sct.grab(monitor)
        img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

        # Try to add cursor overlay
        cursor_pos = self._get_cursor_position()
        if cursor_pos:
            x, y = cursor_pos
            # Adjust coordinates relative to monitor
            monitor_left = monitor.get('left', 0)
            monitor_top = monitor.get('top', 0)
            rel_x = x - monitor_left
            rel_y = y - monitor_top
            if 0 <= rel_x < img.width and 0 <= rel_y < img.height:
                self._draw_cursor(img, rel_x, rel_y)

        return img

    def _capture_with_tool(self, tool_name):
        """Capture screen using external tool (grim, spectacle, gnome-screenshot)."""
        temp_file = os.path.join(self._temp_dir, f'screenshot_{self._frame_count}.png')

        try:
            # Reduced timeout for better responsiveness
            timeout = 0.5  # 500ms max per capture

            if tool_name == 'grim':
                # -c includes cursor
                subprocess.run(['grim', '-c', temp_file], check=True, timeout=timeout,
                             capture_output=True, stderr=subprocess.DEVNULL)
            elif tool_name == 'spectacle':
                # -p includes pointer/cursor, -b is background mode, -n is no notify, -o is output
                subprocess.run(['spectacle', '-bpno', temp_file], check=True, timeout=timeout,
                             capture_output=True, stderr=subprocess.DEVNULL)
            elif tool_name == 'gnome-screenshot':
                # -p includes pointer, -f is file output
                subprocess.run(['gnome-screenshot', '-p', '-f', temp_file], check=True, timeout=timeout,
                             capture_output=True, stderr=subprocess.DEVNULL)

            # Load the screenshot
            if os.path.exists(temp_file):
                img = Image.open(temp_file)
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Clean up
                try:
                    os.remove(temp_file)
                except:
                    pass
                return img
            else:
                raise Exception(f"Screenshot file not created by {tool_name}")

        except Exception as e:
            logging.error(f"Error capturing with {tool_name}: {e}")
            raise

    def generate_test_pattern(self):
        """
        Generate a test pattern frame for headless/demo mode.

        Returns:
            PIL.Image: Test pattern image
        """
        # Create a 1280x720 test pattern
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), color='#1a1a1a')
        draw = ImageDraw.Draw(img)

        # Draw colored bars
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
        bar_width = width // len(colors)
        for i, color in enumerate(colors):
            x0 = i * bar_width
            x1 = (i + 1) * bar_width if i < len(colors) - 1 else width
            draw.rectangle([x0, 0, x1, height // 3], fill=color)

        # Draw frame counter
        self._frame_count += 1
        text = f"QuickStream - HEADLESS MODE\nFrame: {self._frame_count}\nTest Pattern"

        # Try to use default font, fall back to basic if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        except:
            font = ImageFont.load_default()

        # Draw text with shadow
        text_x, text_y = width // 2 - 200, height // 2
        draw.text((text_x + 2, text_y + 2), text, fill='#000000', font=font)
        draw.text((text_x, text_y), text, fill='#ffffff', font=font)

        # Draw timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((20, height - 60), timestamp, fill='#ffffff', font=font)

        return img

    def capture_frame(self):
        """
        Capture a single frame from the screen.

        Returns:
            bytes: JPEG encoded frame
        """
        frame_start = time.time()

        if self.capture_method == 'headless':
            # Generate test pattern in headless mode
            img = self.generate_test_pattern()
        elif self.capture_method == 'mss':
            # Capture with mss (X11)
            img = self._capture_with_mss()
        elif self.capture_method in ('grim', 'spectacle', 'gnome-screenshot'):
            # Capture with Wayland tool
            img = self._capture_with_tool(self.capture_method)
        else:
            # Fallback to test pattern
            img = self.generate_test_pattern()

        # Encode as JPEG (optimize=False for speed)
        encode_start = time.time()
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=self.quality, optimize=False)
        encode_time = time.time() - encode_start

        total_time = time.time() - frame_start

        # Track FPS
        self._fps_frame_count += 1
        time_since_last_log = time.time() - self._last_fps_log
        if time_since_last_log >= 5.0:  # Log every 5 seconds
            actual_fps = self._fps_frame_count / time_since_last_log
            logging.info(f"Actual FPS: {actual_fps:.1f} (target: {self.fps}), "
                        f"avg frame time: {(time_since_last_log/self._fps_frame_count)*1000:.1f}ms")
            self._last_fps_log = time.time()
            self._fps_frame_count = 0

        # Log performance if frame takes longer than target
        if total_time > self.frame_delay * 1.5:  # Only warn if 50% over target
            logging.warning(
                f"Frame capture slow: {total_time*1000:.1f}ms (target: {self.frame_delay*1000:.1f}ms) "
                f"- capture: {(total_time-encode_time)*1000:.1f}ms, encode: {encode_time*1000:.1f}ms"
            )

        return buffer.getvalue()

    def generate_frames(self):
        """
        Generator that yields frames for MJPEG streaming.

        Yields:
            bytes: MJPEG frame with multipart headers
        """
        while not self._stop_event.is_set():
            start_time = time.time()

            try:
                frame = self.capture_frame()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            except Exception as e:
                logging.error(f"Error capturing frame: {e}")
                continue

            # Maintain target FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, self.frame_delay - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def stop(self):
        """Stop the screen capture."""
        self._stop_event.set()
        # Thread-local mss instances will be cleaned up when threads terminate

        # Clean up temporary directory
        try:
            import shutil
            if os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir)
        except Exception as e:
            logging.warning(f"Failed to clean up temp directory: {e}")


class Config:
    """Handles configuration loading and validation."""

    DEFAULT_CONFIG = {
        'process_name': 'quickstream',
        'host': '0.0.0.0',
        'port': 5000,
        'quality': 75,
        'fps': 30,
        'monitor': 0
    }

    def __init__(self, config_path='config.ini'):
        """
        Load configuration from file.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load configuration from INI file."""
        if not self.config_path.exists():
            logging.warning(f"Config file not found: {self.config_path}, using defaults")
            return

        parser = configparser.ConfigParser()
        try:
            parser.read(self.config_path)

            if 'server' in parser:
                server_config = parser['server']
                self.config['process_name'] = server_config.get('process_name', self.config['process_name'])
                self.config['host'] = server_config.get('host', self.config['host'])
                self.config['port'] = server_config.getint('port', self.config['port'])
                self.config['quality'] = server_config.getint('quality', self.config['quality'])
                self.config['fps'] = server_config.getint('fps', self.config['fps'])
                self.config['monitor'] = server_config.getint('monitor', self.config['monitor'])

            logging.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logging.error(f"Error loading config: {e}, using defaults")

    def get(self, key, default=None):
        """Get configuration value."""
        return self.config.get(key, default)


# HTML template for the viewer
VIEWER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QuickStream Viewer</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #1a1a1a;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            font-family: Arial, sans-serif;
            color: #fff;
        }
        h1 {
            margin: 20px;
            font-size: 24px;
        }
        #stream-container {
            position: relative;
            max-width: 95vw;
            max-height: 90vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        #stream {
            max-width: 100%;
            max-height: 90vh;
            border: 2px solid #333;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            cursor: pointer;
        }
        .info {
            margin: 10px;
            font-size: 14px;
            color: #888;
        }
        .status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 8px 16px;
            background-color: #28a745;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
        }
        .status.disconnected {
            background-color: #dc3545;
        }
        .fullscreen-btn {
            position: absolute;
            bottom: 20px;
            right: 20px;
            padding: 10px 20px;
            background-color: rgba(52, 152, 219, 0.9);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
            transition: background-color 0.3s, transform 0.1s;
            z-index: 100;
        }
        .fullscreen-btn:hover {
            background-color: rgba(41, 128, 185, 1);
            transform: scale(1.05);
        }
        .fullscreen-btn:active {
            transform: scale(0.95);
        }
        /* Fullscreen styles */
        #stream-container:fullscreen {
            background-color: #000;
            max-width: 100vw;
            max-height: 100vh;
        }
        #stream-container:fullscreen #stream {
            max-width: 100vw;
            max-height: 100vh;
            border: none;
        }
        #stream-container:-webkit-full-screen {
            background-color: #000;
            max-width: 100vw;
            max-height: 100vh;
        }
        #stream-container:-webkit-full-screen #stream {
            max-width: 100vw;
            max-height: 100vh;
            border: none;
        }
    </style>
</head>
<body>
    <div class="status" id="status">Connected</div>
    <h1>QuickStream</h1>
    <div id="stream-container">
        <img id="stream" src="/video_feed" alt="Stream">
        <button class="fullscreen-btn" id="fullscreen-btn" title="Toggle fullscreen (or double-click stream)">
            ⛶ Fullscreen
        </button>
    </div>
    <div class="info">Simple LAN Screen Streaming • Double-click or use fullscreen button</div>

    <script>
        const img = document.getElementById('stream');
        const status = document.getElementById('status');
        const streamContainer = document.getElementById('stream-container');
        const fullscreenBtn = document.getElementById('fullscreen-btn');

        // Monitor connection status
        img.addEventListener('error', function() {
            status.textContent = 'Disconnected';
            status.classList.add('disconnected');

            // Try to reconnect after 2 seconds
            setTimeout(function() {
                img.src = '/video_feed?' + new Date().getTime();
            }, 2000);
        });

        img.addEventListener('load', function() {
            status.textContent = 'Connected';
            status.classList.remove('disconnected');
        });

        // Fullscreen functionality
        function toggleFullscreen() {
            if (!document.fullscreenElement && !document.webkitFullscreenElement) {
                // Enter fullscreen
                if (streamContainer.requestFullscreen) {
                    streamContainer.requestFullscreen();
                } else if (streamContainer.webkitRequestFullscreen) {
                    streamContainer.webkitRequestFullscreen();
                }
            } else {
                // Exit fullscreen
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                }
            }
        }

        // Fullscreen button click
        fullscreenBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleFullscreen();
        });

        // Double-click on stream to toggle fullscreen
        img.addEventListener('dblclick', toggleFullscreen);

        // Update button text when fullscreen changes
        document.addEventListener('fullscreenchange', updateFullscreenButton);
        document.addEventListener('webkitfullscreenchange', updateFullscreenButton);

        function updateFullscreenButton() {
            if (document.fullscreenElement || document.webkitFullscreenElement) {
                fullscreenBtn.textContent = '⛶ Exit Fullscreen';
            } else {
                fullscreenBtn.textContent = '⛶ Fullscreen';
            }
        }
    </script>
</body>
</html>
"""


def create_app(config):
    """
    Create and configure the Flask application.

    Args:
        config: Config object

    Returns:
        Flask app instance
    """
    app = Flask(__name__)

    # Initialize screen capture
    screen_capture = ScreenCapture(
        monitor=config.get('monitor'),
        quality=config.get('quality'),
        fps=config.get('fps')
    )

    @app.route('/')
    def index():
        """Serve the viewer page."""
        return render_template_string(VIEWER_TEMPLATE)

    @app.route('/video_feed')
    def video_feed():
        """Video streaming route."""
        return Response(
            screen_capture.generate_frames(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    @app.route('/health')
    def health():
        """Health check endpoint."""
        return {'status': 'ok', 'service': 'quickstream'}

    # Store screen_capture for cleanup
    app.screen_capture = screen_capture

    return app


def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Load configuration
    config = Config('config.ini')

    # Set process name
    process_name = config.get('process_name')
    if setproctitle:
        setproctitle.setproctitle(process_name)
        logging.info(f"Process name set to: {process_name}")
    else:
        logging.warning("setproctitle not available, process name not changed")

    # Create Flask app
    app = create_app(config)

    # Get server configuration
    host = config.get('host')
    port = config.get('port')

    logging.info(f"Starting QuickStream server on {host}:{port}")
    logging.info(f"Open http://localhost:{port} in your browser to view the stream")
    logging.info(f"Other devices on your LAN can connect to http://YOUR_IP:{port}")

    try:
        # Run the Flask app
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        if hasattr(app, 'screen_capture'):
            app.screen_capture.stop()
        logging.info("Server stopped")


if __name__ == '__main__':
    main()
