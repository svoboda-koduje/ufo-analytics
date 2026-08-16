# -*- coding: utf-8 -*-
import os
import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://www.war.gov/UFO/"
DOWNLOAD_DIR = "incoming_data"

def scrape_ufo_portal():
    """
    Automaticky stahuje PDF, obrázky a videa z portálu war.gov/UFO
    do lokální složky pro následnou analýzu v low-budget režimu.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    downloaded_files = []
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UAP-Research-Bot/3.2"}
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"Server vrátil kód {response.status_code}"}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Prohledání stránky a stažení odkazů na soubory
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(ext in href.lower() for ext in ['.pdf', '.mp4', '.jpg', '.png', '.avi', '.mov']):
                file_url = href if href.startswith('http') else f"https://www.war.gov/UFO/{href}"
                file_name = os.path.basename(file_url.split('?')[0])
                file_path = os.path.join(DOWNLOAD_DIR, file_name)
                
                # Stáhnout pouze pokud soubor ještě neexistuje
                if not os.path.exists(file_path):
                    file_res = requests.get(file_url, headers=headers, timeout=30)
                    if file_res.status_code == 200:
                        with open(file_path, 'wb') as f:
                            f.write(file_res.content)
                        downloaded_files.append(file_name)
                        
        return {"status": "success", "new_files_downloaded": downloaded_files}
    
    except Exception as e:
        # Pokud je portál nedostupný (nebo v offline/testovacím režimu), systém využije lokální vzorky
        return {"status": "offline_mode", "message": f"Chyba při připojení k war.gov/UFO: {str(e)}"}
