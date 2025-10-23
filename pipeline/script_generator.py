from dataclasses import dataclass
from typing import Dict, Optional
import os

@dataclass
class ScriptGenerator:
    cfg: Dict

    def _openai_generate(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        try:
            from openai import OpenAI
            client = OpenAI()
            model = self.cfg["llm"].get("model", "gpt-4o-mini")
            temperature = float(self.cfg["llm"].get("temperature", 0.7))
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return None

    def generate_script(self, topic: str, style: str, duration_seconds: int, language: str) -> str:
        system_prompt = f"Você é roteirista especialista em vídeos curtos. Estilo: {style}. Idioma: {language}. Duração: {duration_seconds}s."
        user_prompt = (
            f"Crie um roteiro persuasivo para 9:16 sobre '{topic}'. "
            "Abertura com dor/gancho; curiosidade; benefícios/prova; CTA. "
            "Apenas o texto, sem marcação de tempo."
        )
        use_openai = os.getenv("OPENAI_API_KEY") and self.cfg["llm"].get("provider") == "openai"
        if use_openai:
            out = self._openai_generate(system_prompt, user_prompt)
            if out: return out
        return (
            "Cansado de setups complicados?\n"
            "Conheça o mini teclado sem fio: compacto, preciso e pronto em segundos.\n"
            "Transforme seu home office e seus games com conforto real.\n"
            "Link na bio e experimente hoje."
        )
