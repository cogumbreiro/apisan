# Makefile for testcase

SRCS = $(wildcard *.c)
OBJS = $(SRCS:.c=.o)

%o: %c
	$(CC) $(CFLAGS) -c -o $@ $<

all: $(OBJS)

test:
	../../apisan build make
	../../apisan check --checker=intovfl

clean:
	rm -rf $(OBJS)
	rm -rf as-out

.PHONY: all test clean
