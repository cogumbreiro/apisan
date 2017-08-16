#include <assert.h>
#include <pthread.h>

#define SIZE 16

pthread_mutex_t mutex;
static inline void my_mutex_lock(){
  pthread_mutex_lock(&mutex);
  __assert_fail("assert", "file", 0, "function");
}

extern void my_thread_safe_api();

#define good(n) \
	void good##n() {\
    my_mutex_lock(&mutex); \
		my_thread_safe_api(); \
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


int good11() {
  my_thread_safe_api();
}

