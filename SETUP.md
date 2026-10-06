# Guida di configurazione (una volta sola)

Tempo totale: 1-2 ore. Puoi farla a tappe: **ogni pezzo che colleghi si attiva da solo**, il resto continua a lavorare in modalità anteprima.

Ordine consigliato: **1 → 2 → 3** (il sistema gira già) → 4-6 (YouTube) → 7-9 (guadagni) → 10 (extra).

---

## 1. Metti il progetto su GitHub (10 min)

0. **Prima di tutto:** nella cartella `business-autonomo` rinomina la cartella **`_github`** in **`.github`** (con il punto davanti). Contiene gli orari automatici del bot: senza questo passaggio GitHub non li vede. Windows potrebbe avvisarti del nome con il punto: conferma.
1. Installa **GitHub Desktop** (gratis): https://desktop.github.com e accedi con il tuo account `AlessioGori05`.
2. *File → Add local repository* → scegli la cartella `business-autonomo` → se chiede, clicca *create a repository*.
3. Clicca **Publish repository**:
   - Nome: `business-autonomo`
   - **Togli la spunta "Keep this code private"**.
     Perché pubblico: con l'account gratuito GitHub Pages (il sito) funziona solo sui repository pubblici, e i minuti di Actions sono illimitati. Password e chiavi **non** finiscono nel codice: stanno nei *Secrets*, che nessuno può leggere.

## 2. Dai i permessi al bot (3 min)

Sul sito di GitHub, nel repository:

1. **Settings → Actions → General** → in fondo, *Workflow permissions* → **Read and write permissions** → Save.
2. **Settings → Pages** → *Source*: **Deploy from a branch** → Branch `main`, cartella **`/docs`** → Save.
   Dopo qualche minuto il sito è su `https://alessiogori05.github.io/business-autonomo/`.

## 3. Primo avvio di prova (5 min)

1. Tab **Actions** → se chiede, *I understand my workflows, go ahead and enable them*.
2. Clicca **1 - Produzione giornaliera** → **Run workflow**.
3. Dopo ~10-20 minuti apri l'esecuzione: in fondo, sezione **Artifacts**, scarichi i video prodotti (anteprime, perché YouTube non è ancora collegato).
4. Vai su **Issues**: troverai i report e le richieste del bot. Attiva le email in *Watch → All activity* (in alto a destra nel repository) se non le ricevi.

Da qui in poi il sistema gira ogni giorno da solo. L'AI che scrive i testi è **GitHub Models**, gratuita e già inclusa: non serve nessuna chiave.

---

## 4. Crea i canali YouTube (15 min)

Con un solo account Google puoi avere più canali ("account brand"):

1. https://www.youtube.com/channel_switcher → **Crea un canale**. Creane 4 (o solo quelli che vuoi usare ora):
   - canale EN (es. *Smart Daily Picks*)
   - canale IT (es. *Scelte Smart*)
   - canale bambini EN (es. *Little Learners*)
   - canale bambini IT (es. *Piccoli Esploratori*)
2. Nei canali bambini: **YouTube Studio → Impostazioni → Canale → Impostazioni avanzate → "Sì, imposta questo canale come destinato ai bambini"**.
3. Nei canali EN/IT: **Personalizzazione → Informazioni di base → Link**, aggiungi il tuo sito:
   - EN: `https://alessiogori05.github.io/business-autonomo/en/index.html`
   - IT: `https://alessiogori05.github.io/business-autonomo/it/index.html`

   È il "link in bio" citato nei video: YouTube non rende cliccabili i link nelle descrizioni degli Shorts, ma quello del profilo sì.
4. Verifica il telefono su https://www.youtube.com/verify (serve per alcune funzioni).

## 5. Crea le chiavi API di Google (15 min per canale)

La quota gratuita di YouTube permette circa **6 caricamenti al giorno per progetto**. Per questo conviene **un progetto Google per canale**. Ripeti per ogni canale:

1. https://console.cloud.google.com → in alto *Seleziona progetto* → **Nuovo progetto** (es. `ba-main-en`).
2. *API e servizi → Libreria*: abilita **YouTube Data API v3** e **YouTube Analytics API**.
3. *API e servizi → Schermata consenso OAuth* (o *Google Auth Platform*):
   - Tipo utente **Esterno**, nome app (es. `Business Autonomo`), la tua email.
   - In *Pubblico/Test users* aggiungi la tua email.
   - **Importante:** clicca **Pubblica app / Passa in produzione**. Se resta "In test", il collegamento scade ogni 7 giorni e il bot si ferma. Non serve la verifica di Google: sei l'unico utente.
4. *Credenziali → Crea credenziali → ID client OAuth* → tipo **App desktop** → Crea.
   Copia **ID client** e **Client secret**.

## 6. Collega i canali al bot (5 min per canale)

Sul tuo PC:

1. Installa Python da https://www.python.org/downloads/ (durante l'installazione spunta **Add Python to PATH**).
2. Apri la cartella del progetto, clicca sulla barra dell'indirizzo, scrivi `cmd` e premi Invio.
3. Esegui:
   ```
   python scripts\get_youtube_token.py
   ```
   Incolla ID client e Client secret, si apre il browser: **scegli il canale giusto** e autorizza (se compare "Google non ha verificato questa app" → *Avanzate → Vai a…*). Il terminale stampa il **refresh token**.
4. Su GitHub: **Settings → Secrets and variables → Actions → New repository secret**, crea i tre segreti del canale:

| Canale | Segreti da creare |
|---|---|
| EN | `YT_MAIN_EN_CLIENT_ID`, `YT_MAIN_EN_CLIENT_SECRET`, `YT_MAIN_EN_REFRESH_TOKEN` |
| IT | `YT_MAIN_IT_CLIENT_ID`, `YT_MAIN_IT_CLIENT_SECRET`, `YT_MAIN_IT_REFRESH_TOKEN` |
| Bambini EN | `YT_KIDS_EN_CLIENT_ID`, `YT_KIDS_EN_CLIENT_SECRET`, `YT_KIDS_EN_REFRESH_TOKEN` |
| Bambini IT | `YT_KIDS_IT_CLIENT_ID`, `YT_KIDS_IT_CLIENT_SECRET`, `YT_KIDS_IT_REFRESH_TOKEN` |

Dal giorno dopo quel canale pubblica da solo.

### 6b. Audit di YouTube: passaggio obbligatorio

Google blocca come **privati** i video caricati da progetti API nuovi finché il progetto non supera un controllo gratuito. Per ogni progetto:

- Compila il modulo **YouTube API Services – Audit and Quota Extension**: https://support.google.com/youtube/contact/yt_api_form
- Uso dichiarato: *"Internal tool that uploads original content I create to my own YouTube channels and reads analytics for those channels. Single user (me). No data from other users is collected."*
- Può richiedere da alcuni giorni a qualche settimana, e Google può chiedere chiarimenti. Finché non arriva l'ok, il report serale ti segnala "video bloccati come privati".

---

## 7. Amazon Affiliati, metodo B (10 min)

- IT: https://programma-affiliazione.amazon.it — EN: https://affiliate-program.amazon.com
- Come sito indica `https://alessiogori05.github.io/business-autonomo/` e i canali YouTube.
- Copia il tuo **tag** (es. `alessio-21`) in `config/settings.yaml` → `amazon_tag_it` / `amazon_tag_en`.
- Nota: Amazon chiude l'account se non arrivano **3 vendite entro 180 giorni**. Conviene iscriversi quando i canali hanno già un po' di visualizzazioni.

## 8. Email gratuite, metodo C (20 min)

1. Crea un account gratuito su **MailerLite** (gratis fino a 1.000 iscritti): https://www.mailerlite.com
2. *Subscribers → Groups* → crea il gruppo `Guide EN` (e `Guide IT`).
3. *Forms → Embedded form* collegato al gruppo → in *HTML code* trova `action="https://assets.mailerlite.com/jsonp/.../subscribe"`: copia quell'URL in `newsletter_form_action_en` / `_it` di `settings.yaml`.
4. *Automations → New → When subscriber joins a group*: incolla le email che trovi in `funnels/en/` e `funnels/it/` (il bot le scrive per ogni nuova guida) e allega il link al PDF della guida.

Finché il form non c'è, le guide si scaricano direttamente senza chiedere l'email.

## 9. Print on Demand, metodo D (15 min, poi ~10 min a settimana)

1. Apri un negozio gratuito su **Redbubble**, **Spreadshirt** o **TeePublic**.
2. Metti l'URL del negozio in `pod_store_url_en` / `_it` di `settings.yaml`.
3. Ogni lunedì ricevi una issue **🎨 Nuovi design POD**: scarica lo zip dalla pagina Actions indicata, carica i PNG usando titoli e tag di `listing.csv`, chiudi la issue.

Queste piattaforme non offrono un sistema gratuito per caricare i design in automatico: è l'unico passaggio manuale ricorrente.

## 10. Extra gratuiti (facoltativi)

| Segreto / impostazione | A cosa serve | Dove si ottiene |
|---|---|---|
| `PEXELS_API_KEY` (segreto) | Sfondi video reali invece dei colori sfumati: video più curati | https://www.pexels.com/api/ |
| `GEMINI_API_KEY` (segreto) | AI di riserva se GitHub Models è al limite | https://aistudio.google.com/apikey |
| `goatcounter_code` (settings) | Conta visite e click su link affiliati e guide | https://www.goatcounter.com |

---

## Uso quotidiano

- **Non devi fare nulla.** Ricevi ogni sera il report (3 righe + tabella KPI) e ogni lunedì il report settimanale.
- **Video per bambini**: arriva una issue *👶 Approva video bambini* con i link (privati, li vedi solo tu). Guardali e commenta `/approva`, `/approva 1,3` oppure `/rifiuta`.
- **Cambiare qualcosa** (canali, quanti video, argomenti, soglie KPI): modifica `config/settings.yaml` o `config/methods.yaml` direttamente da GitHub (icona matita).
- **Mettere in pausa tutto**: *Actions* → workflow → *⋯* → *Disable workflow*.
- **Avviare subito** senza aspettare l'orario: *Actions* → workflow → *Run workflow*.

## Aspettative realistiche

- **Guadagni pubblicitari YouTube** arrivano solo dopo l'ammissione al Programma partner (1.000 iscritti + 10 milioni di visualizzazioni Shorts in 90 giorni). Prima di allora le entrate possibili sono affiliazioni, POD ed email.
- YouTube **non monetizza i contenuti "ripetitivi o prodotti in serie"**. Per questo il sistema varia argomenti, ganci, grafica e voci e scarta i duplicati. Controlla comunque ogni tanto i video: se un formato sembra troppo uguale a sé stesso, togli o cambia argomenti in `methods.yaml`.
- I canali **per bambini** hanno commenti disattivati e annunci non personalizzati: guadagnano meno per visualizzazione.
- Nei primi 1-2 cicli i dati sono pochi: il sistema non sposta le quote finché la media è sotto 20 visualizzazioni a video ("dati insufficienti" nel report).
- GitHub disattiva i workflow programmati dopo 60 giorni senza attività nel repository. I salvataggi quotidiani del bot di solito bastano a evitarlo; se succede, riattivali da *Actions*.
