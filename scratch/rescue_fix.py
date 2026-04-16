import paramiko
import time
import sys

# Ensure UTF-8 output if possible, but we'll just remove emojis to be safe
def rescue_fix():
    server = "157.180.24.243"
    user = "root"
    password = "hdkHUKrNkfJR" 
    
    pub_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC1JegvmLP6oL/Y9ksMji6XT8U1bUsSku2U5YLcaGhk2WDno82axz7bMV2cHv4OewgxNQedU6n1u62qoZ81xR0Zv99Xi35Rvp6jk4c/JTq8ZjuK569JWFmfMOMDIMOK2BpO69e+BaZlCcXml3zr0mxB9+isVNaCoiFYeF52jUBoU3bTMEPEK7pHXI8s3AoRnnfL4j46CuP/ncmIbSsxTFay1PMd+gTtWtd+D0XE1pq4OHJpr+V44LApOrLl/wUEP3bYApVzrhxpDjQX5e+QFPkte/uLrLjnW2aRRoRBLF4XJhCQFuK/IRwb3LkiQdYyacBw2xHVqxcEe28ZnAC809xawhM9okRxN9rn6KLwIRbrfe5trZOR6Csdu4ydT+lqUCTirLYav4z410BIYJ3vuBG/Ix7XogCODIls0I1acb2bIEc1oj8YvuzdBBe5jprGg4Ctuf5BQPjW9x/sx+qjdufGXG4tpXFJ4WbXRN8obdxZ/ZIPpCpudsdotN3T9tjkUXRJWtVlJv9wuvDSxJzzBsbNGHFuoINFrkgsUAUNkiQczXqVo1FpuSSMLfwJKpKg8PFdo9hEJRcsEjlC9rOOsw8dkXR5GxyXONsqsxFVlWDxzgwKRaAiGqNv94tON+IlZ44+nP4QMt2JdN5Rlj5tMliuNT+abFs9dq8hbiEUa6Ey9w== priyansh dere@DESKTOP-I6977KJ"

    print(f">> Connecting to RESCUE system at {server}...")
    client = None
    for attempt in range(3):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(server, username=user, password=password, timeout=20,
                          look_for_keys=False, allow_agent=False)
            print("[OK] Connected to Rescue System!")
            break
        except Exception as e:
            print(f"--- Attempt {attempt+1} failed: {e}")
            if attempt < 2: time.sleep(10)
            else: 
                print("!!! All connection attempts failed.")
                return

    try:
        print(">> Mounting main partition and fixing keys...")
        commands = [
            # Mounting /dev/sda1 or /dev/vda1 or /dev/sda3
            "mkdir -p /mnt",
            "mount /dev/sda1 /mnt || mount /dev/vda1 /mnt || mount /dev/sda3 /mnt || mount /dev/vdb1 /mnt",
            "mkdir -p /mnt/root/.ssh",
            f"echo '{pub_key}' >> /mnt/root/.ssh/authorized_keys",
            "chmod 600 /mnt/root/.ssh/authorized_keys",
            "sed -i 's/^#?PasswordAuthentication .*/PasswordAuthentication yes/' /mnt/etc/ssh/sshd_config",
            "sed -i 's/^#?PermitRootLogin .*/PermitRootLogin yes/' /mnt/etc/ssh/sshd_config",
            "sync",
            "umount /mnt",
            "reboot"
        ]

        for cmd in commands:
            print(f">> Running: {cmd}")
            stdin, stdout, stderr = client.exec_command(cmd)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status != 0:
                print(f"--- Warning: {stderr.read().decode()}")

        print("\n[SUCCESS] DONE! The server is rebooting. Wait 60 seconds and run automate_setup.py.")
        client.close()

    except Exception as e:
        print(f"!!! Error during execution: {e}")

if __name__ == "__main__":
    rescue_fix()
