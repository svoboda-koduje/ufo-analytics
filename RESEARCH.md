# Česká badatelna: překlad, souvislosti a filtry

Aktualizace 20. 9. 2026. Aplikace běží místně na http://127.0.0.1:8765/.

## Jak ji použít

1. Obnovte stránku v prohlížeči. V poli **Český obsah** vyberte **Alespoň část připravena**.
2. Otevřete například `18_100754_ General 1946-7_Vol_2.pdf`. Připravený je rozbor celého spisu a české čtení všech 28 stran. Souhrn obsahuje odkazy na zdrojové stránky.
3. Níže čtěte český překlad vedle originálu. Původní text a OCR lze rozbalit pro kontrolu. Začerněné a nečitelné části zůstávají označené.
4. Horní filtry umožňují vybrat rok události od–do, zemi, čas ve zdroji od–do, typ média a dostupnost českého obsahu. Filtry lze kombinovat; všechny podmínky se musí týkat stejné evidované události. Rozsah času přes půlnoc je podporován.
5. Pro ověření zkuste rok **2016–2016** a čas **13:00–13:20**. Výsledek odkazuje na pozorování letounu P-8 s citací `18/1310Z`, tedy 13:10 UTC. Po zrušení filtrů lze samostatně zvolit zemi **Kazachstán**.
6. U nepřipraveného souboru tlačítko **Připravit české čtení a rozbor** provede první zpracování. Tato první příprava chvíli trvá a používá API; další čtení již uložených výsledků neprovádí AI volání.

Pokud aplikace neběží, spusťte `Spustit-badatelnu.cmd` v adresáři projektu. Pokud běží, stačí otevřít uvedenou adresu, nespouštějte druhou kopii.

## Co je nyní hotové

Pilotní dávka má **8 souborů, 47 stránek/obrázků/snímků a 8 celkových přehledů**. Každá zpracovaná část obsahuje český překlad nebo popis obrazu, shrnutí, pramenný kontext, pozorování a konkrétní omezení. Překlad je oddělený od interpretace.

| Soubor | Zpracované stránky / snímky |
|---|---:|
| FBI-Photo-A7.png | 1 |
| NASA-UAP-D6-Apollo-17-Technical-Crew-Debriefing-1973.pdf | 2 |
| 18_100754_ General 1946-7_Vol_2.pdf | 28 |
| DoW-UAP-D079_Narrative-1_Western-US-Event.pdf | 2 |
| 059UAP00011.pdf | 5 |
| DOD_111830080.mp4 | 5 |
| DOS-UAP-D2-Cable-2-Kazakhstan-January-1994.pdf | 3 |
| DOW-UAP-D55-Mission-Report-Syria-November-2016.pdf | 1 |

„Připraveno“ znamená uložený strojový výstup, nikoli odborně ověřený překlad. Nečitelné části nelze převést na úplný text. U některých jednotek je výslovně uveden částečný přepis. Původní data zůstávají zachována.

## Rozpočet a ochrana proti opakovaným platbám

Uživatel schválil pro ověřovací dávku nejvýše **20 USD**. Součet evidovaných nákladů je **1.688505 USD**. Jde o konzervativní výpočet ze spotřebovaných tokenů podle standardní ceny; sleva za cache se nezapočítává. Přesné vyúčtování určuje poskytovatel.

Před každým API požadavkem se transakčně rezervuje konzervativní maximum. Do výpočtu patří text, obraz, schéma a maximální výstup. Nové volání se odmítne, pokud by překročilo zbývající limit. Neúspěšný nebo nejednoznačný požadavek se automaticky neopakuje; rezervace zůstává započtená do prověření. Čtení, filtrování a hledání žádné API požadavky nespouští.

V této dávce skončily všechny evidované požadavky stavem `done`. Používá se model `gpt-5.4-2026-03-05`; prvotní test levnějšího modelu je započten v rozpočtu, jeho dva výstupy byly nahrazeny kvalitnějším zpracováním. Nastaven je standardní režim, bez placených nástrojů a bez automatických SDK opakování.

Implementace používá [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). Sazby vycházejí z [dokumentace GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4) a u úvodního testu z [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini), ověřeno 20. 9. 2026.

## Jak rozumět filtrům

- Datum vzniku či odtajnění dokumentu není automaticky datem popisované události. Samotná titulní stránka se nepočítá jako pozorování.
- Ke každému vyplněnému filtračnímu údaji se vyžaduje doslovná citace přítomná ve vstupním textu. Rok se kontroluje i číselně. Údaje bez této opory zůstávají neznámé. Tato kontrola neprokazuje pravdivost svědectví ani nenahrazuje odbornou interpretaci citace.
- Model může údaj nerozpoznat nebo jej nepřiřadit správně. Filtry jsou nad strojově vytěženými kandidátními údaji, nikoli nad odborně revidovaným katalogem všech událostí.
- Údaje rozdělené mezi různé stránky zatím nejsou automaticky spojované do jedné normalizované události. Proto může být pokrytí filtrů menší než skutečný obsah spisu. Další etapa musí přidat kontrolované slučování a revizní rozhraní.
- Časy se porovnávají tak, jak jsou uvedené ve zdroji. UTC se neporovnává jako převedený místní čas; pásmo je zobrazené u výsledku. Pro globální chronologii bude potřeba samostatná normalizace pásem.
- Název souboru, název agentury nebo sídlo autora se nepoužívají jako náhrada místa události. Země v nabídce se zobrazí až po vytěžení podloženého údaje.
- Vzorek snímků videa nedokládá průběh celého záznamu ani pohybovou trajektorii. Zobrazené závěry se týkají pouze vzorků, bez analýzy zvuku.

## Technické ověření

Prošlo **26 automatických testů**: zachování textu při dělení, OCR a obnova, zneplatnění překladu po novém OCR, citace a odstranění administrativních událostí, kombinace filtrů na stejné události, čas přes půlnoc, české hledání, limit nákladů před požadavkem, cache placeného výsledku, odmítnutí opakování nejednoznačného volání, nepublikování neúplné odpovědi a odkazy souhrnu na existující zdroje.

Kontrola JavaScriptové syntaxe prošla. V prohlížeči bylo ověřeno české čtení, výběr připravených souborů a kombinovaný filtr roku/času. Jednorázové místní načtení detailu 28stránkového spisu trvalo **46.2 ms** bez API volání; jde o měření HTTP odpovědi, ne záruku rychlosti vykreslení či budoucího veřejného webu.

## Co ještě zbývá pro požadovaný profesionální web

**Celý archiv zatím není předpřeložený.** Okamžité české čtení je dostupné pro uvedenou dávku. Pro libovolný soubor bez prvního čekání je nutné postupně předzpracovat zbývající archiv, vyhodnotit kvalitu a uložit výsledky před zveřejněním.

Další práce: normalizovaný katalog událostí napříč stránkami, odborná revize a opravy metadat, slučování duplicitních událostí, práce s nejistými daty a pásmy, trvalá fronta a dávkový provoz, synchronizace výsledků do serverové databáze a nasazení do veřejného webu. Web na Renderu touto etapou změněn nebyl.

## Technický přehled implementace

`backend/research.py` zajišťuje obnovitelné překlady po blocích, obrazový kontext, hierarchické přehledy dlouhých souborů a evidenci nákladů v SQLite. `research_units`, `research_documents`, `research_calls` a `research_search` ukládají výstupy, souhrny, účetní záznamy a české vyhledávání. Klíč zůstává pouze na serveru v prostředí / backend/.env.

Výstupy a spotřeba jsou v `backend/local_state/archive.sqlite3`, tedy mimo Git. Změna OCR zneplatní odvozený překlad a celkový přehled; původní účetní záznamy zůstávají. API i badatelna jsou pouze místní, ne veřejné produkční rozhraní.
