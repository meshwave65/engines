# ==============================================================================
# SCRIPT: download_worker.py
# VERSÃO: 1.1
# DATA: 22/05/2026
# LOCAL: /mnt/hd1tb/projetos/sofia-engines/download_worker.py
# DESCRIÇÃO: Worker que realiza o download via Selenium e PyAutoGUI.
#            Inclui fallback para variáveis de ambiente do display X11.
# ==============================================================================

#!/usr/bin/env python3
import time
import sys
import os
import shutil
import requests

# --- CONFIGURAÇÃO DE AMBIENTE X11 (FALLBACK) ---
# Garante que o PyAutoGUI consiga se conectar ao display mesmo se o daemon falhar
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'
if 'XAUTHORITY' not in os.environ:
    possible_xauth = [
        '/home/meshwave/.Xauthority',
        os.path.expanduser('~/.Xauthority')
    ]
    for path in possible_xauth:
        if os.path.exists(path):
            os.environ['XAUTHORITY'] = path
            break

import pyautogui
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv("/mnt/hd1tb/projetos/.env")

# Configurações de Caminhos
KNOWLEDGE_ROOT_STR = os.getenv("KNOWLEDGE_ROOT")
if KNOWLEDGE_ROOT_STR:
    KNOWLEDGE_ROOT = Path(KNOWLEDGE_ROOT_STR)
else:
    KNOWLEDGE_ROOT = Path("/mnt/hd1tb/projetos/_storage/knowledge")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

TABLE = "appsofia_tasks"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# COORDENADAS DE CLIQUE (Ajuste conforme sua tela)
CLICK_1 = (1132, 166) # PASTINHA
CLICK_2 = (863, 263)  # SETINHA
CLICK_3 = (844, 868)  # DOWNLOAD LOTE

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5
DOWNLOADS_FOLDER = Path.home() / "Downloads"

# ======================
# DATABASE OPERATIONS
# ======================
def get_task(task_id):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{task_id}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()[0]

def update_status(task_id, status):
    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{task_id}"
        requests.patch(url, json={"downloader_status": status}, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"⚠️ Erro ao atualizar downloader_status: {e}")

# ======================
# SELENIUM DRIVER SETUP
# ======================
def get_driver(task_id):
    options = Options()
    options.add_argument("--start-maximized")
    
    # ISOLAMENTO DE PERFIL PARA EVITAR CONFLITOS
    user_data_dir = f"/tmp/chrome_profile_downloader_{task_id}"
    options.add_argument(f"--user-data-dir={user_data_dir}")
    
    return webdriver.Chrome(options=options), user_data_dir

# ======================
# PYAUTOGUI ACTIONS
# ======================
def real_click(x, y, label):
    print(f"🖱️ {label}: ({x}, {y})")
    pyautogui.moveTo(x, y, duration=1.2)
    time.sleep(0.1)
    pyautogui.mouseDown()
    time.sleep(0.15)
    pyautogui.mouseUp()
    time.sleep(1.0)

# ======================
# FILE MANAGEMENT
# ======================
def move_files(dest):
    print(f"📂 Movendo arquivos de {DOWNLOADS_FOLDER} para {dest}")
    count = 0
    for f in DOWNLOADS_FOLDER.iterdir():
        if f.is_file():
            try: 
                shutil.move(str(f), str(dest / f.name))
                count += 1
            except Exception as e:
                print(f"⚠️ Falha ao mover {f.name}: {e}")
    print(f"✅ {count} arquivos movidos.")

# =======================
# DESCOMPACTA E APAGA ZIP
# =======================
def extract_zip_files(dest):
    import zipfile

    print(f"📦 Verificando ZIPs em: {dest}")

    extracted = 0

    for f in dest.iterdir():
        if f.is_file() and f.suffix.lower() == ".zip":
            try:
                print(f"📦 Extraindo: {f.name}")

                with zipfile.ZipFile(f, 'r') as zip_ref:
                    zip_ref.extractall(dest)

                os.remove(f)

                print(f"🗑️ ZIP removido: {f.name}")

                extracted += 1

            except Exception as e:
                print(f"❌ Erro ao extrair {f.name}: {e}")

    print(f"✅ ZIPs extraídos: {extracted}")


# ======================
# MAIN EXECUTION
# ======================
def main():
    if len(sys.argv) < 2: return
    task_id = sys.argv[1]
    
    user_data_dir = None
    try:
        task = get_task(task_id)
#/        url = task.get("full_url")
        url = (task.get("full_url") or "").strip()
        client_uuid = task.get("client_uuid")
#/        origin = task.get("origin_provider", "")
        origin = (task.get("origin_provider") or "").strip()
        # 1. REGRA DE FILTRAGEM
        is_manus_origin = origin.lower() == "manus"
        is_manus_url = "manus.im" in url

        if not is_manus_origin or is_manus_url.lower()
            print(f"ℹ️ Link não-Manus detectado ({url}). Marcando NOWORK.")
            update_status(task_id, "NOWORK")
            return

        if not url:
            print(f"❌ DOWNLOAD ERROR: URL não encontrada para task {task_id}")
            update_status(task_id, "FAIL")
            return

        # 2. ATUALIZA STATUS PARA PROCESS
        update_status(task_id, "PROCESS")

        # 3. GARANTIR DIRETÓRIO DE DESTINO
        base_dir = KNOWLEDGE_ROOT / client_uuid / task_id
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"❌ DOWNLOAD ERROR: Falha ao criar diretório {base_dir}: {e}")
            update_status(task_id, "FAIL")
            return

        driver, user_data_dir = get_driver(task_id)

        try:
            print(f"🌐 OPEN DOWNLOAD: {url}", flush=True)
            driver.get(url)
            time.sleep(10)
            
            # Foca na janela para o pyautogui
            pyautogui.click(10, 10)
            time.sleep(1)

            real_click(*CLICK_1, "PASTINHA")
            time.sleep(6)
            real_click(*CLICK_2, "SETINHA")
            time.sleep(3)
            real_click(*CLICK_3, "DOWNLOAD LOTE")

            print("⏳ Aguardando download (15s)...")
            time.sleep(15)
            
            move_files(base_dir)

            update_status(task_id, "DONE")
            print(f"✅ DONE: Download concluído para {task_id}")

        except Exception as e:
            print(f"❌ DOWNLOAD ERROR: {e}")
            update_status(task_id, "FAIL")
        finally:
            driver.quit()
            if user_data_dir and os.path.exists(user_data_dir):
                shutil.rmtree(user_data_dir, ignore_errors=True)

    except Exception as e:
        print(f"❌ DOWNLOAD FATAL ERROR: {e}")
        update_status(task_id, "FAIL")

if __name__ == "__main__":
    main()
