# Mercato dei pensieri: risultato del cancello (15/10/2026, 21:30-21:40)

Piano: PIANO_MERCATO.md (commit 0529def; correzione di lettura dichiarata, 833e805). Dati: strumenti/risultati/mercato/.
206 correzioni diverse di Gemma su HumanEvalFix (160 giuste, 46 sbagliate secondo i test nascosti), 144 compiti.
Ricontato da un agente separato con codice proprio: MATCH.

| Segnale (AUC, giusta = positivo) | Valore |
|---|---|
| Voce Gemma 4 E4B ("è giusta? sì/no") | 0,78 |
| Voce Qwen3 8B | 0,81 |
| Mercato semplice (media delle due voci) | 0,82 |
| Mercato con memoria (pesi imparati, 5 parti per compito) | 0,78 |
| Controllo stupido: passano i test visibili? | 0,88 |
| Test visibili + mercato con memoria | 0,94 |

**Cancello: NON passa.** Condizione 1 no: unire le voci non batte la voce migliore (servivano almeno 0,84).
Condizione 2 sì: le voci aggiungono informazione a ciò che dicono i test visibili (+0,06).

## Esplorativo (da confermare)

Tra le correzioni che passano i test visibili (162, di cui 9 sbagliate davvero), la domanda a mente fresca a Gemma
separa le 9 sbagliate dalle giuste con AUC 0,88 (Qwen 0,75). Sono solo 9 casi: è un indizio, non un risultato.
Lettura: il "mercato" in sé non serve; un secondo sguardo a mente fresca, alla fine, sembra smascherare alcuni falsi
"ho finito" che i test visibili non vedono. Il giudice con un modello linguistico è un campo molto studiato: prima
di una prova vera serve il controllo di cosa esiste.
