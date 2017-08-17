#include <assert.h>
#include <pthread.h>

void my_no_return() __attribute__ ((__noreturn__));
extern void my_thread_safe_api();

pthread_mutex_t mutex;

static inline void my_mutex_lock1(){
  pthread_mutex_lock(&mutex);
  __assert_fail("assert", "file", 0, "function");
}

static inline void my_mutex_lock2(){
  pthread_mutex_lock(&mutex);
  my_no_return();
}

#define no_return_assert(n) \
	void good##n() {\
    my_mutex_lock1(&mutex); \
		my_thread_safe_api(); \
    pthread_mutex_unlock(&mutex); \
	}

#define no_return_attribute(n) \
	void good##n() {\
    my_mutex_lock2(&mutex); \
		my_thread_safe_api(); \
    pthread_mutex_unlock(&mutex); \
	}

// belief
no_return_assert(1)
no_return_assert(2)
no_return_assert(3)
no_return_assert(4)
no_return_assert(5)
no_return_assert(6)
no_return_assert(7)
no_return_assert(8)
no_return_attribute(9)
no_return_attribute(10)
no_return_attribute(11)
no_return_attribute(12)
no_return_attribute(13)
no_return_attribute(14)


int good15() {
  my_thread_safe_api();
}

