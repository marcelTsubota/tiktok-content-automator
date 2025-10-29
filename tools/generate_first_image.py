import argparse, base64, os, re
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

IMAGES_SECTION_RE = re.compile(r"##\s*IMAGENS\s*\(ChatGPT\)(.*?)(?:\n##|\Z)", re.IGNORECASE | re.DOTALL)
FIRST_PROMPT_RE = re.compile(r"1\.\s*(.+?)(?:\n\s*2\.|\Z)", re.DOTALL)

def read_text(p: Path) -> Optional[str]:
    if not p.exists(): return None
    try: return p.read_text(encoding="utf-8")
    except UnicodeDecodeError: return p.read_text(encoding="utf-8-sig")

def extract_first_image_prompt(text: str) -> Optional[str]:
    msec = IMAGES_SECTION_RE.search(text)
    if not msec: return None
    sec = msec.group(1).strip()
    mfirst = FIRST_PROMPT_RE.search(sec)
    if not mfirst: return None
    return mfirst.group(1).strip()

def find_downloaded_reference(dest_dir: Path, pack_name: str) -> Optional[Path]:
    for ext in (".jpg",".jpeg",".png",".webp"):
        p = dest_dir / f"{pack_name}_img1{ext}"
        if p.exists(): return p
    return None

def build_prompt(base_prompt: str, ref_path: Optional[Path]) -> str:
    core_rules = ("Proporção estrita 9:16 (vertical). "
                  "Imagem sem qualquer texto/legenda/marca-d'água/overlays. "
                  "Foco no produto em contexto real.")
    cleaned = re.sub(r"^\*\*.*?\*\*\s*", "", base_prompt.strip())
    cleaned = re.sub(r"^#+\s.*\n", "", cleaned).strip()
    if ref_path:
        return (f"{cleaned}\n\nRequisitos: {core_rules}\n"
                f"Referência visual: use características (cor/material/textura) da foto do produto em '{ref_path.name}'.")
    return f"{cleaned}\n\nRequisitos: {core_rules}"

def ensure_9x16_size() -> str:
    return "1024x1792"

def generate_image(prompt: str, save_to: Path, model: str = "gpt-image-1"):
    from openai import OpenAI
    client = OpenAI()
    resp = client.images.generate(model=model, prompt=prompt, size=ensure_9x16_size(), quality="high", n=1)
    b64 = resp.data[0].b64_json
    img_bytes = base64.b64decode(b64)
    save_to.parent.mkdir(parents=True, exist_ok=True)
    with open(save_to, "wb") as f:
        f.write(img_bytes)

def main():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Falta OPENAI_API_KEY no .env")
    ap = argparse.ArgumentParser(description="Gera 1 imagem 9:16 (sem textos) por pack a partir do arquivo .txt.")
    ap.add_argument("--packs-root", default="outputs/prompt_packs")
    ap.add_argument("--final-root", default=None, help="Se os arquivo .txt estão fora do projeto, aponte aqui.")
    ap.add_argument("--out-name", default="{pack}_gen1.png")
    ap.add_argument("--model", default="gpt-image-1")
    args = ap.parse_args()

    packs_root = Path(args.packs_root)
    if not packs_root.exists(): raise SystemExit(f"Pasta não encontrada: {packs_root.resolve()}")
    final_root = Path(args.final_root).resolve() if args.final_root else None

    packs = [p for p in packs_root.iterdir() if p.is_dir()]
    if not packs: raise SystemExit("Nenhum pack encontrado em " + str(packs_root.resolve()))

    total = 0
    for pack in sorted(packs):
        pack_name = pack.name
        if final_root:
            final_txt = final_root / f"{pack_name}.txt"
            dest_dir = final_root
        else:
            final_txt = (pack / f"{pack.name}.txt")
            dest_dir = pack

        txt = read_text(final_txt)
        if not txt:
            print(f"⚠️  pulando {pack_name}: não encontrei {final_txt.name}")
            continue

        base_prompt = extract_first_image_prompt(txt)
        if not base_prompt:
            print(f"⚠️  pulando {pack_name}: não consegui extrair a 1ª variação.")
            continue

        ref = find_downloaded_reference(dest_dir, pack_name)
        prompt = build_prompt(base_prompt, ref)

        out_path = dest_dir / args.out_name.format(pack=pack_name)
        try:
            generate_image(prompt, out_path, model=args.model)
            print(f"✅ imagem gerada: {out_path}")
            total += 1
        except Exception as e:
            print(f"❌ falha em {pack_name}: {e}")

    print(f"\n🎉 Concluído. Imagens geradas: {total}")

if __name__ == "__main__":
    main()
