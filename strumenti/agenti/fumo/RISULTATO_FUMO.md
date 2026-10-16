# Fumo: risultato (15/10/2026)

Piano: PIANO_FUMO.md (commit c5078bb, congelato prima dei punteggi). Dati: strumenti/risultati/fumo/
(fumo_passi.jsonl, fumo_risultati.json). 1.761 corse ancora in corso al punto di controllo: Opus 489 (106
fallimenti), Gemma 272 (163), Qwen 30B 500 (242), Qwen 480B 500 (152).

## Esito secondo il piano

| Punto di vista | AUC sull'agente lasciato fuori (Opus / Gemma / Qwen 30B / Qwen 480B) | Promettente? | Traguardo |
|---|---|---|---|
| B0, quota di errori (base) | 0,46 / 0,40 / 0,52 / 0,54 | — | 0 agenti su 4 |
| V1, rallentamento critico | 0,49 / 0,38 / 0,50 / 0,47 | no (media −0,02 rispetto a B0) | 0 su 4 |
| V2, esploratore senza scoperte | 0,43 / 0,54 / 0,51 / 0,51 | no (+0,02) | 0 su 4 |
| V3, valori normali | 0,50 / 0,55 / 0,45 / 0,48 | no (+0,02) | 0 su 4 |
| V4, segnali nel parlato | — / 0,54 / 0,52 / 0,50 | no (+0,03) | 0 su 3 |

0,5 = caso. **Nessun punto di vista è promettente e nessuno si avvicina al traguardo.** Su Gemma V2, V3 e V4
battono B0 con intervalli che escludono lo zero, ma solo perché B0 lì va al contrario (0,40); da soli restano a
0,54–0,55. Esplorativo, metà della corsa mediana: AUC tra 0,38 e 0,57, traguardo 0 su 4.

## Esplorative (decise dopo aver visto i risultati; non cambiano l'esito)

- **Il problema non è il passaggio tra agenti.** Anche allenando e provando sullo stesso agente (5 parti), gli
  stessi indicatori danno AUC tra 0,42 e 0,61. Nei primi 30–50% di una corsa tipica, da fuori, non si vede quasi
  niente dell'esito.
- **Il segnale arriva tardi.** La lunghezza totale della corsa distingue fallimenti e successi (AUC 0,73 Qwen 30B,
  0,68 Qwen 480B, 0,71 Opus, 0,58 Gemma): chi fallisce gira più a lungo, ma lo si sa solo alla fine. Questo
  controllo dice anche che dati ed esiti sono letti bene.
- **Il fumo sembra stare nel compito, non nel lavoro.** Sugli stessi 500 compiti: quando Qwen 30B riesce, Qwen 480B
  fallisce solo il 4% delle volte; quando Qwen 30B fallisce, il 58%. Quando Opus fallisce, Qwen 30B fallisce
  nell'85% dei casi (contro il 37% quando Opus riesce). Il fallimento dipende soprattutto da quanto è difficile il
  compito. Pista per una prova nuova, con un piano scritto prima: prevedere il fallimento **prima di partire**,
  dal compito.

## Lavori vicini (ricerca veloce di un agente separato, 8 ricerche, letti per lo più gli abstract; da verificare)

- Rallentamento critico applicato agli agenti: non trovato (NEW). Novità d'azione, ritmo normale, segnali nel
  parlato: in parte già studiati (StuckDetector di OpenHands, OAT 2607.12747, SELFDOUBT 2604.06389).
- Coerente con il nostro risultato: in altri lavori la differenza tra corse riuscite e fallite è nulla fino a metà
  corsa (Lee 2026, 2602.19008) e le prove del fallimento compaiono dopo il 59–84% della corsa (Baidya 2026,
  2606.05414).
- Il più vicino all'obiettivo: "Fail-Fast, Restart-Smart" (2608.03222), un piccolo modello da 0,6B allenato che
  legge il testo della corsa: risparmia il 15–20% dei token fermando al massimo il 5% dei successi. Ancora lontano
  dal traguardo di questo piano.

## Ricalcolo indipendente

Fatto il 15/10 da un agente separato con codice proprio (senza fumo.py e valuta_fumo.py): punti di controllo,
corse e fallimenti identici; AUC degli indicatori grezzi tra 0,45 e 0,60 per ogni agente (nessun segnale precoce
utile); lunghezza totale e tabella sugli stessi compiti identiche. **MATCH.** Note del ricalcolo: per Qwen quasi
tutte le corse (468–479 su 500) non ripetono nessuna azione nei primi passi, quindi V2 lì non può distinguere;
per fermare metà dei fallimenti perdendo il 2% dei successi servirebbe un'AUC di circa 0,93.
