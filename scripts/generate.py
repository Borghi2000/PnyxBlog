import os
import json
import datetime
import google.generativeai as genai
from ddgs import DDGS
import requests
import time

def load_env():
    """Carrega variáveis de ambiente de um arquivo .env local."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

load_env()

def get_approval_from_telegram(article_title):
    """Envia o título do artigo para o Telegram e aguarda aprovação manual."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Aviso: Configurações do Telegram ausentes. Pulando aprovação (Modo Automático).")
        return True
    
    url_send = f"https://api.telegram.org/bot{token}/sendMessage"
    text = (
        f"🩺 <b>NOVO ARTIGO PNYXMED GERADO!</b>\n\n"
        f"<b>Título:</b> {article_title}\n\n"
        f"Responda <b>SIM</b> para publicar agora ou <b>NÃO</b> para descartar."
    )
    
    try:
        requests.post(url_send, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
        print(f"Solicitação de aprovação enviada para o Telegram (ID: {chat_id}).")
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")
        return True # Segue automático se falhar a rede

    print("Aguardando resposta no Telegram (Timeout: 10 minutos)...")
    start_time = time.time()
    last_update_id = 0
    
    # Busca o último update_id para ignorar mensagens antigas
    try:
        initial_updates = requests.get(f"https://api.telegram.org/bot{token}/getUpdates?limit=1").json()
        if initial_updates.get("result"):
            last_update_id = initial_updates["result"][-1]["update_id"]
    except:
        pass

    while time.time() - start_time < 600: # 10 minutos
        try:
            offset = int(last_update_id) + 1
            url_updates = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
            resp = requests.get(url_updates, timeout=35).json()
            
            if resp.get("result"):
                for update in resp["result"]:
                    last_update_id = update["update_id"]
                    message = update.get("message", {})
                    
                    # Verifica se a mensagem veio do chat_id correto
                    if str(message.get("chat", {}).get("id")) == str(chat_id):
                        text_received = message.get("text", "").upper().strip()
                        if text_received == "SIM":
                            print("✅ Artigo APROVADO via Telegram!")
                            return True
                        if text_received in ["NÃO", "NAO", "NO"]:
                            print("❌ Artigo REJEITADO via Telegram.")
                            return False
        except Exception as e:
            print(f"Erro ao consultar updates: {e}")
        
        time.sleep(5)
    
    print("⏰ Timeout: Nenhuma resposta recebida no Telegram. Artigo descartado.")
    return False

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
Seu objetivo é analisar as notícias médicas recentes fornecidas e escolher o tema MAIS RELEVANTE para quem estuda para provas de residência médica no Brasil (ENARE, USP, SUS-SP, etc).

DIRETRIZ DE FONTES DE PESQUISA (MANDATÓRIO):
O conteúdo do artigo deve advir EXCLUSIVAMENTE de Fontes Oficiais: 
1) Órgãos governamentais (Ministério da Saúde, OMS, OPAS, ANVISA, CDC); 
2) Conselhos, Sociedades de Especialidades e Instituições de Residência Médica de Prestígio (CFM, AMB, SBC, SBP, FEBRASGO, USP, UNICAMP, EINSTEIN, SIRIO-LIBANES, ENARE, etc.); 
3) Bases científicas (PubMed, SciELO, Cochrane) e jornais médicos Tier-1 (NEJM, Lancet, JAMA).

Foco Especial: Priorize informações sobre processos seletivos, cronogramas e editais das faculdades mais renomadas (USP, UNICAMP, Albert Einstein, Sírio-Libanês) quando o tema for relacionado a carreira e residência.

É EXPRESSAMENTE PROIBIDO consultar, citar, resumir ou referenciar qualquer conteúdo vindo de cursinhos preparatórios médicos, concorrentes ou plataformas educacionais (ex: SanarMed, Estratégia MED, Medway, Medcel, Aristo, Afya, Medgrupo). Também é EXPRESSAMENTE PROIBIDO o uso de sites de notícias gerais (UOL, G1, CNN), portais de fofocas, celebridades, entretenimento ou tabloides (ex: TV Prime, Terra, Léo Dias, etc.) como fonte primária médica. Todo embasamento científico e clínico deve vir da literatura original indexada e de guidelines oficiais.

ESTILIZAÇÃO DE TEXTO (MANDATÓRIO):
Você deve destacar TODOS os termos médicos vitais, conceitos-chave, nomes de doenças, guidelines, drogas e doses, ou sinais patognomônicos utilizando a seguinte tag HTML para aplicar a cor "azul accent":
<span className="text-blue-500 font-semibold">Termo Importante</span>
Aplique essa estilização generosamente ao longo de todas as seções para facilitar a leitura rápida (escaneabilidade) do médico.

PROLONGAMENTO E PROFUNDIDADE (MANDATÓRIO):
O conteúdo fornecido anteriormente foi considerado "curto" e "raso". VOCÊ DEVE redigir parágrafos longos, técnicos e com alta densidade de informação. Explore a fisiopatologia, o raciocínio diagnóstico diferencial e as minúcias do tratamento.

ESTRUTURA DO JSON (OBRIGATÓRIO):
Retorne APENAS um objeto JSON válido, sem markdown em volta (sem ```json), com esta exata estrutura:
{
  "id": "YYYY-MM-DD-slug-do-tema",
  "title": "Título de Alta Autoridade",
  "date": "YYYY-MM-DD",
  "category": "Atualização Médica",
  "tags": ["Tag1", "Tag2"],
  "content": {
    "contexto_clinico": "Parágrafos MENSURAVELMENTE LONGOS (mínimo 300 palavras nesta seção) detalhando a epidemiologia, fisiopatologia avançada e quadro clínico completo. Use abundantemente o destaque azul em sintomas e sinais físicos.",
    "o_que_mudou": "Análise técnica profunda das mudanças recentes ou consensos vigentes. Cite nomes de grandes estudos se houver.",
    "evidencias_e_guidelines": "Detalhamento das referências oficiais (ex: Diretriz da SBC, Guidelines da AHA/ESC/WHO), especificando graus de recomendação e níveis de evidência.",
    "o_que_muda_na_pratica": "Passo-a-passo clínico para o plantão e para a prova de residência (Dicas de Ouro / Macetes), focando no que cai nas bancas de elite (USP, Unicamp, ENARE, etc.)."
  },
  "source_urls": ["URL da fonte oficial baseada na notícia fornecida"]
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
    
    # Validação Básica e Aprovação
    try:
        article_json = json.loads(content)
        
        # --- APROVAÇÃO VIA TELEGRAM ---
        # Se você não configurar TELEGRAM_BOT_TOKEN, ele pula esta etapa.
        if not get_approval_from_telegram(article_json.get("title", "Novo Artigo")):
            return # Encerra sem salvar se não for aprovado
            
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
