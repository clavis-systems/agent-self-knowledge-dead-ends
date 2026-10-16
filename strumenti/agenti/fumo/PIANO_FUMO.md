# Fumo: piano della prova (scritto prima di calcolare qualsiasi punteggio), 15/10/2026

## Domanda e traguardo (dell'utente)

Guardando solo da fuori l'inizio del lavoro di un agente di programmazione, si può prevedere se fallirà? Traguardo
detto all'utente: con qualunque agente e modello, fermare in tempo almeno metà dei tentativi destinati a fallire,
perdendo al massimo 2 successi su 100.

## Dati (già sul PC, nessun download)

| Agente | Corse | Esito | Cosa si vede |
|---|---|---|---|
| Qwen3-Coder 30B (OpenHands, SWE-bench Verified) | 500 | risolto o no (results.json) | chiamate, risultati, testo dell'agente |
| Qwen3-Coder 480B (idem) | 500 | idem | idem |
| Claude Opus 4.5 (OpenHands, SWE-bench Verified) | 489 | idem | solo i risultati degli strumenti (niente testo, niente chiamate) |
| Gemma 4 E4B (studio "chi legge la mappa", 84 compiti di prova x 4 condizioni) | 312 | funzione esatta trovata o no | chiamate, risultati, testo |

Gemma: solo i compiti con una definizione d'oro. Fallimento = non risolto (comprese le corse senza patch).

Onestà: lo studio di ottobre ha già mostrato su Qwen 30B/480B che le corse con una modifica "a vuoto" risolvono
meno (vicino al punto di vista 2). Per fissare il punto di controllo ho guardato solo le lunghezze delle corse,
senza gli esiti.

## Punto di controllo

K = max(4, arrotondato(0,3 x lunghezza mediana delle corse di quell'agente)): Qwen 30B 17 passi, Qwen 480B 20,
Opus 15, Gemma 4. Si valutano solo le corse ancora in corso dopo K passi. Secondario (esplorativo): 0,5 x mediana.

## Cosa si misura nei primi K passi (fumo.py estrae i passi, valuta_fumo.py calcola e valuta)

Un passo = una chiamata a uno strumento. "Nuovo" = un'azione mai fatta prima nella corsa (stessa chiamata con gli
stessi argomenti; per Opus, stesso risultato). "Errore" = risultato d'errore (codice d'uscita diverso da 0, errore
dell'editor, testo d'errore per Opus, errore o lista vuota per Gemma).

- **B0, base ovvia:** quota di errori.
- **V1, rallentamento critico:** tempo medio per riprendersi dopo un errore (passi fino alla prima azione nuova);
  quanto cresce questo tempo dalla prima alla seconda metà della finestra; quanto cresce l'autocorrelazione della
  serie "nuovo sì/no" dalla prima alla seconda metà.
- **V2, esploratore senza scoperte:** quota di azioni nuove; quota nell'ultimo terzo; ripetizione massima di
  un'azione.
- **V3, valori normali:** distanza del "ritmo" della corsa (quote di lettura, ricerca, modifica, esecuzione, altro;
  lunghezza media dei risultati) dal ritmo mediano di quello stesso agente, senza usare gli esiti.
- **V4, segnali nel parlato:** frequenza di scuse, ripensamenti, "proviamo un altro approccio" nel testo
  dell'agente. Non disponibile per Opus.

Ogni misura è standardizzata dentro ogni agente (media e deviazione di tutte le sue corse, senza esiti).

## Valutazione: lascia fuori un agente alla volta

Per ogni punto di vista, regressione logistica sui suoi indicatori, allenata sugli altri agenti e provata
sull'agente lasciato fuori. Soglia scelta sugli agenti di allenamento: al massimo 2% dei loro successi fermati.

- AUC sull'agente lasciato fuori (fallimento = positivo); intervallo al 95% della differenza con B0 (1.000
  ricampionamenti delle corse).
- Fallimenti fermati, successi persi, quota dei passi risparmiati.

## Regole di decisione (fissate ora)

- Un punto di vista è **promettente** se l'AUC media sugli agenti lasciati fuori supera B0 di almeno 0,05 e la
  supera in almeno 3 agenti su 4 (V4: 2 su 3).
- Il **traguardo** è raggiunto da un punto di vista se su ogni agente lasciato fuori ferma almeno il 50% dei
  fallimenti perdendo al massimo il 2% dei successi. Si riporta anche su quanti agenti.
- Esplorativo, senza decisioni: tutti gli indicatori insieme; punto di controllo a metà della mediana.

## Limiti noti

Le corse di Gemma non sono indipendenti (stessi compiti in 4 condizioni); per Opus si vedono solo i risultati;
gli errori per Opus si riconoscono dal testo. Un solo set di compiti per gli agenti grandi (SWE-bench Verified).

## Scostamenti

(vuoto)
