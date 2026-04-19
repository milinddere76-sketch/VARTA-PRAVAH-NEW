#!/usr/bin/env python3
"""
VartaPravah Quick Start Script
Starts all services and runs diagnostics to verify the streaming pipeline.
"""

import subprocess
import time
import sys
import os
import requests

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n🔧 {description}")
    print(f"   Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"   ✅ Success")
            return True
        else:
            print(f"   ❌ Failed (exit code {result.returncode})")
            print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"   ⏱️ Timeout after 5 minutes")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def check_service(url, name, timeout=5):
    """Check if a service is responding."""
    try:
        response = requests.get(url, timeout=timeout)
        if response.ok:
            print(f"   ✅ {name} responding")
            return True
        else:
            print(f"   ⚠️ {name} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ {name} not responding: {e}")
        return False

def main():
    print("="*60)
    print("🚀 VARTA PRAVAH - QUICK START")
    print("="*60)

    # Step 1: Start Docker services
    print("\n📦 Starting Docker Services...")
    if not run_command("docker compose -f docker-compose.yml up -d", "Starting postgres, temporal, and temporal-ui"):
        print("❌ Failed to start Docker services. Check Docker is running.")
        return False

    # Step 2: Wait for services to be ready
    print("\n⏳ Waiting for services to initialize...")
    time.sleep(30)

    # Step 3: Check core services
    print("\n🔍 Checking Core Services...")

    services_ok = True
    services_ok &= check_service("http://localhost:7233", "Temporal Server")
    services_ok &= check_service("http://localhost:8080", "Temporal UI")

    if not services_ok:
        print("⚠️ Some core services not ready yet. Waiting longer...")
        time.sleep(30)
        services_ok &= check_service("http://localhost:7233", "Temporal Server")
        services_ok &= check_service("http://localhost:8080", "Temporal UI")

    # Step 4: Start backend services
    print("\n🏗️ Starting Backend Services...")

    # Start backend in background
    backend_cmd = "docker compose -f docker-compose.yml up -d backend backend-worker"
    if not run_command(backend_cmd, "Starting backend API and worker"):
        print("❌ Failed to start backend services.")
        return False

    # Wait for backend to start
    print("\n⏳ Waiting for backend to start...")
    time.sleep(20)

    # Step 5: Check backend services
    print("\n🔍 Checking Backend Services...")
    backend_ok = check_service("http://localhost:8000/health", "Backend API")
    broadcast_ok = check_service("http://localhost:8001/status", "Broadcast Controller")

    if not backend_ok or not broadcast_ok:
        print("⚠️ Backend services not ready. Waiting longer...")
        time.sleep(20)
        backend_ok = check_service("http://localhost:8000/health", "Backend API")
        broadcast_ok = check_service("http://localhost:8001/status", "Broadcast Controller")

    # Step 6: Run diagnostics
    print("\n📊 Running Pipeline Diagnostics...")
    try:
        result = subprocess.run([sys.executable, "backend/diagnose_pipeline.py"],
                              capture_output=True, text=True, timeout=30)
        print(result.stdout)
        if result.returncode != 0:
            print(f"⚠️ Diagnostics completed with warnings: {result.stderr}")
    except Exception as e:
        print(f"❌ Could not run diagnostics: {e}")

    # Step 7: Summary and next steps
    print("\n" + "="*60)
    print("🎯 QUICK START COMPLETE")
    print("="*60)

    if backend_ok and broadcast_ok:
        print("✅ System appears ready for testing!")
        print("\n📋 Next Steps:")
        print("1. Check Temporal UI: http://localhost:8080")
        print("2. Trigger news generation:")
        print("   curl -X POST http://localhost:8000/channels/1/workflow/trigger \\")
        print("        -H 'Content-Type: application/json' -d '{\"immediate\": true}'")
        print("3. Monitor pipeline: curl http://localhost:8000/debug/pipeline")
        print("4. Check broadcast status: curl http://localhost:8001/status")
    else:
        print("⚠️ Some services may not be ready yet.")
        print("\n🔧 Troubleshooting:")
        print("1. Check Docker: docker ps")
        print("2. Check logs: docker compose logs backend")
        print("3. Re-run diagnostics: python backend/diagnose_pipeline.py")
        print("4. Manual start: docker compose up backend backend-worker")

    print("\n🛑 To stop: docker compose down")
    print("="*60)

if __name__ == "__main__":
    main()