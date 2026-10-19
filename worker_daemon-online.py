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

def fetch_task(status):
    """Busca uma tarefa por estado, separando despacho de monitoramento."""
    url = (
        f"{SUPABASE_URL}/rest/v1/{TABLE}"
        f"?status=eq.{status}"
        "&order=created_at.asc"
        "&limit=1"
    )
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    tasks = response.json()
    return tasks[0] if tasks else None


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

    try:
        subprocess.Popen(
            ["bash", SCRIPT_EXTRACTOR, str(task_id)],
            cwd=BASE_DIR,
            close_fds=True
        )
    except Exception as exc:
        print(f"❌ extractor spawn failed {task_id}: {exc}", flush=True)
        update(task_id, {"status": "FAIL", "extractor_status": "FAIL"})
        return

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
        update(task_id, {"status": "FAIL"})
        print(f"🚨 FAIL {task_id}", flush=True)
        return

    # PROCESS/STAGED indicam trabalho em andamento; não delegar prematuramente.
    if ext in ("STAGED", "PROCESS", None):
        return

    if ext == "DONE":
        if dwn in ("DONE", "NOWORK"):
            update(task_id, {"status": "DONE"})
            print(f"✅ DONE {task_id}", flush=True)
        elif dwn == "STAGED":
            update(task_id, {"status": "DELEGATED"})
            print(f"📤 DELEGATED {task_id}: aguardando downloader", flush=True)
        return

    print(f"⚠️ estado extractor desconhecido {task_id}: {ext}", flush=True)


# ============================================================
# LOOP
# ============================================================

def run_worker():
    print("🚀 WORKER ONLINE", flush=True)
    print(f"📁 BASE_DIR: {BASE_DIR}", flush=True)
    print(f"🔧 EXTRACTOR: {SCRIPT_EXTRACTOR}", flush=True)
    print(f"🌐 SUPABASE_URL: {SUPABASE_URL}", flush=True)

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL e SUPABASE_KEY precisam estar configuradas")
    if not os.path.isfile(SCRIPT_EXTRACTOR):
        raise FileNotFoundError(f"Extractor script não encontrado: {SCRIPT_EXTRACTOR}")

    while True:
        try:
            # Cada consulta é independente: uma tarefa em andamento não bloqueia
            # novas tarefas nem impede o acompanhamento das tarefas delegadas.
            for state in ("ACQUIRED", "DELEGATED"):
                task = fetch_task(state)
                if task:
                    monitor(task)

            staged = fetch_task("STAGED")
            if staged:
                dispatch(staged)
        except Exception as exc:
            print(f"⚠️ loop error: {exc}", flush=True)
        time.sleep(5)


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    run_worker()
