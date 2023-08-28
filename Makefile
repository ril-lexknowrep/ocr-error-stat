SHELL:=/bin/bash

I=tests/inputs
O=tests/outputs

CBZ_FILE=$I/2000Folyoirat_2000folyoirat_1989_04.cbz
CBZ_OUTPUT=$O/cbz_output.txt
PDF_FILE=$I/2000folyoirat_1989_04__pages1-50_recognized.pdf
CBZ_OUTPUT=$O/pdf_output.txt

process_cbz:
	python3 cbz_extract/restructure_json.py $(CBZ_FILE) $(CBZ_OUTPUT)

process_pdf:
	python3 pdf_extract/pdf_extract.py $(PDF_FILE) $(PDF_OUTPUT)
