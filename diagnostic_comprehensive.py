#!/usr/bin/env python3
"""
ULTRA-COMPREHENSIVE QuickStream Diagnostic Suite
Tests EVERY aspect of PipeWire, portals, GStreamer, DBus, and system configuration
to identify EXACTLY what's blocking stream initialization.
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

def print_subheader(text):
    print(f"\n{BOLD}{YELLOW}>>> {text}{RESET}")
    print(f"{YELLOW}{'-' * 80}{RESET}")

def print_success(text):
    print(f"{GREEN}   ✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}   ✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}   ⚠ {text}{RESET}")

def print_info(text):
    print(f"   → {text}")

# ============================================================================
# SECTION 1: SYSTEM ENVIRONMENT ANALYSIS
# ============================================================================

print_header("SECTION 1: ULTRA-DETAILED SYSTEM ENVIRONMENT ANALYSIS")

print_subheader("1.1 All Environment Variables")
env_vars = [
    'XDG_SESSION_TYPE', 'WAYLAND_DISPLAY', 'DISPLAY',
    'XDG_CURRENT_DESKTOP', 'XDG_SESSION_DESKTOP', 'DESKTOP_SESSION',
    'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS',
    'PIPEWIRE_RUNTIME_DIR', 'PIPEWIRE_LATENCY',
    'GST_DEBUG', 'GST_PLUGIN_PATH', 'GST_REGISTRY',
    'QT_QPA_PLATFORM', 'GDK_BACKEND',
    'XAUTHORITY', 'HOME', 'USER', 'PATH'
]

for var in env_vars:
    value = os.environ.get(var, '<not set>')
    if value != '<not set>':
        print_success(f"{var} = {value}")
    else:
        print_warning(f"{var} = {value}")

# Session detection
print_subheader("1.2 Session Type Detection")
is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
print_info(f"Wayland session: {is_wayland}")

desk = " ".join([
    os.environ.get("XDG_CURRENT_DESKTOP", ""),
    os.environ.get("XDG_SESSION_DESKTOP", ""),
    os.environ.get("DESKTOP_SESSION", "")
]).lower()

wlroots_keywords = ("sway", "hyprland", "wlroots", "river", "wayfire", "labwc", "niri")
is_wlroots = any(k in desk for k in wlroots_keywords)
is_kde = "kde" in desk or "plasma" in desk
is_gnome = "gnome" in desk

print_info(f"wlroots compositor: {is_wlroots}")
print_info(f"KDE/Plasma: {is_kde}")
print_info(f"GNOME: {is_gnome}")
print_info(f"Desktop string: '{desk}'")

# ============================================================================
# SECTION 2: PIPEWIRE SERVICE STATUS
# ============================================================================

print_header("SECTION 2: PIPEWIRE SERVICE STATUS AND CONFIGURATION")

print_subheader("2.1 PipeWire Service Status (systemd --user)")

services = ['pipewire.service', 'pipewire-pulse.service', 'wireplumber.service']
for service in services:
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'status', service],
            capture_output=True,
            text=True,
            timeout=2
        )
        if 'Active: active (running)' in result.stdout:
            print_success(f"{service} is running")
        elif 'Active: inactive' in result.stdout:
            print_error(f"{service} is INACTIVE")
        elif 'could not be found' in result.stdout or 'could not be found' in result.stderr:
            print_warning(f"{service} not found/not installed")
        else:
            print_warning(f"{service} status unknown")

        # Show last few log lines
        print_info(f"Recent logs for {service}:")
        log_result = subprocess.run(
            ['journalctl', '--user', '-u', service, '-n', '5', '--no-pager'],
            capture_output=True,
            text=True,
            timeout=2
        )
        for line in log_result.stdout.split('\n')[-5:]:
            if line.strip():
                print(f"      {line}")
    except Exception as e:
        print_error(f"Error checking {service}: {e}")

print_subheader("2.2 PipeWire Runtime Directory")
runtime_dir = os.environ.get('XDG_RUNTIME_DIR', '')
if runtime_dir:
    print_success(f"XDG_RUNTIME_DIR: {runtime_dir}")

    pipewire_socket = Path(runtime_dir) / 'pipewire-0'
    if pipewire_socket.exists():
        print_success(f"PipeWire socket exists: {pipewire_socket}")
        print_info(f"Socket permissions: {oct(pipewire_socket.stat().st_mode)[-3:]}")
    else:
        print_error(f"PipeWire socket NOT found: {pipewire_socket}")
else:
    print_error("XDG_RUNTIME_DIR not set!")

print_subheader("2.3 PipeWire Process Information")
try:
    result = subprocess.run(
        ['ps', 'aux'],
        capture_output=True,
        text=True,
        timeout=2
    )
    pipewire_procs = [line for line in result.stdout.split('\n') if 'pipewire' in line.lower() and not 'grep' in line]
    if pipewire_procs:
        print_success(f"Found {len(pipewire_procs)} PipeWire-related processes:")
        for proc in pipewire_procs:
            print(f"      {proc}")
    else:
        print_error("NO PipeWire processes found!")
except Exception as e:
    print_error(f"Error checking processes: {e}")

print_subheader("2.4 PipeWire Command Line Tools")
pw_tools = ['pw-cli', 'pw-dump', 'pw-top', 'wpctl']
for tool in pw_tools:
    try:
        result = subprocess.run(['which', tool], capture_output=True, timeout=1)
        if result.returncode == 0:
            print_success(f"{tool} found: {result.stdout.decode().strip()}")
        else:
            print_warning(f"{tool} not found")
    except Exception as e:
        print_error(f"Error checking {tool}: {e}")

# Test pw-cli info
print_subheader("2.5 PipeWire Node Information (pw-cli)")
try:
    result = subprocess.run(
        ['pw-cli', 'info', 'all'],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        print_success("pw-cli info succeeded")
        print_info("First 20 lines of output:")
        for line in result.stdout.split('\n')[:20]:
            if line.strip():
                print(f"      {line}")
    else:
        print_error(f"pw-cli info failed with code {result.returncode}")
        print_info(f"Error: {result.stderr[:500]}")
except Exception as e:
    print_error(f"pw-cli error: {e}")

# ============================================================================
# SECTION 3: DBUS AND PORTAL ANALYSIS
# ============================================================================

print_header("SECTION 3: ULTRA-DETAILED DBUS AND PORTAL ANALYSIS")

print_subheader("3.1 DBus Session Bus")
dbus_addr = os.environ.get('DBUS_SESSION_BUS_ADDRESS', '')
if dbus_addr:
    print_success(f"DBUS_SESSION_BUS_ADDRESS: {dbus_addr}")
else:
    print_error("DBUS_SESSION_BUS_ADDRESS not set!")

print_subheader("3.2 Portal Process Status")
try:
    result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=2)
    portal_procs = [line for line in result.stdout.split('\n')
                   if 'xdg-desktop-portal' in line and not 'grep' in line]
    if portal_procs:
        print_success(f"Found {len(portal_procs)} portal processes:")
        for proc in portal_procs:
            print(f"      {proc}")
    else:
        print_error("NO xdg-desktop-portal processes found!")
except Exception as e:
    print_error(f"Error checking portal processes: {e}")

print_subheader("3.3 Portal DBus Interface Detection")
try:
    result = subprocess.run(
        ['busctl', '--user', 'list'],
        capture_output=True,
        text=True,
        timeout=3
    )
    if result.returncode == 0:
        portal_services = [line for line in result.stdout.split('\n')
                          if 'desktop.portal' in line.lower()]
        if portal_services:
            print_success(f"Found {len(portal_services)} portal services on DBus:")
            for svc in portal_services:
                print(f"      {svc}")
        else:
            print_error("NO portal services found on DBus!")
    else:
        print_error(f"busctl failed: {result.stderr}")
except Exception as e:
    print_error(f"busctl error: {e}")

print_subheader("3.4 Detailed Portal ScreenCast Interface Introspection")
try:
    result = subprocess.run(
        [
            'busctl', '--user', 'introspect',
            'org.freedesktop.portal.Desktop',
            '/org/freedesktop/portal/desktop'
        ],
        capture_output=True,
        text=True,
        timeout=3
    )
    if result.returncode == 0:
        print_success("Portal DBus interface introspection succeeded!")
        print_info("Looking for ScreenCast methods:")
        for line in result.stdout.split('\n'):
            if 'ScreenCast' in line or 'CreateSession' in line or 'SelectSources' in line or 'Start' in line:
                print(f"      {line}")
    else:
        print_error(f"Portal introspection failed: {result.stderr}")
except Exception as e:
    print_error(f"Portal introspection error: {e}")

print_subheader("3.5 Portal Configuration Files")
portal_config_paths = [
    Path.home() / '.config/xdg-desktop-portal',
    Path('/etc/xdg-desktop-portal'),
    Path('/usr/share/xdg-desktop-portal'),
]

for config_path in portal_config_paths:
    if config_path.exists():
        print_success(f"Portal config path exists: {config_path}")
        try:
            for file in config_path.rglob('*'):
                if file.is_file():
                    print_info(f"Config file: {file}")
                    with open(file, 'r') as f:
                        print(f"      Content:\n{f.read()}")
        except Exception as e:
            print_warning(f"Error reading config: {e}")
    else:
        print_warning(f"Portal config path not found: {config_path}")

# ============================================================================
# SECTION 4: GSTREAMER ULTRA-DETAILED ANALYSIS
# ============================================================================

print_header("SECTION 4: ULTRA-DETAILED GSTREAMER ANALYSIS")

print_subheader("4.1 GStreamer Import and Version")
try:
    import gi
    print_success(f"PyGObject (gi) import successful")
    print_info(f"PyGObject version: {gi.__version__}")

    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    print_success(f"GStreamer initialized successfully")
    print_info(f"GStreamer version: {Gst.version()}")
    print_info(f"GStreamer version string: {Gst.version_string()}")
except Exception as e:
    print_error(f"GStreamer initialization failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print_subheader("4.2 GStreamer Plugin Registry")
try:
    registry = Gst.Registry.get()
    print_success(f"Got GStreamer registry")

    all_plugins = registry.get_plugin_list()
    print_info(f"Total plugins registered: {len(all_plugins)}")

    # Check for PipeWire plugin
    print_info("\nSearching for PipeWire-related plugins:")
    pipewire_plugins = [p for p in all_plugins if 'pipe' in p.get_name().lower() or 'wire' in p.get_name().lower()]
    if pipewire_plugins:
        for plugin in pipewire_plugins:
            print_success(f"Found plugin: {plugin.get_name()}")
            print_info(f"  Description: {plugin.get_description()}")
            print_info(f"  Filename: {plugin.get_filename()}")
            print_info(f"  Version: {plugin.get_version()}")
    else:
        print_error("NO PipeWire plugins found!")
except Exception as e:
    print_error(f"Plugin registry error: {e}")

print_subheader("4.3 GStreamer Element Availability")
elements_to_check = [
    'pipewiresrc',
    'fakesink',
    'videoconvert',
    'videoscale',
    'capsfilter',
    'appsink'
]

for element_name in elements_to_check:
    try:
        factory = Gst.ElementFactory.find(element_name)
        if factory:
            print_success(f"Element factory found: {element_name}")
            print_info(f"  Rank: {factory.get_rank()}")
            print_info(f"  Metadata: {factory.get_metadata('long-name')}")

            # Try to actually create it
            element = Gst.ElementFactory.make(element_name, None)
            if element:
                print_success(f"  Successfully created {element_name} element!")
            else:
                print_error(f"  Factory exists but FAILED to create {element_name}")
        else:
            print_error(f"Element factory NOT found: {element_name}")
    except Exception as e:
        print_error(f"Error checking element {element_name}: {e}")

print_subheader("4.4 GStreamer Pipeline Creation Test")
pipelines_to_test = [
    ("Basic fakesink", "fakesink"),
    ("VideoTestSrc", "videotestsrc ! fakesink"),
    ("PipeWire source (minimal)", "pipewiresrc ! fakesink"),
    ("PipeWire with caps", "pipewiresrc ! video/x-raw ! fakesink"),
]

for pipeline_name, pipeline_str in pipelines_to_test:
    print_info(f"\nTesting pipeline: {pipeline_name}")
    print_info(f"  Pipeline string: {pipeline_str}")
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        print_success(f"  Pipeline created successfully")

        # Try to set to READY state
        ret = pipeline.set_state(Gst.State.READY)
        print_info(f"  set_state(READY) returned: {ret}")

        if ret == Gst.StateChangeReturn.FAILURE:
            print_error(f"  Pipeline FAILED to reach READY state")
        else:
            print_success(f"  Pipeline reached READY state")

        # Clean up
        pipeline.set_state(Gst.State.NULL)

    except Exception as e:
        print_error(f"  Pipeline creation error: {type(e).__name__}: {e}")

print_subheader("4.5 GStreamer Environment Variables")
gst_env_vars = ['GST_DEBUG', 'GST_PLUGIN_PATH', 'GST_PLUGIN_SYSTEM_PATH',
                'GST_REGISTRY', 'GST_DEBUG_FILE', 'GST_DEBUG_DUMP_DOT_DIR']
for var in gst_env_vars:
    value = os.environ.get(var, '<not set>')
    if value != '<not set>':
        print_info(f"{var} = {value}")
    else:
        print_info(f"{var} = {value}")

# ============================================================================
# SECTION 5: PYDBUS AND PORTAL COMMUNICATION TEST
# ============================================================================

print_header("SECTION 5: PYDBUS AND PORTAL COMMUNICATION TEST")

print_subheader("5.1 pydbus Import Test")
try:
    import pydbus
    print_success("pydbus imported successfully")
    print_info(f"pydbus version: {pydbus.__version__ if hasattr(pydbus, '__version__') else 'unknown'}")
except ImportError as e:
    print_error(f"pydbus import FAILED: {e}")
    print_error("CRITICAL: pydbus is required for portal communication!")
    print_info("Install with: pip install pydbus")
    pydbus = None

if pydbus:
    print_subheader("5.2 Session Bus Connection")
    try:
        bus = pydbus.SessionBus()
        print_success("Connected to session bus")
    except Exception as e:
        print_error(f"Failed to connect to session bus: {e}")
        bus = None

    if bus:
        print_subheader("5.3 Portal Desktop Object Access")
        try:
            portal = bus.get('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
            print_success("Got portal desktop object")
            print_info(f"Portal object: {portal}")
        except Exception as e:
            print_error(f"Failed to get portal object: {e}")
            print_error(f"Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            portal = None

        if portal:
            print_subheader("5.4 Portal ScreenCast Interface Access")
            try:
                # Try to access ScreenCast interface
                print_info("Attempting to access portal.ScreenCast...")
                screencast = portal.ScreenCast
                print_success("ScreenCast interface accessible!")
                print_info(f"ScreenCast object: {screencast}")
            except AttributeError as e:
                print_error(f"ScreenCast interface NOT accessible: {e}")
                print_error("Portal may not support ScreenCast interface!")
            except Exception as e:
                print_error(f"Error accessing ScreenCast: {type(e).__name__}: {e}")

            print_subheader("5.5 Portal Version and Interfaces")
            try:
                # Try to introspect portal
                print_info("Portal introspection:")
                if hasattr(portal, 'version'):
                    print_info(f"  Portal version: {portal.version}")

                # List all available interfaces/methods
                print_info("  Available attributes:")
                for attr in dir(portal):
                    if not attr.startswith('_'):
                        print(f"      {attr}")
            except Exception as e:
                print_error(f"Portal introspection error: {e}")

            print_subheader("5.6 Attempt to Create ScreenCast Session")
            try:
                print_info("Creating session options...")
                session_options = {
                    'session_handle_token': 'quickstream_session',
                    'handle_token': 'quickstream_handle'
                }

                print_info(f"Options: {session_options}")
                print_info("Calling CreateSession...")

                # This will likely fail, but we want to see HOW it fails
                response = portal.CreateSession(session_options)
                print_success(f"CreateSession returned: {response}")

            except AttributeError as e:
                print_error(f"CreateSession method not found: {e}")
                print_error("Portal may not expose ScreenCast.CreateSession")
            except Exception as e:
                print_error(f"CreateSession failed: {type(e).__name__}: {e}")
                print_info("This is expected if portal requires user interaction")
                import traceback
                print_info("Full traceback:")
                traceback.print_exc()

# ============================================================================
# SECTION 6: ACTUAL PIPEWIRE CAPTURE ATTEMPT WITH FULL LOGGING
# ============================================================================

print_header("SECTION 6: ACTUAL PIPEWIRE CAPTURE ATTEMPT WITH ULTRA-VERBOSE LOGGING")

print_subheader("6.1 Enable GStreamer Debug Logging")
os.environ['GST_DEBUG'] = '4'  # Set to level 4 for detailed logging
print_info("Set GST_DEBUG=4 for detailed GStreamer logging")

print_subheader("6.2 Test PipeWire Source with State Changes")
try:
    from gi.repository import Gst

    print_info("Creating pipewiresrc element...")
    src = Gst.ElementFactory.make('pipewiresrc', 'pwsrc')
    if not src:
        print_error("FAILED to create pipewiresrc element!")
    else:
        print_success("pipewiresrc element created")

        print_info("Creating fakesink element...")
        sink = Gst.ElementFactory.make('fakesink', 'sink')

        print_info("Creating pipeline...")
        pipeline = Gst.Pipeline.new('test-pipeline')

        print_info("Adding elements to pipeline...")
        pipeline.add(src)
        pipeline.add(sink)

        print_info("Linking elements...")
        if src.link(sink):
            print_success("Elements linked successfully")
        else:
            print_error("FAILED to link elements!")

        print_info("\n=== Attempting state changes ===")

        # NULL -> READY
        print_info("Setting pipeline to READY...")
        ret = pipeline.set_state(Gst.State.READY)
        print_info(f"  Result: {ret}")
        if ret == Gst.StateChangeReturn.FAILURE:
            print_error("  FAILED to reach READY state!")
        else:
            print_success("  Reached READY state")

        # READY -> PAUSED
        print_info("Setting pipeline to PAUSED...")
        ret = pipeline.set_state(Gst.State.PAUSED)
        print_info(f"  Result: {ret}")
        if ret == Gst.StateChangeReturn.FAILURE:
            print_error("  FAILED to reach PAUSED state!")
        elif ret == Gst.StateChangeReturn.ASYNC:
            print_warning("  State change is ASYNC, waiting...")
            ret2, state, pending = pipeline.get_state(5 * Gst.SECOND)
            print_info(f"  After wait: {ret2}, state={state}, pending={pending}")
        else:
            print_success("  Reached PAUSED state")

        # Check for errors on bus
        print_info("\nChecking pipeline bus for messages...")
        bus = pipeline.get_bus()
        msg_count = 0
        while True:
            msg = bus.pop()
            if not msg:
                break
            msg_count += 1
            print_info(f"  Message {msg_count}: {msg.type}")

            if msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print_error(f"    ERROR: {err}")
                print_error(f"    Debug: {debug}")
            elif msg.type == Gst.MessageType.WARNING:
                warn, debug = msg.parse_warning()
                print_warning(f"    WARNING: {warn}")
                print_info(f"    Debug: {debug}")
            elif msg.type == Gst.MessageType.INFO:
                info, debug = msg.parse_info()
                print_info(f"    INFO: {info}")
            elif msg.type == Gst.MessageType.STATE_CHANGED:
                old, new, pending = msg.parse_state_changed()
                print_info(f"    State changed: {old} -> {new} (pending: {pending})")

        if msg_count == 0:
            print_info("  No messages on bus")

        # Clean up
        print_info("\nCleaning up...")
        pipeline.set_state(Gst.State.NULL)
        print_success("Pipeline cleanup complete")

except Exception as e:
    print_error(f"Pipeline test error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# SECTION 7: QUICKSTREAM SERVER CAPTURE TEST
# ============================================================================

print_header("SECTION 7: QUICKSTREAM SERVER CAPTURE INITIALIZATION TEST")

print_subheader("7.1 Import QuickStream server module")
try:
    import server
    print_success("server module imported successfully")
except Exception as e:
    print_error(f"Failed to import server: {e}")
    import traceback
    traceback.print_exc()
    server = None

if server:
    print_subheader("7.2 Test PipeWirePortalCapture initialization")
    try:
        print_info("Creating PipeWirePortalCapture instance...")
        capture = server.PipeWirePortalCapture()
        print_success("PipeWirePortalCapture instance created")

        print_info("\nCalling initialize() with maximum verbosity...")
        print_info("=" * 80)

        # Temporarily increase logging level
        import logging
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

        try:
            capture.initialize()
            print_success("initialize() completed successfully!")
            print_success("PipeWire portal capture is WORKING!")

            print_info("\nTrying to capture a frame...")
            frame = capture.capture_frame()
            print_success(f"Frame captured! Size: {frame.size if hasattr(frame, 'size') else 'unknown'}")

            capture.stop()

        except Exception as init_error:
            print_error(f"initialize() FAILED: {type(init_error).__name__}: {init_error}")
            print_info("\nFull error traceback:")
            import traceback
            traceback.print_exc()

            print_info("\n=== ANALYZING FAILURE ===")
            print_info("Checking capture object state:")
            print_info(f"  _initialized: {getattr(capture, '_initialized', 'N/A')}")
            print_info(f"  gst_pipeline: {getattr(capture, 'gst_pipeline', 'N/A')}")
            print_info(f"  session_path: {getattr(capture, 'session_path', 'N/A')}")

    except Exception as e:
        print_error(f"Failed to create PipeWirePortalCapture: {e}")
        import traceback
        traceback.print_exc()

    print_subheader("7.3 Test FFmpegPipeWireCapture initialization")
    try:
        print_info("Creating FFmpegPipeWireCapture instance...")
        ffmpeg_capture = server.FFmpegPipeWireCapture()
        print_success("FFmpegPipeWireCapture instance created")

        print_info("\nCalling initialize()...")
        try:
            ffmpeg_capture.initialize()
            print_success("FFmpegPipeWireCapture initialized successfully!")

            frame = ffmpeg_capture.capture_frame()
            print_success(f"Frame captured! Size: {frame.size if hasattr(frame, 'size') else 'unknown'}")

            ffmpeg_capture.stop()

        except Exception as init_error:
            print_error(f"FFmpegPipeWireCapture.initialize() FAILED: {init_error}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print_error(f"Failed to create FFmpegPipeWireCapture: {e}")

# ============================================================================
# FINAL SUMMARY
# ============================================================================

print_header("DIAGNOSTIC COMPLETE - SUMMARY OF FINDINGS")

print("\nThis comprehensive diagnostic has tested:")
print("  1. System environment and session detection")
print("  2. PipeWire service status and sockets")
print("  3. DBus and portal availability")
print("  4. GStreamer plugins and elements")
print("  5. pydbus portal communication")
print("  6. Actual PipeWire capture attempts")
print("  7. QuickStream server initialization")
print("\nPlease send the COMPLETE output of this diagnostic back for analysis.")
print(f"\n{BOLD}To save output to file:{RESET}")
print(f"  python3 diagnostic_comprehensive.py > diagnostic_output.txt 2>&1")
