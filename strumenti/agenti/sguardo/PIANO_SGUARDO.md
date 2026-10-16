# Secondo sguardo a mente fresca: piano del cancello (scritto prima di ogni risultato), 15/10/2026

Indizio dal mercato (RISULTATO_MERCATO.md): tra le correzioni che passano i test visibili, una domanda a mente
fresca a Gemma separava le 9 sbagliate con AUC 0,88. Troppi pochi casi. L'utente: "scarica e facciamo la prova".

## Dati

- HumanEval+ (EvalPlus, 164 funzioni, test molto più severi; esterni/humanevalplus, sha256 4436f5c0…).
- A: le 206 correzioni di Gemma su HumanEvalFix già giudicate nel mercato (stesse domande, stesse voci).
- B: soluzioni nuove: Gemma 4 E4B scrive ogni funzione da zero partendo da firma e docstring, 3 volte
  (temperatura 0,7, semi 1, 2, 3); una sola copia per testo identico.
- Per ogni soluzione: test visibili (gli esempi della docstring, humanevalpack "example_test") e test severi
  (HumanEval+). Tutto il codice gira solo nella sandbox WASM. L'aiuto numpy dei test severi è sostituito da una
  versione in Python puro con la stessa regola (tolleranza 1e-6 per i decimali, rtol 1e-7); gli altri aiuti del test
  restano. Si escludono i compiti in cui la soluzione ufficiale non passa i test severi qui (prova di fumo: il 32,
  find_zero, fallisce anche con la soluzione ufficiale).

## Giudici (come nel mercato)

Domanda a mente fresca, senza test: "Does the implementation do exactly what the docstring says, for all inputs?
Answer yes or no." Punteggio P(sì) − P(no). Gemma 4 E4B (giudica il proprio codice) e Qwen3 8B (codice altrui).

## Il caso che conta

Soluzioni che passano i test visibili: sono quelle per cui un agente direbbe "ho finito". Un "falso ho finito" è una
soluzione che passa i visibili e fallisce i severi.

## Cancello (fissato ora)

- Servono almeno 40 falsi "ho finito"; se sono meno, la prova è inconcludente (si aggiungono soluzioni).
- **Passa** se, tra le soluzioni che passano i visibili, il giudizio di Gemma separa i falsi "ho finito" con AUC
  almeno 0,75 **e** batte di almeno 0,10 il controllo stupido (la lunghezza del codice).
- Si riporta anche: con la soglia che trova metà dei falsi "ho finito", quante soluzioni buone vengono segnalate per
  errore; Qwen contro Gemma (giudicare il proprio codice contro quello altrui); A e B separati. Esplorativo.

## Scostamenti

(vuoto)
