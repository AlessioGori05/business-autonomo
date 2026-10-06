"""Ottieni il REFRESH TOKEN di un canale YouTube (da eseguire UNA volta per canale sul tuo PC).

Uso (Windows, dal Prompt dei comandi nella cartella del progetto):
    python scripts\\get_youtube_token.py

Ti chiede Client ID e Client Secret (dal progetto Google Cloud), apre il browser,
scegli il canale giusto e autorizzi. Alla fine stampa il refresh token da incollare
nei segreti GitHub. Usa solo la libreria standard di Python: niente da installare.
"""
import http.server
import json
import secrets
import threading
import urllib.parse
import urllib.request
import webbrowser

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]
PORT = 8765
REDIRECT = f"http://localhost:{PORT}/"


def main():
    print("== Collegamento canale YouTube ==")
    client_id = input("Client ID: ").strip()
    client_secret = input("Client Secret: ").strip()
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                result["code"] = q["code"][0]
                msg = "Autorizzazione completata. Puoi chiudere questa scheda e tornare al terminale."
            else:
                msg = "Errore: richiesta non valida."
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h2>{msg}</h2>".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state})
    print("\nSi apre il browser. Accedi e SCEGLI IL CANALE GIUSTO (EN, IT o bambini).")
    print("Se compare 'Google non ha verificato questa app': Avanzate > Vai a ... (è la tua app).\n")
    webbrowser.open(url)
    print("Se il browser non si apre, copia questo link:\n" + url + "\n")
    while "code" not in result:
        threading.Event().wait(0.5)
    data = urllib.parse.urlencode({"code": result["code"], "client_id": client_id, "client_secret": client_secret,
                                   "redirect_uri": REDIRECT, "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data) as r:
        tok = json.load(r)
    print("\n==============================================")
    print("REFRESH TOKEN (copialo nel segreto GitHub ..._REFRESH_TOKEN):\n")
    print(tok.get("refresh_token", "(non ricevuto: rimuovi l'accesso dell'app dal tuo account Google e riprova)"))
    print("==============================================")


if __name__ == "__main__":
    main()
