import os
import json
import re
import requests

PROMPT_TEMPLATE = """
You are a forensic investment analyst with deep expertise in fundamental analysis, management evaluation,
and historical stock research. You have access to all publicly available information up to the analysis date
including annual reports, quarterly reports, management transcripts, press conferences, investor presentations,
and video recordings. Where video content is available, assess management body language and confidence levels.
You must not use any information beyond the specified historical date. Zero forward-looking bias is permitted.

ANALYSIS DATE: {analysis_date}
COMPANY: {company_name}
STOCK PRICE ON ANALYSIS DATE: {stock_price}

SECTION 2 - THEMATIC FLAGS (answer YES or NO only):
A. SUNRISE_SECTOR
B. STRONG_BRAND
C. CAPACITY_EXPANSION
D. MA_NEWS
E. GOVT_TAILWIND

SECTION 3 - OWNERSHIP (numbers only, null if unavailable):
PROMOTER_HOLDING_PCT, FII_PCT, DII_PCT, MF_PCT

SECTION 4 - SCORES (integer 0-100 for each, strictly as of {analysis_date}):
1. PROMOTER HOLDING
2. MANAGEMENT EXPERIENCE
3. MARKET OPPORTUNITY
4. GOVERNMENT BUDGET ALLOCATION
5. MANAGEMENT ASPIRATION
6. INTEGRITY OF MANAGEMENT
7. PRODUCT INNOVATION
8. TECHNOLOGY ADOPTION
9. EXPORT OPPORTUNITY EXECUTION
10. POLITICAL CONNECTIONS
11. TIMELY COMPLETION OF ORDERS
12. TIMELY EXECUTION OF PROJECTS
13. HIGH MARGIN OR MONOPOLY PRODUCTS
14. DEBTOR DAYS
15. CURRENT FINANCIAL CONDITION

SECTION 5 - VALUATION:
TARGET_PRICE_3Y (numeric only)

STRICT RULES:
- Use ONLY information available on or before {analysis_date}
- No hindsight, no forward-looking bias
- If data unavailable for a parameter, assign a conservative score

OUTPUT: Respond ONLY with a valid JSON object in this exact format, no other text:
{{
  "scores": [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13, s14, s15],
  "sunrise_sector": true/false,
  "strong_brand": true/false,
  "capacity_expansion": true/false,
  "ma_news": true/false,
  "govt_tailwind": true/false,
  "promoter_holding_pct": null or number,
  "fii_pct": null or number,
  "dii_pct": null or number,
  "mf_pct": null or number,
  "target_price_3y": number
}}
"""

def analyse_stock(stock_name: str, analysis_date: str, stock_price: float) -> dict:
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    if not api_key:
        raise ValueError("LLM_API_KEY is missing. Set it in .env")
    if not model:
        raise ValueError("LLM_MODEL is missing. Set it in .env")

    prompt = PROMPT_TEMPLATE.format(
        company_name=stock_name,
        analysis_date=analysis_date,
        stock_price=stock_price
    )
    
    raw = _call_gemini(prompt, api_key, model)
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)

def _call_gemini(prompt: str, api_key: str, model: str) -> str:
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",  
                "maxOutputTokens": 1024,
                "temperature": 0.2
            }
        }
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]
