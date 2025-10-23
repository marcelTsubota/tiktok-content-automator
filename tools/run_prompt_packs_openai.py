# tools/run_prompt_packs_openai.py
# Versão unificada com:
#   --only-final   → não grava intermediários (RESPOSTA_*.txt)
#   --final-root   → salva RESULTADO_COMPLETO.txt fora do projeto
#   --download-image / --images-from / --csv-path / --max-images → baixa imagens do produto e salva no mesmo dir do final
#
# Exemplos:
#   python tools/run_prompt_packs_openai.py --model gpt-4o-mini --temperature 0.7 --only-final
#   python tools/run_prompt_packs_openai.py --model gpt-4o-mini --temperature 0.7 --only-final --final-root "D:/Conteudos/Resultados"
#   python tools/run_prompt_packs_openai.py --only-final --download-image --images-from csv --csv-path data/batch_items.csv --max-images 1

import argparse
import os
import re
import csv
import mimetypes
import shutil
from pathlib import Path
from typing import Optional, List, Dict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from dotenv import load_dotenv

PACKS_ROOT = Path("outputs") / "prompt_packs"
PLACEHOLDER = "[roteiro Chatgpt]"

MASTER_SYSTEM = """Você é um redator e diretor de conteúdo para TikTok em pt-BR.
Regras gerais:
- Formato vertical 9:16.
- Sem marcações de tempo nos roteiros.
- Frases curtas, objetivas; no máx. 1 emoji por bloco (quando fizer sentido).
- CTA curto: “Link na bio” ou “Link no perfil”.
- Evite jargões; fale como quem recomenda um achado real.

Para PROMPTS DE IMAGEM:
- Entregue 6 variações, cada uma com um título curto e 1 parágrafo (1–2 frases).
- Sem texto sobre a imagem; explicite 9:16; foco no produto e contexto real de uso.

Para DESCRIÇÕES:
- 1–2 parágrafos + bullets opcionais + 10–15 hashtags relevantes (evite genéricas demais).

Se receber URLs de imagens (Shopee), trate como referência visual (cores, ângulos, contexto).

Para InVideo:
- Respeite: “No Captions, No avatar, No Narrator image.”
- O roteiro final será inserido num template; você não precisa gerar esse template.
"""


def read(path: Path) -> Optional[str]:
    return path.read_text(encoding="utf-8") if path.exists() else None

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text or "").strip() + "\n", encoding="utf-8")

def ask_openai(prompt: str, model: str, temperature: float, system: Optional[str] = None) -> str:
    from openai import OpenAI
    client = OpenAI()
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=msgs,
    )
    return resp.choices[0].message.content.strip()

def count_words(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))

def extract_hashtags(text: str) -> List[str]:
    tags = re.findall(r"#\w+", text)
    out, seen = [], set()
    for t in tags:
        if t.lower() not in seen:
            out.append(t)
            seen.add(t.lower())
    return out

def split_to_6_blocks(text: str) -> List[str]:
    parts = re.split(r"(?:\n|\r\n)\s*(?:\d{1}[\)\.\:]\s+)", "\n" + text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 6:
        return parts
    parts = re.split(r"(?:^|\n)\s*\d{1}\s*[:\-]\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 6:
        return parts
    parts = [b.strip() for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    return parts

def run_imagens(p01: str, model: str, temperature: float) -> str:
    reforco = (
        "\n\n[REQUISITOS OBRIGATÓRIOS — IMAGENS]\n"
        "- Proporção estrita: 9:16 (vertical).\n"
        "- A imagem NÃO pode conter textos, legendas, marcas d’água ou overlays.\n"
        "- Descreva apenas a cena/elementos visuais (sem pedir textos na imagem).\n"
    )

    prompt_reforcado = f"{p01}{reforco}"

    out = ask_openai(prompt_reforcado, model, temperature, system=MASTER_SYSTEM)

    lower = out.lower()
    has_ratio = "9:16" in out
    mentions_no_text = ("sem texto" in lower) or ("sem textos" in lower) or ("sem legenda" in lower) or ("sem legendas" in lower)
    if not (has_ratio and mentions_no_text):
        fix = (
            "Ajuste a resposta garantindo que TODAS as variações especifiquem explicitamente: "
            "Proporção 9:16 e que a imagem não possui texto/legendas. "
            "Mantenha a descrição visual; não altere o conteúdo além disso."
        )
        out = ask_openai(f"{prompt_reforcado}\n\n{fix}", model, temperature, system=MASTER_SYSTEM)

    return out

def run_roteiro(p02: str, model: str, temperature: float, max_words: int = 160) -> str:
    out = ask_openai(p02, model, temperature, system=MASTER_SYSTEM)
    if count_words(out) > max_words:
        fix_prompt = (
            f"A resposta ficou longa. Encurte para no máximo {max_words} palavras, mantendo a estrutura: "
            "dor/gancho → curiosidade → benefícios/prova simples → CTA curto ('Link na bio' ou 'Link no perfil'). "
            "Apenas o texto do roteiro."
        )
        out = ask_openai(f"{p02}\n\n{fix_prompt}\n\n---\nRascunho anterior (encurtar):\n{out}", model, temperature, system=MASTER_SYSTEM)
    return out

def run_descricao(p04: str, model: str, temperature: float, min_tags: int = 10, max_tags: int = 15) -> str:
    out = ask_openai(p04, model, temperature, system=MASTER_SYSTEM)
    tags = extract_hashtags(out)
    if not (min_tags <= len(tags) <= max_tags):
        fix_prompt = (
            f" ajuste a resposta para conter entre {min_tags} e {max_tags} hashtags reais do nicho (não genéricas demais). "
            "Mantenha os parágrafos e bullets como estão."
        )
        out = ask_openai(f"{p04}\n\nA resposta veio com {len(tags)} hashtags;{fix_prompt}\n\n---\nVersão anterior (ajustar hashtags):\n{out}",
                         model, temperature, system=MASTER_SYSTEM)
    return out

URL_PATTERN = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)

def parse_urls_from_p01(p01_text: Optional[str]) -> List[str]:
    """Extrai URLs aparentes do texto do prompt_01 (útil se você anexar URLs lá)."""
    if not p01_text:
        return []
    urls = URL_PATTERN.findall(p01_text)
    return [u.strip() for u in urls if u.strip()]

def load_urls_from_csv(csv_path: Path) -> Dict[int, List[str]]:
    """
    Lê batch_items.csv e retorna {index_1based: [url1, url2, ...]}.
    Coluna esperada: 'shopee_image_urls' com URLs separadas por ';'.
    A linha 1 do CSV corresponde ao pack '001-*', a 2 ao '002-*', etc.
    """
    out: Dict[int, List[str]] = {}
    if not csv_path.exists():
        return out
    with csv_path.open("r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        rows = list(rd)
    for i, row in enumerate(rows, 1):
        urls = (row.get("shopee_image_urls") or "").strip()
        lst = [u.strip() for u in urls.split(";") if u.strip()] if urls else []
        out[i] = lst
    return out

def pack_index_from_name(pack_dir: Path) -> Optional[int]:
    """Extrai o índice do diretório do pack: '001-slug' → 1, '012-algo' → 12."""
    try:
        prefix = pack_dir.name.split("-")[0]
        return int(prefix)
    except Exception:
        return None

def pick_ext(url: str, content_type: Optional[str]) -> str:
    """Decide extensão pelo Content-Type; fallback pelo sufixo da URL."""
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    for cand in (".jpg", ".jpeg", ".png", ".webp"):
        if url.lower().split("?")[0].endswith(cand):
            return cand
    return ".jpg"

def download_one(url: str, dest_without_ext: Path, timeout: int = 20) -> Optional[Path]:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            ext = pick_ext(url, ct)
            out_path = dest_without_ext.with_suffix(ext)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "wb") as f:
                shutil.copyfileobj(r, f)
        print(f"🖼️  Baixou: {out_path.name}")
        return out_path
    except (URLError, HTTPError) as e:
        print(f"⚠️  Falha ao baixar {url}: {e}")
        return None
    except Exception as e:
        print(f"⚠️  Erro inesperado em {url}: {e}")
        return None

def download_images_for_pack(pack: Path, dest_dir: Path, images_from: str,
                             csv_map: Dict[int, List[str]], max_images: int) -> List[Path]:
    """Seleciona URLs (CSV ou p01) e baixa até N imagens para dest_dir."""
    urls: List[str] = []
    if images_from == "csv":
        idx = pack_index_from_name(pack)
        if idx and idx in csv_map:
            urls = csv_map[idx]
    else:
        urls = parse_urls_from_p01(read(pack / "prompt_01_cenas.txt"))

    urls = [u for u in urls if u.lower().startswith("http")]
    if not urls:
        print("ℹ️  Nenhuma URL de imagem encontrada para este pack.")
        return []

    saved: List[Path] = []
    for i, url in enumerate(urls[:max_images], 1):
        base = f"{pack.name}_img{i}"
        dest_wo_ext = dest_dir / base
        out = download_one(url, dest_wo_ext)
        if out:
            saved.append(out)
    return saved

def main():
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Falta OPENAI_API_KEY no .env")

    ap = argparse.ArgumentParser(description="Executa packs e gera o resultado final; suporta --only-final, --final-root e download de imagens.")
    ap.add_argument("--packs-root", default=str(PACKS_ROOT), help="Pasta com os packs (default: outputs/prompt_packs)")
    ap.add_argument("--model", default="gpt-4o-mini", help="Modelo OpenAI (ex: gpt-4o-mini, gpt-4.1-mini, etc.)")
    ap.add_argument("--temperature", type=float, default=0.7, help="Temperatura do LLM (0.0-1.0)")
    ap.add_argument("--skip-existing", action="store_true", help="Não reprocessa packs que já têm RESULTADO_COMPLETO")
    ap.add_argument("--only-final", action="store_true", help="Não gerar intermediários; salvar apenas RESULTADO_COMPLETO")
    ap.add_argument("--final-root", default=None, help="Diretório externo para salvar somente os RESULTADO_COMPLETO (um .txt por pack)")
    ap.add_argument("--download-image", action="store_true", help="Baixar imagem(ns) do produto para a mesma pasta do RESULTADO_COMPLETO")
    ap.add_argument("--images-from", choices=["csv", "p01"], default="p01", help="Origem das URLs: 'csv' (batch_items.csv) ou 'p01' (prompt_01_cenas.txt)")
    ap.add_argument("--csv-path", default="data/batch_items.csv", help="Caminho do CSV (usado se --images-from csv)")
    ap.add_argument("--max-images", type=int, default=1, help="Máximo de imagens para baixar por pack (default: 1)")
    args = ap.parse_args()

    packs_root = Path(args.packs_root)
    if not packs_root.exists():
        raise SystemExit(f"Pasta não encontrada: {packs_root.resolve()}")

    final_root = Path(args.final_root).resolve() if args.final_root else None
    if final_root:
        final_root.mkdir(parents=True, exist_ok=True)

    packs = [p for p in packs_root.iterdir() if p.is_dir()]
    if not packs:
        raise SystemExit("Nenhum pack encontrado.")

    # Mapa de URLs do CSV (se necessário)
    csv_map: Dict[int, List[str]] = {}
    if args.download_image and args.images_from == "csv":
        csv_map = load_urls_from_csv(Path(args.csv_path))

    def result_dir_for(pack: Path) -> Path:
        """Diretório onde o final será gravado (pack ou final_root)."""
        return final_root if final_root else pack

    def result_path_for(pack: Path) -> Path:
        """Caminho do arquivo final."""
        if final_root:
            return final_root / f"{pack.name}.txt"
        return pack / "RESULTADO_COMPLETO.txt"

    def result_exists(pack: Path) -> bool:
        return result_path_for(pack).exists()

    def write_if(path: Path, content: str):
        if not args.only_final:
            write(path, content)

    total = 0
    for pack in sorted(packs):
        if args.skip_existing and result_exists(pack):
            print(f"⏭  pulando (já existe): {pack.name}")
            continue

        print(f"\n▶️  processando: {pack.name}")

        p01 = read(pack / "prompt_01_cenas.txt")
        p02 = read(pack / "prompt_02_roteiro.txt")
        p03 = read(pack / "prompt_03_invideo.txt")
        p04 = read(pack / "prompt_04_descricao_hashtags.txt")

        if not p02:
            print(f"⚠️  {pack.name}: falta prompt_02_roteiro.txt — pulando.")
            continue

        # 1) IMAGENS (texto para o relatório)
        if p01:
            try:
                imagens_out = run_imagens(p01, args.model, args.temperature)
                write_if(pack / "RESPOSTA_prompt_01_cenas.txt", imagens_out)
            except Exception as e:
                imagens_out = f"[ERRO ao gerar imagens: {e}]"
                write_if(pack / "RESPOSTA_prompt_01_cenas.txt", imagens_out)
        else:
            imagens_out = "[Sem prompt_01_cenas.txt]"

        # 2) ROTEIRO
        try:
            roteiro_out = run_roteiro(p02, args.model, args.temperature, max_words=160)
            write_if(pack / "RESPOSTA_prompt_02_roteiro.txt", roteiro_out)
        except Exception as e:
            roteiro_out = f"[ERRO ao gerar roteiro: {e}]"
            write_if(pack / "RESPOSTA_prompt_02_roteiro.txt", roteiro_out)

        # 3) INVIDEO READY
        if p03:
            if PLACEHOLDER in (p03 or "") and roteiro_out and not roteiro_out.startswith("[ERRO"):
                invideo_ready = p03.replace(PLACEHOLDER, roteiro_out)
            else:
                invideo_ready = (p03 or "") + "\n\n# Roteiro (anexo)\n" + (roteiro_out or "")
            write_if(pack / "RESPOSTA_prompt_03_invideo_READY.txt", invideo_ready)
        else:
            invideo_ready = "[Sem prompt_03_invideo.txt]"

        # 4) DESCRIÇÃO/HASHTAGS
        if p04:
            try:
                desc_out = run_descricao(p04, args.model, args.temperature, min_tags=10, max_tags=15)
                write_if(pack / "RESPOSTA_prompt_04_descricao_hashtags.txt", desc_out)
            except Exception as e:
                desc_out = f"[ERRO ao gerar descrição: {e}]"
                write_if(pack / "RESPOSTA_prompt_04_descricao_hashtags.txt", desc_out)
        else:
            desc_out = "[Sem prompt_04_descricao_hashtags.txt]"

        # 5) Consolida o final
        final_dir = result_dir_for(pack)
        final_path = result_path_for(pack)
        full = []
        full.append(f"# {pack.name}\n")
        full.append("## IMAGENS (ChatGPT)\n"); full.append(imagens_out or "")
        full.append("\n## ROTEIRO (ChatGPT)\n"); full.append(roteiro_out or "")
        full.append("\n## INVIDEO (READY)\n"); full.append(invideo_ready or "")
        full.append("\n## DESCRIÇÃO/HASHTAGS (ChatGPT)\n"); full.append(desc_out or "")
        write(final_path, "\n".join(full))
        print(f"✅ pronto: {final_path}")

        # 6) (Opcional) Baixar imagem(ns) do produto para a MESMA pasta do final
        if args.download_image:
            saved = download_images_for_pack(
                pack=pack,
                dest_dir=final_dir,
                images_from=args.images_from,
                csv_map=csv_map,
                max_images=max(1, int(args.max_images)),
            )
            if saved:
                print(f"🖼️  Imagens salvas em: {final_dir} → {[p.name for p in saved]}")

        total += 1

    print(f"\n🎉 Finalizado! {total} packs processados.")
    print(f"↳ Origem dos packs: {packs_root.resolve()}")
    if final_root:
        print(f"↳ Resultados finais em: {final_root.resolve()}")

if __name__ == "__main__":
    main()
