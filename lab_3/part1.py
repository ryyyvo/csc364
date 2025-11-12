import threading 
from queue import Queue
import time

def sum_of_squares(numbers, q, thread_id):
    total = sum(num ** 2 for num in numbers)
    q.put((thread_id, total))

def thread_sum_of_squares(numbers, num_threads):
    q = Queue()
    chunk_size = len(numbers) // num_threads
    chunks = []
    
    for i in range(num_threads):
        start_idx = i * chunk_size
        if i == num_threads - 1:
            end_idx = len(numbers)
        else:
            end_idx = start_idx + chunk_size
        chunks.append(numbers[start_idx:end_idx])
    
    threads = []
    for i, chunk in enumerate(chunks):
        thread = threading.Thread(
            target=sum_of_squares,
            args=(chunk, q, i)
        )
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    total_sum = 0
    while not q.empty():
        thread_id, partial_sum = q.get()
        total_sum += partial_sum
    
    return total_sum

def main():
    numbers = list(range(1, 1000001))
    num_threads = 4
    start_time = time.time()
    result = thread_sum_of_squares(numbers, num_threads)
    end_time = time.time()

    print(f"Result: {result}")
    print(f"Time taken: {end_time - start_time} seconds")

if __name__ == "__main__":
    main()