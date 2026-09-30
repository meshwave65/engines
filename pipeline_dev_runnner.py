import os
import shutil

# =========================
# BASE PATHS
# =========================
TASK_BASE = "./tasks"
CURATED_BASE = "./curated"
VECTOR_BASE = "./vectorized"

os.makedirs(TASK_BASE, exist_ok=True)
os.makedirs(CURATED_BASE, exist_ok=True)
os.makedirs(VECTOR_BASE, exist_ok=True)


# =========================
# TASK GENERATION
# =========================
def create_task(task_id, content_prefix):
    path = os.path.join(TASK_BASE, task_id)
    os.makedirs(path, exist_ok=True)

    files = []
    for i in range(1, 4):
        file_path = os.path.join(path, f"{content_prefix}_0000{i}.txt")
        with open(file_path, "w") as f:
            f.write(f"CONTENT_{content_prefix}_PARA_{i}")
        files.append(file_path)

    return files


# =========================
# CURATOR
# =========================
def curator_process(task_id):
    print(f"\n🟡 CURATOR PROCESS {task_id}")

    task_path = os.path.join(TASK_BASE, task_id)

    for file in os.listdir(task_path):
        full_path = os.path.join(task_path, file)

        if not file.endswith(".txt"):
            continue

        # simula canonical check global
        canonical_path = os.path.join(CURATED_BASE, file)

        if not os.path.exists(canonical_path):
            # move como canonical
            shutil.copy(full_path, canonical_path)
            print(f"✔ canonical created: {file}")

            # reduz original (simulação “quase zero byte”)
            with open(full_path, "w") as f:
                f.write(f"DEPRECATED -> {canonical_path}")

        else:
            # já existe canonical
            with open(full_path, "w") as f:
                f.write(f"DEPRECATED -> {canonical_path}")

            print(f"↳ duplicate detected: {file}")


# =========================
# VECTORIZER
# =========================
def vectorizer_process():
    print("\n🔵 VECTORIZE CURATED BASE")

    for file in os.listdir(CURATED_BASE):
        src = os.path.join(CURATED_BASE, file)

        vec_file = os.path.join(VECTOR_BASE, file.replace(".txt", ".vec"))

        with open(src, "r") as f:
            content = f.read()

        with open(vec_file, "w") as f:
            f.write(f"VECTOR({content})")

        print(f"✔ vectorized: {file}")


# =========================
# RUN SIMULATION
# =========================
if __name__ == "__main__":

    print("\n🚀 GENERATING TASKS\n")

    task1 = create_task("task_001", "alpha")
    task2 = create_task("task_002", "alpha")  # duplicado proposital

    print("\n🟢 TASKS CREATED")

    curator_process("task_001")
    curator_process("task_002")

    vectorizer_process()

    print("\n✅ DONE\n")
