# fill_invideo_with_script.py
# Lê outputs/prompt_packs/*/ e substitui o placeholder [roteiro Chatgpt]
# pelo conteúdo de prompt_02_roteiro.txt, gerando prompt_03_invideo_ready.txt

from pathlib import Path

ROOT = Path("outputs") / "prompt_packs"
PLACEHOLDER = "[roteiro Chatgpt]"

def run():
    if not ROOT.exists():
        raise SystemExit(f"Pasta não encontrada: {ROOT.resolve()}")

    packs = [p for p in ROOT.iterdir() if p.is_dir()]
    if not packs:
        raise SystemExit("Nenhum pack encontrado em outputs/prompt_packs/")

    done = 0
    for pack in sorted(packs):
        p2 = pack / "prompt_02_roteiro.txt"
        p3 = pack / "prompt_03_invideo.txt"
        if not p2.exists() or not p3.exists():
            print(f"⚠️  pulando {pack.name}: faltam arquivos.")
            continue

        roteiro = p2.read_text(encoding="utf-8").strip()
        invideo = p3.read_text(encoding="utf-8")

        if PLACEHOLDER not in invideo:
            print(f"ℹ️  {pack.name}: sem placeholder, gerando cópia pronta mesmo assim.")
            ready = invideo + "\n\n# Roteiro (anexo)\n" + roteiro
        else:
            ready = invideo.replace(PLACEHOLDER, roteiro)

        out = pack / "prompt_03_invideo_ready.txt"
        out.write_text(ready.strip() + "\n", encoding="utf-8")
        done += 1
        print(f"✅ preenchido: {pack.name}")

    print(f"\n🎉 Pronto! {done} arquivos gerados com roteiro embutido.")

if __name__ == "__main__":
    run()
