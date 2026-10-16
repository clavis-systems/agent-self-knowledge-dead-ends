# Istinto e sogno: piano a cancelli (scritto prima di ogni risultato), 15/10/2026

L'utente: "uniamo 2 e 1 … mi serve qualcosa dove già dei test veloci iniziali ci dicono se siamo sulla strada giusta,
altrimenti cambiamo". Quindi prove brevi in fila; ogni cancello ha una soglia scritta qui; se un cancello resta
chiuso ci si ferma su quella strada.

## Idea

- **Istinto (di giorno):** il programma misura tre "emozioni" mentre l'agente lavora e, quando una scatta, gli
  scrive una reazione. Disagio: i test falliscono due volte di fila dopo una modifica. Noia: l'agente ripete
  un'azione identica o risponde due volte di fila senza usare strumenti. Fatica: 12 chiamate su 20 senza aver finito.
- **Sogno (di notte):** su ogni compito fallito l'agente rilegge il suo errore (il codice finale e l'errore dei test
  nascosti) e scrive una sola lezione generale. La lezione si tiene solo se, riprovando lo stesso compito con la
  lezione, lo risolve ("sogno verificato"). Il giorno dopo l'agente riceve le lezioni tenute.

## Banco di prova

HumanEvalFix Python (164 bug in funzioni, test nascosti, sandbox WASM), con l'agente Gemma 4 E4B già usato a ottobre
(strumenti/agenti/modifiche/agente_gemma.py, congelato dbb70bc7, 20 chiamate, temperatura 0, seme 1). Le corse di
ottobre senza avvisi ("off", compiti 20–163) sono il "giorno 0": 144 compiti, 27 falliti. Si usa solo quel che serve
per scegliere i compiti; nessun dato dei compiti di ottobre 0–19.

- I 27 falliti, mescolati con il seme "istinto-sogno-2026-10-15": i primi 13 = **D1** (su cui si sogna), gli altri 14 =
  **D2** (compiti nuovi del giorno dopo). **S2** = 14 compiti risolti a ottobre, scelti a caso con lo stesso seme
  (controllo dei danni).
- Ogni condizione si esegue di nuovo nella stessa sessione, anche BASE, perché Ollama può non ripetere esattamente le
  risposte di ottobre.

## Cancelli e soglie

0. **Il segnale c'è?** (solo processore, corse di ottobre) Per ogni emozione: in quante corse scatta con almeno 5
   chiamate rimaste, e quante di quelle falliscono. **Passa** un'emozione che scatta in almeno il 10% delle corse e,
   quando scatta, la corsa fallisce almeno nel 50% dei casi (in media fallisce il 19%). Se nessuna passa, l'istinto
   così com'è non si prova dal vivo.
1a. **Il sogno insegna qualcosa?** (13 compiti D1) Lezione scritta da Gemma, poi due nuovi tentativi: con la lezione
   e senza. **Passa** se i compiti risolti con la lezione superano quelli risolti senza di almeno 4. Se no, il sogno
   si ferma qui: non insegna nemmeno sullo stesso compito.
1b. **La lezione si trasferisce?** (solo se 1a passa; D2 + S2) BASE contro SOGNO (tutte le lezioni verificate nel
   messaggio iniziale). **Passa** se SOGNO salva almeno 4 compiti D2 più di BASE e ne rompe al massimo 2 di S2.
   Zona grigia: +2 o +3, si allarga la prova a tutti i compiti prima di decidere.
2. **L'istinto aiuta dal vivo?** (solo se il cancello 0 passa per almeno un'emozione; D2 + S2) BASE contro ISTINTO,
   con le reazioni solo per le emozioni che hanno passato il cancello 0. Stessa soglia di 1b.
3. **Insieme** (solo se 1b e 2 passano): ISTINTO + SOGNO contro BASE, almeno +6 su D2, danni al massimo 2.

## Reazioni dell'istinto (testo fissato ora)

- Disagio: "[Host] The tests failed twice in a row after your edit. Stop and re-read the docstring and the failing
  line. Write in one sentence what the function must do differently, then fix it."
- Noia: "[Host] You are repeating yourself. Try a different approach: view the function again and change your plan."
- Fatica: "[Host] You have used 12 of 20 calls. Focus the remaining calls on the single most likely fix, then run
  the tests."

## Limiti noti

Pochi compiti (cancelli veloci, non prove conclusive); un solo modello; compiti piccoli e indipendenti (le lezioni
devono essere generali per trasferirsi). Un cancello aperto giustifica una prova più grande con un piano nuovo.

## Scostamenti

- 15/10, 20:30, dopo il cancello 1a (passato: 8 su 13 con la lezione, 3 su 13 senza) e PRIMA di ogni corsa del giorno
  2: aggiunta una condizione esplorativa PLACEBO (8 consigli generici scritti da me, non ricavati da nessun errore;
  testo in istinto_sogno.py, PLACEBO_TIPS). Motivo: molte lezioni del sogno sono generiche ("rileggi la
  descrizione"), quindi va separato l'effetto del sogno da quello di un consiglio di attenzione. La decisione del
  cancello 1b resta BASE contro SOGNO, come fissato. Il cancello 2 (istinto dal vivo) è chiuso dal cancello 0.
