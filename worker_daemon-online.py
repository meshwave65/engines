import time
import requests
import subprocess
import os
from datetime import datetime, timezone


# ============================================================
# SUPABASE — AMBIENTE ONLINE
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TABLE = "appsofia_tasks"


# ============================================================
# CAMINHO DO EXTRACTOR — AMBIENTE ONLINE
# ============================================================

# O Render executa o repositório a partir do diretório onde
# este arquivo está localizado.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPT_EXTRACTOR = os.path.join(
    BASE_DIR,
    "run_extractor-online.sh"
)


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# ============================================================
# FETCH TASK
# ============================================================

def fetch_task():
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        "?status=eq.STAGED"
        "&order=created_at.asc"
        "&limit=1"
    )

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    if r.status_code == 200 and r.json():
        return r.json()[0]

    return None


# ============================================================
# UPDATE TASK
# ============================================================

def update(task_id, payload):
    try:
        url = (
            f"{SUPABASE_URL}/rest/v1/{TABLE}"
            f"?id=eq.{task_id}"
        )

        payload["last_synced_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

        requests.patch(
            url,
            json=payload,
            headers=HEADERS,
            timeout=10
        )

    except Exception as e:
        print(
            f"⚠️ update error {task_id}: {e}",
            flush=True
        )


# ============================================================
# DISPATCH
# ============================================================

def dispatch(task):
    task_id = task["id"]

    print(
        f"▶️ DISPATCH {task_id}",
        flush=True
    )

    update(
        task_id,
        {
            "status": "ACQUIRED",
            "extractor_status": "STAGED",
            "downloader_status": "STAGED"
        }
    )

    subprocess.Popen(
        [
            "bash",
            SCRIPT_EXTRACTOR,
            str(task_id)
        ]
    )

    print(
        f"📡 extractor spawned via shell {task_id}",
        flush=True
    )


# ============================================================
# MONITOR
# ============================================================

def monitor(task):
    task_id = task["id"]

    ext = task.get("extractor_status")
    dwn = task.get("downloader_status")

    if ext == "FAIL" or dwn == "FAIL":

        update(
            task_id,
            {
                "status": "FAIL"
            }
        )

        print(
            f"🚨 FAIL {task_id}",
            flush=True
        )

        return

    if ext not in ["STAGED", None] or dwn not in ["STAGED", None]:

        update(
            task_id,
            {
                "status": "DELEGATED"
            }
        )

        print(
            f"📤 DELEGATED {task_id}",
            flush=True
        )

        return

    if ext == "DONE" and dwn in ["DONE", "NOWORK"]:

        update(
            task_id,
            {
                "status": "DONE"
            }
        )

        print(
            f"✅ DONE {task_id}",
            flush=True
        )


# ============================================================
# LOOP
# ============================================================

def run_worker():

    print(
        "🚀 WORKER ONLINE",
        flush=True
    )

    print(
        f"📁 BASE_DIR: {BASE_DIR}",
        flush=True
    )

    print(
        f"🔧 EXTRACTOR: {SCRIPT_EXTRACTOR}",
        flush=True
    )

    print(
        f"🌐 SUPABASE_URL: {SUPABASE_URL}",
        flush=True
    )

    while True:

        try:

            task = fetch_task()

            if task:

                if task["status"] == "STAGED":
                    dispatch(task)

                else:
                    monitor(task)

        except Exception as e:

            print(
                f"⚠️ loop error: {e}",
                flush=True
            )

        time.sleep(5)


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    run_worker()
