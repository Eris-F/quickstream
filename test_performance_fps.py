#!/usr/bin/env python3
"""
FPS Performance Benchmark Suite for QuickStream
Tests actual frame capture and encoding performance to verify 15+ FPS target.
"""

import time
import sys
import logging
from unittest.mock import Mock, patch
from PIL import Image
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

from server import ScreenCapture, SIMPLEJPEG_AVAILABLE


class FPSBenchmark:
    """Benchmark FPS performance for different configurations."""

    def __init__(self):
        self.results = []

    def benchmark_encoding(self, resolution, quality, fast_encoding=True, num_frames=100):
        """
        Benchmark JPEG encoding speed.

        Args:
            resolution: Tuple of (width, height)
            quality: JPEG quality (1-100)
            fast_encoding: Use fast encoding (simplejpeg)
            num_frames: Number of frames to encode

        Returns:
            dict: Benchmark results
        """
        width, height = resolution
        print(f"\n{'='*70}")
        print(f"Benchmarking: {width}x{height} @ quality={quality}, fast={fast_encoding}")
        print(f"{'='*70}")

        # Create test image
        test_img = Image.new('RGB', (width, height), color=(128, 64, 192))

        # Create mock capture
        with patch('server.mss.mss') as mock_mss:
            mock_sct = Mock()
            mock_sct.monitors = [Mock(), Mock()]
            mock_screenshot = Mock()
            mock_screenshot.size = (width, height)
            mock_screenshot.rgb = b'\x00' * (width * height * 3)
            mock_sct.grab.return_value = mock_screenshot
            mock_mss.return_value = mock_sct

            # Create capture with test settings
            capture = ScreenCapture(
                quality=quality,
                fps=30,
                max_width=None,
                max_height=None,
                fast_encoding=fast_encoding
            )

            # Override internal capture to return our test image
            original_capture = capture._capture_frame_internal
            capture._capture_frame_internal = lambda: test_img

            # Warm up (first frame is slower)
            for _ in range(5):
                capture.capture_frame()

            # Benchmark
            start_time = time.time()
            frame_times = []

            for i in range(num_frames):
                frame_start = time.time()
                jpeg_data = capture.capture_frame()
                frame_end = time.time()

                frame_time = frame_end - frame_start
                frame_times.append(frame_time)

                if (i + 1) % 20 == 0:
                    avg_fps = (i + 1) / (time.time() - start_time)
                    print(f"  Progress: {i+1}/{num_frames} frames, {avg_fps:.1f} FPS")

            total_time = time.time() - start_time
            avg_frame_time = sum(frame_times) / len(frame_times)
            min_frame_time = min(frame_times)
            max_frame_time = max(frame_times)
            avg_fps = num_frames / total_time

            # Calculate size
            final_frame = capture.capture_frame()
            frame_size_kb = len(final_frame) / 1024

            result = {
                'resolution': f'{width}x{height}',
                'quality': quality,
                'fast_encoding': fast_encoding,
                'encoder': 'simplejpeg' if fast_encoding and SIMPLEJPEG_AVAILABLE else 'PIL',
                'num_frames': num_frames,
                'total_time': total_time,
                'avg_fps': avg_fps,
                'avg_frame_time_ms': avg_frame_time * 1000,
                'min_frame_time_ms': min_frame_time * 1000,
                'max_frame_time_ms': max_frame_time * 1000,
                'frame_size_kb': frame_size_kb,
                'bandwidth_mbps': (avg_fps * frame_size_kb * 8) / 1024
            }

            capture.stop()

        return result

    def print_result(self, result):
        """Print benchmark result."""
        print(f"\n{'='*70}")
        print(f"RESULTS: {result['resolution']} @ Q{result['quality']} ({result['encoder']})")
        print(f"{'='*70}")
        print(f"  Average FPS:      {result['avg_fps']:.2f} FPS")
        print(f"  Avg Frame Time:   {result['avg_frame_time_ms']:.2f}ms")
        print(f"  Min Frame Time:   {result['min_frame_time_ms']:.2f}ms")
        print(f"  Max Frame Time:   {result['max_frame_time_ms']:.2f}ms")
        print(f"  Frame Size:       {result['frame_size_kb']:.1f} KB")
        print(f"  Bandwidth:        {result['bandwidth_mbps']:.2f} Mbps")

        # Check if meets target
        target_fps = 15
        if result['avg_fps'] >= target_fps:
            print(f"  ✅ MEETS TARGET:   {result['avg_fps']:.1f} >= {target_fps} FPS")
        else:
            shortfall = target_fps - result['avg_fps']
            print(f"  ❌ BELOW TARGET:   {result['avg_fps']:.1f} < {target_fps} FPS (need +{shortfall:.1f})")

        print(f"{'='*70}\n")

        self.results.append(result)

    def run_comprehensive_benchmarks(self):
        """Run comprehensive benchmarks across different configurations."""
        print("\n" + "="*70)
        print("QuickStream FPS Performance Benchmark Suite")
        print("="*70)
        print(f"simplejpeg available: {SIMPLEJPEG_AVAILABLE}")
        print("="*70)

        # Test configurations
        configs = [
            # High quality, full resolution (baseline)
            {'resolution': (1920, 1080), 'quality': 75, 'fast': False, 'desc': 'Baseline (PIL, Q75)'},
            {'resolution': (1920, 1080), 'quality': 75, 'fast': True, 'desc': 'Fast encoder (simplejpeg, Q75)'},

            # Optimized quality
            {'resolution': (1920, 1080), 'quality': 60, 'fast': False, 'desc': 'Lower quality (PIL, Q60)'},
            {'resolution': (1920, 1080), 'quality': 60, 'fast': True, 'desc': 'Optimized (simplejpeg, Q60)'},

            # Lower resolution
            {'resolution': (1280, 720), 'quality': 60, 'fast': False, 'desc': '720p (PIL, Q60)'},
            {'resolution': (1280, 720), 'quality': 60, 'fast': True, 'desc': '720p optimized (simplejpeg, Q60)'},

            # Aggressive optimization
            {'resolution': (1280, 720), 'quality': 50, 'fast': True, 'desc': 'Aggressive (720p, Q50)'},
        ]

        for i, config in enumerate(configs):
            print(f"\n[Test {i+1}/{len(configs)}] {config['desc']}")
            result = self.benchmark_encoding(
                resolution=config['resolution'],
                quality=config['quality'],
                fast_encoding=config['fast'],
                num_frames=50  # 50 frames for quick test
            )
            self.print_result(result)
            time.sleep(0.5)  # Brief pause between tests

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print summary of all benchmarks."""
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY")
        print("="*70)
        print(f"{'Configuration':<35} {'FPS':>10} {'Frame Time':>12} {'Status':>10}")
        print("-"*70)

        for result in self.results:
            config = f"{result['resolution']} Q{result['quality']} ({result['encoder']})"
            fps = f"{result['avg_fps']:.1f}"
            frame_time = f"{result['avg_frame_time_ms']:.1f}ms"
            status = "✅ PASS" if result['avg_fps'] >= 15 else "❌ FAIL"
            print(f"{config:<35} {fps:>10} {frame_time:>12} {status:>10}")

        print("="*70)

        # Find best configuration
        best = max(self.results, key=lambda r: r['avg_fps'])
        print(f"\n🏆 Best Performance: {best['resolution']} Q{best['quality']} ({best['encoder']})")
        print(f"   {best['avg_fps']:.1f} FPS, {best['avg_frame_time_ms']:.1f}ms per frame")

        # Count passing configurations
        passing = sum(1 for r in self.results if r['avg_fps'] >= 15)
        print(f"\n✅ {passing}/{len(self.results)} configurations meet 15+ FPS target")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if best['avg_fps'] >= 20:
            print("   - System can easily achieve 15+ FPS target")
            print("   - Consider using 1920x1080 @ Q60 for best quality")
        elif best['avg_fps'] >= 15:
            print("   - System meets 15+ FPS target with optimizations")
            print(f"   - Recommended: {best['resolution']} @ Q{best['quality']}")
        else:
            print("   - System may struggle to reach 15 FPS")
            print("   - Consider: Lower resolution (720p), lower quality, or screenshot tools")

        print("="*70 + "\n")


def main():
    """Run FPS benchmarks."""
    benchmark = FPSBenchmark()

    try:
        benchmark.run_comprehensive_benchmarks()
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\n\nBenchmark error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
