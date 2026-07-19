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

# FUNÇÃO PARA CATEGORIZAR AUTOMATICAMENTE
def identificar_grupo(nome):
    n = nome.upper()
    if any(x in n for x in ["ESPN", "SPORTV", "PREMIERE", "COMBATE", "FOX SPORTS", "TNT SPORTS", "BAND SPORTS", "NFL", "UFC"]):
        return "ESPORTES"
    if any(x in n for x in ["HBO", "TELECINE", "WARNER", "PARAMOUNT", "AXN", "UNIVERSAL", "MEGAPIX", "CINEMAX", "STUDIO", "AMC"]):
        return "FILMES E SÉRIES"
    if any(x in n for x in ["DISNEY", "NICK", "CARTOON", "GLOOB", "DISCOVERY KIDS", "BOOMERANG", "TOONCAST"]):
        return "KIDS / INFANTIL"
    if any(x in n for x in ["DISCOVERY", "NAT GEO", "HISTORY", "ANIMAL PLANET", "INVESTIGAÇÃO"]):
        return "DOCUMENTÁRIOS"
    if any(x in n for x in ["GLOBO", "SBT", "RECORD", "BAND", "REDE TV", "TV BRASIL"]):
        return "CANAIS ABERTOS"
    if any(x in n for x in ["GNT", "VIVA", "MULTISHOW", "MTV", "TLC", "E!", "FASHION"]):
        return "VARIEDADES"
    if any(x in n for x in ["NEWS", "CNN", "RECORD NEWS", "BAND NEWS", "BLOOMBERG"]):
        return "NOTÍCIAS"
    return "OUTROS"

def get_channels():
    url = "https://app.megafrixapi.com/TV/1.2/?page=viewChannels"
    playlist = "#EXTM3U\n"
    
    try:
        session = requests.Session()
        response = session.post(url, headers=HEADERS, data={"userHistoric": "[]"}, timeout=25)
        content = response.text

        # Busca por blocos de dados (Base64) - forma mais comum no app
        items = re.findall(r'data-data="([^"]+)"', content)
        if not items:
            items = re.findall(r"getSource\s*\(\s*'[^']*'\s*,\s*'([^']*)'\s*\)", content)

        my_url = request.host_url.rstrip('/')

        for block in items:
            try:
                try:
                    decoded = base64.b64decode(block).decode('utf-8')
                    data = json.loads(decoded)
                except:
                    data = json.loads(block.replace('\\"', '"'))
                
                cid = data.get('id')
                name = data.get('titulo', data.get('name', 'Canal'))
                logo = data.get('img', data.get('poster', ''))
                
                if cid and name:
                    clean_name = re.sub('<[^<]+?>', '', name).strip()
                    
                    # AQUI ACONTECE A MÁGICA:
                    # Se o site já tiver um grupo, usamos ele. Se não tiver, o script decide.
                    group_name = data.get('genre', identificar_grupo(clean_name))
                    
                    stream_link = f"{my_url}/play/{cid}"
                    
                    playlist += f'#EXTINF:-1 tvg-logo="{logo}" group-title="{group_name}",{clean_name}\n'
                    playlist += f"{stream_link}\n"
            except:
                continue

        return playlist
    except Exception as e:
        return f"#EXTM3U\n# Erro: {str(e)}"

@app.route('/play/<canal_id>')
def play(canal_id):
    try:
        ext_url = f"https://app.megafrixapi.com/get_token_channel.php?channel={canal_id}"
        res = requests.get(ext_url, headers=HEADERS, timeout=10)
        m3u8 = re.search(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', res.text)
        if m3u8: return redirect(m3u8.group(1))
        js = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', res.text)
        if js: return redirect(js.group(1))
        return "Video não encontrado", 404
    except:
        return "Erro no extrator", 500

@app.route('/playlist.m3u')
def m3u_route():
    return Response(get_channels(), mimetype='text/plain')

@app.route('/')
def home():
    return "Servidor M3U MegaFlix Online com Auto-Categorias!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
