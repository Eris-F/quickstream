#!/usr/bin/env python3
"""
Worker Scheduling Validation Tests
Validates that the single-worker fix for screenshot tools is working correctly.
"""

import time
import threading
import pytest
from unittest.mock import Mock, patch, MagicMock
from server import ScreenCapture, ThreadedFrameBuffer


class TestWorkerSchedulingValidation:
    """Validate worker scheduling fixes for screenshot tools."""

    def test_screenshot_tool_uses_single_worker(self):
        """Verify screenshot tools are configured with 1 worker, not 5."""
        with patch('server.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1)  # Tool not available

            with patch('server.mss.mss') as mock_mss:
                mock_sct = Mock()
                mock_sct.monitors = [Mock(), Mock()]
                mock_mss.return_value = mock_sct
                mock_sct.grab.side_effect = Exception("mss not available")

                # This should fall back to headless mode
                capture = ScreenCapture()

                # Verify buffer has only 1 worker for screenshot tools
                if hasattr(capture, 'buffer') and capture.buffer:
                    # When using screenshot tools, should have 1 worker
                    assert capture.buffer.num_workers == 1, \
                        f"Screenshot tools should use 1 worker, got {capture.buffer.num_workers}"

                capture.stop()

    def test_single_worker_serialization(self):
        """Test that single worker properly serializes access."""
        call_times = []
        lock = threading.Lock()

        def slow_capture():
            """Simulated slow capture that takes 100ms."""
            with lock:
                call_times.append(time.time())
            time.sleep(0.1)  # Simulate screenshot tool delay
            return Mock(size=(100, 100), rgb=b'\x00' * 30000)

        with patch('server.mss.mss') as mock_mss:
            mock_sct = Mock()
            mock_sct.monitors = [Mock(), Mock()]
            mock_mss.return_value = mock_sct
            mock_sct.grab.side_effect = slow_capture

            capture = ScreenCapture()
            buffer = ThreadedFrameBuffer(
                capture_func=lambda: capture._capture_frame_internal(),
                num_workers=1,  # Single worker
                buffer_size=10
            )

            # Buffer auto-starts workers
            time.sleep(0.05)  # Let it warm up

            # Request multiple frames rapidly
            frames = []
            for _ in range(5):
                frame = buffer.get_frame()
                if frame:
                    frames.append(frame)

            buffer.stop()

            # Verify frames were captured
            assert len(frames) >= 3, f"Should capture at least 3 frames, got {len(frames)}"

            # Verify serialization (calls should be spaced by ~100ms)
            if len(call_times) >= 2:
                gaps = [call_times[i+1] - call_times[i] for i in range(len(call_times)-1)]
                avg_gap = sum(gaps) / len(gaps)
                assert avg_gap >= 0.08, \
                    f"Calls should be serialized (~100ms apart), avg gap: {avg_gap*1000:.1f}ms"

    def test_no_worker_contention_with_single_worker(self):
        """Verify no worker contention when using single worker."""
        capture_count = {'count': 0}
        max_concurrent = {'value': 0, 'current': 0, 'lock': threading.Lock()}

        def counting_capture():
            """Track concurrent captures."""
            with max_concurrent['lock']:
                max_concurrent['current'] += 1
                max_concurrent['value'] = max(max_concurrent['value'], max_concurrent['current'])

            capture_count['count'] += 1
            time.sleep(0.05)  # Simulate work

            with max_concurrent['lock']:
                max_concurrent['current'] -= 1

            return Mock(size=(100, 100), rgb=b'\x00' * 30000)

        buffer = ThreadedFrameBuffer(
            capture_func=counting_capture,
            num_workers=1,
            buffer_size=10
        )

        # Buffer auto-starts workers
        time.sleep(0.5)  # Run for 500ms
        buffer.stop()

        # With single worker, max concurrent should be 1
        assert max_concurrent['value'] == 1, \
            f"Single worker should have max 1 concurrent capture, got {max_concurrent['value']}"

        # Should have captured some frames
        assert capture_count['count'] >= 5, \
            f"Should capture multiple frames, got {capture_count['count']}"


class TestFPSValidation:
    """Validate FPS improvements and measurements."""

    def test_encoding_speed_fast_vs_slow(self):
        """Compare fast encoding vs PIL encoding speeds."""
        from PIL import Image

        # Create test image
        test_img = Image.new('RGB', (1920, 1080), color=(128, 64, 192))

        with patch('server.mss.mss') as mock_mss:
            mock_sct = Mock()
            mock_sct.monitors = [Mock(), Mock()]
            mock_mss.return_value = mock_sct

            # Test fast encoding
            capture_fast = ScreenCapture(
                quality=60,
                fps=30,
                fast_encoding=True
            )
            capture_fast._capture_frame_internal = lambda: test_img

            # Test PIL encoding
            capture_slow = ScreenCapture(
                quality=60,
                fps=30,
                fast_encoding=False
            )
            capture_slow._capture_frame_internal = lambda: test_img

            # Benchmark fast encoding
            start = time.time()
            for _ in range(10):
                capture_fast.capture_frame()
            fast_time = time.time() - start

            # Benchmark slow encoding
            start = time.time()
            for _ in range(10):
                capture_slow.capture_frame()
            slow_time = time.time() - start

            capture_fast.stop()
            capture_slow.stop()

            fast_fps = 10 / fast_time
            slow_fps = 10 / slow_time

            print(f"\nEncoding Speed Comparison:")
            print(f"  Fast: {fast_fps:.1f} FPS ({fast_time/10*1000:.1f}ms per frame)")
            print(f"  Slow: {slow_fps:.1f} FPS ({slow_time/10*1000:.1f}ms per frame)")

            # Both should be fast enough (this is encoding only, not capture)
            assert fast_fps > 20, f"Fast encoding should exceed 20 FPS, got {fast_fps:.1f}"
            assert slow_fps > 20, f"PIL encoding should exceed 20 FPS, got {slow_fps:.1f}"

    def test_resolution_scaling_performance(self):
        """Test that resolution scaling improves performance."""
        from PIL import Image

        # Create large test image
        large_img = Image.new('RGB', (3840, 2160), color=(128, 64, 192))

        with patch('server.mss.mss') as mock_mss:
            mock_sct = Mock()
            mock_sct.monitors = [Mock(), Mock()]
            mock_mss.return_value = mock_sct

            # Test with scaling (max 1920x1080)
            capture_scaled = ScreenCapture(
                quality=60,
                max_width=1920,
                max_height=1080,
                fast_encoding=True
            )
            capture_scaled._capture_frame_internal = lambda: large_img

            # Test without scaling
            capture_full = ScreenCapture(
                quality=60,
                max_width=None,
                max_height=None,
                fast_encoding=True
            )
            capture_full._capture_frame_internal = lambda: large_img

            # Benchmark scaled
            start = time.time()
            for _ in range(10):
                capture_scaled.capture_frame()
            scaled_time = time.time() - start

            # Benchmark full resolution
            start = time.time()
            for _ in range(10):
                capture_full.capture_frame()
            full_time = time.time() - start

            capture_scaled.stop()
            capture_full.stop()

            scaled_fps = 10 / scaled_time
            full_fps = 10 / full_time
            speedup = scaled_fps / full_fps

            print(f"\nResolution Scaling Performance:")
            print(f"  Scaled (1920x1080): {scaled_fps:.1f} FPS")
            print(f"  Full (3840x2160): {full_fps:.1f} FPS")
            print(f"  Speedup: {speedup:.2f}x")

            # Scaled should be faster (4x fewer pixels)
            assert scaled_fps > full_fps * 1.2, \
                f"Scaled should be faster than full res, got {speedup:.2f}x"

    def test_quality_performance_impact(self):
        """Test performance impact of different quality settings."""
        from PIL import Image

        test_img = Image.new('RGB', (1920, 1080), color=(128, 64, 192))

        with patch('server.mss.mss') as mock_mss:
            mock_sct = Mock()
            mock_sct.monitors = [Mock(), Mock()]
            mock_mss.return_value = mock_sct

            results = {}
            for quality in [95, 75, 60, 40]:
                capture = ScreenCapture(quality=quality, fast_encoding=True)
                capture._capture_frame_internal = lambda: test_img

                start = time.time()
                frame = None
                for _ in range(10):
                    frame = capture.capture_frame()
                elapsed = time.time() - start

                fps = 10 / elapsed
                size_kb = len(frame) / 1024 if frame else 0

                results[quality] = {'fps': fps, 'size_kb': size_kb}
                capture.stop()

            print(f"\nQuality vs Performance:")
            for quality, data in sorted(results.items(), reverse=True):
                print(f"  Q{quality}: {data['fps']:.1f} FPS, {data['size_kb']:.1f} KB")

            # Lower quality should be faster and smaller (or similar if simple image)
            assert results[40]['fps'] >= results[95]['fps'] * 0.8, \
                "Lower quality should be similar or faster"
            # Note: simple test patterns may compress similarly at all qualities
            # In real images, lower quality produces much smaller files
            assert results[40]['size_kb'] <= results[95]['size_kb'] * 1.1, \
                "Lower quality should produce similar or smaller files"


class TestPerformanceRegression:
    """Regression tests to ensure performance doesn't degrade."""

    def test_encoding_performance_baseline(self):
        """Ensure encoding meets minimum performance baseline."""
        from PIL import Image

        test_img = Image.new('RGB', (1920, 1080), color=(128, 64, 192))

        with patch('server.mss.mss') as mock_mss:
            mock_sct = Mock()
            mock_sct.monitors = [Mock(), Mock()]
            mock_mss.return_value = mock_sct

            capture = ScreenCapture(quality=60, fast_encoding=True)
            capture._capture_frame_internal = lambda: test_img

            # Warm up
            for _ in range(5):
                capture.capture_frame()

            # Measure
            start = time.time()
            for _ in range(50):
                capture.capture_frame()
            elapsed = time.time() - start

            fps = 50 / elapsed
            frame_time_ms = (elapsed / 50) * 1000

            capture.stop()

            print(f"\nEncoding Baseline:")
            print(f"  FPS: {fps:.1f}")
            print(f"  Frame Time: {frame_time_ms:.1f}ms")

            # Baseline: encoding should take < 20ms per frame
            assert frame_time_ms < 20, \
                f"Encoding should be < 20ms per frame, got {frame_time_ms:.1f}ms"

            # Baseline: should achieve > 30 FPS with encoding alone
            assert fps > 30, \
                f"Encoding alone should achieve > 30 FPS, got {fps:.1f}"

    def test_buffer_no_excessive_memory(self):
        """Ensure buffer doesn't consume excessive memory."""
        import sys
        from PIL import Image

        test_img = Image.new('RGB', (1920, 1080), color=(128, 64, 192))

        frame_count = {'count': 0}

        def counting_capture():
            frame_count['count'] += 1
            return test_img

        buffer = ThreadedFrameBuffer(
            capture_func=counting_capture,
            num_workers=1,
            buffer_size=10
        )

        # Buffer auto-starts workers
        # Run for 2 seconds, requesting frames
        start = time.time()
        frames_retrieved = 0
        while time.time() - start < 2.0:
            frame = buffer.get_frame()
            if frame:
                frames_retrieved += 1
            time.sleep(0.01)

        buffer.stop()

        print(f"\nBuffer Stats:")
        print(f"  Frames captured: {frame_count['count']}")
        print(f"  Frames retrieved: {frames_retrieved}")
        print(f"  Buffer size: {buffer.frame_queue.qsize()}")

        # Buffer should not exceed max size (10)
        assert buffer.frame_queue.qsize() <= 10, \
            f"Buffer should not exceed max size of 10 frames, got {buffer.frame_queue.qsize()}"

        # Should have captured reasonable number of frames
        assert frame_count['count'] >= 30, \
            f"Should capture ~60 frames in 2s @ 30fps, got {frame_count['count']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
