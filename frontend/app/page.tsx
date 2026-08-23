'use client';

import React, { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import type { UfoCase } from './MapComponent';
import fileMapping from './file_to_asset_mapping.json';

const DynamicMap = dynamic(() => import('./MapComponent'), { 
  ssr: false, 
  loading: () => (
    <div className="flex h-full items-center justify-center text-slate-500 font-mono text-xs">
      Načítám GIS modul mapy...
    </div>
  )
});

interface Stats {
  total_cases: number;
  resolved_cases: number;
  unresolved_cases: number;
  unresolved_percentage: number;
}

// Speciální slovník pro nestandardně pojmenované stažené soubory
const SPECIAL_FILENAME_MAP: Record<string, string> = {
  "059UAP00011.PDF": "STATE DEPARTMENT UAP CABLE 003, TBILISI, GEORGIA, OCTOBER 30, 2001",
  "059UAP00012.PDF": "STATE DEPARTMENT UAP CABLE 004, ASHGABAT, TURKMENISTAN, NOVEMBER 5, 2004",
  "059UAP00013.PDF": "STATE DEPARTMENT UAP CABLE 005, MEXICO, SEPTEMBER 16, 2003",
  "DOS-UAP-D1-CABLE-1-PAPUA-NEW-GUINEA-JANUARY-1985.PDF": "STATE DEPARTMENT UAP CABLE 001, PAPUA NEW GUINEA, JANUARY 28, 1985",
  "DOS-UAP-D2-CABLE-2-KAZAKHSTAN-JANUARY-1994.PDF": "STATE DEPARTMENT UAP CABLE 002, KAZAKHSTAN, JANUARY 31, 1994",
  "2024-04-30-COMPOSITE-SKETCH.PDF": "FBI SEPTEMBER 2023 SIGHTING - COMPOSITE SKETCH",
  "SERIAL-3_REDACTED.PDF": "FBI SEPTEMBER 2023 SIGHTING - SERIAL 003",
  "SERIAL-4-REDACTED_REDACTED.PDF": "FBI SEPTEMBER 2023 SIGHTING - SERIAL 004",
  "SERIAL 5 REDACTED_REDACTED.PDF": "FBI SEPTEMBER 2023 SIGHTING - SERIAL 005",
  "USPER-STATEMENT-REDACTED.PDF": "USPER STATEMENT ABOUT UAP SIGHTING",
  "WESTERN_US_EVENT_SLIDES_5.08.2026.PDF": "WESTERN US EVENT",
  "255_T_763_R1B_TRANSCRIPTS.PDF": "NASA-UAP-D003, GEMINI 7 TRANSCRIPT, 1965"
};

// Pomocná funkce pro vyhledání oficiálního ASSET názvu a sestavení URL na war.gov
const getAssetInfo = (ufoCase: UfoCase | null) => {
  if (!ufoCase) {
    return {
      assetName: "",
      url: "https://www.war.gov/UFO/#records"
    };
  }

  // 1. Zjistíme čistý identifikátor z názvu nebo case_id
  const rawTitle = (ufoCase.title || "").replace(/Odtajněný spis:\s*/gi, "").trim();
  const rawCaseId = (ufoCase.case_id || "").replace(/^UAP-/i, "").trim();
  const rawFileNameUpper = (rawTitle || rawCaseId).toUpperCase();

  // 2. Kontrola ve speciálním slovníku
  if (SPECIAL_FILENAME_MAP[rawFileNameUpper]) {
    const asset = SPECIAL_FILENAME_MAP[rawFileNameUpper];
    return {
      assetName: asset,
      url: `https://www.war.gov/UFO/?search=${encodeURIComponent(asset)}#records`
    };
  }

  // 3. Pokud ufoCase již má platný asset_file_name (který nekončí příponou souboru)
  if (
    ufoCase.asset_file_name &&
    ufoCase.asset_file_name.trim() !== "" &&
    !/\.(pdf|mp4|jpg|png)$/i.test(ufoCase.asset_file_name.trim())
  ) {
    const asset = ufoCase.asset_file_name.trim();
    return {
      assetName: asset,
      url: `https://www.war.gov/UFO/?search=${encodeURIComponent(asset)}#records`
    };
  }

  // 4. Prohledání souboru file_to_asset_mapping.json
  const cleanNameNoExt = rawFileNameUpper.replace(/\.(PDF|MP4|JPG|PNG)$/i, "").trim();
  
  // Extrahujeme hlavní prefix (např. DOW-UAP-D098, FBI-UAP-D025, CIA-UAP-002, 18_100754)
  const prefixMatch = cleanNameNoExt.match(/^([A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+|[A-Z0-9]+_[A-Z0-9]+)/i);
  const prefix = prefixMatch ? prefixMatch[0].toUpperCase() : cleanNameNoExt;

  const foundItem = (fileMapping as any[]).find((item: any) => {
    if (!item) return false;
    
    // Shoda podle indexu (pokud ID odpovídá pořadí)
    if (ufoCase.id !== undefined && item.index === Number(ufoCase.id)) return true;

    // Shoda podle oficiálního ASSET názvu nebo row_title
    const itemAsset = (item.asset_file_name || item.row_title || "").toUpperCase();
    if (itemAsset === cleanNameNoExt) return true;
    if (prefix && itemAsset.startsWith(prefix)) return true;

    return false;
  });

  if (foundItem) {
    const asset = foundItem.asset_file_name || foundItem.row_title;
    if (foundItem.war_gov_search_url) {
      const url = foundItem.war_gov_search_url.includes("#records") 
        ? foundItem.war_gov_search_url 
        : `${foundItem.war_gov_search_url}#records`;
      return { assetName: asset, url };
    }
    return {
      assetName: asset,
      url: `https://www.war.gov/UFO/?search=${encodeURIComponent(asset)}#records`
    };
  }

  // 5. Fallback: Vyčistíme podtržítka a pošleme očištěný název
  const fallbackQuery = cleanNameNoExt.replace(/_/g, " ");
  return {
    assetName: fallbackQuery,
    url: `https://www.war.gov/UFO/?search=${encodeURIComponent(fallbackQuery)}#records`
  };
};

export default function UFOAnalyticsDashboard() {
  const [cases, setCases] = useState<UfoCase[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [lang, setLang] = useState<'cs' | 'en'>('cs');
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<UfoCase | null>(null);

  const loadEngineData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('https://ufo-analytics-backend.onrender.com/api/cases', {
        headers: { 'Accept': 'application/json' }
      });

      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setCases(data);
          setSelectedCase(data[0]);
          
          const total = data.length;
          const resolved = data.filter((c: UfoCase) => c.status?.toLowerCase() === 'resolved').length;
          const unresolved = total - resolved;

          setStats({
            total_cases: total,
            resolved_cases: resolved,
            unresolved_cases: unresolved,
            unresolved_percentage: total > 0 ? Number(((unresolved / total) * 100).toFixed(1)) : 0
          });
        }
      }
    } catch (err) {
      console.error("Chyba spojení s backendem:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEngineData();
  }, [loadEngineData]);

  useEffect(() => {
    if (selectedCase && selectedCase.id) {
      const rowElement = document.getElementById(`case-row-${selectedCase.id}`);
      if (rowElement) {
        rowElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  }, [selectedCase]);

  const filteredCases = cases.filter(c => {
    const q = searchFilter.toLowerCase();
    const assetInfo = getAssetInfo(c);
    return (
      (c.id !== undefined && String(c.id).toLowerCase().includes(q)) ||
      (c.case_id && c.case_id.toLowerCase().includes(q)) ||
      (c.title && c.title.toLowerCase().includes(q)) ||
      (c.location && c.location.toLowerCase().includes(q)) ||
      (assetInfo.assetName && assetInfo.assetName.toLowerCase().includes(q))
    );
  });

  const currentAssetInfo = getAssetInfo(selectedCase);

  return (
    <div className="min-h-screen bg-[#070d1e] text-slate-100 p-4 md:p-8 font-sans">
      <header className="mb-6 border-b border-slate-800 pb-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white flex items-center gap-2">
            <span>🛸</span> UFO / UAP Analytics Engine
          </h1>
          <p className="text-slate-400 text-xs md:text-sm mt-1">
            {lang === 'cs' 
              ? "Pokročilá badatelská analýza odtajněných spisů z portálu war.gov/UFO." 
              : "Advanced research analysis of declassified documents from war.gov/UFO."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setLang(lang === 'cs' ? 'en' : 'cs')} 
            className="bg-slate-800 hover:bg-slate-700 border border-slate-700 px-3.5 py-1.5 rounded text-xs font-mono transition shadow"
          >
            🌐 {lang === 'cs' ? 'English Version' : 'Česká verze'}
          </button>
        </div>
      </header>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-[#0c1633] border border-slate-800 p-4 rounded-lg shadow">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              {lang === 'cs' ? 'Celkem zkoumaných spisů' : 'Total Examined Files'}
            </div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-cyan-400 mt-1">
              {stats.total_cases}
            </div>
          </div>
          <div className="bg-[#0c1633] border border-slate-800 p-4 rounded-lg shadow">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              {lang === 'cs' ? 'Nevysvětlené úkazy' : 'Unresolved Cases'}
            </div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-rose-400 mt-1">
              {stats.unresolved_cases} <span className="text-xs font-normal text-rose-300">({stats.unresolved_percentage}%)</span>
            </div>
          </div>
          <div className="bg-[#0c1633] border border-slate-800 p-4 rounded-lg shadow">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              {lang === 'cs' ? 'Vyřešené / Identifikované' : 'Resolved Cases'}
            </div>
            <div className="text-2xl md:text-3xl font-bold font-mono text-emerald-400 mt-1">
              {stats.resolved_cases}
            </div>
          </div>
          <div className="bg-[#0c1633] border border-slate-800 p-4 rounded-lg shadow">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">
              {lang === 'cs' ? 'Stav systému' : 'System Status'}
            </div>
            <div className="text-xs font-mono text-emerald-400 mt-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Live: Supabase ({cases.length} Spisů)
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* GIS Mapa */}
        <section className="lg:col-span-5 bg-[#0c1633] border border-slate-800 p-4 rounded-lg flex flex-col h-[520px] shadow">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-sm font-mono text-cyan-300 font-bold flex items-center gap-2">
              🗺️ {lang === 'cs' ? 'Interaktivní GIS mapa' : 'Interactive GIS Map'}
            </h2>
            <span className="text-[11px] font-mono text-slate-400">
              {filteredCases.length} {lang === 'cs' ? 'bodů' : 'points'}
            </span>
          </div>
          <div className="flex-1 rounded overflow-hidden border border-slate-800 bg-slate-950 relative">
            <DynamicMap 
              cases={filteredCases} 
              selectedCase={selectedCase} 
              onMarkerClick={(c: UfoCase) => setSelectedCase(c)} 
            />
          </div>
        </section>

        {/* Katalog spisů */}
        <section className="lg:col-span-7 bg-[#0c1633] border border-slate-800 p-4 rounded-lg flex flex-col h-[520px] shadow">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-3">
            <h2 className="text-sm font-mono text-cyan-300 font-bold flex items-center gap-2">
              📋 {lang === 'cs' ? 'Katalog odtajněných spisů' : 'Declassified Files Catalog'}
            </h2>
            <div className="relative w-full sm:w-80">
              <input 
                type="text" 
                placeholder={lang === 'cs' ? "Filtrovat ID, název, ASSET, lokaci..." : "Filter ID, title, ASSET, location..."}
                value={searchFilter} 
                onChange={(e) => setSearchFilter(e.target.value)} 
                className="bg-slate-950 border border-slate-800 rounded px-3 py-1.5 pr-8 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-500 w-full"
              />
              {searchFilter && (
                <button
                  onClick={() => setSearchFilter('')}
                  className="absolute right-2.5 top-1.5 text-xs text-slate-400 hover:text-white"
                  title="Zrušit filtr"
                >
                  ✕
                </button>
              )}
            </div>
          </div>

          <div className="overflow-y-auto flex-1 bg-slate-950/60 rounded border border-slate-800/80 custom-scrollbar">
            <table className="w-full text-left text-xs font-mono">
              <thead className="sticky top-0 bg-slate-950 text-slate-400 border-b border-slate-800 z-10 uppercase text-[11px]">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">{lang === 'cs' ? 'Název spisu / ASSET' : 'Title / ASSET'}</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Akce</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="text-center py-12 text-slate-400">
                      Načítám data z databáze...
                    </td>
                  </tr>
                ) : filteredCases.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-12 text-slate-400">
                      Žádné záznamy neodpovídají filtru.
                    </td>
                  </tr>
                ) : (
                  filteredCases.map((c) => {
                    const rowAsset = getAssetInfo(c);
                    return (
                      <tr 
                        key={String(c.id)} 
                        id={`case-row-${c.id}`}
                        onClick={() => setSelectedCase(c)} 
                        className={`border-b border-slate-800/50 cursor-pointer transition ${
                          selectedCase?.id === c.id 
                            ? 'bg-cyan-950/40 border-l-4 border-l-cyan-400 text-white' 
                            : 'hover:bg-slate-900/60 text-slate-300'
                        }`}
                      >
                        <td className="py-2.5 px-3 text-cyan-400 font-bold whitespace-nowrap">{c.id}</td>
                        <td className="py-2.5 px-3 max-w-xs truncate">
                          <span className="font-semibold text-slate-200">{c.title}</span>
                          {rowAsset.assetName && (
                            <span className="block text-[10px] text-cyan-400/80 truncate mt-0.5">
                              {rowAsset.assetName}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 whitespace-nowrap">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950/80 text-rose-300 border border-rose-800/40">
                            {c.status || "Unresolved"}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          <button 
                            onClick={(e) => { e.stopPropagation(); setSelectedCase(c); }} 
                            className="bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded text-[11px] font-medium transition shadow"
                          >
                            Detail
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* Spodní panel s paralelní analýzou */}
      {selectedCase && (
        <section className="mt-6 bg-[#0c1633] border border-slate-800 p-5 rounded-lg shadow">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 pb-4 border-b border-slate-800">
            <div>
              <h2 className="text-base md:text-lg font-mono font-bold text-white flex items-center gap-2">
                🔬 {lang === 'cs' ? 'Detail případu: Paralelní analýza dokumentu' : 'Case Detail: Parallel Document Analysis'}
                <span className="text-xs bg-slate-950 text-cyan-400 px-2 py-0.5 rounded border border-slate-800">
                  ID: {selectedCase.id}
                </span>
              </h2>
              {currentAssetInfo.assetName && (
                <div className="text-xs font-mono text-cyan-300 mt-1">
                  <span className="text-slate-400">Oficiální ASSET FILE NAME:</span> {currentAssetInfo.assetName}
                </div>
              )}
            </div>

            <a 
              href={currentAssetInfo.url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="inline-flex items-center gap-2 text-xs font-mono font-bold bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded transition shadow-md shadow-blue-600/30 shrink-0 text-center"
            >
              🌐 {lang === 'cs' 
                ? 'Detail případu: Paralelní analýza na war.gov (Po načtení stránky scrollujte dolů až k vyhledávacímu poli)' 
                : 'Case Detail: Parallel analysis on war.gov (After loading, scroll down to the search field)'}
            </a>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div className="bg-slate-950/80 border border-slate-800 p-4 rounded text-xs font-mono">
              <h3 className="text-slate-400 font-bold uppercase tracking-wider mb-2">
                {lang === 'cs' ? 'Originál (Angličtina / OCR Senzorová data)' : 'Original (English / OCR Sensor Data)'}
              </h3>
              <p className="text-slate-300 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto custom-scrollbar">
                {selectedCase.original_text || "Originální text záznamu nebyl nalezen."}
              </p>
            </div>

            <div className="bg-slate-950/80 border border-cyan-500/20 p-4 rounded text-xs font-mono">
              <h3 className="text-cyan-400 font-bold uppercase tracking-wider mb-2">
                {lang === 'cs' ? 'Český překlad a geolokace (LLM AI)' : 'Czech Translation & Geolocation (LLM AI)'}
              </h3>
              <p className="text-slate-200 leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto custom-scrollbar">
                {selectedCase.translation_snippet || (selectedCase as any).czech_translation || "Automatická analýza a překlad spisu."}
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
