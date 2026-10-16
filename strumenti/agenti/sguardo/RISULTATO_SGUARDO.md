# Secondo sguardo a mente fresca: risultato del cancello (15-16/10/2026)

Piano: PIANO_SGUARDO.md (commit 0a9b116). Dati: strumenti/risultati/sguardo/ (sguardo_risultati.json). Interrotto il
15/10 alle 22:31 su richiesta dell'utente e ripreso il 16/10 alle 16:17 con lo stesso codice (le parti fatte sono
state saltate, nessuna rifatta). Ricontato da un agente separato con codice proprio: MATCH.

- 597 soluzioni con esito (A: 206 correzioni HumanEvalFix; B: soluzioni scritte da zero da Gemma); escluso il compito 32.
- Passano i test visibili: 507. Di queste, **40 sono "falsi ho finito"** (falliscono i test severi di HumanEval+):
  A 22 su 161, B 18 su 346. Il minimo fissato (40) è raggiunto.

| Segnale tra le 507 (AUC, giusta = positivo) | Valore |
|---|---|
| Giudice Gemma 4 E4B a mente fresca | 0,725 |
| Giudice Qwen3 8B (esplorativo) | 0,768 |
| Controllo stupido: lunghezza del codice | 0,513 |

**Cancello: NON passa** (Gemma 0,725, serviva almeno 0,75; batte la lunghezza di più di 0,10). Per trovare metà dei
falsi "ho finito" con il giudizio di Gemma si segnalerebbero per errore 95 soluzioni buone su 467 (20%).

Note:
- L'indizio di ieri (0,88 su 9 casi) non regge con 40 casi: era in gran parte fortuna dei piccoli numeri.
- Per parte: Gemma A 0,72, B 0,67; Qwen A 0,68, B 0,77. Sul codice scritto da Gemma da zero (B) giudica meglio l'altro
  modello: l'idea "si conosce meglio da sola" non è sostenuta.
- Il ricalcolo nota che la lunghezza va in direzioni opposte nelle due parti (A 0,46, B 0,63): il valore complessivo
  0,51 non vuol dire che la lunghezza non conti. Su B il giudice di Gemma (0,67) batte di poco la lunghezza (0,63).
