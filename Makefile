# Makefile ---

# Author: David Ochoa <ochoa@ebi.ac.uk>

ROOTDIR := $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))

DOCSDIR= $(ROOTDIR)/docs
SRCDIR= $(ROOTDIR)/src
TMPDIR = $(ROOTDIR)/temp

#Paths
REPORT = $(DOCSDIR)/index.html

# Programs
R ?= $(shell which R)
RSCRIPT ?= $(shell which Rscript)

report: $(REPORT)

figures:
	$(RSCRIPT) $(SRCDIR)/figures.R

clean-report:
	-rm $(REPORT)

clean-report-all:
	-rm $(REPORT)
	-rm -rf $(DOCSDIR)/report_files
	-rm -rf $(TMPDIR)/report_cache

$(TMPDIR):
	mkdir -p $@

$(DOCSDIR):
	mkdir -p $@

#Report
$(REPORT): $(TMPDIR) $(DOCSDIR)
	$(RSCRIPT) \
	-e "setwd('$(SRCDIR)')" \
	-e "cachePath <- '$(TMPDIR)'" \
	-e "rmarkdown::render('report.rmd', knit_root_dir='$(SRCDIR)', encoding = 'UTF-8',output_file = '$@')"