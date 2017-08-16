# Makefile for testcase

SRCS = $(wildcard *.c)
OBJS = $(SRCS:.c=.o)

%o: %c
	$(CC) $(CFLAGS) -c -o $@ $<

all: $(OBJS)

test:
	../../apisan build make
	../../apisan check --checker=cpair

clean:
	rm -rf $(OBJS)
	rm -rf as-out

.PHONY: all test clean
