import data from './source_catalog.json';
export type SourceRecord = {
 source_id:string; asset_file_name:string; source_url:string; download_url:string; download_filename:string;
 release:string; release_date:string; agency:string; incident_date:string; incident_location:string;
 document_type:string; description_en:string; related_ids:string[]; local_filenames:string[]; catalog_years?:number[];
 translation?:{title_cs:string; description_cs:string; location_cs:string; country_cs:string|null; country_evidence:string|null; category:string; date_kind:string};
 analyses?:{sha256:string;units:number;url:string}[];
 events?:{year:number|null;time_local:string|null;timezone?:string|null;country_cs:string|null;description_cs:string}[];
};
export const records=data as unknown as SourceRecord[];
export function sourceFor(name:string, asset?:string){
 const clean=name.replace(/^Odtajněný spis:\s*/i,'').trim().toLowerCase();
 const exact=records.filter(r=>r.asset_file_name.toLowerCase()===asset?.toLowerCase()||r.local_filenames.some(n=>n.toLowerCase()===clean));
 return exact.length===1?exact[0]:undefined;
}
export const categories:Record<string,string>={pozorovani:'Pozorování / hlášení',vyzkum:'Technický výzkum',administrativa:'Administrativa',historie:'Historický přehled',jine:'Jiný materiál'};
// Deliberately coarse reference centres, NEVER claimed as incident coordinates.
export const countryCentres:Record<string,[number,number]>={
 'USA':[39,-98],'Spojené státy':[39,-98],'Spojené státy americké':[39,-98],
 'Kanada':[57,-106],'Mexiko':[23,-102],'Brazílie':[-10,-53],'Argentina':[-34,-64],
 'Chile':[-33,-71],'Peru':[-10,-76],'Kolumbie':[4,-73],'Venezuela':[8,-66],
 'Spojené království':[54,-2],'Francie':[47,2],'Německo':[51,10],'Itálie':[43,12],
 'Španělsko':[40,-4],'Portugalsko':[40,-8],'Řecko':[39,22],'Norsko':[62,10],
 'Švédsko':[62,15],'Finsko':[64,26],'Polsko':[52,19],'Česko':[50,15],
 'Rusko':[60,90],'Ukrajina':[49,32],'Gruzie':[42,44],'Kazachstán':[48,68],
 'Turkmenistán':[39,59],'Irák':[33,44],'Írán':[32,54],'Sýrie':[35,38],
 'Jordánsko':[31,36],'Izrael':[31,35],'Spojené arabské emiráty':[24,54],
 'Saúdská Arábie':[24,45],'Omán':[21,57],'Turecko':[39,35],'Afghánistán':[34,66],
 'Čína':[35,104],'Japonsko':[37,138],'Jižní Korea':[36,128],'Indie':[22,79],
 'Austrálie':[-25,134],'Nový Zéland':[-41,174],'Papua Nová Guinea':[-6,145],
 'Egypt':[27,30],'Maroko':[32,-6],'Jihoafrická republika':[-29,25],
 'Papua-Nová Guinea':[-6,145],'Džibutsko':[12,43],'Maďarsko':[47,19],
 'Nizozemsko':[52,5],'Zimbabwe':[-19,30],'Ázerbájdžán':[40,47]
};
export function catalogYears(r:SourceRecord):number[]{
 if(r.catalog_years)return r.catalog_years;
 const ys=r.incident_date.match(/\b(?:18|19|20)\d{2}\b/g);if(ys)return [...new Set(ys.map(Number))];
 const m=r.incident_date.match(/^\d{1,2}\/\d{1,2}\/(\d{2})$/);if(!m)return [];
 const y=Number(m[1]);return [y<=26?2000+y:1900+y];
}
export function timeMatches(time:string|null,from:string,to:string){
 if(!from&&!to)return true;if(!time)return false;
 return from&&to&&from>to?time>=from||time<=to:(!from||time>=from)&&(!to||time<=to);
}
