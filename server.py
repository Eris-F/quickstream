#!/usr/bin/env python3
"""
QuickStream - Simple LAN Screen Streaming Service
A barebones, reliable screen sharing application for local networks.
"""

import io
import time
import configparser
import logging
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
        self.headless_mode = False
        # Use thread-local storage for mss instances (mss uses thread-local display connections)
        self._thread_local = local()

        self.monitor = monitor
        self.quality = quality
        self.fps = fps
        self.frame_delay = 1.0 / fps
        self._stop_event = Event()
        self._frame_count = 0

        # Test if screen capture actually works (not just if display exists)
        try:
            test_sct = mss.mss()
            # Actually try to capture to verify it works
            test_monitor = test_sct.monitors[1] if len(test_sct.monitors) > 1 else test_sct.monitors[0]
            test_sct.grab(test_monitor)
            test_sct.close()
            logging.info("Screen capture available - will stream actual screen")
        except (mss.exception.ScreenShotError, Exception) as e:
            logging.warning(f"Screen capture not available: {e}")
            logging.warning("Running in HEADLESS mode with test pattern")
            self.headless_mode = True

    def _get_sct(self):
        """Get or create thread-local mss instance."""
        if self.headless_mode:
            return None

        if not hasattr(self._thread_local, 'sct'):
            self._thread_local.sct = mss.mss()
        return self._thread_local.sct

    def get_monitor(self):
        """Get the monitor to capture."""
        if self.headless_mode:
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
        if self.headless_mode:
            # Generate test pattern in headless mode
            img = self.generate_test_pattern()
        else:
            # Capture actual screen
            sct = self._get_sct()
            monitor = self.get_monitor()
            screenshot = sct.grab(monitor)
            # Convert to PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

        # Encode as JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
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
        }
        .status.disconnected {
            background-color: #dc3545;
        }
    </style>
</head>
<body>
    <div class="status" id="status">Connected</div>
    <h1>QuickStream</h1>
    <div id="stream-container">
        <img id="stream" src="/video_feed" alt="Stream">
    </div>
    <div class="info">Simple LAN Screen Streaming</div>

    <script>
        const img = document.getElementById('stream');
        const status = document.getElementById('status');

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
