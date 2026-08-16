import os
from openai import OpenAI

def translate_ufo_text(english_text: str) -> str:
    """
    Modul pro specializovaný překlad s využitím OpenAI API a odborného glosáře.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return f"[Simulovaný překlad - chybí OPENAI_API_KEY]: {english_text}"
    
    client = OpenAI(api_key=api_key)
    
    system_prompt = (
        "Jsi odborný vojenský a aviatický překladatel pro analýzu UFO/UAP případů. "
        "Přelož následující anglický text do češtiny. "
        "Zachovej přesnou odbornou terminologii (např. Range Fouler, Thermal Crossover, Motion Parallax, Azimuth, Tearline Report). "
        "Výsledek vrať čistě v češtině."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": english_text}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Chyba při komunikaci s OpenAI API: {str(e)}"
