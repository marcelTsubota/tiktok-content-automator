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

DEFAULT_PACKS_ROOT = Path("outputs") / "prompt_packs"

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write(p: Path, content: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text((content or "").strip() + "\n", encoding="utf-8")

def split_to_6_blocks(text: str) -> List[str]:
    # mesmo espírito do validador do seu runner
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
    # se vierem mais de 6 blocos por algum motivo, corta nos 6 primeiros
    return parts[:6]

def build_image_prompt(block: str) -> str:
    """
    Normaliza o texto do bloco para um prompt de imagem.
    Garante: 9:16 vertical, sem texto/legendas, foco no produto/ambiente.
    """
    # remove numeração tipo "1) Título — texto"
    block = re.sub(r"^\s*\d+\s*[\)\.\:\-]\s*", "", block).strip()
    # opcional: se houver um título em primeira linha, mantemos como contexto curto
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

def ensure_openai():
    try:
        from openai import OpenAI  # noqa
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
        # você pode ajustar: quality="high", style="natural"
    )
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
    args = ap.parse_args()

    packs_root = Path(args.packs_root)
    if not packs_root.exists():
        raise SystemExit(f"Pasta não encontrada: {packs_root.resolve()}")

    packs = [p for p in packs_root.iterdir() if p.is_dir()]
    if not packs:
        raise SystemExit("Nenhum pack encontrado.")

    total_imgs = 0
    for pack in sorted(packs):
        # preferir a RESPOSTA (já validada). Se não existir, cai no prompt original.
        respostas = pack / "RESPOSTA_prompt_01_cenas.txt"
        original = pack / "prompt_01_cenas.txt"
        text = read(respostas) or read(original)
        if not text:
            print(f"⚠️  {pack.name}: sem texto de cenas — pulando.")
            continue

        blocks = split_to_6_blocks(text)
        if len(blocks) < 1:
            print(f"⚠️  {pack.name}: não foi possível separar 6 cenas — pulando.")
            continue

        out_dir = pack / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        captions_path = out_dir / "_captions.txt"
        captions_lines = []

        print(f"\n▶️  {pack.name}: gerando imagens ({len(blocks)} cenas detectadas; usarei até 6).")
        for idx, block in enumerate(blocks[:6], start=1):
            png_path = out_dir / f"{idx:03d}.png"
            if png_path.exists() and not args.overwrite:
                print(f"⏭  {png_path.name} já existe (use --overwrite para refazer).")
                captions_lines.append(f"{png_path.name} | {block}")
                continue

            prompt = build_image_prompt(block)
            try:
                img_bytes = generate_image_b64(client, args.model, prompt, args.size)
                png_path.write_bytes(img_bytes)
                captions_lines.append(f"{png_path.name} | {prompt}")
                total_imgs += 1
                print(f"✅  salvo: {png_path.relative_to(pack)}")
            except Exception as e:
                err_path = out_dir / f"{idx:03d}_ERROR.txt"
                write(err_path, f"Falha ao gerar esta cena.\nPrompt:\n{prompt}\n\nErro:\n{e}")
                print(f"❌  erro na cena {idx}: {e}")

        write(captions_path, "\n".join(captions_lines))
        print(f"🗂  legendas: {captions_path.relative_to(pack)}")

    print(f"\n🎉 Concluído. Imagens geradas: {total_imgs}")

if __name__ == "__main__":
    main()
