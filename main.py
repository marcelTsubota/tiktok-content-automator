import argparse, os
from pathlib import Path
import yaml
from dotenv import load_dotenv
from pipeline.script_generator import ScriptGenerator
from pipeline.metadata_generator import MetadataGenerator
from pipeline.shotlist_builder import ShotlistBuilder
from pipeline.asset_prompter import AssetPrompter

def load_config():
    with open(Path("configs/default.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def save(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((content or "").strip() + "\n", encoding="utf-8")

def run(topic: str, style: str, duration: int, language: str):
    cfg = load_config()
    load_dotenv()

    script = ScriptGenerator(cfg).generate_script(topic=topic, style=style, duration_seconds=duration, language=language)
    meta = MetadataGenerator(cfg).generate_metadata(topic=topic, script=script, language=language)
    shotlist_md = ShotlistBuilder(cfg).build_shotlist(script=script, duration_seconds=duration, language=language)
    asset_prompts = AssetPrompter(cfg).build_asset_prompts(topic=topic, script=script, language=language)

    out = Path("outputs")
    save(out/"script.txt", script)
    save(out/"title.txt", meta["title"])
    save(out/"description.txt", meta["description"])
    save(out/"hashtags.txt", "\n".join(meta["hashtags"]))
    save(out/"caption.txt", meta["caption"])
    save(out/"shotlist.md", shotlist_md)
    save(out/"asset_prompts.txt", "\n".join(asset_prompts["asset_search_terms"]))
    save(out/"thumbnail_prompts.txt", "\n".join(asset_prompts["thumbnail_prompts"]))
    print("✅ Conteúdos gerados em 'outputs/'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TikTok content automator (text-only)")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--style", default=None)
    parser.add_argument("--duration", type=int, default=None)
    parser.add_argument("--language", default=None)
    args = parser.parse_args()

    cfg = load_config()
    run(
        topic=args.topic,
        style=args.style or cfg["content"]["default_style"],
        duration=args.duration or cfg["content"]["default_duration"],
        language=args.language or cfg["content"]["default_language"],
    )
