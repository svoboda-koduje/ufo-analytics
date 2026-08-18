'use client';

import React, { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';

const DynamicMap = dynamic(() => import('./MapComponent'), { 
  ssr: false, 
  loading: () => <div className="flex h-full items-center justify-center text-slate-500">Načítám GIS modul...</div> 
});

interface UfoCase {
  id: string;
  title: string;
  date: string;
  location: string;
  status: string;
  translation_snippet: string;
  original_text: string;
  latitude: number;
  longitude: number;
}

interface Stats {
  total_cases: number;
  resolved_cases: number;
  unresolved_cases: number;
  unresolved_percentage: number;
}

// POMOCNÁ FUNKCE: Chytrý generátor přesných vyhledávacích dotazů pro war.gov
const getWarGovUrl = (ufoCase: UfoCase) => {
  if (!ufoCase) return "https://www.war.gov/UFO/";

  // 1. Zkusíme primárně použít přesné ID případu (to je nejspolehlivější)
  let searchTerm = ufoCase.id;

  // 2. Pokud ID z nějakého důvodu chybí, pokusíme se ho vyseparovat z názvu (původní záchranná logika)
  if (!searchTerm || searchTerm === "N/A" || searchTerm === "ID chybí") {
    if (!ufoCase.title) return "https://www.war.gov/UFO/";
    
    let rawName = ufoCase.title.replace(/Odtajněný spis: |Senzorový záznam HUD\/FLIR: |Obrazový důkaz: |Záznam: /g, "").trim();
    rawName = rawName.replace(/\.(pdf|mp4|jpg|png|avi|mov)$/i, "");
    searchTerm = rawName;

    const videoMatch = rawName.match(/(DOD_\d+)/i);
    if (videoMatch) {
      searchTerm = videoMatch[1];
    } else if (rawName.match(/^([A-Z]+-UAP-[A-Z0-9]+)/i)) {
      const agencyMatch = rawName.match(/^([A-Z]+-UAP-[A-Z0-9]+)/i);
      if (agencyMatch) {
          searchTerm = agencyMatch[1].toUpperCase();
          searchTerm = searchTerm.replace(/PRO(\d+)/, 'PR0$1');
          searchTerm = searchTerm.replace(/-([A-Z]+)(\d+)$/, (match, letters, numbers) => `-${letters}` + numbers.padStart(3, '0'));
      }
    } else if (rawName.match(/^(\d+_\d+)_/)) {
      const numMatch = rawName.match(/^(\d+_\d+)/);
      if (numMatch) searchTerm = numMatch[1];
    } else if (rawName.includes('_')) {
       searchTerm = rawName.split('_')[0];
    }
  }

  // 3. Vrácení vygenerované URL s garantovaným a správným parametrem ?search=
  return `https://www.war.gov/UFO/?search=${encodeURIComponent(searchTerm)}`;
};
  // 3. Číselné archivy s podtržítky (18_100754_General..., 255_413270_...)
  else if (rawName.match(/^(\d+_\d+)_/)) {
    const numMatch = rawName.match(/^(\d+_\d+)/);
    if (numMatch) {
        searchTerm = numMatch[1];
    }
  }
  // 4. Ostatní dokumenty s podtržítkem (Serial-3_Redacted, EOP-UAP-D001_...)
  else if (rawName.includes('_')) {
     searchTerm = rawName.split('_')[0];
  }
  // 5. Zbytek (např. 059UAP00011)
  else {
     searchTerm = rawName;
  }

  // Vrácení vygenerované URL s parametrem vyhledávání
  return `https://www.war.gov/UFO/?search=${encodeURIComponent(searchTerm)}`;
};

export default function UFOAnalyticsDashboard() {
  const [cases, setCases] = useState<UfoCase[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [lang, setLang] = useState<'cs' | 'en'>('cs');
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<UfoCase | null>(null);

  useEffect(() => {
    async function loadEngineData() {
      try {
        const res = await fetch('https://ufo-analytics-backend.onrender.com/api/cases/');
        
        if (res.ok) {
          const data = await res.json();
          if (data && data.length > 0) {
            setCases(data);
            setSelectedCase(data[0]);
            
            const total = data.length;
            const resolved = data.filter((c: UfoCase) => c.status === 'Resolved').length;
            setStats({
              total_cases: total,
              resolved_cases: resolved,
              unresolved_cases: total - resolved,
              unresolved_percentage: total > 0 ? Number((((total - resolved) / total) * 100).toFixed(1)) : 0
            });
          }
        }
      } catch (err) {
        console.error("Nelze se spojit se serverem:", err);
      } finally {
        setLoading(false);
      }
    }
    
    loadEngineData();
  }, []);

  useEffect(() => {
    if (selectedCase && selectedCase.id) {
      const rowElement = document.getElementById(`case-row-${selectedCase.id}`);
      if (rowElement) {
        rowElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [selectedCase]);

  const filteredCases = cases.filter(c => 
    (c.id && c.id.toLowerCase().includes(searchFilter.toLowerCase())) ||
    (c.title && c.title.toLowerCase().includes(searchFilter.toLowerCase())) ||
    (c.location && c.location.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6 md:p-10 font-sans">
      <header className="mb-8 border-b border-slate-700 pb-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white">🛸 UFO / UAP Analytics Engine</h1>
          <p className="text-slate-400 text-sm mt-1">
            {lang === 'cs' ? "Pokročilá badatelská analýza odtajněných spisů z portálu war.gov/UFO." : "Advanced research analysis of declassified documents from war.gov/UFO."}
          </p>
        </div>
        <button 
          onClick={() => setLang(lang === 'cs' ? 'en' : 'cs')} 
          className="bg-slate-800 border border-slate-600 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-700 transition shadow"
        >
          🌐 {lang === 'cs' ? 'English Version' : 'Česká verze'}
        </button>
      </header>

      {stats && cases.length > 0 && (
        <div className="mb-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl shadow">
              <p className="text-xs text-slate-400 uppercase tracking-wider">{lang === 'cs' ? 'Celkem zkoumaných spisů' : 'Total Examined Files'}</p>
              <p className="text-3xl font-bold text-white mt-2">{stats.total_cases}</p>
            </div>
            <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl shadow">
              <p className="text-xs text-slate-400 uppercase tracking-wider">{lang === 'cs' ? 'Nevysvětlené úkazy (Unresolved)' : 'Unresolved Cases'}</p>
              <p className="text-3xl font-bold text-red-400 mt-2">{stats.unresolved_cases} ({stats.unresolved_percentage}%)</p>
            </div>
            <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl shadow">
              <p className="text-xs text-slate-400 uppercase tracking-wider">{lang === 'cs' ? 'Vyřešené / Identifikované' : 'Resolved Cases'}</p>
              <p className="text-3xl font-bold text-emerald-400 mt-2">{stats.resolved_cases}</p>
            </div>
            <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl shadow">
              <p className="text-xs text-slate-400 uppercase tracking-wider">{lang === 'cs' ? 'Stav systému' : 'System Status'}</p>
              <p className="text-sm font-semibold text-blue-400 mt-3 flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                Live: Supabase DB
              </p>
            </div>
          </div>

          <div className="bg-slate-800 border border-slate-700 p-5 rounded-xl shadow">
            <div className="flex justify-between items-end mb-3">
              <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-widest">{lang === 'cs' ? 'Analýza úspěšnosti identifikace' : 'Identification Success Rate'}</h3>
            </div>
            <div className="w-full bg-slate-900 rounded-full h-4 flex overflow-hidden border border-slate-700">
              <div 
                className="bg-red-500 h-4 transition-all duration-1000" 
                style={{ width: `${stats.unresolved_percentage}%` }}
                title={lang === 'cs' ? 'Nevysvětleno' : 'Unresolved'}
              ></div>
              <div 
                className="bg-emerald-500 h-4 transition-all duration-1000" 
                style={{ width: `${100 - stats.unresolved_percentage}%` }}
                title={lang === 'cs' ? 'Vyřešeno' : 'Resolved'}
              ></div>
            </div>
            <div className="flex justify-between mt-2 text-xs font-medium">
              <span className="text-red-400">{stats.unresolved_percentage}% {lang === 'cs' ? 'Nevysvětleno (UAP)' : 'Unresolved (UAP)'}</span>
              <span className="text-emerald-400">{100 - stats.unresolved_percentage}% {lang === 'cs' ? 'Identifikováno' : 'Resolved'}</span>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <section className="lg:col-span-1 bg-slate-800 border border-slate-700 p-6 rounded-xl flex flex-col h-[500px] shadow-lg">
          <h2 className="text-xl font-semibold mb-4 text-white">🗺️ {lang === 'cs' ? 'Interaktivní GIS mapa' : 'Interactive GIS Map'}</h2>
          <div className="flex-1 bg-slate-900 rounded-lg overflow-hidden border border-slate-700 relative">
            {cases.length > 0 ? (
              <DynamicMap cases={filteredCases} onMarkerClick={setSelectedCase} />
            ) : (
              <div className="flex h-full items-center justify-center text-slate-500">
                 {loading ? (lang === 'cs' ? 'Načítám data...' : 'Loading data...') : (lang === 'cs' ? 'Čekám na data z backendu...' : 'Waiting for backend data...')}
              </div>
            )}
          </div>
        </section>

        <section className="lg:col-span-2 bg-slate-800 border border-slate-700 p-6 rounded-xl flex flex-col h-[500px] shadow-lg">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
            <h2 className="text-xl font-semibold text-white">📋 {lang === 'cs' ? 'Katalog odtajněných spisů' : 'Declassified Files Catalog'}</h2>
            <input 
              type="text" 
              placeholder={lang === 'cs' ? "Filtrovat ID, název, lokaci..." : "Filter ID, title, location..."}
              value={searchFilter} 
              onChange={(e) => setSearchFilter(e.target.value)} 
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500 w-full sm:w-64"
            />
          </div>
          <div className="overflow-y-auto flex-1 bg-slate-900/50 rounded-lg border border-slate-700/60 custom-scrollbar">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-900 text-slate-400 border-b border-slate-700 z-10">
                <tr>
                  <th className="py-2.5 px-3">ID</th>
                  <th className="py-2.5 px-3">{lang === 'cs' ? 'Název' : 'Title'}</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Akce</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-slate-400">{lang === 'cs' ? 'Načítám data ze Supabase...' : 'Loading data from Supabase...'}</td>
                  </tr>
                ) : filteredCases.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-slate-400">{lang === 'cs' ? 'Žádné záznamy nenalezeny.' : 'No records found.'}</td>
                  </tr>
                ) : (
                  filteredCases.map((c) => (
                    <tr 
                      key={c.id} 
                      id={`case-row-${c.id}`}
                      onClick={() => setSelectedCase(c)} 
                      className={`border-b border-slate-700/50 cursor-pointer transition ${selectedCase?.id === c.id ? 'bg-blue-900/40 border-l-4 border-l-blue-500' : 'hover:bg-slate-700/40'}`}
                    >
                      <td className="py-2.5 px-3 font-mono text-blue-400 text-xs font-semibold">{c.id || "N/A"}</td>
                      <td className="py-2.5 px-3 text-slate-200 truncate max-w-xs">{c.title}</td>
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${c.status === 'Resolved' ? 'bg-emerald-950 text-emerald-300 border-emerald-800/50' : 'bg-red-950 text-red-300 border-red-800/50'}`}>
                          {c.status || "Unknown"}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        <button 
                          onClick={(e) => { e.stopPropagation(); setSelectedCase(c); }} 
                          className="bg-blue-600 hover:bg-blue-500 text-white px-2.5 py-1 rounded text-xs transition font-medium shadow"
                        >
                          {lang === 'cs' ? 'Prozkoumat' : 'Inspect'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500 mt-3 text-right">
            {lang === 'cs' ? `Zobrazeno ${filteredCases.length} položek` : `Showing ${filteredCases.length} items`}
          </p>
        </section>
      </div>

      {selectedCase && (
        <section className="mt-8 bg-slate-800 border border-slate-700 p-6 rounded-xl shadow-lg flex flex-col">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4 border-b border-slate-700 pb-3 shrink-0">
            <div>
              <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                🔬 {lang === 'cs' ? 'Detail případu: Paralelní analýza dokumentu' : 'Case Detail: Parallel Document Analysis'}
                <span className="text-xs font-mono bg-slate-900 text-blue-400 px-2.5 py-1 rounded border border-slate-700">
                  {selectedCase.id || "ID chybí"}
                </span>
              </h2>
              {/* ODKAZ S FUNKCÍ PRO PŘESNÉ VYHLEDÁVÁNÍ */}
              <a 
                href={getWarGovUrl(selectedCase)} 
                target="_blank" 
                rel="noopener noreferrer" 
                className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold bg-blue-900/40 hover:bg-blue-800/60 text-blue-300 px-3 py-1.5 rounded transition border border-blue-700/50 shadow"
              >
                🌐 {lang === 'cs' ? 'Vyhledat originál ve vládní databázi war.gov' : 'Search original in war.gov database'}
              </a>
            </div>
            <span className="text-xs text-slate-400 font-medium">📍 {selectedCase.location} | 📅 {selectedCase.date}</span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-700 p-4 rounded-lg flex flex-col h-72">
              <h3 className="text-xs text-slate-400 uppercase tracking-widest mb-3 font-bold shrink-0">{lang === 'cs' ? 'Originál (Angličtina / OCR Senzorová data)' : 'Original (English / OCR Sensor Data)'}</h3>
              <div className="overflow-y-auto pr-2 custom-scrollbar">
                <p className="text-sm text-slate-400 font-mono leading-relaxed break-words whitespace-pre-wrap">
                  {selectedCase.original_text || "Originální text nenalezen."}
                </p>
              </div>
            </div>
            
            <div className="bg-slate-900 border border-blue-500/30 p-4 rounded-lg flex flex-col h-72">
              <h3 className="text-xs text-blue-400 uppercase tracking-widest mb-3 font-bold shrink-0">{lang === 'cs' ? 'Český překlad a geolokace (LLM AI)' : 'Czech Translation & Geolocation (LLM AI)'}</h3>
              <div className="overflow-y-auto pr-2 custom-scrollbar">
                <p className="text-sm text-slate-200 leading-relaxed break-words whitespace-pre-wrap">
                  {selectedCase.translation_snippet || "Analýza zatím nebyla provedena."}
                </p>
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
