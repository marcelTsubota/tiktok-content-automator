# tools/pipeline_oneclick.py
import argparse, sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

def run(cmd):
    print("↪", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser(description="One-click: CSV -> packs -> prompts finais (+ download de imagem)")
    ap.add_argument("--csv", required=True, help="CSV com product_name/produto e shopee_image_urls")
    ap.add_argument("--packs-root", default=str(ROOT / "outputs" / "prompt_packs"))
    ap.add_argument("--final-root", default="", help="Onde salvar os arquivo .txt")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--only-final", action="store_true", help="Não salvar intermediários RESPOSTA_*.txt")
    ap.add_argument("--skip-existing", action="store_true", help="Pular packs já processados")
    # flags do downloader do run_prompt_packs_openai.py
    ap.add_argument("--download-image", action="store_true")
    ap.add_argument("--images-from", choices=["csv","p01"], default="csv")
    ap.add_argument("--csv-path", default="data/batch_items.csv")
    ap.add_argument("--max-images", type=int, default=1)
    args = ap.parse_args()

    # 1) gerar os packs a partir do CSV
    run([sys.executable, str(TOOLS/"make_prompt_packs.py"),
         "--csv", args.csv,
         "--packs-root", args.packs_root])

    # 2) executar e produzir os .txt (+ download de imagem)
    cmd = [sys.executable, str(TOOLS/"run_prompt_packs_openai.py"),
           "--packs-root", args.packs_root,
           "--model", args.model,
           "--temperature", str(args.temperature)]
    if args.only_final:      cmd.append("--only-final")
    if args.skip_existing:   cmd.append("--skip-existing")
    if args.final_root:      cmd += ["--final-root", args.final_root]
    if args.download_image:  cmd.append("--download-image")
    cmd += ["--images-from", args.images_from,
            "--csv-path", args.csv_path,
            "--max-images", str(args.max_images)]
    run(cmd)

    # (opcional) índice consolidado, se você usa o index_csv_export.py
    idx = ROOT / "index_csv_export.py"
    if idx.exists():
        run([sys.executable, str(idx)])
        
    # 3) gerar imagens IA (6 por pack)
    try:
        print("\n🖼️  Chamando gerador de imagens IA (6 por pack)...")
        subprocess.run([
            sys.executable, str(TOOLS / "generate_images_openai.py"),
            "--packs-root", args.packs_root,
            "--model", "gpt-image-1",
            "--size", "1024x1536",
            "--source-root", args.final_root if args.final_root else "",
            "--final-root",  args.final_root if args.final_root else "",
            "--overwrite"
        ], check=False)
    except Exception as e:
        print(f"⚠️  Falha ao gerar imagens IA: {e}")

    print("\n🎉 Pipeline concluído!")

if __name__ == "__main__":
    main()




