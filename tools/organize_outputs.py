import argparse, shutil
from pathlib import Path
from typing import List

def list_packs(packs_root: Path) -> List[Path]:
    return sorted([p for p in packs_root.iterdir() if p.is_dir()])

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def move(src: Path, dst: Path):
    if not src.exists(): return False
    ensure_dir(dst.parent)
    try:
        shutil.move(str(src), str(dst))
        print(f"→ moveu: {src} -> {dst}")
        return True
    except Exception as e:
        print(f"⚠️  falha ao mover {src} -> {dst}: {e}")
        return False

def organize(packs_root: Path, final_root: Path, images_subdir: str = "", rename_first: str = ""):
    packs = list_packs(packs_root)
    if not packs:
        raise SystemExit(f"Nenhum pack encontrado em {packs_root.resolve()}")
    for pack in packs:
        name = pack.name
        flat_root = final_root if final_root else pack
        per_pack_dir = (final_root / name) if final_root else pack
        images_dir = per_pack_dir / images_subdir if images_subdir else per_pack_dir

        # mover RESULTADO_COMPLETO
        candidates_final = [flat_root / f"{name}.txt", pack / "RESULTADO_COMPLETO.txt"]
        final_src = next((c for c in candidates_final if c.exists()), None)
        if final_src:
            final_dst = per_pack_dir / "RESULTADO_COMPLETO.txt"
            if final_src.resolve() != final_dst.resolve():
                ensure_dir(per_pack_dir)
                move(final_src, final_dst)
        else:
            print(f"ℹ️  {name}: sem RESULTADO_COMPLETO para mover.")

        # mover imagens *_img*.ext
        moved_any = False
        for ext in (".jpg",".jpeg",".png",".webp"):
            for i in range(1, 10):
                src = flat_root / f"{name}_img{i}{ext}"
                if src.exists():
                    ensure_dir(images_dir)
                    dst_name = f"{rename_first}{ext}" if (rename_first and i == 1) else src.name
                    dst = images_dir / dst_name
                    move(src, dst)
                    moved_any = True
        if not moved_any:
            print(f"ℹ️  {name}: nenhuma imagem *_imgN* encontrada para mover.")

def main():
    ap = argparse.ArgumentParser(description="Organiza RESULTADO_COMPLETO e imagens em pastas por pack.")
    ap.add_argument("--packs-root", default="outputs/prompt_packs")
    ap.add_argument("--final-root", default=None, help="Se seus finais estão fora do projeto, aponte aqui.")
    ap.add_argument("--images-subdir", default="", help='Subpasta para imagens (ex.: "images")')
    ap.add_argument("--rename-first", default="", help='Renomear 1ª imagem (ex.: "thumb")')
    args = ap.parse_args()

    packs_root = Path(args.packs_root)
    final_root = Path(args.final_root).resolve() if args.final_root else None

    if not packs_root.exists():
        raise SystemExit(f"Pasta de packs não encontrada: {packs_root.resolve()}")
    if args.final_root and not final_root.exists():
        raise SystemExit(f"final-root não existe: {final_root}")

    organize(packs_root, final_root if final_root else Path(), args.images_subdir, args.rename_first)
    print("\n🎉 Organização concluída.")

if __name__ == "__main__":
    main()
