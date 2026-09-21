"""Start detached rebuild on the LAN server, then poll the deploy log."""
import paramiko
import sys
import time

HOST = "100.84.254.18"
USER = "root"
PASSWORD = "311211"

START_CMD = (
    "cd /opt/accounting && "
    "nohup bash -c 'docker compose -f docker-compose.yml -f docker-compose.lan.yml "
    "build backend frontend > /opt/accounting/deploy.log 2>&1 && "
    "docker compose -f docker-compose.yml -f docker-compose.lan.yml up -d --remove-orphans --force-recreate nginx "
    ">> /opt/accounting/deploy.log 2>&1; echo \"EXIT:$?\" >> /opt/accounting/deploy.log' "
    "> /dev/null 2>&1 & echo STARTED"
)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
ssh.exec_command(START_CMD, timeout=20)
print("STARTED_SENT", flush=True)

deadline = time.time() + 900
while time.time() < deadline:
    time.sleep(25)
    _, out, _ = ssh.exec_command("tail -1 /opt/accounting/deploy.log", timeout=30)
    line = out.read().decode(errors="replace").strip()
    print("deploy.log:", line, flush=True)
    if "EXIT:" in line:
        sys.exit(0 if "EXIT:0" in line else 1)
sys.exit(2)
