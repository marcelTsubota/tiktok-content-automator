from dataclasses import dataclass
from typing import Dict, List

@dataclass
class AssetPrompter:
    cfg: Dict

    def build_asset_prompts(self, topic: str, script: str, language: str = "pt-BR") -> Dict[str, List[str]]:
        asset_terms = [
            f"{topic} close-up",
            f"{topic} on desk setup",
            "wireless keyboard minimalist desk",
            "typing hands macro",
            "gamer rgb desk close",
            "home office productivity vertical"
        ]
        thumb_prompts = [
            f"{topic} centralizado, fundo clean, luz lateral suave, contraste alto (vertical 9:16)",
            f"mão segurando {topic}, foco no detalhe, bokeh no fundo (9:16)",
            "setup clean com monitor e acessórios, estética minimalista, linhas simétricas (9:16)",
            "close dramático com sombras leves, textura do produto evidente (9:16)"
        ]
        return {"asset_search_terms": asset_terms, "thumbnail_prompts": thumb_prompts}
