#!/usr/bin/env python3
"""Sobe um vídeo no canal pela YouTube Data API v3, SEMPRE como privado.

Uso:
    python3 upload_youtube.py video.json

O video.json tem:
{
  "arquivo": "caminho/do/video.mp4",
  "titulo": "Título do vídeo",
  "descricao": "Texto livre"               (OU use o modelo do canal abaixo)
  "modelo": {                              (preenche modelo_descricao.txt)
     "abertura": "2 parágrafos de gancho",
     "cta_gancho": "Quer parar de X e começar a Y?",
     "cta_beneficio": "transformar X em hábito",
     "aprendizados": ["tópico 1", "tópico 2"],
     "hashtags": ["estoicismo", "audiobook"]
  },
  "creditos": "caminho/creditos.txt",      (opcional, entra antes das hashtags)
  "transcricao": "caminho/segments.json",  (opcional, vira legenda pt-BR)
  "tags": ["estoicismo", "audiobook"],
  "capa": "caminho/capa.jpg",              (opcional, até 2 MB, 1280x720)
  "playlist_id": "PL..."                   (opcional)
}

Na primeira vez abre o navegador para você autorizar o canal.
Depois guarda a autorização em token.json e não pergunta mais.
Precisa do arquivo client_secret.json (baixado do Google Cloud) na mesma pasta.

Para instalar o necessário (uma vez só):
    pip3 install google-api-python-client google-auth-oauthlib
"""
import json
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

PASTA = os.path.dirname(os.path.abspath(__file__))
SEGREDO = os.path.join(PASTA, "client_secret.json")
TOKEN = os.path.join(PASTA, "token.json")
CANAL_CERTO = "UCgV3jee73uLoCBFi9-0bSsQ"  # A Arte Estoica
ESCOPOS = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",  # capa e playlist
    "https://www.googleapis.com/auth/youtube.force-ssl",  # legendas
]


def autenticar():
    cred = None
    if os.path.exists(TOKEN):
        cred = Credentials.from_authorized_user_file(TOKEN, ESCOPOS)
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            try:
                cred.refresh(Request())
            except Exception:
                cred = None
        if not cred or not cred.valid:
            if not os.path.exists(SEGREDO):
                sys.exit("Falta o client_secret.json nesta pasta: " + PASTA)
            fluxo = InstalledAppFlow.from_client_secrets_file(SEGREDO, ESCOPOS)
            cred = fluxo.run_local_server(port=0, prompt="consent")
        with open(TOKEN, "w") as f:
            f.write(cred.to_json())
    return build("youtube", "v3", credentials=cred)


SITE_REPO = os.environ.get("SITE_REPO", "/home/user/arte-estoica")
SITE_URL = "https://eljonh7.github.io/arte-estoica/"


def publicar_creditos(titulo, texto):
    """Põe os créditos completos numa página do site e devolve o texto curto com o link."""
    import html, re, subprocess, unicodedata
    slug = unicodedata.normalize("NFKD", titulo.split("|")[0]).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")[:60] or "video"
    pasta = os.path.join(SITE_REPO, "creditos")
    os.makedirs(pasta, exist_ok=True)
    corpo = re.sub(r"(https?://\S+)", r'<a href="\1">\1</a>', html.escape(texto))
    with open(os.path.join(pasta, slug + ".html"), "w", encoding="utf-8") as f:
        f.write('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f"<title>Créditos – {html.escape(titulo)}</title>"
                "<style>body{font-family:Georgia,serif;background:#111;color:#eee;max-width:900px;"
                "margin:auto;padding:24px;line-height:1.6;white-space:pre-wrap;word-break:break-word}"
                "a{color:#d4af37}</style></head><body>"
                f"<h1>Créditos – {html.escape(titulo)}</h1>{corpo}</body></html>")
    git = ["git", "-C", SITE_REPO]
    subprocess.run(git + ["add", "creditos"], check=True)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode:
        subprocess.run(git + ["-c", "user.name=ElJonh7", "-c",
                              "user.email=206900307+ElJonh7@users.noreply.github.com",
                              "commit", "-qm", "Créditos: " + titulo[:60]], check=True)
        subprocess.run(git + ["push", "-q", "origin", "main"], check=True)
    link = SITE_URL + "creditos/" + slug + ".html"
    print("Créditos publicados em", link)
    return "🎵🖼️ Créditos de música e imagens: " + link


def tempo_srt(seg):
    ms = int(round(seg * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def caminho(base, p):
    return p if os.path.isabs(p) else os.path.join(base, p)


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: python3 upload_youtube.py video.json")
    cfg_path = os.path.abspath(sys.argv[1])
    base = os.path.dirname(cfg_path)
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    creditos = ""
    if cfg.get("creditos"):
        with open(caminho(base, cfg["creditos"]), encoding="utf-8") as f:
            creditos = f.read().strip()
        if cfg.get("creditos_no_site", True):
            creditos = publicar_creditos(cfg["titulo"], creditos)
    if cfg.get("modelo"):
        m = cfg["modelo"]
        with open(os.path.join(PASTA, "modelo_descricao.txt"), encoding="utf-8") as f:
            modelo = f.read()
        descricao = modelo.format(
            abertura=m["abertura"].strip(),
            cta_gancho=m["cta_gancho"].strip(),
            cta_beneficio=m["cta_beneficio"].strip(),
            aprendizados="\n".join("• " + a for a in m["aprendizados"]),
            creditos=("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n" + creditos + "\n") if creditos else "",
            hashtags=" ".join("#" + h.lstrip("#").replace(" ", "") for h in m.get("hashtags", [])),
        ).strip()
    else:
        descricao = cfg.get("descricao", "")
        if creditos:
            descricao = descricao.rstrip() + "\n\n" + creditos
    if len(descricao) > 5000:
        sys.exit(f"Descrição tem {len(descricao)} caracteres; o limite do YouTube é 5000.")

    corpo = {
        "snippet": {
            "title": cfg["titulo"][:100],
            "description": descricao,
            "tags": cfg.get("tags", []),
            "categoryId": cfg.get("categoria", "27"),  # 27 = Educação
            "defaultLanguage": "pt-BR",
            "defaultAudioLanguage": "pt-BR",
        },
        "status": {
            "privacyStatus": "private",  # nunca público sem o ok do Jonh
            "selfDeclaredMadeForKids": False,
        },
    }

    yt = autenticar()
    canais = yt.channels().list(part="id", mine=True).execute().get("items", [])
    if not canais or canais[0]["id"] != CANAL_CERTO:
        sys.exit("Autorização é de outro canal, não do A Arte Estoica. Apague token.json e autorize de novo.")
    video = caminho(base, cfg["arquivo"])
    midia = MediaFileUpload(video, chunksize=8 * 1024 * 1024, resumable=True)
    pedido = yt.videos().insert(part="snippet,status", body=corpo, media_body=midia)

    print("Enviando", os.path.basename(video))
    resposta = None
    while resposta is None:
        status, resposta = pedido.next_chunk()
        if status:
            print(f"  {int(status.progress() * 100)}%")
    vid = resposta["id"]
    print("Vídeo enviado como PRIVADO: https://studio.youtube.com/video/" + vid + "/edit")

    if cfg.get("capa"):
        yt.thumbnails().set(
            videoId=vid, media_body=MediaFileUpload(caminho(base, cfg["capa"]))
        ).execute()
        print("Capa aplicada.")

    if cfg.get("transcricao"):
        srt = os.path.join(PASTA, vid + ".srt")
        with open(caminho(base, cfg["transcricao"]), encoding="utf-8") as f:
            segs = json.load(f)
        with open(srt, "w", encoding="utf-8") as f:
            for i, s in enumerate(s for s in segs if s.get("text")):
                f.write(f"{i + 1}\n{tempo_srt(s['start'])} --> {tempo_srt(s['end'])}\n{s['text']}\n\n")
        yt.captions().insert(
            part="snippet",
            body={"snippet": {"videoId": vid, "language": "pt-BR", "name": "Português", "isDraft": False}},
            media_body=MediaFileUpload(srt, mimetype="application/octet-stream"),
        ).execute()
        os.remove(srt)
        print("Legenda enviada.")

    if cfg.get("playlist_id"):
        yt.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": cfg["playlist_id"],
                              "resourceId": {"kind": "youtube#video", "videoId": vid}}},
        ).execute()
        print("Adicionado à playlist.")


if __name__ == "__main__":
    main()
