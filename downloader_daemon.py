# ==============================================================================
# SCRIPT: download_daemon.py
# VERSÃO: 1.1
# DATA: 22/05/2026
# LOCAL: /mnt/hd1tb/projetos/sofia-engines/download_daemon.py
# DESCRIÇÃO: Daemon que monitora tarefas de download no Supabase e inicia o worker.
#            Corrigido para passar variáveis de ambiente X11 para o subprocesso.
# ==============================================================================

import time
import requests
import subprocess
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv("/mnt/hd1tb/projetos/.env")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

TABLE = "appsofia_tasks"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_DOWNLOAD = os.path.join(BASE_DIR, "download_worker.py")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# =========================
# UPDATE STATUS
# =========================
def update_downloader_status(task_id, status):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{task_id}"
        requests.patch(url, json={"downloader_status": status}, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"⚠️ Erro ao atualizar downloader_status para {task_id}: {e}")

# =========================
# FETCH TASK FOR DOWNLOAD
# =========================
def fetch_download_task():
    # Busca tarefas onde o downloader_status é STAGED
    # Importante: A tarefa deve estar em ACQUIRED ou DELEGATED
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        "?downloader_status=eq.STAGED"
        "&status=in.(ACQUIRED,DELEGATED)"
        "&order=created_at.asc"
        "&limit=1"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                return data[0]
    except Exception as e:
        print(f"⚠️ Erro ao buscar tarefa de download: {e}")
    return None

# =========================
# RUN DOWNLOADER DAEMON
# =========================
def run_downloader():
    print("🚀 DOWNLOADER DAEMON ONLINE [v1.1]", flush=True)
    
    # Define o interpretador Python (usa o venv se existir)
    PYTHON_SYS = sys.executable
    PYTHON_VENV = os.path.join(BASE_DIR, "venv", "bin", "python")
    EXECUTOR = PYTHON_VENV if os.path.exists(PYTHON_VENV) else PYTHON_SYS

    while True:
        try:
            task = fetch_download_task()
            if task:
                task_id = task["id"]
#/                url = task.get("full_url", "")
                url = (task.get("full_url") or "").strip()
#/                origin = task.get("origin_provider", "")
                origin = (task.get("origin_provider") or "").strip()
                # REGRAS DE FILTRAGEM
                is_manus_origin = (origin.lower() == "manus")
                is_manus_url = url and ("manus.im" in url)

                if not (is_manus_origin or is_manus_url):
                    print(f"ℹ️ Task {task_id} não é Manus. Marcando NOWORK.", flush=True)
                    update_downloader_status(task_id, "NOWORK")
                    continue

                print(f"📂 PICKING UP DOWNLOAD FOR TASK {task_id}", flush=True)
                
                # PREPARAÇÃO DO AMBIENTE X11 PARA PYAUTOGUI
                # Copia o ambiente atual e injeta as variáveis do display
                env_vars = os.environ.copy()
                env_vars["DISPLAY"] = ":0"
                # Caminho padrão do .Xauthority para o usuário meshwave
                env_vars["XAUTHORITY"] = "/home/meshwave/.Xauthority"

                # Executa o download_worker de forma síncrona (wait)
                # Passamos env=env_vars para que o worker tenha acesso ao display
                subprocess.run([EXECUTOR, SCRIPT_DOWNLOAD, str(task_id)], env=env_vars)
                
                print(f"🏁 Finished processing download for {task_id}", flush=True)
            
        except Exception as e:
            print(f"⚠️ Erro no loop do downloader: {e}")
            
        time.sleep(5) # Intervalo entre checagens

if __name__ == "__main__":
    run_downloader()
