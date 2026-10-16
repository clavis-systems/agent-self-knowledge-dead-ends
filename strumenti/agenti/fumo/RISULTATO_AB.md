# Fumo, prove A, B e C: risultato (15/10/2026)

Piano: PIANO_AB.md (commit d0792b8, congelato prima dei risultati). Dati: strumenti/risultati/fumo/ab_risultati.json.

## A. Il punto di arrivo (barando: con la soluzione vera)

| Agente | Arriva a un file giusto nei primi K passi | Fallisce se ci arriva / se non ci arriva | AUC del "quando ci arriva" |
|---|---|---|---|
| Claude Opus 4.5 (K 15) | 97% | 21% / 46% | 0,57 |
| Gemma 4 E4B (K 4) | 43% | 42% / 74% | 0,68 |
| Qwen3-Coder 30B (K 17) | 84% | 44% / 72% | 0,61 |
| Qwen3-Coder 480B (K 20) | 88% | 28% / 50% | 0,59 |

**Regola: non superata** (AUC almeno 0,65 in 1 agente su 4, ne servivano 3). A metà della corsa mediana: uguale.
Lettura: gli agenti grandi trovano quasi sempre il file giusto presto; il fallimento si decide dopo, nella
correzione. Anche sapendo la risposta, il primo terzo dice poco.

## B. Il fumo nel compito (prima di partire)

| Agente | B1 testo (8 indicatori + repository) | B2 testo + parole | Difficoltà stimata da persone (riferimento) |
|---|---|---|---|
| Claude Opus 4.5 | 0,62 | 0,59 | 0,65 |
| Qwen3-Coder 30B | 0,59 | 0,56 | 0,68 |
| Qwen3-Coder 480B | 0,61 | 0,59 | 0,68 |

**Regola: non superata** (media 0,61 e 0,58; serviva 0,70). Saltando compiti al 2% di successi persi si evitano solo
il 3–6% dei fallimenti. Nemmeno la stima umana della difficoltà arriva a 0,70.

## C. L'accordo tra esploratori (descrittivo)

AUC del basso accordo sui file guardati nei primi passi: 0,49 (Opus), 0,52 (Qwen 30B), 0,45 (Qwen 480B). Niente.

## Esplorative (decise dopo i risultati)

- **Lo scout:** la lunghezza della corsa di un altro agente sullo stesso compito prevede il fallimento meglio del
  testo: da 0,57 a 0,74. Nella direzione utile (agente economico che fa da esploratore per quello costoso): Qwen 30B
  verso Qwen 480B 0,65, verso Opus 0,57. L'esito dell'altro agente arriva fino a 0,82, ma richiede i test nascosti.
- **"La prova del nove"** (lo stesso comando fallisce prima della correzione e passa dopo): misurata così non
  compare quasi mai (1 corsa su 500), perché gli agenti ripetono i comandi con piccole variazioni. Misura fallita,
  non prova contraria.

## Ricalcolo indipendente

Fatto il 15/10 da un agente separato con codice proprio (senza ab.py, fumo.py, valuta_fumo.py): A (tutti e quattro
gli agenti, anche a metà corsa), difficoltà umana di B e lo scout esplorativo identici. **MATCH.** Note: le 272
corse di Gemma vengono da 77 compiti in 4 condizioni (intervallo per compito 0,60–0,76); per Qwen 30B l'intervallo
è 0,57–0,67, ma la regola usa il valore puntuale.
