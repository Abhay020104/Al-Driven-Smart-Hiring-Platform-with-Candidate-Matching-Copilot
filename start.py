"""
Single launcher — starts the FastAPI backend and Streamlit frontend
in one terminal.  Press Ctrl+C to stop both.

Usage:
    python start.py
"""

import os
import signal
import subprocess
import sys
import time

import requests

# Force UTF-8 output on Windows to support emoji characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.abspath(__file__))

processes: list[subprocess.Popen] = []


def cleanup(*_):
    print("\n🛑 Shutting down...")
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    for p in processes:
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def check_ollama() -> bool:
    """Check if Ollama is reachable."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def kill_port(port: int) -> None:
    """Kill any process listening on the given port (Windows)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=5,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                print(f"  ⚠️  Port {port} is held by PID {pid} — killing it...")
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, timeout=5)
                time.sleep(1)  # wait for OS to release the port
    except Exception:
        pass



def main():
    print("=" * 60)
    print("  AI-Driven Smart Hiring Platform Copilot")
    print("=" * 60)
    print()

    # ── 1. Check Ollama ──────────────────────────────────────────
    if check_ollama():
        print("✅ Ollama is running")
    else:
        print("⚠️  Ollama not detected on port 11434")
        print("   AI features will be unavailable.")
        print("   To fix: run 'ollama serve' in another terminal.")
        print()

    # ── 2. Start Backend (FastAPI) ───────────────────────────────
    kill_port(8000)
    kill_port(8501)
    print("🚀 Starting backend (FastAPI) on http://localhost:8000 ...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", "8000", "--reload"],
        cwd=ROOT,
    )
    processes.append(backend)

    # Wait for backend to be ready
    for i in range(30):
        time.sleep(1)
        try:
            r = requests.get("http://localhost:8000", timeout=2)
            if r.status_code == 200:
                print("✅ Backend is ready")
                break
        except Exception:
            pass
    else:
        print("⚠️  Backend didn't respond in 30s, starting frontend anyway...")

    # ── 3. Start Frontend (Streamlit) ────────────────────────────
    print("🚀 Starting frontend (Streamlit) on http://localhost:8501 ...")
    frontend = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", "8501",
         "--server.headless", "true"],
        cwd=ROOT,
    )
    processes.append(frontend)

    print()
    print("=" * 60)
    print("  ✅ Everything is running!")
    print()
    print("  Frontend : http://localhost:8501")
    print("  Backend  : http://localhost:8000")
    print("  API Docs : http://localhost:8000/docs")
    print()
    print("  Press Ctrl+C to stop all services")
    print("=" * 60)
    print()

    # Keep alive until Ctrl+C or a process exits
    try:
        while True:
            # If either process dies, report it
            if backend.poll() is not None:
                print("❌ Backend exited unexpectedly!")
                cleanup()
            if frontend.poll() is not None:
                print("❌ Frontend exited unexpectedly!")
                cleanup()
            time.sleep(2)
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
