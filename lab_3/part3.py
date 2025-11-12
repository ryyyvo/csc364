import part1
import part2
import threading
import multiprocessing
import time
import queue

def io_worker(iterations, q, worker_id):
    total = 0
    for i in range(iterations):
        time.sleep(0.02)
        total += i
    q.put((worker_id, total))


def threaded_io_bound(iterations, num_threads):
    q = queue.Queue()
    threads = [threading.Thread(target=io_worker, args=(iterations, q, i)) 
               for i in range(num_threads)]
    
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    
    return sum(q.get()[1] for _ in range(num_threads))


def multiprocessing_io_bound(iterations, num_processes):
    q = multiprocessing.Queue()
    processes = [multiprocessing.Process(target=io_worker, args=(iterations, q, i)) 
                 for i in range(num_processes)]
    
    for process in processes:
        process.start()
    for process in processes:
        process.join()
    
    return sum(q.get()[1] for _ in range(num_processes))


def main():
    cpu_data = list(range(1, 1000001))
    num_workers = 4
    io_iterations = 50

    print("\nCPU Bound:")

    start = time.time()
    part1.thread_sum_of_squares(cpu_data, num_workers)
    thread_cpu_time = time.time() - start
    print(f"Threads: {thread_cpu_time:.4f}s")
    
    start = time.time()
    part2.multiprocessing_sum_of_squares(cpu_data, num_workers)
    process_cpu_time = time.time() - start
    print(f"Processes: {process_cpu_time:.4f}s")

    print("\nI/O Bound:")

    start = time.time()
    threaded_io_bound(io_iterations, num_workers)
    thread_io_time = time.time() - start
    print(f"Threads: {thread_io_time:.4f}s")
    
    start = time.time()
    multiprocessing_io_bound(io_iterations, num_workers)
    process_io_time = time.time() - start
    print(f"Processes: {process_io_time:.4f}s")

if __name__ == "__main__":
    main()