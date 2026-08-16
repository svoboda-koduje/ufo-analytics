// @ts-nocheck
'use client';
import React, { useEffect, useState } from 'react';
import MapWrapper from './MapWrapper';

export default function UFOAnalyticsDashboard() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState(null);
  const [lang, setLang] = useState('cs'); // 'cs' nebo 'en'
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [sortOrder, setSortOrder] = useState('newest'); // 'newest' nebo 'oldest'

  useEffect(() => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    fetch(`${API_URL}/api/cases/`)
      .then((res) => res.json())
      .then((data) => {
        setCases(data);
        if (data.length > 0) setSelectedCase(data[0]);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Chyba při komunikaci s backendem:", err);
        setLoading(false);
      });
  }, []);

  // Filtrování a řazení případů
  const filteredCases = cases.filter((c) => {
    const matchesSearch = 
      c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.location.toLowerCase().includes(searchTerm.toLowerCase()) ||
      c.translation_snippet.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;

    return matchesSearch && matchesStatus;
  }).sort((a, b) => {
    const dateA = new Date(a.date);
    const dateB = new Date(b.date);
    if (sortOrder === 'newest') {
      return dateB - dateA; // Od nejnovějších
    } else {
      return dateA - dateB; // Od nejstarších
    }
  });

  // Statistické souhrny pro badatele
  const totalCount = cases.length;
  const unresolvedCount = cases.filter(c => c.status === 'Unresolved').length;
  const resolvedCount = totalCount - unresolvedCount;
  const unresolvedPercentage = totalCount > 0 ? Math.round((unresolvedCount / totalCount) * 100) : 0;

  // Generování automatického badatelského souhrnu
  const generateSummaryReport = () => {
    if (totalCount === 0) return lang === 'cs' ? "Zatím nejsou k dispozici žádná data k sumarizaci." : "No data available for summary yet.";
    
    if (lang === 'cs') {
      return `Analytický souhrn AARO / war.gov/UFO: Celkově bylo analyzováno ${totalCount} záznamů (spisů, obrazových a videozáznamů). Z toho ${unresolvedCount} případů (${unresolvedPercentage} %) zůstává klasifikováno jako nevysvětlené anomálie vykazující netradiční letové charakteristiky či vysokou akceleraci bez viditelných nosných ploch. Zbývající část představují konvenční jevy nebo probíhá jejich ověřování.`;
    } else {
      return `AARO / war.gov/UFO Analytical Summary: A total of ${totalCount} records (reports, imagery, and video files) have been analyzed. Out of these, ${unresolvedCount} cases (${unresolvedPercentage}%) remain classified as unresolved anomalies exhibiting non-standard flight characteristics or high acceleration without visible aerodynamic surfaces. The remaining cases represent conventional phenomena or are under active verification.`;
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      {/* Hlavička s přepínačem jazyků */}
      <header className="mb-8 border-b border-slate-700 pb-4 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">UFO Analytics Dashboard</h1>
          <p className="text-slate-400">
            {lang === 'cs' 
              ? 'Automatizovaná analýza materiálů z war.gov/UFO a AARO' 
              : 'Automated analysis of materials from war.gov/UFO and AARO'}
          </p>
        </div>
        <div>
          <button 
            onClick={() => setLang(lang === 'cs' ? 'en' : 'cs')}
            className="bg-slate-800 border border-slate-600 px-3 py-1.5 rounded text-sm hover:bg-slate-700 transition"
          >
            🌐 {lang === 'cs' ? 'Switch to English' : 'Přepnout do češtiny'}
          </button>
        </div>
      </header>

      {/* Rychlé statistické widgety pro badatele */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <p className="text-slate-400 text-xs uppercase tracking-wider">
            {lang === 'cs' ? 'Celkem evidováno případů' : 'Total Logged Cases'}
          </p>
          <p className="text-2xl font-bold text-blue-400 mt-1">{totalCount}</p>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <p className="text-slate-400 text-xs uppercase tracking-wider">
            {lang === 'cs' ? 'Neznámé / Nevysvětlené jevy' : 'Unresolved Anomalies'}
          </p>
          <p className="text-2xl font-bold text-amber-400 mt-1">{unresolvedCount} ({unresolvedPercentage}%)</p>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700 shadow">
          <p className="text-slate-400 text-xs uppercase tracking-wider">
            {lang === 'cs' ? 'Vysvětleno / Konvenční jevy' : 'Resolved / Conventional'}
          </p>
          <p className="text-2xl font-bold text-emerald-400 mt-1">{resolvedCount} ({100 - unresolvedPercentage}%)</p>
        </div>
      </div>

      {/* Modul souhrnné zprávy (Executive Summary) */}
      <section className="mb-8 bg-slate-800 p-6 rounded-lg shadow-lg border border-blue-500/20">
        <h2 className="text-xl font-semibold mb-2 flex items-center gap-2">
          <span>📊</span> {lang === 'cs' ? 'Souhrnná badatelská zpráva' : 'Executive Research Summary'}
        </h2>
        <p className="text-slate-300 text-sm leading-relaxed bg-slate-700/50 p-4 rounded border border-slate-600">
          {generateSummaryReport()}
        </p>
      </section>

      {/* Hlavní mřížka: Mapa a Detail */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <section className="bg-slate-800 p-6 rounded-lg shadow-lg flex flex-col">
          <h2 className="text-xl font-semibold mb-4">
            {lang === 'cs' ? 'Interaktivní GIS mapa' : 'Interactive GIS Map'}
          </h2>
          <div className="h-80 bg-slate-700 rounded overflow-hidden border border-slate-600 flex-grow">
            <MapWrapper cases={filteredCases} />
          </div>
        </section>

        <section className="bg-slate-800 p-6 rounded-lg shadow-lg">
          <h2 className="text-xl font-semibold mb-4">
            {lang === 'cs' ? 'Detail případu: Paralelní analýza dokumentu' : 'Case Detail: Parallel Document Analysis'}
          </h2>
          {selectedCase ? (
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-bold text-amber-400">{selectedCase.title}</span>
                <span className="bg-red-900 text-red-200 px-2 py-0.5 rounded text-xs font-mono">
                  {selectedCase.status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mb-4">
                📅 {selectedCase.date} | 📍 {selectedCase.location} | GPS: [{selectedCase.latitude}, {selectedCase.longitude}]
              </p>
              
              <div className="grid grid-cols-1 gap-4 text-xs">
                <div className="bg-slate-700 p-3 rounded">
                  <h3 className="text-slate-400 uppercase tracking-widest mb-1 font-bold">
                    {lang === 'cs' ? 'Originál (Angličtina)' : 'Original (English)'}
                  </h3>
                  <p className="leading-relaxed whitespace-pre-wrap">{selectedCase.original_text || selectedCase.translation_snippet}</p>
                </div>
                <div className="bg-slate-700 p-3 rounded border border-blue-500/30">
                  <h3 className="text-blue-400 uppercase tracking-widest mb-1 font-bold">
                    {lang === 'cs' ? 'Český překlad (LLM AI)' : 'Czech Translation (LLM AI)'}
                  </h3>
                  <p className="leading-relaxed">{selectedCase.translation_snippet}</p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-slate-400 text-sm">Načítám detail případu...</p>
          )}
        </section>
      </div>

      {/* Katalog a ovládací prvky pro vyhledávání, filtry a řazení */}
      <section className="mt-8 bg-slate-800 p-6 rounded-lg shadow-lg">
        <div className="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
          <h2 className="text-xl font-semibold">
            {lang === 'cs' ? 'Katalog evidovaných případů z war.gov/UFO' : 'Catalog of Logged Cases from war.gov/UFO'}
          </h2>
          
          <div className="flex flex-wrap gap-3 w-full md:w-auto items-center">
            {/* Výběr řazení podle data */}
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              className="bg-slate-700 border border-slate-600 px-3 py-1.5 rounded text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="newest">{lang === 'cs' ? '📅 Nejnovější nejdříve' : '📅 Newest First'}</option>
              <option value="oldest">{lang === 'cs' ? '📅 Nejstarší nejdříve' : '📅 Oldest First'}</option>
            </select>

            {/* Filtr podle statusu */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-700 border border-slate-600 px-3 py-1.5 rounded text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="ALL">{lang === 'cs' ? 'Všechny statusy' : 'All Statuses'}</option>
              <option value="Unresolved">Unresolved</option>
              <option value="Resolved">Resolved</option>
            </select>

            {/* Vyhledávací pole */}
            <input 
              type="text"
              placeholder={lang === 'cs' ? 'Vyhledat v případech...' : 'Search cases...'}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-700 border border-slate-600 px-3 py-1.5 rounded text-sm text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 w-full md:w-64"
            />
          </div>
        </div>

        {loading ? (
          <p className="text-slate-400">Načítám data z databáze...</p>
        ) : filteredCases.length === 0 ? (
          <p className="text-slate-400 py-4 text-center">Žádné případy neodpovídají zadaným kritériím.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-600 text-slate-400">
                  <th className="pb-2">ID</th>
                  <th className="pb-2">{lang === 'cs' ? 'Název případu' : 'Case Title'}</th>
                  <th className="pb-2">{lang === 'cs' ? 'Datum pozorování' : 'Observation Date'}</th>
                  <th className="pb-2">Status</th>
                  <th className="pb-2">{lang === 'cs' ? 'Český překlad (AI)' : 'Czech Translation (AI)'}</th>
                  <th className="pb-2 text-right">Akce</th>
                </tr>
              </thead>
              <tbody>
                {filteredCases.map((c: any) => (
                  <tr 
                    key={c.id} 
                    className="border-b border-slate-700 hover:bg-slate-700/50 transition cursor-pointer"
                    onClick={() => setSelectedCase(c)}
                  >
                    <td className="py-3 font-mono text-blue-400">{c.id}</td>
                    <td className="py-3 font-medium">{c.title}</td>
                    <td className="py-3 text-slate-300">{c.date}</td>
                    <td className="py-3">
                      <span className="bg-amber-900/60 text-amber-200 px-2 py-0.5 rounded text-xs font-mono">
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 text-slate-300 truncate max-w-sm">{c.translation_snippet}</td>
                    <td className="py-3 text-right">
                      <button 
                        onClick={(e) => { e.stopPropagation(); setSelectedCase(c); }}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded text-xs transition"
                      >
                        {lang === 'cs' ? 'Prohlédnout' : 'View'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
