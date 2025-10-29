# tools/generate_images_openai.py
# ===============================================================
# Gera imagens IA a partir dos prompts originais (seção "## IMAGENS (ChatGPT)").
# Salva na mesma pasta externa (--final-root). Usa imagem-base se disponível;
# se o SDK não tiver images.edit/edits, cai automaticamente para generate().
# ===============================================================

import os
import re
import base64
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Optional
from PIL import Image


# ----------------- util -----------------

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write(p: Path, text: str):
    p.write_text(text, encoding="utf-8")

def to_png(src: Path) -> Optional[Path]:
    if not src or not src.exists():
        return None
    if src.suffix.lower() == ".png":
        return src
    png_path = src.with_suffix(".png")
    img = Image.open(src).convert("RGBA")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(png_path, format="PNG")
    return png_path


# ----------------- parsing -----------------

SECTION_START = re.compile(r"^\s*##\s*IMAGENS\s*\(CHATGPT\)\s*$", re.IGNORECASE)
SECTION_NEXT  = re.compile(r"^\s*##\s+", re.IGNORECASE)

def extract_images_section(full_text: str) -> str:
    """Recorta apenas a seção '## IMAGENS (ChatGPT)' até o próximo '##'."""
    lines = full_text.splitlines()
    in_sec = False
    buf = []
    for ln in lines:
        if not in_sec and SECTION_START.match(ln):
            in_sec = True
            continue
        if in_sec and SECTION_NEXT.match(ln):
            break
        if in_sec:
            buf.append(ln)
    # fallback: se não achou a seção, devolve o texto inteiro
    return "\n".join(buf).strip() if buf else full_text

def split_prompts(text: str) -> List[str]:
    """
    Divide o texto em prompts por marcadores como:
    **Gerar imagem 1.** / Gerar imagem 2: / GERAR IMAGEM 3 -
    Aceita variações, com ou sem negrito, e suporta quebra de linha ou não.
    """
    # força quebra de linha antes de cada "Gerar imagem"
    normalized = re.sub(r"(\*\*?\s*Gerar\s+imagem\s*\d+[\.\:\-]?\s*\*\*?)", r"\n\1", text, flags=re.IGNORECASE)
    parts = re.split(r"(?:\*\*)?\s*Gerar\s+imagem\s*\d+\s*[\.\:\-]?\s*(?:\*\*)?", normalized, flags=re.IGNORECASE)
    blocks = [b.strip() for b in parts if b and b.strip()]
    # fallback por segurança
    if len(blocks) < 6:
        blocks = [b.strip() for b in re.split(r"\n{2,}", normalized) if b.strip()]
    return blocks

def build_image_prompt(block: str) -> str:
    """Usa o texto original como prompt direto (limpa markdown leve)."""
    clean = re.sub(r"\*\*Gerar\s+imagem\s*\d+\s*[\.\:\-]?\*\*", "", block, flags=re.IGNORECASE).strip()
    clean = re.sub(r"[#>`*_]", "", clean).strip()
    return clean


# ----------------- image base lookup -----------------

def find_source_image(pack_dir: Path, source_root: Optional[Path]) -> Optional[Path]:
    cands = []
    if source_root and (source_root / pack_dir.name).exists():
        cands += list((source_root / pack_dir.name).glob("*_img*.*"))
    cands += list(pack_dir.glob("*_img*.*"))
    for c in cands:
        if c.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            return c
    return None


# ----------------- openai helpers -----------------

def generate_image_bytes_from_text(client, model: str, prompt: str, size: str) -> bytes:
    resp = client.images.generate(model=model, prompt=prompt, size=size)
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)

def generate_image_bytes_from_edit_with_fallback(client, model: str, source_png: Path, prompt: str, size: str) -> bytes:
    """
    Tenta image-to-image; se o SDK não tiver .edits/.edit, cai para generate().
    """
    try:
        # SDKs mais antigos:
        fn = getattr(client.images, "edits", None) or getattr(client.images, "edit", None)
        if fn is None:
            raise AttributeError("images.edits/edit não disponível; usando generate()")
        with open(source_png, "rb") as f:
            resp = fn(model=model, image=f, prompt=prompt, size=size)
        b64 = resp.data[0].b64_json
        return base64.b64decode(b64)
    except Exception as e:
        print(f"ℹ️  image-to-image indisponível ({e}); usando generate().")
        return generate_image_bytes_from_text(client, model, prompt, size)


# ----------------- main -----------------

def main():
    load_dotenv()
    from openai import OpenAI
    client = OpenAI()

    ap = argparse.ArgumentParser(description="Gera imagens IA a partir dos prompts de '## IMAGENS (ChatGPT)'.")
    ap.add_argument("--packs-root", default="outputs/prompt_packs")
    ap.add_argument("--model", default="gpt-image-1")
    ap.add_argument("--size", default="1024x1536")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--source-root", default="", help="Pasta externa com a imagem baixada (ex.: --final-root da pipeline)")
    ap.add_argument("--final-root",  default="", help="Pasta externa onde salvar as PNGs (subpasta por produto)")
    args = ap.parse_args()

    packs_root = Path(args.packs_root)
    source_root = Path(args.source_root) if args.source_root else None
    final_root  = Path(args.final_root)  if args.final_root  else None

    if not packs_root.exists():
        raise SystemExit(f"Pasta de packs não encontrada: {packs_root}")

    packs = [p for p in packs_root.iterdir() if p.is_dir()]
    total = 0

    for pack in sorted(packs):
        # 1) pega o texto de cenas
        respostas = pack / "RESPOSTA_prompt_01_cenas.txt"
        original  = pack / "prompt_01_cenas.txt"
        full_text = read(respostas) or read(original)
        if not full_text:
            print(f"⚠️  {pack.name}: sem texto de cenas — pulando.")
            continue

        only_images = extract_images_section(full_text)
        blocks = split_prompts(only_images)
        print(f"\n▶️  {pack.name}: gerando imagens ({len(blocks)} prompts detectados).")
        if not blocks:
            print("⚠️  Nenhum prompt de imagem detectado nesta seção — pulando.")
            continue

        # 2) pasta de saída
        out_dir = (final_root / pack.name) if final_root else pack
        out_dir.mkdir(parents=True, exist_ok=True)
        captions_path = out_dir / "_captions.txt"
        captions_lines = []

        # 3) imagem base
        source = find_source_image(pack, source_root)
        source_png = to_png(source) if source else None
        if source_png:
            print(f"🧷 usando imagem-base: {source_png}")
        else:
            print("ℹ️  sem imagem-base; gerando a partir de texto puro")

        # 4) gera cada prompt
        for idx, block in enumerate(blocks, start=1):
            prompt = build_image_prompt(block)
            png_path = out_dir / f"{idx:03d}.png"

            if png_path.exists() and not args.overwrite:
                print(f"⏭  {png_path.name} já existe (use --overwrite para refazer).")
                captions_lines.append(f"{png_path.name} | {prompt}")
                continue

            print(f"🎯 Gerando imagem {idx} ({png_path.name})...")

            try:
                if source_png:
                    img_bytes = generate_image_bytes_from_edit_with_fallback(client, args.model, source_png, prompt, args.size)
                else:
                    img_bytes = generate_image_bytes_from_text(client, args.model, prompt, args.size)

                png_path.write_bytes(img_bytes)
                captions_lines.append(f"{png_path.name} | {prompt}")
                total += 1
                print(f"✅  salvo: {png_path}")
            except Exception as e:
                err = out_dir / f"{idx:03d}_ERROR.txt"
                write(err, f"Prompt:\n{prompt}\n\nErro:\n{e}")
                print(f"❌  erro na cena {idx}: {e}")

        write(captions_path, "\n".join(captions_lines))
        print(f"🗂  legendas: {captions_path}")

    print(f"\n🎉 Concluído. Imagens geradas: {total}")


if __name__ == "__main__":
    main()
