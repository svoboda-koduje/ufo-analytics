print("🔐 Generátor konfiguračního souboru pro UAP Databázi (vylepšený)")
print("Zkopíruj Transaction pooler URI adresu ze Supabase (s portem 6543).")
final_url = input("Vlož adresu a stiskni Enter: ").strip()

# Pokud na konci chybí ?sslmode=require, automaticky ho doplníme
if "?" not in final_url:
    final_url += "?sslmode=require"

# Bezpečný zápis do správně pojmenovaného souboru .env
with open(".env", "w", encoding="utf-8") as f:
    f.write(f"DATABASE_URL={final_url}")

print("✅ Tajný soubor .env byl úspěšně aktualizován a zabezpečen!")