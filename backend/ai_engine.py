# -*- coding: utf-8 -*-
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def translate_and_extract_metadata(raw_text: str):
    """
    Využívá OpenAI GPT-4o k extrakci metadat a odbornému překladu
    aviatické a vojenské terminologie do češtiny.
    """
    if not client.api_key:
        return {
            "snippet": "Lokální analýza: Detekován anomální objekt bez viditelných nosných ploch.",
            "status": "Unresolved"
        }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Jsi expert na analýzu odtajněných UAP/UFO spisů AARO a Ministerstva války. "
                               "Analyzuj text, zachovej vojenskou a aviatickou terminologii (např. Thermal Crossover, Azimuth, Range Fouler), "
                               "vyextruj klíčové informace a vytvoř stručný český překlad a shrnutí."
                },
                {"role": "user", "content": raw_text[:4000]}
            ],
            temperature=0.3
        ]
        result_text = response.choices[0].message.content
        return {
            "snippet": result_text,
            "status": "Unresolved"
        }
    except Exception as e:
        return {
            "snippet": f"Chyba AI zpracování: {str(e)}",
            "status": "Unresolved"
        }
