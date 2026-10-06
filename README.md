# Business Autonomo

Sistema che crea, pubblica, misura e ottimizza **da solo** più micro-business online in parallelo, girando gratis su **GitHub Actions**. Tu intervieni solo per la configurazione iniziale (una volta), per approvare i video per bambini e per caricare i design Print on Demand.

> Versione **gratuita**: budget pubblicitario 0 €, nessun freelancer, solo servizi con piano gratuito.

## Cosa fa ogni giorno, senza di te

| Ora (Italia) | Workflow | Cosa succede |
|---|---|---|
| 08:17 | `1 - Produzione giornaliera` | Sceglie i metodi in base alle quote, scrive i testi con AI gratuita (Google Gemini, piano free), controllo qualità, voce, video 1080x1920, caricamento su YouTube, aggiorna il sito |
| 20:43 | `2 - KPI e report serale` | Legge visualizzazioni, durata media, engagement, ricavi; valuta le varianti; ti manda il **report di 3 righe + tabella KPI** |
| Lunedì 07:07 | `3 - Riallocazione settimanale` | Sposta le quote verso i metodi che rendono di più, taglia/ferma quelli negativi, **report settimanale** con motivazioni |
| Quando commenti | `4 - Approvazione video bambini` | `/approva` pubblica, `/rifiuta` scarta |

I report arrivano come **Issue di GitHub** → ricevi un'email automatica da GitHub. Restano anche in `reports/`.

## Metodi testati in parallelo

| | Metodo | Canale | Automazione |
|---|---|---|---|
| A | Shorts virali (curiosità, life hack) | EN + IT | 100% |
| B | Affiliate micro-video + pagina con link Amazon | EN + IT | 100% (dopo iscrizione ad Amazon Affiliati) |
| C | Micro-corsi/lead magnet: guida PDF + raccolta email + sequenza email | EN + IT | 100% (sequenza email da incollare una volta) |
| D | Print on Demand: design generati + Shorts promozionali | EN + IT | 95% (caricamento design sul negozio: ~2 min/design a settimana) |
| E | Shorts educativi per bambini | canali kids EN + IT | pubblica solo dopo il tuo `/approva` |
| F | Ads e retargeting | — | spento (budget 0) |

## Regole del tuo prompt, come sono implementate

- **≥ 4 metodi in parallelo, 10 varianti per metodo** (gancio × tema grafico × durata, es. A1…A10).
- **Finestra di test**: 7 giorni o 1.000 visualizzazioni, la prima che arriva.
- **Classificazione varianti**: *vincitore* (punteggio ≥ 1,3 × mediana del metodo, riceve il doppio dei caricamenti), *sospeso* (engagement < 0,5% e durata media < 3 s per 2 cicli), *da riprogettare* (punteggio < 60% della mediana → sostituita da una nuova combinazione).
- **Ogni 7 giorni**: quote spostate verso la resa più alta; *+50%* se un metodo supera il target; metodo negativo per 2 cicli → *-50%* e nuova tattica; ancora negativo → *fermato*.
- **Controllo qualità** prima di ogni pubblicazione: lunghezze, parole a rischio, marchi/personaggi protetti, link, affidabilità dei fatti ≥ 0,8, niente duplicati, regole speciali per i bambini.
- **Limiti**: budget 0 €, freelancer 0 €, nessuna pubblicazione per bambini senza il tuo OK.

Tutto è regolabile in `config/settings.yaml` e `config/methods.yaml`.

## Struttura

```
config/      impostazioni e metodi (l'unica parte da modificare)
src/         il motore (generazione, video, YouTube, KPI, decisioni, report, sito)
scripts/     get_youtube_token.py: collega un canale (una volta, dal tuo PC)
data/        memoria del sistema (contenuti, quote, varianti, metriche) - aggiornata dal bot
docs/        sito gratuito su GitHub Pages (link in bio, liste affiliate, guide PDF)
funnels/     sequenze email da incollare nel servizio email gratuito
reports/     report giornalieri e settimanali
```

## Inizia da qui

Segui **[SETUP.md](SETUP.md)**: passo passo, circa 1-2 ore la prima volta. Puoi farlo un pezzo alla volta: il sistema funziona già con quello che colleghi (i canali non ancora collegati producono video di anteprima scaricabili).

Prova senza account: `python -m src.run demo` (testi d'esempio, nessuna pubblicazione).
