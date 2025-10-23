from pathlib import Path
from contextlib import redirect_stdout

# pastas que não queremos listar
IGNORAR = {"lib", "__pycache__", ".venv", "env", "venv", ".git"}

def listar(pasta: Path, nivel=0):
    prefixo = "│   " * (nivel - 1) + ("├── " if nivel > 0 else "")
    print(f"{prefixo}{pasta.name}/" if pasta.is_dir() else f"{prefixo}{pasta.name}")
    if pasta.is_dir():
        for item in sorted(pasta.iterdir()):
            # ignora pastas ou arquivos indesejados
            if item.name in IGNORAR:
                continue
            listar(item, nivel + 1)

root = Path(".")  # raiz do projeto
with open("estrutura.txt", "w", encoding="utf-8") as f:
    with redirect_stdout(f):
        listar(root)

print("✅ Arquivo 'estrutura.txt' gerado (sem pastas ignoradas)!")
