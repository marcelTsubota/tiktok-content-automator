# tools/make_prompt_packs.py
# Gerador de prompt packs a partir de um CSV.
# Uso:
#   python tools/make_prompt_packs.py --guide "guides/Guia criação dos vídeos.txt" \
#       --csv "data/batch_items.csv" --packs-root "outputs/prompt_packs"

import argparse
import csv
import os
import re
from pathlib import Path

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)   # remove pontuação
    text = re.sub(r"\s+", "-", text, flags=re.UNICODE)       # espaços -> hífen
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-") or "item"

def read_text(path: Path) -> str:
    if not path or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8-sig")

def main():
    ap = argparse.ArgumentParser(description="Gera prompt packs a partir de CSV.")
    ap.add_argument("--guide", default="guides/Guia criação dos vídeos.txt",
                    help="Guia base (opcional). Default: guides/Guia criação dos vídeos.txt")
    ap.add_argument("--csv", default="data/batch_items.csv",
                    help="CSV com colunas: produto, shopee_image_urls")
    ap.add_argument("--packs-root", default="outputs/prompt_packs",
                    help="Diretório de saída dos packs")
    args = ap.parse_args()

    guide_path = Path(args.guide)
    # se vier só o nome, tenta em guides/
    if not guide_path.exists():
        alt = Path("guides") / guide_path.name
        guide_path = alt if alt.exists() else guide_path

    csv_path = Path(args.csv)
    out_root = Path(args.packs_root)
    out_root.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        raise SystemExit(f"CSV não encontrado: {csv_path.resolve()}")

    guide_text = read_text(guide_path)  # opcional

    # lê CSV e valida cabeçalhos
    with csv_path.open("r", encoding="utf-8") as f:
        try:
            rd = csv.DictReader(f)
            rows = list(rd)
            headers = [h.strip() for h in (rd.fieldnames or [])]
        except UnicodeDecodeError:
            f.close()
            with csv_path.open("r", encoding="utf-8-sig") as f2:
                rd = csv.DictReader(f2)
                rows = list(rd)
                headers = [h.strip() for h in (rd.fieldnames or [])]

    if not rows:
        raise SystemExit("CSV vazio — adicione ao menos uma linha.")

    # resolve nomes de colunas tolerantes
    lower = {h.lower(): h for h in headers}
    def pick(*cands):
        for c in cands:
            if c in lower: return lower[c]
        return None

    col_prod = pick("produto", "product", "title", "nome", "nome_produto")
    col_urls = pick("shopee_image_urls", "image_urls", "urls", "links")
    if not col_prod:
        raise SystemExit(f"CSV sem coluna 'produto'. Cabeçalhos encontrados: {headers}")

    created = 0
    for i, row in enumerate(rows, 1):
        produto = (row.get(col_prod) or "").strip()
        if not produto:
            print(f"[{i:03d}] pulado: sem '{col_prod}'")
            continue
        urls_raw = (row.get(col_urls) or "").strip() if col_urls else ""
        urls = [u.strip() for u in urls_raw.split(";") if u.strip()] if urls_raw else []

        slug = slugify(produto)
        pack_dir = out_root / f"{i:03d}-{slug}"
        pack_dir.mkdir(parents=True, exist_ok=True)

        # --------- Templates ---------
        p01 = []
        if guide_text:
            p01.append("# Contexto (guia)\n" + guide_text.strip() + "\n")
        p01.append(f"Você vai propor 6 ideias visuais para o produto: **{produto}**.")
        p01.append(
            "- Regras obrigatórias para TODAS as ideias: proporção **9:16 (vertical)** e **sem textos/legendas/overlays** na imagem.\n"
            "- Descreva apenas a cena e os elementos visuais (nada de escrever texto na imagem)."
        )
        if urls:
            p01.append("Referências visuais (imagens reais do produto):\n" + "\n".join(urls))
        prompt_01 = "\n".join(p01).strip() + "\n"

        p02 = f"""Gere um roteiro curto em pt-BR para TikTok do produto **{produto}**.
Regras:
- Frases curtas, objetivas; máximo ~160 palavras no total.
- Estrutura: gancho/dor → benefício/curiosidade → prova simples → CTA curto ("Link na bio" ou "Link no perfil").
- Sem marcações de tempo.
- Linguagem natural, sem jargões.
"""

        p03 =f"""Esse é o roteiro do meu vídeo de vendas para o tiktok, dimensões 9:16. O produto é **{produto}**.
Important: No Captions, No avatar, No Narrator image. Crie a voz com essas falas:
No Captions, No avatar, No Narrator image.

[roteiro Chatgpt]
"""

        p04 = f"""Escreva uma descrição curta para o vídeo do produto **{produto}** em pt-BR,
com 1–2 parágrafos + (opcional) bullets curtos e 10–15 hashtags relevantes (evite genéricas demais).
"""

        # --------- Write files ---------
        (pack_dir / "prompt_01_cenas.txt").write_text(prompt_01, encoding="utf-8")
        (pack_dir / "prompt_02_roteiro.txt").write_text(p02.strip() + "\n", encoding="utf-8")
        (pack_dir / "prompt_03_invideo.txt").write_text(p03.strip() + "\n", encoding="utf-8")
        (pack_dir / "prompt_04_descricao_hashtags.txt").write_text(p04.strip() + "\n", encoding="utf-8")

        created += 1
        print(f"[{i:03d}] pack criado: {pack_dir.name}")

    if created == 0:
        print("⚠️ Nenhum pack foi criado (linhas sem 'produto'?).")
    else:
        print(f"🎉 {created} pack(s) criado(s) em {out_root.resolve()}")

if __name__ == "__main__":
    main()
