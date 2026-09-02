# ORCID → Awesome-CV

Genera automaticamente sezioni LaTeX di Awesome-CV a partire dai dati pubblici
di un record ORCID. Usa solo la libreria standard di Python.

## 1. Prerequisiti

- Python 3.10 o successivo;
- XeLaTeX;
- `awesome-cv.cls` e la cartella `font/` del progetto Awesome-CV nella stessa
  directory, oppure Awesome-CV già disponibile nella propria installazione TeX;
- credenziali gratuite per la ORCID Public API.

Le credenziali si creano da **ORCID → Developer tools → Register for the free
ORCID public API**. Non inserire mai il secret nei sorgenti o nel repository.

## 2. Configurazione

```bash
export ORCID_CLIENT_ID='APP-...'
export ORCID_CLIENT_SECRET='...'
```

Personalizzare nome, recapiti e ORCID iD nell'intestazione di `cv.tex`.

## 3. Generazione

```bash
python3 generate_cv.py --orcid 0000-0000-0000-0000 --out generated
xelatex cv.tex
```

Oppure:

```bash
make pdf ORCID_ID=0000-0000-0000-0000
```

Il comando `make update` conserva anche `orcid-record.json`, utile come copia
locale e per diagnosticare eventuali campi mancanti.

## Uso offline

```bash
python3 generate_cv.py --record-json orcid-record.json --out generated
```

## Classificazione del servizio editoriale

ORCID espone le voci di servizio in un contenitore comune. Lo script identifica
quelle editoriali tramite ruolo, dipartimento e organizzazione. È possibile
aggiungere termini specifici:

```bash
python3 generate_cv.py --orcid 0000-0000-0000-0000 \
  --editorial-keyword caporedattore --editorial-keyword periodico
```

## Privacy e limiti

La Public API restituisce soltanto elementi con visibilità pubblica. Le
asserzioni equivalenti possono essere raggruppate da ORCID; lo script usa la
prima voce di ciascun gruppo per evitare duplicati. I file dentro `generated/`
sono rigenerati a ogni aggiornamento e non vanno modificati manualmente.
