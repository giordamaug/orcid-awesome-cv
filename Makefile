ORCID_ID ?= 0000-0000-0000-0000
PYTHON ?= python3

.PHONY: update pdf clean test

update:
	$(PYTHON) generate_cv.py --orcid "$(ORCID_ID)" --out generated --save-json orcid-record.json

pdf: update
	xelatex -interaction=nonstopmode -halt-on-error cv.tex
	xelatex -interaction=nonstopmode -halt-on-error cv.tex

test:
	$(PYTHON) -m unittest discover -s tests -v

clean:
	rm -f cv.aux cv.log cv.out cv.pdf
