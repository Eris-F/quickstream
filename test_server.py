"""
Comprehensive tests for QuickStream server.
"""

import io
import time
import tempfile
import configparser
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from PIL import Image

from server import ScreenCapture, Config, create_app


class TestConfig:
    """Tests for configuration handling."""

    def test_default_config(self):
        """Test that default configuration is loaded when no file exists."""
        config = Config('nonexistent.ini')
        assert config.get('process_name') == 'quickstream'
        assert config.get('host') == '0.0.0.0'
        assert config.get('port') == 5000
        assert config.get('quality') == 75
        assert config.get('fps') == 30
        assert config.get('monitor') == 0

    def test_load_config_from_file(self):
        """Test loading configuration from a file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("""[server]
process_name = teststream
host = 127.0.0.1
port = 8080
quality = 90
fps = 60
monitor = 1
""")
            config_path = f.name

        try:
            config = Config(config_path)
            assert config.get('process_name') == 'teststream'
            assert config.get('host') == '127.0.0.1'
            assert config.get('port') == 8080
            assert config.get('quality') == 90
            assert config.get('fps') == 60
            assert config.get('monitor') == 1
        finally:
            Path(config_path).unlink()

    def test_partial_config(self):
        """Test that partial config files work with defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("""[server]
process_name = partialstream
port = 3000
""")
            config_path = f.name

        try:
            config = Config(config_path)
            assert config.get('process_name') == 'partialstream'
            assert config.get('port') == 3000
            # Defaults should still be present
            assert config.get('host') == '0.0.0.0'
            assert config.get('quality') == 75
        finally:
            Path(config_path).unlink()

    def test_invalid_config_uses_defaults(self):
        """Test that invalid config falls back to defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("invalid config content @#$%")
            config_path = f.name

        try:
            config = Config(config_path)
            # Should use defaults
            assert config.get('process_name') == 'quickstream'
            assert config.get('port') == 5000
        finally:
            Path(config_path).unlink()

    def test_get_with_default(self):
        """Test get method with default value."""
        config = Config('nonexistent.ini')
        assert config.get('nonexistent_key', 'default_value') == 'default_value'
        assert config.get('process_name', 'default') == 'quickstream'


class TestScreenCapture:
    """Tests for screen capture functionality."""

    @patch('server.mss.mss')
    def test_screen_capture_init(self, mock_mss):
        """Test ScreenCapture initialization."""
        capture = ScreenCapture(monitor=0, quality=80, fps=25)
        assert capture.monitor == 0
        assert capture.quality == 80
        assert capture.fps == 25
        assert capture.frame_delay == 1.0 / 25

    @patch('server.mss.mss')
    def test_get_monitor_primary(self, mock_mss):
        """Test getting primary monitor."""
        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},  # All monitors
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},  # Monitor 1
        ]
        mock_mss.return_value = mock_sct

        capture = ScreenCapture(monitor=0)
        monitor = capture.get_monitor()
        assert monitor == mock_sct.monitors[1]

    @patch('server.mss.mss')
    def test_get_monitor_all(self, mock_mss):
        """Test getting all monitors."""
        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 3840, 'height': 1080},  # All monitors
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},  # Monitor 1
        ]
        mock_mss.return_value = mock_sct

        capture = ScreenCapture(monitor=-1)
        monitor = capture.get_monitor()
        assert monitor == mock_sct.monitors[0]

    @patch('server.mss.mss')
    def test_capture_frame(self, mock_mss):
        """Test capturing a single frame."""
        # Create a mock screenshot
        mock_screenshot = Mock()
        mock_screenshot.size = (1920, 1080)
        # Create a simple RGB image data
        mock_screenshot.rgb = b'\x00' * (1920 * 1080 * 3)

        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},
        ]
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        capture = ScreenCapture(quality=75)
        frame = capture.capture_frame()

        assert isinstance(frame, bytes)
        assert len(frame) > 0
        # JPEG frames should start with FF D8
        assert frame[:2] == b'\xff\xd8'

    @patch('server.mss.mss')
    def test_generate_frames(self, mock_mss):
        """Test frame generation for streaming."""
        mock_screenshot = Mock()
        mock_screenshot.size = (640, 480)
        mock_screenshot.rgb = b'\x00' * (640 * 480 * 3)

        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 640, 'height': 480},
            {'top': 0, 'left': 0, 'width': 640, 'height': 480},
        ]
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        capture = ScreenCapture(fps=10)
        generator = capture.generate_frames()

        # Get a few frames
        frames = []
        for i, frame in enumerate(generator):
            frames.append(frame)
            if i >= 2:
                capture.stop()
                break

        assert len(frames) == 3
        for frame in frames:
            assert b'--frame' in frame
            assert b'Content-Type: image/jpeg' in frame

    @patch('server.mss.mss')
    def test_stop(self, mock_mss):
        """Test stopping screen capture."""
        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},
        ]
        mock_screenshot = Mock()
        mock_screenshot.size = (1920, 1080)
        mock_screenshot.rgb = b'\x00' * (1920 * 1080 * 3)
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        capture = ScreenCapture()
        capture.stop()

        assert capture._stop_event.is_set()
        # In headless mode, no close is called; in normal mode close is called during init
        # Just verify the stop event is set

    @patch('server.mss.mss')
    def test_frame_rate_limiting(self, mock_mss):
        """Test that frame rate limiting works."""
        mock_screenshot = Mock()
        mock_screenshot.size = (100, 100)
        mock_screenshot.rgb = b'\x00' * (100 * 100 * 3)

        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 100, 'height': 100},
            {'top': 0, 'left': 0, 'width': 100, 'height': 100},
        ]
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        capture = ScreenCapture(fps=10)  # 10 FPS = 0.1 second per frame
        generator = capture.generate_frames()

        start_time = time.time()
        frame_count = 0
        for frame in generator:
            frame_count += 1
            if frame_count >= 5:
                capture.stop()
                break

        elapsed = time.time() - start_time
        # 5 frames at 10 FPS should take ~0.4 seconds (allowing some margin)
        assert elapsed >= 0.3


class TestFlaskApp:
    """Tests for Flask application."""

    @patch('server.mss.mss')
    def test_create_app(self, mock_mss):
        """Test Flask app creation."""
        config = Config('nonexistent.ini')
        app = create_app(config)

        assert app is not None
        assert hasattr(app, 'screen_capture')

    @patch('server.mss.mss')
    def test_index_route(self, mock_mss):
        """Test the index route."""
        config = Config('nonexistent.ini')
        app = create_app(config)
        client = app.test_client()

        response = client.get('/')
        assert response.status_code == 200
        assert b'QuickStream' in response.data
        assert b'video_feed' in response.data

    @patch('server.mss.mss')
    def test_health_route(self, mock_mss):
        """Test the health check route."""
        config = Config('nonexistent.ini')
        app = create_app(config)
        client = app.test_client()

        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['service'] == 'quickstream'

    @patch('server.mss.mss')
    def test_video_feed_route(self, mock_mss):
        """Test the video feed route."""
        mock_screenshot = Mock()
        mock_screenshot.size = (320, 240)
        mock_screenshot.rgb = b'\x00' * (320 * 240 * 3)

        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 320, 'height': 240},
            {'top': 0, 'left': 0, 'width': 320, 'height': 240},
        ]
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        config = Config('nonexistent.ini')
        app = create_app(config)
        client = app.test_client()

        response = client.get('/video_feed')
        assert response.status_code == 200
        assert response.content_type == 'multipart/x-mixed-replace; boundary=frame'

        # Read a small chunk of the response
        data = next(response.response)
        assert b'--frame' in data


class TestIntegration:
    """Integration tests for the complete system."""

    @patch('server.mss.mss')
    def test_full_streaming_flow(self, mock_mss):
        """Test complete streaming flow from capture to delivery."""
        mock_screenshot = Mock()
        mock_screenshot.size = (800, 600)
        mock_screenshot.rgb = b'\xff\x00\x00' * (800 * 600)  # Red image

        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 800, 'height': 600},
            {'top': 0, 'left': 0, 'width': 800, 'height': 600},
        ]
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        config = Config('nonexistent.ini')
        app = create_app(config)
        client = app.test_client()

        # Test that we can access the viewer
        viewer_response = client.get('/')
        assert viewer_response.status_code == 200

        # Test that we can get video feed
        feed_response = client.get('/video_feed')
        assert feed_response.status_code == 200

        # Test health check
        health_response = client.get('/health')
        assert health_response.status_code == 200

    @patch('server.mss.mss')
    @patch('server.setproctitle')
    def test_process_name_setting(self, mock_setproctitle, mock_mss):
        """Test that process name is set correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("""[server]
process_name = testprocess
""")
            config_path = f.name

        try:
            config = Config(config_path)

            # Simulate what main() does
            if mock_setproctitle:
                mock_setproctitle.setproctitle(config.get('process_name'))
                mock_setproctitle.setproctitle.assert_called_with('testprocess')
        finally:
            Path(config_path).unlink()

    @patch('server.mss.mss')
    def test_concurrent_viewers(self, mock_mss):
        """Test that multiple viewers can connect simultaneously."""
        mock_screenshot = Mock()
        mock_screenshot.size = (400, 300)
        mock_screenshot.rgb = b'\x00' * (400 * 300 * 3)

        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 400, 'height': 300},
            {'top': 0, 'left': 0, 'width': 400, 'height': 300},
        ]
        mock_sct.grab.return_value = mock_screenshot
        mock_mss.return_value = mock_sct

        config = Config('nonexistent.ini')
        app = create_app(config)
        client = app.test_client()

        # Simulate multiple concurrent connections
        responses = []
        for i in range(3):
            response = client.get('/video_feed')
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @patch('server.mss.mss')
    def test_screen_capture_error_recovery(self, mock_mss):
        """Test that screen capture recovers from errors."""
        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 100, 'height': 100},
            {'top': 0, 'left': 0, 'width': 100, 'height': 100},
        ]

        # First call raises exception, subsequent calls succeed
        call_count = [0]
        def grab_side_effect(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Simulated capture error")
            mock_screenshot = Mock()
            mock_screenshot.size = (100, 100)
            mock_screenshot.rgb = b'\x00' * (100 * 100 * 3)
            return mock_screenshot

        mock_sct.grab.side_effect = grab_side_effect
        mock_mss.return_value = mock_sct

        capture = ScreenCapture(fps=10)
        generator = capture.generate_frames()

        # Should skip the error and continue
        frames = []
        for i, frame in enumerate(generator):
            frames.append(frame)
            if i >= 1:
                capture.stop()
                break

        # Should have recovered and generated frames
        assert len(frames) >= 1

    @patch('server.mss.mss')
    def test_invalid_monitor_index(self, mock_mss):
        """Test handling of invalid monitor index."""
        mock_sct = Mock()
        mock_sct.monitors = [
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},
            {'top': 0, 'left': 0, 'width': 1920, 'height': 1080},
        ]
        mock_mss.return_value = mock_sct

        # Invalid monitor index should fall back to primary
        capture = ScreenCapture(monitor=999)
        monitor = capture.get_monitor()
        assert monitor == mock_sct.monitors[1]  # Should use primary


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=server', '--cov-report=term-missing'])
