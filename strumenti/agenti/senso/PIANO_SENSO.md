# Il senso costruito al bisogno: piano del cancello (scritto prima di ogni risultato), 16/10/2026

L'utente: "procedi con la 2 e poi la 1". Idea: quando l'agente dice "ho finito", si costruisce da solo un senso nuovo.
Leggendo solo la specifica (firma e docstring), mai la soluzione, scrive controlli che ogni soluzione giusta deve
superare, e li fa girare. Se un controllo fallisce, segnala "probabilmente sbagliata".

## Dati (gli stessi del secondo sguardo, nessun download)

Le 507 soluzioni che passano i test visibili (strumenti/risultati/sguardo/etichette.jsonl, compito 32 escluso), di cui
40 "falsi ho finito" (falliscono i test severi di HumanEval+) e 467 buone.

## Come (senso.py)

- Per ognuno dei 163 compiti, Gemma 4 E4B (temperatura 0, seme 1) scrive una funzione `check_properties(candidate)`:
  almeno 8 chiamate su ingressi scelti da lei, casi limite compresi, con `assert` su risultati certi o su relazioni
  tra ingresso e uscita. Vede solo la specifica, nessuna soluzione e nessun test.
- Il codice dei controlli si legge solo come testo sull'host (controllo della sintassi, nessuna esecuzione) e gira
  solo nella sandbox WASM, insieme a ogni soluzione. Segnalata = i controlli falliscono. Se il codice dei controlli
  non è valido, quel compito non ha il senso (nessuna segnalazione).
- Confronto: il giudice a mente fresca di Gemma (dal secondo sguardo), alla stessa quota di falsi allarmi.

## Cancello (fissato ora)

**Passa** se il senso costruito trova almeno la metà dei falsi "ho finito" (almeno 20 su 40) **e** segnala per
errore al massimo il 10% delle soluzioni buone (al massimo 46 su 467). Per confronto: il giudice, per trovarne metà,
ne segnalava per errore il 20%.

Esplorativo, senza decisioni: un filtro "di consenso" che toglie i controlli che falliscono su tutte le soluzioni
visibili di quel compito (2 o più), perché probabilmente sono i controlli a essere sbagliati (non usa la verità);
il confronto con il giudice alla stessa quota di falsi allarmi.

## Scostamenti

(vuoto)
