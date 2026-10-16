# L'alveare: risultato del cancello (16/10/2026, 18:50)

Piano: PIANO_ALVEARE.md (commit f2d6a82). Dati: strumenti/risultati/alveare/alveare_risultati.json. Simulazione sui 3
tentativi registrati di Gemma per ognuna delle 163 funzioni di HumanEval (compito 32 escluso). Ricontato da un agente
separato con codice proprio: MATCH (163 compiti, P1 137, V 143 con 1,282 tentativi, ORACOLO 145).

| Strategia | Risolti su 163 | Tentativi medi | Quota del tetto della fortuna |
|---|---|---|---|
| P1, un solo tentativo | 137 (84,0%) | 1,00 | — |
| V, riprova se i test visibili falliscono (controllo stupido) | 143 (87,7%) | 1,28 | 75% |
| ALVEARE (riprova anche se il giudice dubita) | 143 (87,7%) | 1,68 | 75% |
| P3, sempre 3 tentativi | 143 (87,7%) | 3,00 | 75% |
| ORACOLO (basta un tentativo giusto su 3) | 145 (89,0%) | 3,00 | tetto |

**Cancello: NON passa.** Il dubbio del giudice non salva nessun compito in più del controllo stupido e costa più
tentativi; il tetto della fortuna qui è piccolo (8 compiti) e riprovare quando i test visibili falliscono ne prende già 6.

Nota del ricontrollo: in 12 tentativi (compiti 38, 41, 50, 83, 84, 119) i test severi passano mentre i visibili no o
restano incerti (il 119 è incerto in tutti i tentativi): imperfezioni della misura dei test visibili. Contandoli in
modo più severo i numeri scendono tutti di 6 (P1 131, V 137, ORACOLO 139); la conclusione non cambia.
