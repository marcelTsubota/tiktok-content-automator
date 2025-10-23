# tools/pipeline_oneclick.py (versão corrigida p/ Windows + preflight)
import argparse
import os
import subprocess
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS = PROJECT_ROOT / "tools"
PACKS_DIR = PROJECT_ROOT / "outputs" / "prompt_packs"
GUIDE_DEFAULT = PROJECT_ROOT / "guides" / "Guia criação dos vídeos.txt"
CSV_DEFAULT = PROJECT_ROOT / "data" / "batch_items.csv"

def run_cmd(args_list, cwd=None, extra_env=None):
    cwd = cwd or PROJECT_ROOT
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    print("\n$ ", " ".join([str(a) for a in args_list]), f"\n  (cwd={cwd})")
    subprocess.run(args_list, check=True, cwd=cwd, env=env)

def ensure_dirs():
    PACKS_DIR.mkdir(parents=True, exist_ok=True)

def clean_packs_dir():
    if not PACKS_DIR.exists(): return
    for child in PACKS_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try: child.unlink()
            except Exception: pass
    print("🧹 Limpou conteúdo de outputs/prompt_packs (regenerate).")

def main():
    ap = argparse.ArgumentParser(description="Pipeline 1-click: make → (fill) → run (final).")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--packs-root", default=str(PACKS_DIR))
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--only-final", action="store_true", default=True)
    ap.add_argument("--final-root", default=None)
    ap.add_argument("--no-fill", action="store_true")
    ap.add_argument("--download-image", action="store_true")
    ap.add_argument("--images-from", choices=["csv", "p01"], default="csv")
    ap.add_argument("--csv-path", default=str(CSV_DEFAULT))
    ap.add_argument("--max-images", type=int, default=1)
    ap.add_argument("--regenerate", action="store_true")
    ap.add_argument("--guide-path", default=str(GUIDE_DEFAULT),
                    help="Caminho do guia (default: guides/Guia criação dos vídeos.txt)")
    args = ap.parse_args()

    ensure_dirs()
    if args.regenerate: clean_packs_dir()

    # ✅ Pré-checagem
    guide_path = Path(args.guide_path)
    csv_path = Path(args.csv_path)
    if not guide_path.exists():
        print(f"❌ Guia não encontrado em: {guide_path}")
        print("   Dica: confirme se o arquivo está em 'guides/Guia criação dos vídeos.txt' ou passe --guide-path.")
        sys.exit(1)
    if not csv_path.exists():
        print(f"❌ CSV não encontrado em: {csv_path}")
        print("   Dica: confirme se o arquivo está em 'data/batch_items.csv' ou passe --csv-path.")
        sys.exit(1)

    # 1) make_prompt_packs.py (passa GUIDE_PATH e CSV_PATH via env)
    env_make = {
        "GUIDE_PATH": str(guide_path),
        "CSV_PATH": str(csv_path),
        "PACKS_ROOT": str(Path(args.packs_root)),
    }
    
    run_cmd([
        sys.executable, str(TOOLS / "make_prompt_packs.py"),
        "--guide", str(guide_path),
        "--csv", str(csv_path),
        "--packs-root", str(Path(args.packs_root))
    ], cwd=PROJECT_ROOT)
    
    # ✅ Checagem imediata: existem pastas criadas?
    from pathlib import Path as _P
    _created = [d for d in _P(args.packs_root).iterdir() if d.is_dir()] if _P(args.packs_root).exists() else []
    if not _created:
        raise SystemExit(
            f"⚠️ make_prompt_packs.py não gerou nenhum pack em {Path(args.packs_root).resolve()}.\n"
            f"Verifique o CSV e o Guia. Tente rodar manualmente para ver mensagens:\n"
            f'  {sys.executable} {TOOLS / "make_prompt_packs.py"} '
            f'--guide "{guide_path}" --csv "{csv_path}" --packs-root "{Path(args.packs_root)}"'
        )

    # 2) (opcional) fill_invideo_with_script.py
    if not args.no_fill:
        run_cmd([sys.executable, str(TOOLS / "fill_invideo_with_script.py")],
                cwd=PROJECT_ROOT)

    # 3) run_prompt_packs_openai.py
    cmd = [
        sys.executable,
        str(TOOLS / "run_prompt_packs_openai.py"),
        "--packs-root", args.packs_root,
        "--model", args.model,
        "--temperature", str(args.temperature),
        "--only-final",
    ]
    if args.skip_existing: cmd.append("--skip-existing")
    if args.final_root: cmd += ["--final-root", args.final_root]
    if args.download_image:
        cmd.append("--download-image")
        cmd += ["--images-from", args.images_from, "--csv-path", str(csv_path), "--max-images", str(args.max_images)]

    run_cmd(cmd, cwd=PROJECT_ROOT)
    print("\n🎉 Pipeline concluído!")

if __name__ == "__main__":
    main()
