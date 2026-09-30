#!/usr/bin/env python3
import sys
import re
from pathlib import Path

# ----------------------------
# HARD NOISE (nível 1)
# ----------------------------
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

# ----------------------------
# CODE DETECTION
# ----------------------------
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
    # tenta preservar frases úteis dentro de blocos híbridos
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

        # aceita frases com linguagem natural
        letters = len(re.findall(r"[a-zA-Zá-úÁ-Ú]", s))
        if letters > 10:
            out.append(s)

    return out


def clean(text: str):
    blocks = re.split(r"\n{2,}", text)

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

        # tenta extrair humano mesmo de blocos mistos
        extracted = extract_human_sentences(b)

        if extracted:
            human.extend(extracted)
        else:
            # fallback: se não parece ruído extremo, mantém parcial
            if len(b) > 40:
                human.append(b)

    return "\n\n".join(human), "\n\n".join(code)


def main():
    if len(sys.argv) != 2:
        print("Uso: python3 curador.py <arquivo.txt>")
        sys.exit(1)

    path = Path(sys.argv[1])
    raw = path.read_text(encoding="utf-8", errors="ignore")

    human, code = clean(raw)

    out_text = path.parent / f"curator_text_{path.name}"
    out_code = path.parent / f"curator_code_{path.name}"

    out_text.write_text(human, encoding="utf-8")
    out_code.write_text(code, encoding="utf-8")

    print("✔ Texto limpo:", out_text)
    print("✔ Código extraído:", out_code)


if __name__ == "__main__":
    main()
