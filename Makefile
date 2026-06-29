# resume-builder/Makefile
# ========================
# Convenience targets wrapping build.py
#
# Usage:
#   make ds                          # Build Data Scientist base resume
#   make da                          # Build Data Analyst base resume
#   make ae                          # Build Analytics Engineer base resume
#   make de                          # Build Data Engineer base resume
#   make mle                         # Build ML Engineer base resume
#   make econ                        # Build Economist base resume
#   make all                         # Build all six base resumes
#   make ds-games                    # Build DS resume in games-industry mode
#   make posting F=data_scientist P=postings/acme/posting.txt
#   make posting-games F=data_scientist P=postings/ea/posting.txt
#   make pdf F=data_scientist        # Build + compile to PDF
#   make validate                    # Validate YAML without building
#   make clean                       # Remove all generated output

PYTHON  := python3
BUILD   := $(PYTHON) build.py
OUTDIR  := output

# Optional gaming flag — surfaces the gaming-specific domain_knowledge
# skill blocks (DA/DS/AE) for video-games postings. Enable with GAMING=1, e.g.
#   make da GAMING=1
#   make posting F=data_analyst P=postings/Electronic_Arts/Advanced_Analyst_Apex.txt GAMING=1
GAMINGFLAG := $(if $(GAMING),--gaming)

# Optional pass-through variables (set on the make command line as KEY=value)
#   INDUSTRY   — games | agnostic         (default: agnostic)
#   EDU        — full | condensed         (--education-mode)
#   CERTS      — education | aside | omit (--certs-placement)
#   TEMPLATE   — standard | ats           (default: standard; ATS = single-column)
#   LOC        — default | relocate | us  (--location-mode; header location signal)
#   CITY       — city name string         (--relocation-city; e.g. "San Francisco")
#
# Example:
#   make posting F=analytics_engineer P=postings/Microsoft/posting.txt \
#        INDUSTRY=games EDU=condensed CERTS=omit TEMPLATE=ats \
#        LOC=us CITY=Redmond

_INDUSTRY_FLAG  := $(if $(INDUSTRY),--industry $(INDUSTRY),)
_EDU_FLAG       := $(if $(EDU),--education-mode $(EDU),)
_CERTS_FLAG     := $(if $(CERTS),--certs-placement $(CERTS),)
_TEMPLATE_FLAG  := $(if $(TEMPLATE),--template $(TEMPLATE),)
_LOC_FLAG       := $(if $(LOC),--location-mode $(LOC),)
_CITY_FLAG      := $(if $(CITY),--relocation-city "$(CITY)",)
_EXTRA          := $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG) $(_TEMPLATE_FLAG) $(_LOC_FLAG) $(_CITY_FLAG)

.PHONY: all da ae de ds mle econ \
        da-games ae-games de-games ds-games mle-games econ-games \
        da-ats ae-ats de-ats ds-ats mle-ats econ-ats \
        posting posting-games posting-ats pdf posting-pdf validate clean install help

## Base resume targets — one per family
## Optional: INDUSTRY=games  EDU=condensed  CERTS=omit
da:
	$(BUILD) --family data_analyst $(_EXTRA)

ae:
	$(BUILD) --family analytics_engineer $(_EXTRA)

de:
	$(BUILD) --family data_engineer $(_EXTRA)

ds:
	$(BUILD) --family data_scientist $(_EXTRA)

mle:
	$(BUILD) --family ml_engineer $(_EXTRA)

econ:
	$(BUILD) --family economist $(_EXTRA)

## Build all six base resumes
all:
	$(BUILD) --all $(GAMINGFLAG)

## Games-industry variants — GAMES bullet variants + games summary + games revoicing persona
## These hard-code --industry games; EDU and CERTS pass-throughs still work.
da-games:
	$(BUILD) --family data_analyst --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

ae-games:
	$(BUILD) --family analytics_engineer --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

de-games:
	$(BUILD) --family data_engineer --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

ds-games:
	$(BUILD) --family data_scientist --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

mle-games:
	$(BUILD) --family ml_engineer --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

econ-games:
	$(BUILD) --family economist --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

## ATS-friendly single-column variants — uses cv-style-ats.cls + resume-ats.tex.j2
## Hard-codes --template ats; INDUSTRY/EDU/CERTS pass-throughs still work.
da-ats:
	$(BUILD) --family data_analyst --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

ae-ats:
	$(BUILD) --family analytics_engineer --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

de-ats:
	$(BUILD) --family data_engineer --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

ds-ats:
	$(BUILD) --family data_scientist --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

mle-ats:
	$(BUILD) --family ml_engineer --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

econ-ats:
	$(BUILD) --family economist --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

## Build against a specific posting
## Usage: make posting F=data_scientist P=postings/acme/posting.txt [INDUSTRY=games] [EDU=condensed] [CERTS=omit]
posting:
ifndef F
	$(error F is required — usage: make posting F=<family> P=<posting_path>)
endif
ifndef P
	$(error P is required — usage: make posting F=<family> P=<posting_path>)
endif
	$(BUILD) --family $(F) --posting $(P) $(_EXTRA)

## Build posting in games-industry mode (shorthand for INDUSTRY=games)
## Usage: make posting-games F=data_scientist P=postings/ea/posting.txt [EDU=condensed] [CERTS=omit]
posting-games:
ifndef F
	$(error F is required — usage: make posting-games F=<family> P=<posting_path>)
endif
ifndef P
	$(error P is required — usage: make posting-games F=<family> P=<posting_path>)
endif
	$(BUILD) --family $(F) --posting $(P) --industry games $(_EDU_FLAG) $(_CERTS_FLAG)

## Build posting in ATS-friendly layout (shorthand for TEMPLATE=ats)
## Usage: make posting-ats F=analytics_engineer P=postings/acme/posting.txt [INDUSTRY=games] [EDU=condensed] [CERTS=omit]
posting-ats:
ifndef F
	$(error F is required — usage: make posting-ats F=<family> P=<posting_path>)
endif
ifndef P
	$(error P is required — usage: make posting-ats F=<family> P=<posting_path>)
endif
	$(BUILD) --family $(F) --posting $(P) --template ats $(_INDUSTRY_FLAG) $(_EDU_FLAG) $(_CERTS_FLAG)

## Build + compile to PDF
## Usage: make pdf F=data_scientist [INDUSTRY=games] [EDU=condensed] [CERTS=omit]
pdf:
ifndef F
	$(error F is required — usage: make pdf F=<family>)
endif
	$(BUILD) --family $(F) --pdf $(_EXTRA)

## Build posting + compile to PDF
## Usage: make posting-pdf F=data_scientist P=postings/acme/posting.txt
posting-pdf:
ifndef F
	$(error F is required)
endif
ifndef P
	$(error P is required)
endif
	$(BUILD) --family $(F) --posting $(P) --pdf $(_EXTRA)

## Validate YAML integrity
validate:
	$(BUILD) --validate

## Remove all generated .tex and .pdf files
clean:
	find $(OUTDIR) -name "*.tex" -delete
	find $(OUTDIR) -name "*.pdf" -delete
	find $(OUTDIR) -name "*.aux" -delete
	find $(OUTDIR) -name "*.log" -delete
	find $(OUTDIR) -name "*.fls" -delete
	find $(OUTDIR) -name "*.fdb_latexmk" -delete
	find postings   -name "resume_*.tex" -delete
	find postings   -name "resume_*.pdf" -delete
	@echo "Cleaned generated files."

## Install Python dependencies (uses uv if available, falls back to pip)
install:
	@if command -v uv >/dev/null 2>&1; then \
		uv pip install -r requirements.txt; \
	else \
		pip install -r requirements.txt; \
	fi

help:
	@echo ""
	@echo "  Resume Builder — available targets"
	@echo "  ─────────────────────────────────"
	@echo "  make da              				Build Data Analyst base resume"
	@echo "  make ae              				Build Analytics Engineer base resume"
	@echo "  make de              				Build Data Engineer base resume"
	@echo "  make ds              				Build Data Scientist base resume"
	@echo "  make mle             				Build ML Engineer base resume"
	@echo "  make econ            				Build Economist base resume"
	@echo "  make all             				Build all six base resumes"
	@echo "  make posting F=<f> P=<path>   		Build against a job posting"
	@echo "  make pdf F=<f>       				Build + compile to PDF"
	@echo "  add GAMING=1         				Surface gaming domain-knowledge blocks (DA/DS/AE)"
	@echo "  make da|ae|de|ds|mle|econ          Build base resume for a family"
	@echo "  make all                            Build all six base resumes"
	@echo "  make ds-games                       Build DS resume in games-industry mode"
	@echo "  make da-games|ae-games|...          (all families have -games variants)"
	@echo "  make ds-ats                         Build DS resume in ATS-friendly layout"
	@echo "  make da-ats|ae-ats|...              (all families have -ats variants)"
	@echo "  make posting-games F=<f> P=<path>   Build posting in games-industry mode"
	@echo "  make posting-ats F=<f> P=<path>     Build posting in ATS-friendly layout"
	@echo "  make pdf F=<f>                      Build + compile to PDF"
	@echo "  make validate                       Validate YAML content"
	@echo "  make clean                          Remove generated files"
	@echo "  make install                        Install Python dependencies"
	@echo ""
	@echo "  Optional KEY=value overrides (append to any target):"
	@echo "    INDUSTRY=games            Use games-industry framing"
	@echo "    EDU=condensed             Condense education section"
	@echo "    CERTS=omit|aside          Move or drop certifications"
	@echo "    TEMPLATE=ats              ATS-friendly single-column layout"
	@echo "    LOC=relocate|us           Header location: add relocation/US-eligibility signal"
	@echo "    CITY=\"<name>\"             Override relocation city (default: Vancouver / Seattle)"
	@echo ""
	@echo "  Example:"
	@echo "    make posting F=analytics_engineer P=postings/Microsoft/posting.txt \\"
	@echo "         INDUSTRY=games EDU=condensed CERTS=omit TEMPLATE=ats \\"
	@echo "         LOC=us CITY=Redmond"
	@echo ""
