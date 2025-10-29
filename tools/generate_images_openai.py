# tools/generate_images_openai.py
# Gera 6 imagens por pack usando as descrições de cena (ChatGPT) e salva localmente.
# Uso:
#   python tools/generate_images_openai.py --packs-root outputs/prompt_packs --model gpt-image-1 --size 1024x1792 --overwrite
#
# Requisitos:
#   pip install openai python-dotenv

import argparse
import base64
import os
import re
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from PIL import Image

DEFAULT_PACKS_ROOT = Path("outputs") / "prompt_packs"

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((content or "").strip() + "\n", encoding="utf-8")

def split_to_6_blocks(text: str) -> List[str]:
    txt = text.strip()
    if not txt:
        return []
    parts = re.split(r"(?:\n|\r\n)\s*(?:\d{1}[\)\.\:]\s+)", "\n" + txt)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 6:
        return parts
    parts = re.split(r"(?:^|\n)\s*\d{1}\s*[:\-]\s+", txt)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 6:
        return parts
    parts = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
    return parts[:6]

def ensure_openai():
    try:
        from openai import OpenAI
    except Exception as e:
        raise SystemExit("Falta o pacote 'openai'. Instale com: pip install openai") from e

def generate_image_b64(client, model: str, prompt: str, size: str) -> bytes:
    """
    Usa a API de geração de imagens da OpenAI.
    Documentação: https://platform.openai.com/docs/guides/images
    """
    resp = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
    )
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)

def to_png(src: Path) -> Path:
    """Converte WEBP/JPG -> PNG em disco e retorna o caminho PNG."""
    if src.suffix.lower() == ".png":
        return src
    png_path = src.with_suffix(".png")
    img = Image.open(src).convert("RGBA")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(png_path, format="PNG")
    return png_path

def find_source_image(pack_dir: Path, source_root: Path | None) -> Path | None:
    """
    Tenta achar uma imagem 'base' do produto:
    1) dentro do final-root/<pack_name> (pasta final do pipeline_oneclick),
    2) se não houver, tenta dentro do próprio pack.
    """
    candidates = []
    if source_root and (source_root / pack_dir.name).exists():
        candidates += list((source_root / pack_dir.name).glob("*_img*.*"))
    candidates += list(pack_dir.glob("*_img*.*"))
    for c in candidates:
        if c.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
            return c
    return None

def build_image_prompt(block: str, product_hint: str | None = None) -> str:
    block = re.sub(r"^\s*\d+\s*[\)\.\:\-]\s*", "", block).strip()
    body = " ".join([l.strip() for l in block.splitlines() if l.strip()]) or "Cena vertical de produto."
    focus = "mostrar claramente o produto em primeiro plano, foco nítido, sem pessoas, sem texto/legendas"
    style = "vertical 9:16 (composição tipo 1024x1536), luz suave, realista/naturalista, DOF leve, fundo limpo"
    product = f"Produto: {product_hint}. " if product_hint else ""
    return f"{product}{body}. {focus}. {style}."

def build_image_prompt(block: str) -> str:
    """
    Normaliza o texto do bloco para um prompt de imagem.
    Garante: 9:16 vertical, sem texto/legendas, foco no produto/ambiente.
    """
    block = re.sub(r"^\s*\d+\s*[\)\.\:\-]\s*", "", block).strip()
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if not lines:
        return "Cena vertical 9:16, realista, iluminação natural, sem texto."
    title = ""
    body = " ".join(lines)
    prompt = (
        f"{body} | vertical 9:16, naturalista/realista, luz suave, profundidade de campo, "
        f"sem texto/legendas, enquadramento limpo, nitidez alta."
    )
    return prompt

def generate_image_bytes_from_text(client, model: str, prompt: str, size: str) -> bytes:
    resp = client.images.generate(model=model, prompt=prompt, size=size)
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)

def generate_image_bytes_from_edit(client, model: str, source_png: Path, prompt: str, size: str) -> bytes:
    with open(source_png, "rb") as f:
        resp = client.images.edits(model=model, image=f, prompt=prompt, size=size)
    b64 = resp.data[0].b64_json
    return base64.b64decode(b64)

def main():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Falta OPENAI_API_KEY no .env")

    ensure_openai()
    from openai import OpenAI
    client = OpenAI()

    ap = argparse.ArgumentParser(description="Gera imagens 9:16 a partir dos prompts de cena.")
    ap.add_argument("--packs-root", default=str(DEFAULT_PACKS_ROOT), help="Pasta dos packs (default: outputs/prompt_packs)")
    ap.add_argument("--model", default="gpt-image-1", help="Modelo de imagem (ex.: gpt-image-1)")
    ap.add_argument("--size", default="1024x1792", help="Tamanho (9:16). Sug.: 1024x1792, 768x1365, 512x912")
    ap.add_argument("--overwrite", action="store_true", help="Sobrescrever imagens existentes")
    ap.add_argument("--source-root", default="", help="Pasta com imagens baixadas do produto (ex.: --final-root do pipeline_oneclick)")
    ap.add_argument("--final-root", default="", help="Pasta externa onde as imagens geradas devem ser salvas (subpastas por produto)")
    ap.add_argument("--limit-scenes", type=int, default=6, help="Gerar no máx. N cenas por pack (padrão: 6)")
    args = ap.parse_args()

    packs_root = Path(args.packs_root)
    source_root = Path(args.source_root) if args.source_root else None

    packs = [p for p in packs_root.iterdir() if p.is_dir()]
    total_imgs = 0
    for pack in sorted(packs):
        respostas = pack / "RESPOSTA_prompt_01_cenas.txt"
        original = pack / "prompt_01_cenas.txt"
        text = read(respostas) or read(original)
        if not text:
            print(f"⚠️  {pack.name}: sem texto de cenas — pulando.")
            continue

        blocks = split_to_6_blocks(text)
        #blocks = blocks[: max(1, args.limit_scenes)]
        if args.final_root:
            out_dir = Path(args.final_root) / pack.name
        else:
            out_dir = pack
        out_dir.mkdir(parents=True, exist_ok=True)
        #captions_path = out_dir / "_captions.txt"
        #captions_lines = []

        product_hint = pack.name.split("-", 1)[-1].replace("-", " ")

        source = find_source_image(pack, source_root)
        source_png = to_png(source) if source and source.exists() else None
        if source_png:
            print(f"🧷  usando imagem-base: {source_png}")

        print(f"\n▶️  {pack.name}: gerando imagens ({len(blocks)} cenas detectadas; usarei até {len(blocks)}).")
        for idx, block in enumerate(blocks, start=1):
            png_path = out_dir / f"{idx:03d}.png"
            if png_path.exists() and not args.overwrite:
                print(f"⏭  {png_path.name} já existe (use --overwrite para refazer).")
                #captions_lines.append(f"{png_path.name} | {block}")
                continue

            prompt = build_image_prompt(block, product_hint=product_hint)
            try:
                if source_png:
                    img_bytes = generate_image_bytes_from_edit(client, args.model, source_png, prompt, args.size)
                else:
                    img_bytes = generate_image_bytes_from_text(client, args.model, prompt, args.size)

                png_path.write_bytes(img_bytes)
                #captions_lines.append(f"{png_path.name} | {prompt}")
                total_imgs += 1
                print(f"✅  salvo: {png_path.relative_to(pack)}")
            except Exception as e:
                err_path = out_dir / f"{idx:03d}_ERROR.txt"
                write(err_path, f"Falha ao gerar esta cena.\nPrompt:\n{prompt}\n\nErro:\n{e}")
                print(f"❌  erro na cena {idx}: {e}")

        #write(captions_path, "\n".join(captions_lines))
        #print(f"🗂  legendas: {captions_path.relative_to(pack)}")

    print(f"\n🎉 Concluído. Imagens geradas: {total_imgs}")

if __name__ == "__main__":
    main()
