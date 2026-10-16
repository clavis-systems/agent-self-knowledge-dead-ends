# L'alveare (la fortuna come risorsa): piano del cancello (scritto prima di ogni risultato), 16/10/2026

L'utente: "procedi con la 1". Idea: quasi metà dei fallimenti di un modello piccolo sparisce riprovando. Una colonia
di tentativi non riprova dappertutto: riprova solo dove "danza" il dubbio (i test visibili falliscono, oppure il
giudice a mente fresca è incerto) e così trasforma il caso in precisione spendendo poco.

## Dati (nessuna nuova corsa del modello)

Le soluzioni della prova "secondo sguardo", parte B: Gemma 4 E4B ha scritto da zero ogni funzione di HumanEval 3 volte
(semi 1, 2, 3, temperatura 0,7). Per ogni tentativo: test visibili, test severi di HumanEval+ (l'esito vero), punteggio
del giudice di Gemma. 164 compiti, il 32 escluso: 163. I 37 tentativi senza codice valido contano come falliti.

## Strategie (i tentativi si usano nell'ordine dei semi)

- P1: un solo tentativo.
- V, il controllo stupido: riprova solo se i test visibili falliscono; restituisce il primo tentativo che li passa.
- ALVEARE: si ferma solo se i test visibili passano **e** il giudice non dubita (punteggio almeno pari alla soglia);
  altrimenti riprova, fino a 3. Restituisce il primo tentativo che passa i visibili senza dubbio; altrimenti quello
  che passa i visibili con il punteggio più alto; altrimenti il primo. Soglia del dubbio, fissata senza guardare gli
  esiti: il 25° percentile dei punteggi del giudice tra i tentativi che passano i visibili.
- P3: sempre 3 tentativi (riferimento). ORACOLO: basta che uno dei 3 sia giusto (il tetto della fortuna).

Misure: quota di compiti risolti (test severi), tentativi medi, e quanto del tetto della fortuna si cattura:
(risolti − P1) / (ORACOLO − P1).

## Cancello (fissato ora)

**Passa** se valgono entrambe:
1. l'ALVEARE cattura almeno l'80% del tetto della fortuna con al massimo 1,6 tentativi in media;
2. l'ALVEARE risolve almeno 2 punti percentuali in più del controllo stupido V (circa 3 compiti su 163).

## Limiti noti

Simulazione su tentativi già fatti (stesso risultato di una corsa vera, perché i tentativi sono indipendenti); un solo
modello e compiti piccoli; 163 compiti.

## Scostamenti

(vuoto)
