# test_openai_api.py
from openai import OpenAI
from dotenv import load_dotenv
import os

# Carrega o .env com a chave
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("❌ A variável OPENAI_API_KEY não foi encontrada no .env")
    exit()

# Inicializa o cliente
client = OpenAI()

print("🔄 Testando comunicação com a API da OpenAI...")

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Diga 'Olá, API da OpenAI está funcionando!'"}],
        max_tokens=20
    )

    print("✅ Sucesso! Resposta da API:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ Erro ao conectar na API:")
    print(e)
