import time
import requests
import subprocess
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv("/mnt/hd1tb/projetos/.env")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

TABLE = "appsofia_tasks"

BASE_DIR = "/mnt/hd1tb/projetos/sofia-engines"

# ENTRYPOINT FIXO (SEU PIPELINE ESTÁVEL)
SCRIPT_EXTRACTOR = os.path.join(BASE_DIR, "run_extractor.sh")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# =========================
# FETCH TASK
# =========================
def fetch_task():
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        "?status=eq.STAGED"
        "&order=created_at.asc"
        "&limit=1"
    )

    r = requests.get(url, headers=HEADERS, timeout=10)
    if r.status_code == 200 and r.json():
        return r.json()[0]

    return None


# =========================
# UPDATE TASK
# =========================
def update(task_id, payload):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{task_id}"

        payload["last_synced_at"] = datetime.now(timezone.utc).isoformat()

        requests.patch(url, json=payload, headers=HEADERS, timeout=10)

    except Exception as e:
        print(f"⚠️ update error {task_id}: {e}", flush=True)


# =========================
# DISPATCH (SÓ EXTRACTOR AGORA)
# =========================
def dispatch(task):
    task_id = task["id"]

    print(f"▶️ DISPATCH {task_id}", flush=True)

    # marca estado inicial do pipeline
    update(task_id, {
        "status": "ACQUIRED",
        "extractor_status": "STAGED",
        "downloader_status": "STAGED"
    })

    # 🔥 EXECUÇÃO CONTROLADA VIA SHELL (ISOLAMENTO TOTAL)
    subprocess.Popen([
        "bash",
        SCRIPT_EXTRACTOR,
        str(task_id)
    ])

    print(f"📡 extractor spawned via shell {task_id}", flush=True)


# =========================
# MONITOR (SEM OVERENGINEERING)
# =========================
def monitor(task):
    task_id = task["id"]

    ext = task.get("extractor_status")
    dwn = task.get("downloader_status")

    # FAIL GLOBAL
    if ext == "FAIL" or dwn == "FAIL":
        update(task_id, {"status": "FAIL"})
        print(f"🚨 FAIL {task_id}", flush=True)
        return

    # PROGRESSO (qualquer execução ativa)
    if ext not in ["STAGED", None] or dwn not in ["STAGED", None]:
        update(task_id, {"status": "DELEGATED"})
        print(f"📤 DELEGATED {task_id}", flush=True)
        return

    # FINALIZAÇÃO
    if ext == "DONE" and dwn in ["DONE", "NOWORK"]:
        update(task_id, {"status": "DONE"})
        print(f"✅ DONE {task_id}", flush=True)


# =========================
# LOOP PRINCIPAL
# =========================
def run_worker():
    print("🚀 WORKER ONLINE", flush=True)

    while True:
        try:
            task = fetch_task()

            if task:
                if task["status"] == "STAGED":
                    dispatch(task)
                else:
                    monitor(task)

        except Exception as e:
            print(f"⚠️ loop error: {e}", flush=True)

        time.sleep(5)


if __name__ == "__main__":
    run_worker()
