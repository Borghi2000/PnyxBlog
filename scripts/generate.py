import os
import json
import datetime
import google.generativeai as genai
from ddgs import DDGS

def get_medical_news():
    """Busca as últimas notícias médicas e diretrizes usando DuckDuckGo (Gratuito)"""
    print("Buscando notícias recentes...")
    try:
        results = DDGS().text(
            "atualização diretriz medicina clínica cirurgia pediatria GO residência médica",
            region='br-tz',
            timelimit='w', # Última semana
            max_results=5
        )
        snippets = [f"- {r['title']} ({r['body']}) [Link: {r['href']}]" for r in results]
        return "\n".join(snippets)
    except Exception as e:
        print(f"Erro na pesquisa web: {e}")
        return "- Novas diretrizes de HAS 2024\n- Atualizações em sepse pediátrica\n- Manejo moderno de insuficiência cardíaca"

def generate_article():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente.")
    
    genai.configure(api_key=api_key)
    # Using gemini-3-flash-preview as requested by the user
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    news_context = get_medical_news()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print("Analisando temas com Google Gemini...")
    
    system_instruction = """
Você é um médico preceptor de residência médica de altíssimo nível acadêmico.
Seu objetivo é analisar as notícias médicas recentes fornecidas e escolher o tema MAIS RELEVANTE para quem estuda para provas de residência (ENARE, USP, SUS-SP, etc).

Em seguida, redija um artigo técnico focado.
OBRIGATÓRIO retornar APENAS um objeto JSON válido, sem markdown em volta (sem ```json), com esta exata estrutura:
{
  "id": "YYYY-MM-DD-slug-do-tema",
  "title": "Título Claro e Direto",
  "date": "YYYY-MM-DD",
  "category": "Atualização Médica",
  "tags": ["Tag1", "Tag2"],
  "content": {
    "contexto_clinico": "Parágrafos detalhados sobre a doença/condição.",
    "o_que_mudou": "O que a nova diretriz, paper ou consenso trouxe de novo.",
    "evidencias_e_guidelines": "Referências a evidências e grau de recomendação.",
    "o_que_muda_na_pratica": "Secão OBRIGATÓRIA explicando o que o interno/residente deve fazer diferente no plantão ou na prova."
  },
  "source_urls": ["URL da fonte baseada na notícia fornecida"]
}
"""

    prompt = f"""
{system_instruction}

Baseado nas seguintes notícias dos últimos 7 dias:
{news_context}

Escolha 1 tema, o mais frequente em provas, e gere o JSON para o artigo de hoje ({today_str}).
Lembre-se: SAÍDA APENAS EM JSON VÁLIDO.
"""

    print("Gerando o artigo via API...")
    response = model.generate_content(
        prompt,
        # Gemini specific setting to guarantee JSON output
        generation_config={"response_mime_type": "application/json"} 
    )
    
    content = response.text
    
    # Validação Básica
    try:
        article_json = json.loads(content)
        # Garante a data correta
        article_json["date"] = today_str
        file_name = f"{today_str}-{article_json['id'].split('-', 3)[-1]}.json"
        if not file_name.endswith('.json'):
             file_name += '.json'
        
        file_path = os.path.join(os.path.dirname(__file__), "..", "articles", file_name)
        
        # Cria a pasta se não existir
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(article_json, f, ensure_ascii=False, indent=2)
            
        print(f"Sucesso! Artigo gerado: {file_path}")
        
        # Atualiza o index.json
        index_path = os.path.join(os.path.dirname(file_path), "index.json")
        index_data = []
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        
        index_data.insert(0, {
            "id": article_json.get("id", f"{today_str}-novo-artigo"),
            "title": article_json.get("title", "Novo Artigo do Dia"),
            "date": article_json.get("date", today_str),
            "category": article_json.get("category", "Atualização Médica"),
            "tags": article_json.get("tags", []),
            "file": file_name
        })
        
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
            
        print("index.json atualizado com sucesso!")
        
    except json.JSONDecodeError as e:
        print(f"Erro ao parsear o JSON da IA: {e}")
        print("Raw output:", content)
        exit(1)

if __name__ == "__main__":
    generate_article()
