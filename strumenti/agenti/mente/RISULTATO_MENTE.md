# Leggere nella mente: risultato del cancello (16/10/2026, 17:06-17:11)

Piano: PIANO_MENTE.md (commit 65fe023). Dati: strumenti/risultati/mente/ (qwen_full.npy, qwen_code.npy,
mente_risultati_qwen.json). Stato interno di Qwen3 8B letto con llama.cpp (llama-server, ultimo strato, ultima
parola) dallo stesso file usato da Ollama; nessun download.

Tra le 507 soluzioni che passano i test visibili (40 falsi "ho finito"), AUC (giusta = positivo):

| Segnale | AUC |
|---|---|
| Rilevatore sullo stato interno (PCA 50 + logistica, 5 parti per compito) | 0,608 |
| Giudizio a parole dello stesso modello | 0,768 |
| Rilevatore + parole (esplorativo) | 0,699 |
| Controllo: stato interno del solo codice | 0,584 |
| Controllo: etichette mescolate | 0,413 |
| Controllo: lunghezza | 0,513 |

**Cancello: NON passa** (serviva almeno 0,818). Con l'ultimo strato e circa 600 esempi, leggere lo stato interno dice
meno che chiedere a parole.

Ricontrollo indipendente (agente separato, codice proprio, molte varianti del rilevatore: logistica e ridge, con e
senza PCA, varie penalità, 5 semi): AUC tra 0,50 e 0,72 (mediana 0,65), sempre sotto 0,75; parole 0,768; etichette
mescolate 0,49. **CONSISTENTE.** Limite: solo l'ultimo strato (gli studi che trovano più informazione dentro il
modello usano spesso gli strati intermedi, che questa versione di llama-server non espone) e pochi esempi negativi.
