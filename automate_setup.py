import paramiko
from scp import SCPClient
import os
import time
import sys

def create_ssh_client(server, user):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # Using the specific key we just generated
    key_path = os.path.expanduser("~/.ssh/id_rsa")
    client.connect(server, username=user, key_filename=key_path)
    return client

def progress(value, total):
    """Simple upload progress bar."""
    sys.stdout.write(f"\r--- Progress: {value/total*100:.1f}%")
    sys.stdout.flush()

def main():
    server = "157.180.24.243"
    user = "root"
    remote_path = "/root/vartapravah"
    
    print(f"MASTER DEPLOYER: Connecting to {server} via Security Bridge...")
    ssh = create_ssh_client(server, user)

    print("MASTER DEPLOYER: Establishing Security Bridge (Key Injection)...")
    try:
        with open(os.path.expanduser("~/.ssh/id_rsa.pub"), "r") as f:
            pub_key = f.read().strip()
        ssh.exec_command(f"mkdir -p ~/.ssh && echo '{pub_key}' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys")
        print("MASTER DEPLOYER: Security Bridge LOCKED.")
    except Exception as e:
        print(f"MASTER DEPLOYER: Key Injection skipped ({e})")

    print("MASTER DEPLOYER: Preparing server environment...")
    setup_env = [
        "apt update",
        "apt install -y docker-compose git",
        f"mkdir -p {remote_path}"
    ]
    for cmd in setup_env:
        _, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()

    print("MASTER DEPLOYER: Synchronizing codebase (this may take a minute)...")
    with SCPClient(ssh.get_transport()) as scp:
        # Syncing folders recursively
        scp.put("backend", remote_path, recursive=True)
        scp.put("frontend", remote_path, recursive=True)
        scp.put("docker-compose.yml", f"{remote_path}/docker-compose.yml")
        # Ensure .env is also pushed if it exists locally
        if os.path.exists("backend/.env"):
            print("MASTER DEPLOYER: Pushing Production Keys...")
            scp.put("backend/.env", f"{remote_path}/backend/.env")

    print("MASTER DEPLOYER: Building and Launching Stack...")
    launch_cmd = f"cd {remote_path} && docker-compose down && docker-compose up -d --build"
    stdin, stdout, stderr = ssh.exec_command(launch_cmd)
    # Print build progress - caution: large output
    for line in stdout: print(f"[BUILD] {line.strip()}")

    print("MASTER DEPLOYER: Waiting for services to stabilize (20s)...")
    time.sleep(20)

    print("MASTER DEPLOYER: Initializing News Engine (Namespace Registration)...")
    # Using the admin-tools container on the static network to register the namespace
    init_cmd = (
        f"docker run --rm --network vartapravah_vartapravah-net temporalio/admin-tools:latest "
        f"temporal --address temporal:7233 operator namespace create --namespace default"
    )
    ssh.exec_command(init_cmd)
    
    print("MASTER DEPLOYER: Total Autonomy Launch Complete!")
    print(f"Your Dashboard is LIVE at http://{server}:3000")
    print("Autopilot is now managing the broadcast.")
    ssh.close()

if __name__ == "__main__":
    main()
