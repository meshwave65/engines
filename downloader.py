#!/usr/bin/env python3
"""
Manus Batch Downloader - Execução Automática
"""

import time
import sys
from pathlib import Path

import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ====================== CONFIG ======================
KNOWLEDGE_ROOT = Path("/mnt/hd1tb/projetos/_storage/knowledge")

COORDS = {
    "pastinha": (1132, 166),
    "setinha":  (863, 263),
    "lote":     (844, 868)
}

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5


# ====================== DRIVER ======================
def get_driver():
    print("🚀 Iniciando Chrome via Selenium...")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    print("✅ Chrome aberto!")
    return driver


# ====================== CLICK REAL ======================
def real_click(x, y, label):
    print(f"🖱️ {label}: ({x}, {y})")

    pyautogui.moveTo(x, y, duration=1.2)
    time.sleep(0.3)

    pyautogui.mouseDown()
    time.sleep(0.15)
    pyautogui.mouseUp()

    time.sleep(1.5)


# ====================== MAIN ======================
def main(manus_url: str):
    print(f"🔗 URL: {manus_url}\n")

    driver = None
    try:
        driver = get_driver()
        driver.get(manus_url)

        print("⏳ Aguardando carregamento da página...")
        time.sleep(10)

        # ativa foco
        pyautogui.click(10, 10)
        time.sleep(1)

        print("🚀 Iniciando sequência automática...\n")

        # ======================
        # CLIQUE 1
        # ======================
        real_click(*COORDS["pastinha"], "PASTINHA")
        time.sleep(3)

        # ======================
        # CLIQUE 2
        # ======================
        real_click(*COORDS["setinha"], "SETINHA")
        time.sleep(2)

        # ======================
        # CLIQUE 3
        # ======================
        real_click(*COORDS["lote"], "DOWNLOAD LOTE")

        print("⏳ aguardando download...")
        time.sleep(3)  # 🔥 AJUSTE AQUI

        print("✅ Fluxo finalizado")

    except Exception as e:
        print(f"❌ Erro: {e}")

    finally:
        if driver:
            driver.quit()


# ====================== ENTRY ======================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python download_worker.py <URL>")
        sys.exit(1)

    url = sys.argv[1].strip()
    main(url)
