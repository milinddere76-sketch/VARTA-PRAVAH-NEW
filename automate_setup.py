import paramiko
from scp import SCPClient
import os
import time
import sys

# ---------------------------
# SSH CONNECTION
# ---------------------------
def create_ssh_client(server, user):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        key_path = os.path.expanduser("~/.ssh/id_rsa")
        
        # Try Key-based Auth First
        print(f"--- Attempting Key-based Auth for {user}@{server}...")

        try:
            client.connect(server, username=user, key_filename=key_path, timeout=10)
            
            # Add KeepAlive after connection is established
            transport = client.get_transport()
            if transport:
                transport.set_keepalive(30)

            print("--- SSH Connected (Key used)")
            return client
        except paramiko.AuthenticationException:
            # Fallback to Password Auth (Saved)
            print("--- Key auth failed, attempting saved password...")
            passw = "mH7iUXsVRmJJ" 
            try:
                client.connect(server, username=user, password=passw, timeout=10,
                              look_for_keys=False, allow_agent=False)
                print("--- SSH Connected (Saved password)")
                return client
            except paramiko.AuthenticationException:
                # Final Fallback to Manual Input
                print("--- Saved password failed.")
                manual_pass = input("👉 Please enter the root password for the server: ")
                client.connect(server, username=user, password=manual_pass, timeout=10,
                              look_for_keys=False, allow_agent=False)
                print("--- SSH Connected (Manual password)")
                return client

    except Exception as e:
        print(f"!!! SSH Connection Failed: {e}")
        sys.exit(1)


# ---------------------------
# PROGRESS BAR
# ---------------------------
def progress(filename, size, sent):
    percent = (sent / float(size)) * 100
    sys.stdout.write(f"\r--- Uploading {filename}: {percent:.1f}%")
    sys.stdout.flush()


# ---------------------------
# EXEC COMMAND HELPER
# ---------------------------
def run_cmd(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()

    if exit_code != 0:
        error = stderr.read().decode()
        print(f"!!! Command failed: {cmd}\n{error}")
    else:
        print(f"--- {cmd}")

    return exit_code


# ---------------------------
# MAIN DEPLOYER
# ---------------------------
def main():
    server = "157.180.24.243"
    user = "root"
    remote_path = "/root/vartapravah"

    print(f">> Connecting to {server}...")
    ssh = create_ssh_client(server, user)

    # ---------------------------
    # KEY INJECTION (SAFE)
    # ---------------------------
    print("::: Setting up SSH key access...")
    try:
        pub_key_path = os.path.expanduser("~/.ssh/id_rsa.pub")

        if os.path.exists(pub_key_path):
            with open(pub_key_path, "r") as f:
                pub_key = f.read().strip()

            run_cmd(
                ssh,
                f"mkdir -p ~/.ssh && grep -qxF '{pub_key}' ~/.ssh/authorized_keys || echo '{pub_key}' >> ~/.ssh/authorized_keys"
            )
            run_cmd(ssh, "chmod 600 ~/.ssh/authorized_keys")
            print("--- SSH Key secured")
        else:
            print("!!! No public key found, skipping")

    except Exception as e:
        print(f"!!! Key setup skipped: {e}")

    # ---------------------------
    # SERVER SETUP
    # ---------------------------
    print("::: Preparing server (optimizing)...")
    # Check if docker is already installed to skip apt update/install
    docker_check = "docker --version && docker compose version"
    _, stdout, _ = ssh.exec_command(docker_check)
    if stdout.channel.recv_exit_status() == 0:
        print("--- Docker already installed, skipping system setup")
        setup_cmds = [f"mkdir -p {remote_path}"]
    else:
        setup_cmds = [
            "apt update",
            "apt install -y docker.io docker-compose-plugin git",
            f"mkdir -p {remote_path}"
        ]

    for cmd in setup_cmds:
        run_cmd(ssh, cmd)

    # ---------------------------
    # FILE UPLOAD (OPTIMIZED WITH TAR)
    # ---------------------------
    print("::: Compressing project files (fast upload)...")
    tar_file = "project_bundle.tar.gz"
    # Create a compressed tarball excluding heavy/useless directories
    # Note: Using 'tar' which is available on modern Windows
    exclude_list = [
        "node_modules", ".next", "out", "build", 
        "__pycache__", ".git", "videos", ".env", "*.pyc",
        "*.mp4", "*.mkv", "*.mov", "*.zip", "*.tar.gz",
        "backend/videos", "backend/venv", "frontend/node_modules"
    ]
    exclude_args = " ".join([f'--exclude="{x}"' for x in exclude_list])
    
    os.system(f"tar {exclude_args} -czf {tar_file} backend frontend docker-compose.yml")

    print(f"::: Uploading {tar_file}...")
    try:
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            scp.put(tar_file, f"{remote_path}/{tar_file}")

        print("\n::: Extracting files on server...")
        run_cmd(ssh, f"cd {remote_path} && tar -xzf {tar_file} && rm {tar_file}")

        if os.path.exists("backend/.env"):
            print("::: Uploading .env...")
            with SCPClient(ssh.get_transport(), progress=progress) as scp:
                scp.put("backend/.env", f"{remote_path}/backend/.env")
            
        # Cleanup local tar
        if os.path.exists(tar_file):
            os.remove(tar_file)

    except Exception as e:
        print(f"!!! Upload/Extract Failed: {e}")
        if os.path.exists(tar_file): os.remove(tar_file)
        ssh.close()
        sys.exit(1)

    # DOCKER BUILD (BACK TO HIGH-SPEED BUILDKIT)
    print("\n::: Building & starting containers (Turbo Mode)...")
    build_cmd = (
        f"cd {remote_path} && "
        f"DOCKER_BUILDKIT=1 docker compose up -d --build"
    )
    run_cmd(ssh, build_cmd)

    print("\n::: Waiting for services to initialize...")
    print("--- Note: Temporal auto-setup can take 2-3 minutes on first run.")
    for i in range(30, 0, -1):
        sys.stdout.write(f"\r--- System Standby: {i}s remaining... ")
        sys.stdout.flush()
        time.sleep(1)
    print("\n--- Initial standby complete.")

    # ---------------------------
    # TEMPORAL NAMESPACE FIX
    # ---------------------------
    print("::: Setting up Temporal namespace (safe)...")
    namespace_cmd = (
        f"docker run --rm --network vartapravah_vartapravah-net temporalio/admin-tools:latest "
        f"sh -c 'temporal --address temporal:7233 operator namespace describe --namespace default || "
        f"temporal --address temporal:7233 operator namespace create --namespace default'"
    )

    run_cmd(ssh, namespace_cmd)

    # ---------------------------
    # DONE
    # ---------------------------
    print("\n+++ DEPLOYMENT COMPLETE!")
    print(f"--- Dashboard: http://{server}:3000")
    print("--- News Engine is LIVE")

    ssh.close()


# ---------------------------
# ENTRY
# ---------------------------
if __name__ == "__main__":
    main()