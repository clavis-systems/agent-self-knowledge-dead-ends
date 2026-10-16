# Fumo, prove A, B e C: piano (scritto prima di calcolare i risultati), 15/10/2026

Contesto: RISULTATO_FUMO.md. I quattro punti di vista sul "ritmo" della corsa non vedono niente nel primo terzo,
nemmeno sullo stesso agente. Due domande nuove, approvate dall'utente ("procedi con a e b").

Dati: le stesse 1.801 corse (fumo_passi.jsonl), più i file toccati a ogni passo (fumo_percorsi.jsonl: gli argomenti
delle chiamate per Qwen e Gemma, la prima riga del risultato per Opus). SWE-bench Verified (test, 500 compiti,
princeton-nlp/SWE-bench_Verified su Hugging Face, sha256 a45b1fe4…, scaricato il 15/10 con l'OK dell'utente): testo
della segnalazione, suggerimenti, patch vera, difficoltà stimata da persone. Per Gemma i file d'oro sono quelli dello
studio "chi legge la mappa".

## A. Il punto di arrivo (controllo "barando": usa la soluzione vera)

Stesso punto di controllo di Fumo (30% della corsa mediana: 17, 20, 15, 4 passi), stesse corse ancora in corso.
- Misura principale: il passo in cui l'agente tocca per la prima volta un file che la soluzione cambia (K+1 se mai
  nei primi K passi); AUC con il fallimento come positivo.
- Anche: quota di corse che ci arrivano; tasso di fallimento con e senza; aver già modificato un file giusto.
- **Regola:** l'informazione "c'è presto, almeno nel contenuto" se l'AUC è almeno 0,65 in almeno 3 agenti su 4.
  Se no: nessun rilevatore precoce può funzionare con questi dati, e lo si scrive così.
- Secondario: punto di controllo a metà della corsa mediana.

## B. Il fumo nel compito (prima di partire, solo dal testo)

I 3 agenti SWE-bench (Qwen 30B, Qwen 480B, Opus), compiti in comune. Nessuna informazione sulla soluzione o sui test.
- B1: 8 indicatori del testo (lunghezza, blocchi di codice, traceback, file .py nominati, nomi tra apici inversi,
  la parola "expected", indirizzi web, lunghezza dei suggerimenti) più il repository.
- B2: B1 più le parole del testo (4.096 caselle, logaritmo dei conteggi).
- Regressione logistica (B1 λ = 1, B2 λ = 50), 5 parti divise per **compito** (nessun compito sia in allenamento sia in
  prova), una riga per compito e agente con l'agente come indicatore.
- **Regola:** B è promettente se l'AUC media sui 3 agenti è almeno 0,70. Si riporta anche quanti compiti destinati
  a fallire si saltano perdendo il 2% dei successi.
- Riferimento, senza decisioni: la difficoltà stimata da persone (non disponibile per compiti nuovi).

## C. Il disaccordo degli esploratori (solo descrittivo)

Nei primi K passi, quanto si sovrappongono i file guardati dai 3 agenti sullo stesso compito (Jaccard medio con gli
altri due); AUC del basso accordo come segnale di fallimento. Nessuna soglia: serve a decidere se vale una prova.

## Scostamenti

(vuoto)
