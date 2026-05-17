import os
import re
import json
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_ai_config():
    """Retrieve AI configuration from environment variables."""
    return {
        "api_key": os.getenv("AI_API_KEY", os.getenv("OPENAI_API_KEY", "")),
        "api_provider": os.getenv("AI_PROVIDER", "openai").lower(),  # openai, ollama, groq, gemini, opencode
        "api_url": os.getenv("AI_API_URL", ""),
        "model": os.getenv("AI_MODEL", "gpt-4o-mini")
    }

def summarize_data(df: pd.DataFrame) -> dict:
    """Summarize DataFrame into a compact dictionary for LLM analysis."""
    if df.empty:
        return {}
        
    # Global metrics
    total_revenue = float(df['revenue'].sum())
    total_cost = float((df['cost'] * df['quantity']).sum())
    total_profit = float(df['profit'].sum())
    avg_margin = float(df['margin'].mean() * 100)
    total_qty = int(df['quantity'].sum())
    
    # Top 5 products by revenue
    top_products = df.groupby('product').agg(
        total_revenue=('revenue', 'sum'),
        total_qty=('quantity', 'sum'),
        avg_margin=('margin', 'mean')
    ).nlargest(5, 'total_revenue').reset_index()
    
    top_products['avg_margin'] = top_products['avg_margin'] * 100
    top_products_list = top_products.to_dict(orient='records')
    
    # Critical margin products (margin < 15% or negative profit)
    critical_products = df[df['margin'] < 0.15].groupby('product').agg(
        total_revenue=('revenue', 'sum'),
        total_qty=('quantity', 'sum'),
        avg_margin=('margin', 'mean')
    ).nsmallest(5, 'avg_margin').reset_index()
    
    critical_products['avg_margin'] = critical_products['avg_margin'] * 100
    critical_list = critical_products.to_dict(orient='records')
    
    # Sales by category
    category_summary = df.groupby('category').agg(
        total_revenue=('revenue', 'sum'),
        total_profit=('profit', 'sum'),
        total_qty=('quantity', 'sum')
    ).sort_values(by='total_revenue', ascending=False).reset_index().to_dict(orient='records')
    
    # Date evolution (simplified to top dates)
    date_evolution = df.groupby('date').agg(
        total_revenue=('revenue', 'sum'),
        total_profit=('profit', 'sum')
    ).sort_index().tail(10).reset_index().to_dict(orient='records')
    
    return {
        "kpis": {
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "avg_margin_percent": avg_margin,
            "total_quantity_sold": total_qty
        },
        "top_5_products_by_revenue": top_products_list,
        "critical_margin_products_under_15_percent": critical_list,
        "sales_by_category": category_summary,
        "recent_sales_evolution": date_evolution
    }



def ask_llm(provider: str, model: str, api_key: str, api_url: str, prompt: str) -> str:
    """Send requests to the configured LLM API provider."""
    # Clean up accidental double protocol typo like http://http://
    if api_url:
        api_url = re.sub(r'^(https?://)+http://', 'http://', api_url)
        api_url = re.sub(r'^(https?://)+https://', 'https://', api_url)
        
    # Build endpoint and headers
    headers = {"Content-Type": "application/json"}
    
    if provider == "openai":
        url = api_url if api_url else "https://api.openai.com/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        data = {
            "model": model if model else "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
    elif provider == "groq":
        url = api_url if api_url else "https://api.groq.com/openai/v1/chat/completions"
        headers["Authorization"] = f"Bearer {api_key}"
        data = {
            "model": model if model else "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
    elif provider == "ollama":
        if api_url:
            url = api_url
            # Check if user passed base OpenAI-compatible path
            if url.endswith("/v1") or url.endswith("/v1/"):
                url = url.rstrip("/") + "/chat/completions"
                
            # If URL is OpenAI compatible, use standard OpenAI payload
            if "/v1/chat/completions" in url:
                data = {
                    "model": model if model else "llama3",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
                }
            else:
                data = {
                    "model": model if model else "llama3",
                    "prompt": prompt,
                    "stream": False
                }
        else:
            url = "http://localhost:11434/api/generate"
            data = {
                "model": model if model else "llama3",
                "prompt": prompt,
                "stream": False
            }
    elif provider == "gemini":
        # Supports Gemini via OpenAI compatible endpoint or standard key
        if "openai" in api_url or not api_url:
            url = api_url if api_url else "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            headers["Authorization"] = f"Bearer {api_key}"
            data = {
                "model": model if model else "gemini-1.5-flash",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4
            }
        else:
            # Native Gemini API request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model if model else 'gemini-1.5-flash'}:generateContent?key={api_key}"
            data = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
    elif provider == "opencode":
        url = api_url if api_url else "http://localhost:11434/v1/chat/completions"
        if url.endswith("/v1") or url.endswith("/v1/"):
            url = url.rstrip("/") + "/chat/completions"
            
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        data = {
            "model": model if model else "qwen3.5:latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
    else:
        # Fallback to general OpenAI-compatible client
        url = api_url
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4
        }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=1200)
        response.raise_for_status()
        res_json = response.json()
        
        # Parse content based on structure
        if provider == "ollama" and "/v1/chat/completions" not in url:
            return res_json.get("response", "")
        elif "candidates" in res_json: # Native Gemini
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        else: # OpenAI style or Ollama compatible /v1
            return res_json["choices"][0]["message"]["content"]
            
    except Exception as e:
        print(f"API Error in ask_llm ({provider}): {e}")
        raise e

def generate_ai_insights(df: pd.DataFrame, custom_config: dict = None) -> str:
    """Generate strategic business insights from dataset using LLM or fallback heuristics."""
    if df.empty:
        return "Nenhum dado disponível para análise. Importe uma planilha primeiro."
        
    summary = summarize_data(df)
    
    # Get config (check custom override from streamlit first, then environment)
    config = custom_config if custom_config else get_ai_config()
    
    # Block execution if no API key is set for cloud providers
    if not config["api_key"] and config["api_provider"] not in ["ollama", "opencode"]:
        return f"> [!ERROR]\n> A chave de API não foi configurada para o provedor `{config['api_provider'].upper()}`. Por favor, adicione-a nas configurações para gerar a análise."
        
    # Prepare system-like prompt for LLM
    prompt = f"""Você é um Diretor de Business Intelligence (CFO/CMO) sênior e um consultor de negócios especialista em análise de dados corporativos. 
Sua tarefa é analisar os seguintes dados de vendas consolidados e gerar um relatório estratégico executivo de altíssimo nível em Markdown (Português do Brasil).

Dados consolidados do negócio em formato JSON:
{json.dumps(summary, indent=2)}

Por favor, elabore seu relatório com as seguintes seções estruturadas:

1. ## 📈 Relatório Executivo de Performance
- Faça uma análise crítica e narrativa sobre os números gerais: Faturamento (total_revenue), Custos (total_cost), Lucro Líquido (total_profit) e Margem Média (avg_margin_percent).
- Interprete o que esses números representam para a saúde financeira do negócio.
- Identifique qual a categoria dominante e qual a importância dela no faturamento.

2. ## ⚠️ Alertas Críticos de Margem e Operação
- Analise os produtos com margens de lucro críticas (critical_margin_products_under_15_percent).
- Explique o perigo operacional de manter esses produtos operando com margem tão baixa.
- Forneça recomendações práticas imediatas (ex: renegociação, aumento de preço, descontinuação) para cada um deles.

3. ## 💡 Estratégias Promocionais & Alavancagem de Vendas
- Sugira campanhas promocionais modernas e de alta performance baseadas nos dados.
- Crie estratégias de vendas combinadas (Cross-selling / Upselling) ligando os produtos de alto faturamento (top_5_products_by_revenue) a outros produtos ou categorias.
- Indique como expandir categorias secundárias que mostram potencial de crescimento.

4. ## 🔮 Previsões de Demanda e Tendências Futuras
- Baseado na evolução recente de vendas e faturamento, aponte tendências de crescimento ou retração.
- Dê orientações acionáveis para preparar o negócio para os próximos 30 a 60 dias (planejamento de estoque, sazonalidades, capital de giro).

REGRAS DE FORMATAÇÃO:
- Use markdown de alta qualidade com emojis apropriados e linguagem profissional, elegante e persuasiva.
- Nunca exiba a estrutura de JSON do prompt no seu output.
- Seja extremamente específico nos nomes dos produtos e categorias reais fornecidos nos dados.
- Mantenha o tom pragmático e estratégico de um consultor experiente.
- Evite generalidades. Fale diretamente com o dono do negócio sobre os números dele.
"""

    try:
        insights = ask_llm(
            provider=config["api_provider"],
            model=config["model"],
            api_key=config["api_key"],
            api_url=config["api_url"],
            prompt=prompt
        )
        return insights
    except Exception as e:
        # If API call fails, show the raw error to the user without mockups
        error_msg = str(e)
        return f"""> [!WARNING]
> Houve uma falha ao conectar com o provedor de IA ({config['api_provider'].upper()}). 
> Detalhes do erro: `{error_msg}`
> 
> Por favor, verifique se o modelo está rodando localmente (se for o caso) e se sua URL/Chave estão corretas nas configurações."""
