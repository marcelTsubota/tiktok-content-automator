# index_csv_export.py
# Gera um resumo (index.csv) de todos os resultados gerados nos packs.
#
# Lê: outputs/prompt_packs/*/
# Extrai:
#   - Nome do produto (nome da pasta)
#   - Primeira linha do roteiro
#   - Quantidade de hashtags
#   - Caminho do arquivo f"{pack.name}.txt"
#
# Salva em: outputs/index.csv

import csv
import re
from pathlib import Path

ROOT = Path("outputs") / "prompt_packs"
OUT = Path("outputs") / "index.csv"

def extract_first_line(path: Path) -> str:
    """Retorna a primeira linha não vazia do roteiro."""
    file = path / "RESPOSTA_prompt_02_roteiro.txt"
    if not file.exists():
        return ""
    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            return line
    return ""

def count_hashtags(path: Path) -> int:
    """Conta quantas hashtags há no arquivo de descrição."""
    file = path / "RESPOSTA_prompt_04_descricao_hashtags.txt"
    if not file.exists():
        return 0
    text = file.read_text(encoding="utf-8")
    return len(set(re.findall(r"#\w+", text)))

def main():
    packs = [p for p in ROOT.iterdir() if p.is_dir()]
    if not packs:
        print("Nenhum pack encontrado em outputs/prompt_packs/")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for pack in sorted(packs):
        produto = pack.name
        roteiro = extract_first_line(pack)
        hashtags = count_hashtags(pack)
        resultado = (pack / f"{pack.name}.txt")
        rows.append([produto, roteiro, hashtags, resultado.as_posix()])
        print(f"✅ {produto}")

    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["produto", "roteiro_primeira_linha", "qtd_hashtags", "caminho_resultado"])
        writer.writerows(rows)

    print(f"\n🎯 Exportação concluída: {OUT.resolve()}")

if __name__ == "__main__":
    main()
