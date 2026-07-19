from flask import Flask, Response, redirect, request
import requests
import re
import os
import json
import base64

app = Flask(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://megaflix.name/",
    "X-Requested-With": "XMLHttpRequest"
}

# FUNÇÃO DE CATEGORIZAÇÃO INTELIGENTE
def identificar_grupo(nome, tipo="TV"):
    n = nome.upper()
    
    # Se for Filme/Série/Anime, mantém o grupo geral
    if tipo == "FILME": return "🎬 FILMES MEGAFLIX"
    if tipo == "SERIE": return "📺 SÉRIES MEGAFLIX"
    if tipo == "ANIME": return "⛩️ ANIMES MEGAFLIX"
    
    # --- CATEGORIZAÇÃO DE CANAIS DE TV ---
    
    # 1. ESPORTES
    if any(x in n for x in ["ESPN", "SPORTV", "PREMIERE", "COMBATE", "FOX SPORTS", "TNT SPORTS", "BAND SPORTS", "DAZN", "NBA", "UFC", "NFL", "GOLF", "TENIS"]):
        return "⚽ ESPORTES"
    
    # 2. DOCUMENTÁRIOS
    if any(x in n for x in ["DISCOVERY", "NAT GEO", "NATIONAL GEOGRAPHIC", "HISTORY", "ANIMAL PLANET", "INVESTIGAÇÃO", "ID", "OFF", "SCIENCE", "WILD"]):
        return "🌍 DOCUMENTÁRIOS"
    
    # 3. OUTROS GRUPOS DE TV
    if any(x in n for x in ["HBO", "TELECINE", "WARNER", "PARAMOUNT", "AXN", "UNIVERSAL", "MEGAPIX", "CINEMAX", "STUDIO", "AMC"]):
        return "🎭 FILMES E SÉRIES (CANAIS)"
    if any(x in n for x in ["DISNEY", "NICK", "CARTOON", "GLOOB", "BOOMERANG", "TOONCAST", "PANDA"]):
        return "👶 KIDS / INFANTIL"
    if any(x in n for x in ["GLOBO", "SBT", "RECORD", "BAND", "REDE TV", "TV BRASIL", "CULTURA"]):
        return "📡 CANAIS ABERTOS"
    if any(x in n for x in ["NEWS", "CNN", "RECORD NEWS", "BAND NEWS", "BLOOMBERG"]):
        return "📰 NOTÍCIAS"
    
    return "📺 VARIADOS / GERAL"

def extrair_da_pagina(page_name, tipo_item, session):
    url = f"https://app.megafrixapi.com/TV/1.2/?page={page_name}"
    items_list = []
    try:
        response = session.post(url, headers=HEADERS, data={"userHistoric": "[]"}, timeout=20)
        content = response.text
        
        # Busca Base64 ou getSource
        matches = re.findall(r'data-data="([^"]+)"', content)
        if not matches:
            matches = re.findall(r"getSource\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*\)", content)
            
        for block in matches:
            try:
                try:
                    decoded = base64.b64decode(block).decode('utf-8')
                    data = json.loads(decoded)
                except:
                    data = json.loads(block.replace('\\"', '"'))
                
                cid = data.get('id')
                name = data.get('titulo', data.get('name', 'Item'))
                logo = data.get('img', data.get('poster', ''))
                items_list.append({'id': cid, 'name': name, 'logo': logo, 'tipo': tipo_item})
            except:
                continue
    except:
        pass
    return items_list

@app.route('/playlist.m3u')
def m3u_route():
    # Link do EPG embutido na lista
    playlist = "#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/fagner-mms/EPG/master/guide.xml\"\n"
    session = requests.Session()
    # Pega cookies iniciais
    session.get("https://app.megafrixapi.com/TV/1.2/", headers=HEADERS, timeout=10)
    
    # Ordem de prioridade na lista
    alvos = [
        ('viewChannels', 'TV'),
        ('viewMovies', 'FILME'),
        ('viewSeries', 'SERIE'),
        ('viewAnimes', 'ANIME')
    ]
    
    my_url = request.host_url.rstrip('/')
    
    for page, tipo in alvos:
        itens = extrair_da_pagina(page, tipo, session)
        for it in itens:
            clean_name = re.sub('<[^<]+?>', '', it['name']).strip()
            grupo = identificar_grupo(clean_name, it['tipo'])
            
            # Adiciona tvg-id baseado no nome para o EPG funcionar melhor
            epg_id = clean_name.replace(" HD", "").replace(" FHD", "").strip()
            
            playlist += f'#EXTINF:-1 tvg-id="{epg_id}" tvg-logo="{it["logo"]}" group-title="{grupo}",{clean_name}\n'
            playlist += f"{my_url}/play/{it['id']}?tipo={it['tipo']}\n"
            
    return Response(playlist, mimetype='text/plain')

@app.route('/play/<item_id>')
def play(item_id):
    tipo = request.args.get('tipo', 'TV')
    try:
        if tipo == 'TV':
            target_url = f"https://app.megafrixapi.com/get_token_channel.php?channel={item_id}"
        else:
            target_url = f"https://app.megafrixapi.com/get_token_vod.php?id={item_id}"
            
        res = requests.get(target_url, headers=HEADERS, timeout=15)
        
        # Procura .m3u8 ou .mp4
        media_match = re.search(r'["\'](https?://[^"\']+\.(?:m3u8|mp4|mkv|ts)[^"\']*)["\']', res.text)
        
        if media_match:
            return redirect(media_match.group(1))
            
        # Caso seja redirecionamento JS
        js_match = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', res.text)
        if js_match:
            return redirect(js_match.group(1))

        return "Mídia não encontrada", 404
    except:
        return "Erro no extrator", 500

@app.route('/')
def home():
    return "Servidor MegaFlix Master M3U Ativo!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
