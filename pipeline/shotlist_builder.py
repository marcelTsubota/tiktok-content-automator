from dataclasses import dataclass
from typing import Dict

@dataclass
class ShotlistBuilder:
    cfg: Dict

    def build_shotlist(self, script: str, duration_seconds: int, language: str = "pt-BR") -> str:
        beats = [
            ("Abertura/Dor", "Close do produto na mão / contexto real"),
            ("Curiosidade", "Transição mostrando recurso-chave"),
            ("Benefício 1", "Close de ação + texto on-screen"),
            ("Benefício 2", "Wide do ambiente (setup/home office)"),
            ("Prova social", "Corte rápido, detalhe de uso"),
            ("CTA", "Tela final simples, call-to-action direto"),
        ]
        per_beat = max(2, duration_seconds // max(1, len(beats)))
        lines = ["# Shotlist (aprox.)\n"]
        for title, idea in beats:
            lines += [f"## {title}  (~{per_beat}s)", f"- Visual: {idea}", f"- Diálogo/voz (trecho): {script[:120]}...", ""]
        return "\n".join(lines)
