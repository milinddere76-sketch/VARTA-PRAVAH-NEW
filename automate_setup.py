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

        if not os.path.exists(key_path):
            raise FileNotFoundError("SSH key not found at ~/.ssh/id_rsa")

        client.connect(server, username=user, key_filename=key_path, timeout=10)
        print("✅ SSH Connected")
        return client

    except Exception as e:
        print(f"❌ SSH Connection Failed: {e}")
        sys.exit(1)


# ---------------------------
# PROGRESS BAR
# ---------------------------
def progress(value, total):
    percent = (value / total) * 100
    sys.stdout.write(f"\r--- Upload Progress: {percent:.1f}%")
    sys.stdout.flush()


# ---------------------------
# EXEC COMMAND HELPER
# ---------------------------
def run_cmd(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()

    if exit_code != 0:
        error = stderr.read().decode()
        print(f"❌ Command failed: {cmd}\n{error}")
    else:
        print(f"✅ {cmd}")

    return exit_code


# ---------------------------
# MAIN DEPLOYER
# ---------------------------
def main():
    server = "157.180.24.243"
    user = "root"
    remote_path = "/root/vartapravah"

    print(f"🚀 Connecting to {server}...")
    ssh = create_ssh_client(server, user)

    # ---------------------------
    # KEY INJECTION (SAFE)
    # ---------------------------
    print("🔐 Setting up SSH key access...")
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
            print("✅ SSH Key secured")
        else:
            print("⚠️ No public key found, skipping")

    except Exception as e:
        print(f"⚠️ Key setup skipped: {e}")

    # ---------------------------
    # SERVER SETUP
    # ---------------------------
    print("⚙️ Preparing server...")
    setup_cmds = [
        "apt update",
        "apt install -y docker.io docker-compose-plugin git",
        f"mkdir -p {remote_path}"
    ]

    for cmd in setup_cmds:
        run_cmd(ssh, cmd)

    # ---------------------------
    # FILE UPLOAD
    # ---------------------------
    print("📦 Uploading project files...")
    try:
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            scp.put("backend", remote_path, recursive=True)
            scp.put("frontend", remote_path, recursive=True)
            scp.put("docker-compose.yml", f"{remote_path}/docker-compose.yml")

            if os.path.exists("backend/.env"):
                print("\n🔑 Uploading .env...")
                scp.put("backend/.env", f"{remote_path}/backend/.env")

    except Exception as e:
        print(f"❌ SCP Upload Failed: {e}")
        ssh.close()
        sys.exit(1)

    # ---------------------------
    # DOCKER BUILD
    # ---------------------------
    print("\n🐳 Building & starting containers...")
    run_cmd(
        ssh,
        f"cd {remote_path} && docker compose down && docker compose up -d --build"
    )

    print("⏳ Waiting for services (20s)...")
    time.sleep(20)

    # ---------------------------
    # TEMPORAL NAMESPACE FIX
    # ---------------------------
    print("⚡ Setting up Temporal namespace (safe)...")
    namespace_cmd = (
        f"docker run --rm --network vartapravah_vartapravah-net temporalio/admin-tools:latest "
        f"temporal --address temporal:7233 operator namespace describe --namespace default || "
        f"temporal --address temporal:7233 operator namespace create --namespace default"
    )

    run_cmd(ssh, namespace_cmd)

    # ---------------------------
    # DONE
    # ---------------------------
    print("\n🎉 DEPLOYMENT COMPLETE!")
    print(f"🌐 Dashboard: http://{server}:3000")
    print("📡 News Engine is LIVE")

    ssh.close()


# ---------------------------
# ENTRY
# ---------------------------
if __name__ == "__main__":
    main()