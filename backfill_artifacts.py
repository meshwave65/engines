import os
import requests
from datetime import datetime, timezone

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

BUCKET = "sofia_storage_user"

CLIENT_UUID = "7891b8f4-68cc-4344-89e1-c000b80918bb"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


def get_tasks():
    url = f"{SUPABASE_URL}/rest/v1/appsofia_tasks"

    params = {
        "client_uuid": f"eq.{CLIENT_UUID}",
        "select": "id,client_uuid",
        "limit": 10000,
    }

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def list_storage(task_id):
    prefix = f"{CLIENT_UUID}/{task_id}/"

    url = (
        f"{SUPABASE_URL}/storage/v1/object/list/"
        f"{BUCKET}"
    )

    response = requests.post(
        url,
        headers=HEADERS,
        json={
            "prefix": prefix,
            "limit": 1000,
            "offset": 0,
        },
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def register_artifact(task_id, client_uuid, artifact_name):
    url = f"{SUPABASE_URL}/rest/v1/appsofia_artifacts"

    payload = {
        "task_id": task_id,
        "client_uuid": client_uuid,
        "artifact_name": artifact_name,
        "artifact_type": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    response = requests.post(
        url,
        headers={
            **HEADERS,
            "Prefer": "resolution=ignore-duplicates",
        },
        json=payload,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        print(
            f"ERRO AO REGISTRAR {artifact_name}: "
            f"{response.status_code} {response.text}"
        )
        return False

    return True


def main():
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada")

    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY não configurada")

    tasks = get_tasks()

    print(f"TAREFAS NO DB: {len(tasks)}")
    print("VARRENDO STORAGE...")
    print()

    tasks_with_artifacts = 0
    total_artifacts = 0

    for index, task in enumerate(tasks, start=1):
        task_id = task["id"]
        client_uuid = task["client_uuid"]

        objects = list_storage(task_id)

        if not objects:
            continue

        tasks_with_artifacts += 1

        print(
            f"[{index}/{len(tasks)}] "
            f"TAREFA: {task_id} "
            f"-> {len(objects)} artifacts"
        )

        for obj in objects:
            name = obj.get("name")

            if not name:
                continue

            artifact_name = name.split("/")[-1]

            if register_artifact(
                task_id,
                client_uuid,
                artifact_name,
            ):
                print(f"    OK: {artifact_name}")
                total_artifacts += 1

    print()
    print("=" * 60)
    print(f"TAREFAS COM ARTIFACTS: {tasks_with_artifacts}")
    print(f"ARTIFACTS PROCESSADOS: {total_artifacts}")
    print("=" * 60)


if __name__ == "__main__":
    main()
