# Mercato dei pensieri: piano del cancello veloce (scritto prima di ogni risposta), 15/10/2026

L'utente: "procedi ora". Idea: piccole voci scommettono se una correzione finita è giusta; la scommessa combinata
(il "mercato") deve dire se ci si può fidare di un agente che dice "ho finito".

## Dati (già sul PC)

Le correzioni finali di Gemma su HumanEvalFix con l'esito vero dei test nascosti: corse di ottobre (cartella
prova_gemma/prova, condizioni off e on) e corse di oggi (sogno/1a e sogno/giorno2). Si tiene una sola coppia per
(compito, testo finale identico). Per ogni coppia: la specifica (firma e docstring dal dataset), la funzione finale
estratta dal file (se il file non si legge, il file intero), l'esito dei test nascosti.

## Le voci (temperatura 0, una chiamata senza memoria per coppia)

Gemma 4 E4B (gemma4:e4b-it-qat) e Qwen3 8B (qwen3:8b), entrambe già sul PC, senza ragionamento visibile. Domanda:
"Does the implementation do exactly what the docstring says, for all inputs? Answer yes or no." Punteggio =
P(sì) − P(no) dalle probabilità del primo token (i primi 20, tutte le grafie). Le voci non vedono i test.

## Il controllo "stupido" (decisivo)

Passano i test di esempio visibili? Si eseguono sulla funzione finale nella sandbox WASM: è quello che chiunque
può fare senza nessuna voce.

## Misure

AUC (successo = positivo) di: ogni voce; mercato semplice (media delle due voci standardizzate); mercato con memoria
(regressione logistica sulle due voci, 5 parti divise per compito); test visibili; test visibili + mercato con
memoria (stesso schema).

## Cancello (fissato ora)

**Passa** se valgono entrambe:
1. il mercato con memoria supera la voce migliore di almeno 0,03 di AUC (unire le voci serve);
2. test visibili + mercato superano i soli test visibili di almeno 0,03 di AUC (le voci aggiungono qualcosa a ciò
   che si sa già eseguendo i test).
Se no: il mercato, così, non serve; si cambia idea.

## Limiti noti

Un solo banco di piccole funzioni; le correzioni sono tutte di Gemma (anche Gemma giudica se stessa); un solo
passaggio per voce (le probabilità a temperatura 0 cambiano poco tra le corse).

## Scostamenti

- 15/10, prima di ogni risposta delle voci: corretto un errore di lettura (nei file sogno/giorno2 il campo
  "task" contiene "Python/N"; il numero del compito ora si prende dal nome del file). Nessun altro cambiamento.
