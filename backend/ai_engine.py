import os
from openai import OpenAI

def translate_ufo_text(english_text: str) -> str:
    """
    Modul pro specializovaný překlad s využitím OpenAI API a odborného glosáře.
    Využívá model gpt-4o-mini pro úsporu nákladů.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"[Simulovaný překlad - chybí OPENAI_API_KEY]: {english_text[:100]}..."
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = (
        "Jsi odborný vojenský a aviatický překladatel pro analýzu UFO/UAP případů. "
        "Přelož následující anglický text do češtiny. Udělej stručné, ale výstižné shrnutí. "
        "Zachovej přesnou odbornou terminologii (např. Range Fouler, Thermal Crossover, Motion Parallax, Azimuth). "
        "Výsledek vrať čistě v češtině."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Změněno z gpt-4o na mini pro úsporu nákladů
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": english_text[:4000]} # Omezení na 4000 znaků, aby nedošlo k přetečení tokenů
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ Chyba AI překladu: {e}")
        return "Překlad není dočasně k dispozici z důvodu chyby API."
