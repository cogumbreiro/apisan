#include <stdlib.h>
#include <pthread.h>

pthread_mutex_t mutex;
#define SIZE 16

#define good(n) \
	void good##n() {\
    pthread_mutex_lock(&mutex); \
		void *ptr = malloc(SIZE);\
    pthread_mutex_unlock(&mutex); \
	}

// belief
good(1)
good(2)
good(3)
good(4)
good(5)
good(6)
good(7)
good(8)
good(9)
good(10)

void bad() {
	void *ptr = malloc(SIZE);
  free(ptr);
}
