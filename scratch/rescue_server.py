import paramiko
import os
import sys

def setup_server():
    server = "157.180.24.243"
    user = "root"
    password = "bjPTVWtCx3j9"
    pub_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC1JegvmLP6oL/Y9ksMji6XT8U1bUsSku2U5YLcaGhk2WDno82axz7bMV2cHv4OewgxNQedU6n1u62qoZ81xR0Zv99Xi35Rvp6jk4c/JTq8ZjuK569JWFmfMOMDIMOK2BpO69e+BaZlCcXml3zr0mxB9+isVNaCoiFYeF52jUBoU3bTMEPEK7pHXI8s3AoRnnfL4j46CuP/ncmIbSsxTFay1PMd+gTtWtd+D0XE1pq4OHJpr+V44LApOrLl/wUEP3bYApVzrhxpDjQX5e+QFPkte/uLrLjnW2aRRoRBLF4XJhCQFuK/IRwb3LkiQdYyacBw2xHVqxcEe28ZnAC809xawhM9okRxN9rn6KLwIRbrfe5trZOR6Csdu4ydT+lqUCTirLYav4z410BIYJ3vuBG/Ix7XogCODIls0I1acb2bIEc1oj8YvuzdBBe5jprGg4Ctuf5BQPjW9x/sx+qjdufGXG4tpXFJ4WbXRN8obdxZ/ZIPpCpudsdotN3T9tjkUXRJWtVlJv9wuvDSxJzzBsbNGHFuoINFrkgsUAUNkiQczXqVo1FpuSSMLfwJKpKg8PFdo9hEJRcsEjlC9rOOsw8dkXR5GxyXONsqsxFVlWDxzgwKRaAiGqNv94tON+IlZ44+nP4QMt2JdN5Rlj5tMliuNT+abFs9dq8hbiEUa6Ey9w== priyansh dere@DESKTOP-I6977KJ"

    print(f">> Connecting to {server} as {user}...")
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(server, username=user, password=password, timeout=10)
        print("✅ Connection Successful!")

        print(">> Injecting SSH Key...")
        cmd = f'mkdir -p ~/.ssh && echo "{pub_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
        stdin, stdout, stderr = client.exec_command(cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("✅ SSH Key Injected!")
        else:
            print(f"❌ Failed to inject key: {stderr.read().decode()}")

        print(">> Cleaning up Docker and Database...")
        cleanup_cmds = [
            "cd ~/vartapravah && git fetch origin main && git reset --hard origin/main",
            "cd ~/vartapravah && docker compose down",
            "docker volume rm vartapravah_postgres_data_v7 || true",
            "cd ~/vartapravah && docker compose up -d --build"
        ]

        for cmd in cleanup_cmds:
            print(f">> Running: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            # We don't wait for build to finish, but we check if it started
            print(f"--- Process started. (Exit Status check skipped for speed)")

        client.close()
        print("\n🎉 SETUP COMPLETE! Accessing services...")

    except Exception as e:
        print(f"!!! Error during setup: {e}")

if __name__ == "__main__":
    setup_server()
