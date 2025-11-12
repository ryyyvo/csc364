import multiprocessing
from multiprocessing import Queue
import time

def sum_of_squares(numbers, q, process_id):
    total = sum(num ** 2 for num in numbers)
    q.put((process_id, total))

def multiprocessing_sum_of_squares(numbers, num_processes):
    q = Queue()
    chunk_size = len(numbers) // num_processes
    chunks = []
    
    for i in range(num_processes):
        start_idx = i * chunk_size
        if i == num_processes - 1:
            end_idx = len(numbers)
        else:
            end_idx = start_idx + chunk_size
        chunks.append(numbers[start_idx:end_idx])
    
    processes = []
    for i, chunk in enumerate(chunks):
        process = multiprocessing.Process(
            target=sum_of_squares,
            args=(chunk, q, i)
        )
        processes.append(process)
        process.start()
    
    for process in processes:
        process.join()
    
    total_sum = 0
    while not q.empty():
        process_id, partial_sum = q.get()
        total_sum += partial_sum
    
    return total_sum

def main():
    numbers = list(range(1, 1000001))
    num_threads = 4
    start_time = time.time()
    result = multiprocessing_sum_of_squares(numbers, num_threads)
    end_time = time.time()

    print(f"Result: {result}")
    print(f"Time taken: {end_time - start_time} seconds")

if __name__ == "__main__":
    main()