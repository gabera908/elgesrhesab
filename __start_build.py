"""Fire-and-forget: start detached build+up on the server."""
import paramiko

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
ssh.close()
