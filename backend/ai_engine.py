import os
import json
from openai import OpenAI

def analyze_and_translate_ufo_text(english_text: str, filename: str) -> dict:
    """
    Analyzuje text a vrací JSON s překladem a odhadovanými GPS souřadnicemi.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "translation_snippet": f"[Chybí OPENAI_API_KEY]: {english_text[:100]}...",
            "latitude": 37.2350,
            "longitude": -115.8111
        }
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = (
        "Jsi vojenský a aviatický analytik. Tvojí rolí je zpracovat odtajněný UAP/UFO spis.\n"
        "Ze zadaného textu a názvu souboru musíš vyvodit přibližnou geografickou lokaci incidentu "
        "(např. stát Montana, Utah, Středozemní moře, atd.) a převést ji na desetinné GPS souřadnice (latitude a longitude).\n"
        "Dále napiš stručný český překlad a analýzu události. Zachovej odbornou terminologii.\n\n"
        "Odpověz striktně a POUZE ve formátu JSON s těmito přesnými klíči:\n"
        "{\n"
        '  "translation_snippet": "Český překlad a analýza události...",\n'
        '  "latitude": 40.7608,\n'
        '  "longitude": -111.8910\n'
        "}\n"
        "Pokud lokaci nelze z textu ani názvu vůbec zjistit, použij defaultně 37.2350 a -115.8111 (Area 51)."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Název souboru: {filename}\n\nText spisu: {english_text[:4000]}"}
            ],
            temperature=0.2,
            response_format={ "type": "json_object" } # Důležité: Vynutí formát JSON
        )
        
        # Převedení textové odpovědi od AI zpět na Python slovník (dict)
        result_json = json.loads(response.choices[0].message.content)
        return result_json
    except Exception as e:
        print(f"⚠️ Chyba AI analýzy: {e}")
        return {
            "translation_snippet": "Překlad a geolokace selhala kvůli chybě API.",
            "latitude": 37.2350,
            "longitude": -115.8111
        }
