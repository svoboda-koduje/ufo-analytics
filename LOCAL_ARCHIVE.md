> Aktualizace: české překlady, rozbory a filtry jsou nyní doplněné. Aktuální postup a omezení viz [RESEARCH.md](RESEARCH.md). Níže je popis původní místní OCR etapy.

# Místní badatelna UFO / UAP

Aktualizace 20. 9. 2026. Badatelna nyní obsahuje katalog skutečných souborů, vyhledávání v úplném původním textu PDF i zpracovaném OCR a detail s náhledy.

## Nejjednodušší použití

1. V adresáři projektu otevřete dvojklikem `Spustit-badatelnu.cmd`. Ponechte jeho okno otevřené. Pokud badatelna již běží, otevřete přímo http://127.0.0.1:8765/ a nespouštějte druhou kopii.
2. Do vyhledávání napište název souboru nebo slova z dokumentu a stiskněte Vyhledat. Například `ALFMED` najde i zpracovaný sken z Apollo 17.
3. Vyberte soubor nebo shodu v textu. U dlouhých dokumentů použijte tlačítka Předchozí / Další; přehled má 20 stránek dokumentu na jednu obrazovku přehledu.
4. Tlačítko **Spustit místní analýzu** vytvoří náhledy, doplní OCR chybějícího textu a změří technické vlastnosti obrazu. Probíhá jedna úloha současně. U dlouhých PDF může příprava trvat několik minut.
5. Zaškrtávací pole **Provést OCR i přes existující text** použijte, pokud je původní textová vrstva poškozená. Původní text zůstává zachován samostatně.

Výsledky jsou uložené v `backend/local_state/archive.sqlite3`, náhledy v `backend/local_state/previews`. Po opětovném spuštění zůstávají k dispozici. Zálohujte celou složku `local_state` při zastaveném zpracování. Originály v `backend/incoming_data` se nemění.

## Co je skutečně zpracováno

- Inventura: 447 médií, 267 PDF, 150 videí a 30 obrázků. Pomocné soubory macOS se ignorují.
- Všech 11 264 stran PDF má uloženou původní textovou vrstvu. Prázdná vrstva skenu není přepisem obsahu; ten doplňuje až OCR.
- Ověřená analýza 36 souborů: všech 30 obrázků, 3 PDF a 3 videa; celkem 52 stránek, obrázků a snímků, bez chyb zpracování v této dávce.
- OCR používá místní Tesseract s anglickým modelem. Jeho skóre je technický údaj, ne záruka správnosti nebo pravdivosti textu. Přepis kontrolujte proti originálu.
- Video má nejvýše 12 snímků rozložených přes jeho délku podle nastavení vzorkování. Krátké video může mít jediný snímek. Děje mezi snímky mohou být vynechány.
- Jas, kontrast a Laplaceova variance se počítají z náhledu. Nejde o důkaz neobvyklého původu objektu, měření jeho rychlosti ani analýzu trajektorie.

Hledání vrací nejvýše 200 shod v textu. U obecného dotazu jej zpřesněte. Číslo „analýza … jednotek“ v katalogu není počet přeložených stran; stav OCR je vidět v detailu.

## Provoz a omezení

Badatelna běží pouze na tomto počítači. Nevystavujte ji jako veřejný server. Neodesílá archiv do cloudových AI služeb a neprovádí placená API volání. Český překlad, významová AI analýza a propojení s veřejným webem na Renderu zatím nejsou implementovány v této nové cestě.

Dokončené kroky se ukládají průběžně; stejná analýza znovu použije hotové výsledky a zopakuje chyby OCR. Po přerušení aplikace otevřete stejný soubor a analýzu spusťte znovu. Přehled běžící úlohy je pouze v paměti, výsledky jsou v databázi. Skenování a přímou extrakci nespouštějte během analýzy; analytické procesy navzájem chrání souborový zámek.

## Technické příkazy z adresáře projektu

```powershell
python -m pip install -r backend/requirements-local.txt
python backend/local_archive.py scan
python backend/local_analysis.py --reindex
python backend/local_workbench.py --open
python -m unittest discover -s backend/tests -v
```

Pro OCR je nutný samostatný Tesseract a jazykový model `eng`. Na tomto počítači je již ověřen `C:\Program Files\Tesseract-OCR\tesseract.exe`; jinou cestu lze nastavit přes `TESSERACT_CMD`. Soubor requirements instaluje Python závislosti, nikoli Tesseract.

Nové soubory v archivu vyžadují nový `scan`; ten aktualizuje inventuru, nikoli automaticky OCR celého archivu. Vybraný soubor následně zpracujte tlačítkem v badatelně. `--reindex` obnovuje hledání z již uloženého textu, nevytváří nové přepisy.

Starší `tasks.py`, `vision_engine.py` a importéry nejsou součástí této nové cesty. Obsahují nedokončené nebo simulované části a nemají se používat pro vědecké závěry.
