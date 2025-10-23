from dataclasses import dataclass
from typing import Dict, List

@dataclass
class MetadataGenerator:
    cfg: Dict

    def generate_metadata(self, topic: str, script: str, language: str = "pt-BR") -> Dict:
        title = f"{topic.title()} sem complicação"
        description = (
            f"{topic} do jeito certo: rápido, prático e sem dor de cabeça.\n"
            "Confira no vídeo como usar e por que vale a pena."
        )
        hashtags = [
            "#tiktok", "#tecnologia", "#gadgets", "#review", "#dicas",
            "#setup", "#homeoffice", "#smart", "#conectado", "#expressTechTips"
        ]
        caption = f"{topic} • prático e portátil — veja nos stories! 🚀"
        return {"title": title, "description": description, "hashtags": hashtags, "caption": caption}
