# universal_extractor.py
# Versão 1.3 - Integrado com Lógica de Curadoria + Supabase Storage
# 15/09/2026

import os
import sys
import time
import urllib.request
import shutil
import random
import re
import mimetypes
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from dotenv import load_dotenv

# Carrega env
load_dotenv("/mnt/hd1tb/projetos/.env")

print("🔥 EXTRACTOR STARTED", flush=True)
print("ARGS:", sys.argv, flush=True)

# =========================
# CONFIG
# =========================

KNOWLEDGE_ROOT_STR = os.getenv("KNOWLEDGE_ROOT")
KNOWLEDGE_ROOT = (
    Path(KNOWLEDGE_ROOT_STR)
    if KNOWLEDGE_ROOT_STR
    else Path("/mnt/hd1tb/projetos/_storage/knowledge")
)

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY")

TABLE = "appsofia_tasks"

# Bucket já utilizado pelo SWE
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET") or "sofia_storage_user"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# =========================
# CURATOR LOGIC (INTEGRATED)
# =========================

HARD_NOISE_PATTERNS = [
    r"window\.__",
    r"streamController",
    r"reactRouterContext",
    r"loaderData",
    r"actionData",
    r"serverResponse",
    r"__NEXT_DATA__",
    r"gtm",
    r"googletagmanager",
    r"facebook\.net",
]

CODE_HINTS = [
    r"\bfunction\b",
    r"\breturn\b",
    r"\bimport\b",
    r"=>",
    r"[{}]{2,}",
    r"def ",
    r"class ",
]


def is_hard_noise(block: str) -> bool:
    return any(re.search(p, block) for p in HARD_NOISE_PATTERNS)


def looks_like_code(block: str) -> bool:
    score = sum(1 for p in CODE_HINTS if re.search(p, block))
    symbols = len(re.findall(r"[{}\[\];=<>]", block))
    return score >= 2 or symbols > 20


def extract_human_sentences(block: str):
    sentences = re.split(r"(?<=[.!?])\s+", block)
    out = []

    for s in sentences:
        s = s.strip()

        if len(s) < 20:
            continue

        if re.search(r"[{}<>_=]{3,}", s):
            continue

        if re.search(r"\breturn\b|\bfunction\b|window\.__", s):
            continue

        letters = len(re.findall(r"[a-zA-Zá-úÁ-Ú]", s))

        if letters > 10:
            out.append(s)

    return out


def clean_extracted_text(texts_list):
    full_text = "\n\n".join(texts_list)
    blocks = re.split(r"\n{2,}", full_text)

    human = []
    code = []

    for b in blocks:
        b = b.strip()

        if not b:
            continue

        if is_hard_noise(b):
            continue

        if looks_like_code(b):
            code.append(b)
            continue

        extracted = extract_human_sentences(b)

        if extracted:
            human.extend(extracted)
        else:
            if len(b) > 40:
                human.append(b)

    return human, code


# =========================
# TASK OPS
# =========================

def fetch_task(task_id):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{task_id}"

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=15
    )

    r.raise_for_status()

    return r.json()[0]


def update_status(task_id, status):
    print(
        f"📡 STATUS UPDATE {task_id} -> {status}",
        flush=True
    )

    try:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE}?id=eq.{task_id}"

        requests.patch(
            url,
            json={"extractor_status": status},
            headers=HEADERS,
            timeout=15
        )

    except Exception as e:
        print(
            f"⚠️ status update error: {e}",
            flush=True
        )


# =========================
# SUPABASE STORAGE
# =========================

def upload_file_to_storage(local_path: Path, storage_path: str):
    """
    Envia um arquivo local para o bucket Supabase Storage.

    O caminho remoto preserva a estrutura:

        client_uuid/
            task_id/
                arquivo

    Retorna True somente quando o Supabase confirma o upload.
    """

    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL não configurada")

    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY não configurada")

    if not local_path.exists():
        raise FileNotFoundError(
            f"Arquivo local não encontrado: {local_path}"
        )

    encoded_path = quote(
        storage_path,
        safe="/"
    )

    url = (
        f"{SUPABASE_URL}/storage/v1/object/"
        f"{STORAGE_BUCKET}/{encoded_path}"
    )

    content_type = (
        mimetypes.guess_type(local_path.name)[0]
        or "application/octet-stream"
    )

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    print(
        f"☁️ UPLOAD {storage_path}",
        flush=True
    )

    with open(local_path, "rb") as file_handle:
        response = requests.post(
            url,
            headers=headers,
            data=file_handle,
            timeout=120
        )

    if not response.ok:
        raise RuntimeError(
            f"Storage upload failed "
            f"({response.status_code}) "
            f"{storage_path}: {response.text}"
        )

    print(
        f"✅ UPLOADED {storage_path}",
        flush=True
    )

    return True


def upload_artifacts(base_dir: Path, client_uuid: str, task_id: str):
    """
    Localiza todos os artefatos produzidos para a tarefa e envia
    para o bucket Supabase Storage.

    O caminho remoto mantém:

        client_uuid/task_id/nome_do_arquivo

    Retorna a quantidade de arquivos enviados.
    """

    if not base_dir.exists():
        raise RuntimeError(
            f"Diretório de artefatos não encontrado: {base_dir}"
        )

    files = [
        path
        for path in base_dir.iterdir()
        if path.is_file()
    ]

    if not files:
        raise RuntimeError(
            f"Nenhum artefato encontrado em {base_dir}"
        )

    uploaded_count = 0

    for local_path in sorted(files):
        storage_path = (
            f"{client_uuid}/"
            f"{task_id}/"
            f"{local_path.name}"
        )

        upload_file_to_storage(
            local_path,
            storage_path
        )

        uploaded_count += 1

    print(
        f"☁️ STORAGE COMPLETE "
        f"{task_id}: {uploaded_count} arquivo(s)",
        flush=True
    )

    return uploaded_count


# =========================
# DRIVER
# =========================

def get_driver(task_id):
    options = Options()

    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")

    user_data_dir = (
        f"/tmp/chrome_profile_extractor_{task_id}"
    )

    options.add_argument(
        f"--user-data-dir={user_data_dir}"
    )

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation"]
    )

    options.add_experimental_option(
        "useAutomationExtension",
        False
    )

    service = Service(
        ChromeDriverManager().install()
    )

    return (
        webdriver.Chrome(
            service=service,
            options=options
        ),
        user_data_dir
    )


# =========================
# WAIT ENGINE (FIX CRÍTICO)
# =========================

def wait_page_ready(driver, timeout=30):
    try:
        WebDriverWait(
            driver,
            timeout
        ).until(
            lambda d:
            d.execute_script(
                "return document.readyState"
            ) == "complete"
        )

        WebDriverWait(
            driver,
            timeout
        ).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )

    except Exception as e:
        print(
            f"⚠️ wait fallback: {e}",
            flush=True
        )


def handle_special_pages(driver):
    try:
        url = driver.current_url.lower()

        if "drive.google.com" in url:
            time.sleep(5)

            buttons = driver.find_elements(
                By.XPATH,
                "//button | //div[@role='button']"
            )

            for b in buttons:
                txt = (
                    b.text or ""
                ).lower()

                if (
                    "acessar" in txt
                    or "access" in txt
                    or "continue" in txt
                ):
                    print(
                        "🟡 Drive bypass detected",
                        flush=True
                    )

                    b.click()

                    time.sleep(3)

                    break

        time.sleep(2)

    except Exception as e:
        print(
            f"⚠️ special page error: {e}",
            flush=True
        )


# =========================
# SCROLL (ROBUSTO)
# =========================

def safe_scroll(driver):
    try:
        for _ in range(5):
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(1.5)

        driver.execute_script(
            "window.scrollTo(0, 0);"
        )

        time.sleep(1)

    except Exception as e:
        print(
            f"⚠️ scroll error: {e}",
            flush=True
        )


def final_settle(driver):
    try:
        driver.execute_script(
            "return document.body.innerText"
        )

        time.sleep(2)

    except:
        time.sleep(3)


# =========================
# EXTRACTION ENGINE
# =========================

def extract_full(driver):
    texts = []
    links = []
    codes = []
    imgs = []

    js = """
    function collectAll(root, results) {
        const walker = document.createTreeWalker(
            root,
            NodeFilter.SHOW_ELEMENT,
            null,
            false
        );

        let node = walker.nextNode();

        while (node) {
            const tag = node.tagName.toLowerCase();
            const txt = node.innerText
                ? node.innerText.trim()
                : "";

            if (txt)
                results.texts.push(txt);

            if (
                tag === 'a'
                && node.href
            )
                results.links.push(node.href);

            if (
                (tag === 'code' || tag === 'pre')
                && txt
            )
                results.codes.push(txt);

            if (
                tag === 'img'
                && node.src
                && !node.src.startsWith('data:')
            )
                results.imgs.push(node.src);

            if (node.shadowRoot) {
                collectAll(
                    node.shadowRoot,
                    results
                );
            }

            node = walker.nextNode();
        }
    }

    const results = {
        texts: [],
        links: [],
        codes: [],
        imgs: []
    };

    collectAll(
        document.body,
        results
    );

    return results;
    """

    try:
        driver.switch_to.default_content()

        elements = driver.find_elements(
            By.XPATH,
            "//*"
        )

        for el in elements:
            try:
                tag = el.tag_name.lower()

                txt = el.text.strip()

                if txt:
                    texts.append(txt)

                if tag == "a":
                    href = el.get_attribute(
                        "href"
                    )

                    if href:
                        links.append(href)

                if tag in ["code", "pre"]:
                    codes.append(
                        el.text.strip()
                    )

                if tag == "img":
                    src = el.get_attribute(
                        "src"
                    )

                    if (
                        src
                        and not src.startswith("data:")
                    ):
                        imgs.append(src)

            except:
                continue

        js_results = driver.execute_script(js)

        texts.extend(
            js_results["texts"]
        )

        links.extend(
            js_results["links"]
        )

        codes.extend(
            js_results["codes"]
        )

        imgs.extend(
            js_results["imgs"]
        )

    except Exception as e:
        print(
            f"⚠️ extraction error: {e}",
            flush=True
        )

    return (
        list(set(texts)),
        list(set(links)),
        list(set(codes)),
        list(set(imgs))
    )


# =========================
# MAIN
# =========================

def main():

    if len(sys.argv) < 2:
        return

    task_id = sys.argv[1]

    update_status(
        task_id,
        "PROCESS"
    )

    user_data_dir = None

    try:
        task = fetch_task(task_id)

        url = (
            task.get("full_url")
            or (
                f"https://manus.im/share/"
                f"{task['slug']}"
                if task.get("slug")
                else None
            )
        )

        if not url:
            update_status(
                task_id,
                "FAIL"
            )
            return

        user_uuid = task.get(
            "user_uuid",
            "unknown"
        )

        client_uuid = task.get(
            "client_uuid",
            "unknown"
        )

        agent = task.get(
            "agente",
            "default"
        )

        origin = task.get(
            "origin_provider",
            "unknown"
        )

        base_dir = (
            KNOWLEDGE_ROOT
            / client_uuid
            / task_id
        )

        base_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        driver, user_data_dir = get_driver(
            task_id
        )

        try:
            print(
                f"🌐 OPEN {url}",
                flush=True
            )

            driver.get(url)

            wait_page_ready(driver)

            handle_special_pages(driver)

            safe_scroll(driver)

            wait_page_ready(driver)

            final_settle(driver)

            texts, links, codes, imgs = (
                extract_full(driver)
            )

            # --- INTEGRATION: CLEANING ---

            print(
                "🧹 CLEANING NOISE...",
                flush=True
            )

            human_texts, extra_codes = (
                clean_extracted_text(texts)
            )

            codes.extend(
                extra_codes
            )

            # -----------------------------

            timestamp = int(
                time.time()
            )

            base = (
                f"{client_uuid}_"
                f"{user_uuid}_"
                f"{agent}_"
                f"{origin}_"
                f"{task_id}_"
                f"{timestamp}"
            )

            # =========================
            # LOCAL ARTIFACT GENERATION
            # =========================

            context_path = (
                base_dir
                / f"{base}_context.txt"
            )

            links_path = (
                base_dir
                / f"{base}_links.txt"
            )

            code_path = (
                base_dir
                / f"{base}_code.txt"
            )

            context_path.write_text(
                "\n\n".join(
                    human_texts
                ),
                encoding="utf-8"
            )

            links_path.write_text(
                "\n".join(
                    links
                ),
                encoding="utf-8"
            )

            code_path.write_text(
                "\n\n".join(
                    list(set(codes))
                ),
                encoding="utf-8"
            )

            # =========================
            # IMAGE DOWNLOAD
            # =========================

            for i, src in enumerate(imgs):

                try:
                    image_path = (
                        base_dir
                        / f"img_{i:03d}.jpg"
                    )

                    urllib.request.urlretrieve(
                        src,
                        image_path
                    )

                except:
                    pass

            # =========================
            # SUPABASE STORAGE
            # =========================

            print(
                f"☁️ ENVIANDO ARTEFATOS "
                f"PARA STORAGE: {task_id}",
                flush=True
            )

            uploaded_count = upload_artifacts(
                base_dir,
                client_uuid,
                task_id
            )

            print(
                f"☁️ {uploaded_count} "
                f"ARTEFATO(S) ENVIADO(S)",
                flush=True
            )

            # =========================
            # DONE
            # =========================

            print(
                f"✅ DONE {task_id}",
                flush=True
            )

            update_status(
                task_id,
                "DONE"
            )

        except Exception as e:

            print(
                f"❌ ERROR: {e}",
                flush=True
            )

            update_status(
                task_id,
                "FAIL"
            )

        finally:

            driver.quit()

            if (
                user_data_dir
                and os.path.exists(
                    user_data_dir
                )
            ):
                shutil.rmtree(
                    user_data_dir,
                    ignore_errors=True
                )

    except Exception as e:

        print(
            f"❌ FATAL: {e}",
            flush=True
        )

        update_status(
            task_id,
            "FAIL"
        )


if __name__ == "__main__":
    main()
