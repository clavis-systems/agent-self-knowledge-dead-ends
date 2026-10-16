# Leggere nella mente: piano del cancello (scritto prima di ogni risultato), 16/10/2026

L'utente: "procedi con la 2 e poi la 1". Domanda: il modello "sa" dentro di sé se il codice è sbagliato meglio di
quanto lo dica a parole? Invece di chiedergli "sì o no", si legge il suo stato interno mentre legge la domanda, e un
piccolo rilevatore impara a leggerlo.

## Dati (nessun download)

Le 597 soluzioni con l'esito dei test severi (strumenti/risultati/sguardo/etichette.jsonl, compito 32 escluso). Il
gruppo che conta: le 507 che passano i test visibili (40 "falsi ho finito"), come nel secondo sguardo.

## Come (mente.py)

- Modello: Qwen3 8B, lo stesso file che usa Ollama (blob sha256:a3de86cd…), letto con llama.cpp già presente
  (llama-server, build 11160), con `--embeddings --pooling last`: per ogni testo si ottiene lo stato interno
  dell'ultimo strato sull'ultima parola (un vettore). Ollama spento durante la prova.
- Testo letto: esattamente la domanda del giudice (specifica + codice + "Does the implementation do exactly what the
  docstring says…"). Controllo: solo il codice, senza specifica e senza domanda.
- Rilevatore: 5 parti divise per compito (seme "mente-2026-10-16"); in ogni parte, standardizzazione e 50 componenti
  principali calcolate solo sull'allenamento, poi regressione logistica (λ = 1). Allenato su tutte le 597 (successo =
  test severi passati), valutato sulle 507 che passano i visibili.
- Controlli: etichette mescolate nell'allenamento (deve dare circa 0,5); solo codice; lunghezza.

## Cancello (fissato ora)

**Passa** se il rilevatore sullo stato interno, tra le 507, separa i falsi "ho finito" con AUC almeno 0,05 più alta
del giudizio a parole dello stesso modello (Qwen, 0,768): quindi almeno 0,818. Esplorativo: rilevatore + giudizio a
parole insieme; Gemma, se questa versione di llama.cpp legge il suo file.

## Scostamenti

(vuoto)
