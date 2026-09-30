#!/usr/bin/env python3
"""
Manus Pixel Downloader + Movimentação Automática
"""

import time
import sys
from pathlib import Path
import pyautogui
import shutil
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ====================== CONFIG ======================
KNOWLEDGE_ROOT = Path("/mnt/hd1tb/projetos/_storage/knowledge")
CLIENTE = "meshwave65"
USER_DIR = "meshwave65"

# Suas coordenadas (não mexi)
CLICK_1 = (1132, 166)
CLICK_2 = (863, 263)
CLICK_3 = (844, 868)

WAIT_AFTER_OPEN = 15
WAIT_AFTER_CLICK1 = 7
WAIT_AFTER_CLICK2 = 5
WAIT_AFTER_CLICK3 = 45   # tempo para os downloads terminarem

# Pasta padrão de downloads do Chrome (mude se for diferente)
DOWNLOADS_FOLDER = Path.home() / "Downloads"

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.8


def get_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
   
    driver = webdriver.Chrome(options=options)
    return driver


def move_downloaded_files(task_folder: Path):
    """Move os arquivos baixados para a pasta correta"""
    if not DOWNLOADS_FOLDER.exists():
        print(f"⚠️ Pasta de downloads não encontrada: {DOWNLOADS_FOLDER}")
        return

    moved = 0
    for file in DOWNLOADS_FOLDER.iterdir():
        if file.is_file() and not file.name.startswith('.'):
            dest = task_folder / file.name
            try:
                shutil.move(str(file), str(dest))
                print(f"✅ Movido: {file.name}")
                moved += 1
            except Exception as e:
                print(f"❌ Erro ao mover {file.name}: {e}")

    print(f"📦 {moved} arquivos movidos para a pasta da task.")


def main(manus_url: str):
    print(f"🔗 Iniciando tarefa: {manus_url}")

    # Cria pasta da task
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = manus_url.split('/')[-1][:60]
    task_folder = KNOWLEDGE_ROOT / CLIENTE / USER_DIR / "manus" / f"{slug}_batch.{ts}"
    task_folder.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        driver = get_driver()
        driver.get(manus_url)

        print(f"⏳ Aguardando carregamento ({WAIT_AFTER_OPEN}s)...")
        time.sleep(WAIT_AFTER_OPEN)

        print("🖱️ 1. Clicando na pastinha com lupa...")
        pyautogui.moveTo(*CLICK_1, duration=1.2)
        pyautogui.click()
        time.sleep(WAIT_AFTER_CLICK1)

        print("🖱️ 2. Clicando na setinha para baixo...")
        pyautogui.moveTo(*CLICK_2, duration=1.0)
        pyautogui.click()
        time.sleep(WAIT_AFTER_CLICK2)

        print("🖱️ 3. Clicando em 'Download em lote'...")
        pyautogui.moveTo(*CLICK_3, duration=1.0)
        pyautogui.click()

        print(f"⬇️ Download iniciado! Aguardando {WAIT_AFTER_CLICK3}s...")
        time.sleep(WAIT_AFTER_CLICK3)

        print("📂 Movendo arquivos para a pasta correta...")
        move_downloaded_files(task_folder)

        print(f"\n✅ Tarefa finalizada! Arquivos salvos em:\n{task_folder}")

    except Exception as e:
        print(f"❌ Erro: {e}")
    finally:
        if driver:
            input("\nPressione ENTER para fechar o navegador...")
            driver.quit()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python download_worker.py <URL>")
        sys.exit(1)
   
    url = sys.argv[1].strip()
    main(url)
