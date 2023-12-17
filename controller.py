import multiprocessing
import jobs, rebalancer, htlc_stream, p2p

def run_task(task):
    task()

def main():
    tasks = [jobs.main, rebalancer.main, htlc_stream.main, p2p.main]
    print('Controller is starting...')

    processes = []
    for task in tasks:
        process = multiprocessing.Process(target=run_task, args=(task,))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    print('Controller is stopping...')

if __name__ == '__main__':
    main()
