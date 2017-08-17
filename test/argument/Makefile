# Makefile for testcase

SRCS = $(wildcard *.c)
OBJS = $(SRCS:.c=.o)

TPL = python3 ../run.py

all: test

report: report.in
	$(TPL) $< > $@

test: report.out
	../../apisan compile main.c
	../../apisan check --checker=args --skip-cache | diff report.out -

clean:
	rm -rf $(OBJS)
	rm -rf as-out

.PHONY: all test clean
