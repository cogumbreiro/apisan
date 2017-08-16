#include <stdlib.h>
#include <pthread.h>

pthread_mutex_t mutex;
#define SIZE 16

inline void my_lock(pthread_mutex_t *mutex) {
  pthread_mutex_lock(&mutex);
}

inline void my_unlock(pthread_mutex_t *mutex) {
  pthread_mutex_unlock(&mutex);
}

#define good(n) \
	void good##n() {\
    my_lock(&mutex); \
		void *ptr = malloc(SIZE);\
    my_unlock(&mutex); \
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
