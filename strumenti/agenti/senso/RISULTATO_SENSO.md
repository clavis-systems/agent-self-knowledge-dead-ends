# Il senso costruito al bisogno: risultato del cancello (16/10/2026, 16:37-17:05)

Piano: PIANO_SENSO.md (commit e3200fb). Dati: strumenti/risultati/senso/ (proprieta.jsonl, esiti.jsonl,
senso_risultati.json). Nota: i compiti con almeno una soluzione nel gruppo sono 155, non 163 come scritto nel piano;
il metodo non cambia.

- Gemma ha scritto controlli validi (sintassi giusta) per 117 compiti su 155; per gli altri 38 il senso non si è
  costruito (119 soluzioni senza controllo).
- Sulle 507 soluzioni che passano i test visibili (40 "falsi ho finito", 467 buone):

| | Falsi "ho finito" trovati | Buone segnalate per errore |
|---|---|---|
| Senso costruito | 20 su 40 (50%) | 161 su 467 (34%) |
| Giudice a mente fresca, alla stessa quota di errori | 27 su 40 | 161 |
| Filtro di consenso (esplorativo) | 8 su 40 (20%) | 9 su 467 (2%) |

**Cancello: NON passa** (falsi allarmi 34%, il limite era 10%). Spesso sono i controlli a essere sbagliati: Gemma
scrive proprietà o risultati attesi falsi. Il giudice a parole, a parità di falsi allarmi, trova di più (27 contro 20).

Esplorativo: togliendo i controlli che falliscono su tutte le soluzioni di un compito, restano 17 segnalazioni, di cui
8 giuste (47%, contro il 7,9% di partenza): una "spia" precisa ma che vede poco. Sono pochi casi: solo un indizio.

## Ricalcolo indipendente

Fatto il 16/10 da un agente separato con codice proprio: tutti i conteggi identici (507, 40, 467, 117 su 155, 119
senza controllo, 20 trovati, 161 falsi allarmi; filtro: 8 e 9). L'agente segnala una questione di definizione, non
un errore: le quote del filtro sono calcolate su tutte le 467 buone e tutti i 40 falsi (i compiti scartati dal
filtro non segnalano nulla). Contando solo i compiti tenuti dal filtro: 9 su 315 buone (2,9%) e 8 su 28 falsi.
