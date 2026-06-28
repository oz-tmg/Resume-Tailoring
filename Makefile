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
#   make posting F=data_scientist P=postings/acme/posting.txt
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

.PHONY: all da ae de ds mle econ posting pdf validate clean help

## Base resume targets — one per family
da:
	$(BUILD) --family data_analyst $(GAMINGFLAG)

ae:
	$(BUILD) --family analytics_engineer $(GAMINGFLAG)

de:
	$(BUILD) --family data_engineer $(GAMINGFLAG)

ds:
	$(BUILD) --family data_scientist $(GAMINGFLAG)

mle:
	$(BUILD) --family ml_engineer $(GAMINGFLAG)

econ:
	$(BUILD) --family economist $(GAMINGFLAG)

## Build all six base resumes
all:
	$(BUILD) --all $(GAMINGFLAG)

## Build against a specific posting
## Usage: make posting F=data_scientist P=postings/acme/posting.txt
posting:
ifndef F
	$(error F is required — usage: make posting F=<family> P=<posting_path>)
endif
ifndef P
	$(error P is required — usage: make posting F=<family> P=<posting_path>)
endif
	$(BUILD) --family $(F) --posting $(P) $(GAMINGFLAG)

## Build + compile to PDF
## Usage: make pdf F=data_scientist
pdf:
ifndef F
	$(error F is required — usage: make pdf F=<family>)
endif
	$(BUILD) --family $(F) --pdf $(GAMINGFLAG)

## Build posting + compile to PDF
## Usage: make posting-pdf F=data_scientist P=postings/acme/posting.txt
posting-pdf:
ifndef F
	$(error F is required)
endif
ifndef P
	$(error P is required)
endif
	$(BUILD) --family $(F) --posting $(P) --pdf $(GAMINGFLAG)

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

## Install Python dependencies
install:
	pip install -r requirements.txt

help:
	@echo ""
	@echo "  Resume Builder — available targets"
	@echo "  ─────────────────────────────────"
	@echo "  make da              Build Data Analyst base resume"
	@echo "  make ae              Build Analytics Engineer base resume"
	@echo "  make de              Build Data Engineer base resume"
	@echo "  make ds              Build Data Scientist base resume"
	@echo "  make mle             Build ML Engineer base resume"
	@echo "  make econ            Build Economist base resume"
	@echo "  make all             Build all six base resumes"
	@echo "  make posting F=<f> P=<path>   Build against a job posting"
	@echo "  make pdf F=<f>       Build + compile to PDF"
	@echo "  add GAMING=1         Surface gaming domain-knowledge blocks (DA/DS/AE)"
	@echo "  make validate        Validate YAML content"
	@echo "  make clean           Remove generated files"
	@echo "  make install         Install Python dependencies"
	@echo ""
