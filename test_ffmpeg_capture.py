"""
Comprehensive test suite for FFmpegPipeWireCapture edge cases and error handling.
"""

import io
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from threading import Event

import pytest

from server import FFmpegPipeWireCapture


class TestFFmpegCaptureInitialization:
    """Test FFmpeg capture initialization and error handling."""

    def test_init_creates_required_attributes(self):
        """Test that __init__ creates all required attributes."""
        capture = FFmpegPipeWireCapture()
        assert capture.process is None
        assert capture.width is None
        assert capture.height is None
        assert capture.frame_size is None
        assert capture._initialized is False
        assert capture._latest_frame is None
        assert capture._reader_thread is None
        assert capture._stop_event is not None

    @patch('server.is_wlroots_session')
    @patch('server.subprocess.run')
    def test_initialize_skips_wl_screenrec_on_non_wlroots(self, mock_run, mock_is_wlroots):
        """Test that wl-screenrec is skipped on non-wlroots sessions."""
        mock_is_wlroots.return_value = False
        capture = FFmpegPipeWireCapture()

        with pytest.raises(Exception, match="No suitable capture backend available"):
            capture.initialize()

        # wl-screenrec should not have been checked
        mock_is_wlroots.assert_called_once()

    @patch('server.is_wlroots_session')
    @patch('server.subprocess.run')
    def test_initialize_tries_wl_screenrec_on_wlroots(self, mock_run, mock_is_wlroots):
        """Test that wl-screenrec is attempted on wlroots sessions."""
        mock_is_wlroots.return_value = True
        mock_run.return_value = Mock(returncode=0)  # wl-screenrec found

        capture = FFmpegPipeWireCapture()

        # Will fail at Popen, but should try wl-screenrec first
        with pytest.raises(Exception):
            with patch('server.subprocess.Popen') as mock_popen:
                mock_popen.side_effect = FileNotFoundError()
                capture.initialize()

        mock_is_wlroots.assert_called_once()
        # Should have called subprocess.run at least once to check for wl-screenrec
        assert mock_run.call_count >= 1

    @patch('server.subprocess.run')
    def test_initialize_ffmpeg_not_found(self, mock_run):
        """Test initialization when ffmpeg is not found."""
        mock_run.side_effect = FileNotFoundError()
        capture = FFmpegPipeWireCapture()

        with pytest.raises(Exception, match="No suitable capture backend available"):
            capture.initialize()


class TestFFmpegCaptureProcessFailure:
    """Test handling of process failures and crashes."""

    @patch('server.subprocess.Popen')
    def test_wl_screenrec_immediate_exit(self, mock_popen):
        """Test handling when wl-screenrec exits immediately."""
        # Mock process that exits immediately
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Exited with code 1
        mock_process.returncode = 1
        mock_process.stderr.read.return_value = b"Error: No Wayland display"
        mock_process.stdout = Mock()
        mock_popen.return_value = mock_process

        capture = FFmpegPipeWireCapture()
        capture.width = 1920
        capture.height = 1080
        capture.frame_size = 1920 * 1080 * 3

        # Call _init_wl_screenrec directly
        with pytest.raises(Exception, match="wl-screenrec exited with code 1"):
            capture._init_wl_screenrec()

    @patch('server.subprocess.Popen')
    def test_ffmpeg_kmsgrab_permission_denied(self, mock_popen):
        """Test handling when ffmpeg kmsgrab fails due to permissions."""
        # Mock ffmpeg process that fails
        mock_process = Mock()
        mock_process.poll.return_value = 1
        mock_process.returncode = 1
        mock_process.stderr.read.return_value = b"Permission denied: /dev/dri/card0"
        mock_process.stdout = Mock()
        mock_popen.return_value = mock_process

        capture = FFmpegPipeWireCapture()
        capture.width = 1920
        capture.height = 1080
        capture.frame_size = 1920 * 1080 * 3

        # Call _init_ffmpeg_kmsgrab directly
        with pytest.raises(Exception, match="ffmpeg exited with code 1"):
            capture._init_ffmpeg_kmsgrab()

    @patch('server.subprocess.Popen')
    def test_process_timeout_no_frames(self, mock_popen):
        """Test timeout when process runs but produces no frames."""
        # Mock process that runs but produces no output
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_process.stdout = Mock()
        mock_process.stdout.read.return_value = b''  # No data
        mock_popen.return_value = mock_process

        capture = FFmpegPipeWireCapture()
        capture.width = 1920
        capture.height = 1080
        capture.frame_size = 1920 * 1080 * 3

        # Call _init_ffmpeg_kmsgrab directly
        with pytest.raises(Exception, match="No frames received from ffmpeg after 3 seconds"):
            capture._init_ffmpeg_kmsgrab()


class TestFFmpegFrameReader:
    """Test the frame reader thread behavior."""

    def test_frame_reader_detects_process_exit(self):
        """Test that frame reader detects when process exits."""
        capture = FFmpegPipeWireCapture()
        capture.width = 100
        capture.height = 100
        capture.frame_size = 100 * 100 * 3

        # Mock process that has already exited
        mock_process = Mock()
        mock_process.poll.return_value = 1  # Exit code
        mock_process.returncode = 1
        capture.process = mock_process

        # Run frame reader (should exit quickly)
        capture._frame_reader()

        # Should have checked poll
        mock_process.poll.assert_called()

    def test_frame_reader_handles_eof(self):
        """Test that frame reader handles EOF gracefully."""
        capture = FFmpegPipeWireCapture()
        capture.width = 100
        capture.height = 100
        capture.frame_size = 100 * 100 * 3

        # Mock process that returns EOF
        mock_process = Mock()
        mock_process.poll.return_value = None  # Still running
        mock_process.stdout = Mock()
        mock_process.stdout.read.return_value = b''  # EOF
        capture.process = mock_process

        # Run frame reader (should exit after max failures)
        capture._frame_reader()

        # Should have tried to read multiple times
        assert mock_process.stdout.read.call_count >= 5

    def test_frame_reader_handles_incomplete_frames(self):
        """Test that frame reader handles incomplete frames."""
        capture = FFmpegPipeWireCapture()
        capture.width = 100
        capture.height = 100
        capture.frame_size = 100 * 100 * 3  # 30000 bytes

        # Mock process that returns incomplete data
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.stdout = Mock()
        mock_process.stdout.read.return_value = b'incomplete' * 100  # Wrong size
        capture.process = mock_process

        # Run frame reader (should exit after max failures)
        capture._frame_reader()

        # Should have tried multiple times
        assert mock_process.stdout.read.call_count >= 5

    def test_frame_reader_processes_valid_frame(self):
        """Test that frame reader processes valid frames correctly."""
        capture = FFmpegPipeWireCapture()
        capture.width = 10
        capture.height = 10
        capture.frame_size = 10 * 10 * 3  # 300 bytes

        # Mock process with valid frame data
        mock_process = Mock()
        mock_process.poll.return_value = None

        # Create valid RGB data
        frame_data = b'\x00' * capture.frame_size

        # Return frame once, then EOF to stop
        call_count = [0]
        def read_side_effect(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return frame_data
            return b''  # EOF on subsequent calls

        mock_process.stdout = Mock()
        mock_process.stdout.read.side_effect = read_side_effect
        capture.process = mock_process

        # Run frame reader briefly
        capture._stop_event = Event()
        from threading import Thread
        reader = Thread(target=capture._frame_reader, daemon=True)
        reader.start()

        time.sleep(0.2)  # Let it process
        capture._stop_event.set()
        reader.join(timeout=1)

        # Should have captured a frame
        assert capture._latest_frame is not None


class TestFFmpegCaptureStop:
    """Test cleanup and stop behavior."""

    def test_stop_terminates_process(self):
        """Test that stop() terminates the process."""
        capture = FFmpegPipeWireCapture()

        mock_process = Mock()
        capture.process = mock_process

        capture.stop()

        mock_process.terminate.assert_called_once()

    def test_stop_kills_process_if_terminate_fails(self):
        """Test that stop() kills process if terminate hangs."""
        capture = FFmpegPipeWireCapture()

        mock_process = Mock()
        mock_process.wait.side_effect = subprocess.TimeoutExpired('cmd', 2)
        capture.process = mock_process

        capture.stop()

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_stop_waits_for_reader_thread(self):
        """Test that stop() waits for reader thread to exit."""
        capture = FFmpegPipeWireCapture()

        mock_thread = Mock()
        capture._reader_thread = mock_thread

        capture.stop()

        mock_thread.join.assert_called_once()

    def test_stop_sets_stop_event(self):
        """Test that stop() sets the stop event."""
        capture = FFmpegPipeWireCapture()

        assert not capture._stop_event.is_set()
        capture.stop()
        assert capture._stop_event.is_set()


class TestFFmpegResolutionDetection:
    """Test resolution detection methods."""

    @patch('server.subprocess.run')
    def test_detect_resolution_kscreen_doctor(self, mock_run):
        """Test resolution detection with kscreen-doctor."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Output 1\n  Resolution: 1920x1080\n"
        )

        capture = FFmpegPipeWireCapture()
        width, height = capture._detect_resolution()

        assert width == 1920
        assert height == 1080

    @patch('server.subprocess.run')
    def test_detect_resolution_wlr_randr(self, mock_run):
        """Test resolution detection with wlr-randr."""
        # kscreen-doctor fails, wlr-randr succeeds
        mock_run.side_effect = [
            Mock(returncode=1),  # kscreen-doctor fails
            Mock(returncode=0, stdout="Output DP-1\n  2560x1440 @ 144Hz (current)\n")
        ]

        capture = FFmpegPipeWireCapture()
        width, height = capture._detect_resolution()

        assert width == 2560
        assert height == 1440

    @patch('server.subprocess.run')
    def test_detect_resolution_fallback(self, mock_run):
        """Test resolution detection fallback to 1920x1080."""
        mock_run.side_effect = [
            Mock(returncode=1),  # kscreen-doctor fails
            Mock(returncode=1)   # wlr-randr fails
        ]

        capture = FFmpegPipeWireCapture()
        width, height = capture._detect_resolution()

        # Should fall back to default
        assert width == 1920
        assert height == 1080


class TestFFmpegCaptureFrame:
    """Test frame capture method."""

    def test_capture_frame_not_initialized_raises(self):
        """Test that capture_frame raises when not initialized."""
        capture = FFmpegPipeWireCapture()

        with pytest.raises(Exception, match="FFmpeg capture not initialized"):
            capture.capture_frame()

    def test_capture_frame_no_frame_available_raises(self):
        """Test that capture_frame raises when no frame available."""
        capture = FFmpegPipeWireCapture()
        capture._initialized = True
        capture._latest_frame = None

        with pytest.raises(Exception, match="No frame available"):
            capture.capture_frame()

    def test_capture_frame_returns_copy(self):
        """Test that capture_frame returns a copy of the frame."""
        from PIL import Image

        capture = FFmpegPipeWireCapture()
        capture._initialized = True
        capture._latest_frame = Image.new('RGB', (100, 100), color='red')

        frame1 = capture.capture_frame()
        frame2 = capture.capture_frame()

        # Should be different objects
        assert frame1 is not frame2  # Different Image objects
        assert frame1.size == frame2.size
        # But same pixel data
        assert list(frame1.getdata()) == list(frame2.getdata())


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
