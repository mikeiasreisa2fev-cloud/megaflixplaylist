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

def identificar_grupo(nome, tipo="TV"):
    n = nome.upper()
    if tipo == "FILME": return "🎬 FILMES MEGAFLIX"
    if tipo == "SERIE": return "📺 SÉRIES MEGAFLIX"
    if tipo == "ANIME": return "⛩️ ANIMES MEGAFLIX"
    
    # Categorização de Canais de TV
    if any(x in n for x in ["ESPN", "SPORTV", "PREMIERE", "COMBATE", "FOX SPORTS"]): return "⚽ ESPORTES"
    if any(x in n for x in ["HBO", "TELECINE", "WARNER", "PARAMOUNT", "AXN"]): return "🎭 FILMES E SÉRIES (TV)"
    if any(x in n for x in ["DISNEY", "NICK", "CARTOON", "GLOOB"]): return "👶 KIDS"
    if any(x in n for x in ["GLOBO", "SBT", "RECORD", "BAND"]): return "📡 CANAIS ABERTOS"
    return "📺 MEGAFLIX TV"

def extrair_da_pagina(page_name, tipo_item, session):
    url = f"https://app.megafrixapi.com/TV/1.2/?page={page_name}"
    items_list = []
    try:
        response = session.post(url, headers=HEADERS, data={"userHistoric": "[]"}, timeout=15)
        content = response.text
        
        # Procura por blocos Base64 ou getSource
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
    playlist = "#EXTM3U x-tvg-url=\"https://raw.githubusercontent.com/fagner-mms/EPG/master/guide.xml\"\n"
    session = requests.Session()
    session.get("https://app.megafrixapi.com/TV/1.2/", headers=HEADERS) # Pega cookies
    
    # LISTA DE BUSCA: Canais, Filmes, Séries e Animes
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
            
            # Formatação M3U
            playlist += f'#EXTINF:-1 tvg-logo="{it["logo"]}" group-title="{grupo}",{clean_name}\n'
            # Redirecionamos para a nossa rota de extração
            playlist += f"{my_url}/play/{it['id']}?tipo={it['tipo']}\n"
            
    return Response(playlist, mimetype='text/plain')

@app.route('/play/<item_id>')
def play(item_id):
    tipo = request.args.get('tipo', 'TV')
    try:
        # Se for canal de TV, usa o extrator de canais
        if tipo == 'TV':
            target_url = f"https://app.megafrixapi.com/get_token_channel.php?channel={item_id}"
        else:
            # Se for filme/série, a lógica é mais complexa, mas tentamos o extrator padrão
            target_url = f"https://app.megafrixapi.com/get_token_vod.php?id={item_id}"
            
        res = requests.get(target_url, headers=HEADERS, timeout=10)
        m3u8_match = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', res.text)
        
        if m3u8_match:
            return redirect(m3u8_match.group(1))
        
        # Fallback para mp4 (comum em filmes)
        mp4_match = re.search(r'["\'](https?://[^"\']+\.mp4[^"\']*)["\']', res.text)
        if mp4_match:
            return redirect(mp4_match.group(1))
            
        return "Arquivo de mídia não encontrado", 404
    except:
        return "Erro no servidor de mídia", 500

@app.route('/')
def home():
    return "Servidor MegaFlix Full (TV + VOD) Ativo!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
