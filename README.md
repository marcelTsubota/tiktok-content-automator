# 🎬 TikTok Content Automator

Automação completa para geração de **roteiros, descrições, hashtags e assets** de vídeos curtos (9:16) para TikTok — totalmente impulsionada por IA.
O projeto lê uma planilha de produtos, gera prompts com base em um guia de criação, preenche scripts automaticamente e organiza os resultados em pastas prontas para produção.

## COMANDO ÚNICO

python tools\pipeline_oneclick.py --csv data\batch_items.csv --packs-root outputs\prompt_packs --final-root "C:\Users\marce\OneDrive\OneDrive (C)\Área de Trabalho\ExpressTechTips\estoque" --model gpt-4o-mini --temperature 0.7 --only-final --download-image --images-from csv --csv-path data\batch_items.csv --max-images 1

# --only-final [SOMENTE O ARQUIVO COM O RESULTADO]

# --final-root "C:\PASTA_DESTINO" [ESCOLHER A PASTA DE DESTINO]

# --download-image --images-from p01 --max-images 1 [BAIXAR A IMAGEM DO PROMPT]

# --download-image --images-from csv --csv-path data/batch_items.csv --max-images 1 [BAIXAR A IMAGEM DA URL DO CSV]

## 🚀 Funcionalidades principais

- 🧠 **Geração de roteiros e metadados** com IA (OpenAI API)
- 🪄 **Criação automática de “prompt packs”** por produto
- ✍️ **Preenchimento automático** de roteiros (InVideo, VSL, etc.)
- 📂 **Estrutura organizada** para guias, dados e ferramentas
- 📊 **Exportação opcional** para planilha consolidada (roteiro + hashtags)
- ⚙️ Pronto para extensão futura com pipeline de vídeo (TTS, assets e upload)

## 🗂️ Estrutura de pastas

tiktok_content_automator/
├─ README.md
├─ main.py # entrada principal (modo texto-only)
│
├─ configs/
│ └─ default.yaml # presets de estilo, fps, vozes, cores
│
├─ guides/
│ └─ Guia criação dos vídeos.txt # modelo de prompts com placeholders
│
├─ data/
│ └─ batch_items.csv # lista de produtos e URLs
│
├─ pipeline/
│ ├─ init.py
│ ├─ script_generator.py
│ ├─ metadata_generator.py
│ ├─ shotlist_builder.py
│ └─ asset_prompter.py
│
├─ tools/
│ ├─ make_prompt_packs.py # cria prompt packs a partir do CSV
│ ├─ fill_invideo_with_script.py # insere roteiro no prompt_03
│ └─ run_prompt_packs_openai.py # executa prompts com modelo GPT
│
└─ outputs/
├─ prompt_packs/ # diretórios gerados por produto
├─ script.txt
├─ title.txt
├─ description.txt
├─ hashtags.txt
├─ caption.txt
├─ shotlist.md
├─ asset_prompts.txt
└─ thumbnail_prompts.txt

## ⚡ Fluxo de trabalho

### 1️⃣ Gerar Prompt Packs

```bash
python tools/make_prompt_packs.py
Preencher [roteiro ChatGPT] no InVideo
python tools/fill_invideo_with_script.py
Rodar a automação completa (OpenAI)
python tools/run_prompt_packs_openai.py --model gpt-4o-mini --temperature 0.7


Requisitos
Python 3.10+
Bibliotecas: openai, pandas, tqdm, python-dotenv
pip install -r requirements.txt


Extensões futuras (planejadas)
🎙️ Geração de voz com TTS (ex: ElevenLabs, Azure)
🖼️ Criação de imagens/frames com IA
🪞 Montagem de vídeos automáticos (ffmpeg)
⏫ Upload automatizado para TikTok


🧾 Licença
Projeto de uso pessoal e experimental — livre para estudos e modificações.
© 2025 — TikTok Content Automator by Marcel Tsubota
```
