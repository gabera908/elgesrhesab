"""Upload latest code bundle to the LAN docker host. No secrets in logs."""
import os
import tarfile
import tempfile
import paramiko

HOST = "100.84.254.18"
USER = "root"
PASSWORD = "311211"
REMOTE_DIR = "/opt/accounting"

EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist"}
EXCLUDE_FILES = {"__upload_server.py", "__start_build.py", "__poll_server.py", "__smoke_auth.py"}
EXCLUDE_SUFFIX = (".pyc", ".enc", ".sql", ".sql.gz")

LOCAL_FILES = [
    "docker-compose.yml",
    "docker-compose.lan.yml",
    "docker-compose.prod.yml",
    "backend",
    "frontend/src",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/index.html",
    "frontend/Dockerfile",
    "nginx",
]


def should_skip(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    name = parts[-1]
    if name in EXCLUDE_FILES:
        return True
    if name.endswith(EXCLUDE_SUFFIX):
        return True
    return False


tmp = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
tmp.close()
with tarfile.open(tmp.name, "w:gz") as tar:
    for item in LOCAL_FILES:
        if not os.path.exists(item):
            print(f"SKIP missing: {item}", flush=True)
            continue
        if os.path.isdir(item):
            for root, _, files in os.walk(item):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, ".")
                    if should_skip(rel):
                        continue
                    tar.add(full, arcname=rel)
        else:
            if not should_skip(item):
                tar.add(item, arcname=item)
print(f"BUNDLE: {os.path.getsize(tmp.name)} bytes", flush=True)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()
sftp.put(tmp.name, "/tmp/accounting-deploy.tar.gz")
sftp.close()
_, out, _ = ssh.exec_command(
    f"cd {REMOTE_DIR} && tar -xzf /tmp/accounting-deploy.tar.gz "
    "&& rm -f /tmp/accounting-deploy.tar.gz && echo EXTRACT_OK",
    timeout=120,
)
print(out.read().decode(errors="replace"), flush=True)
ssh.close()
print("UPLOAD_DONE", flush=True)
