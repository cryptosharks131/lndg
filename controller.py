import multiprocessing, sys
import jobs, rebalancer, htlc_stream, p2p, manage

def run_task(task):
    task()

def main():
    tasks = [jobs.main, rebalancer.main, htlc_stream.main, p2p.main]
    print('Controller is starting...')

    processes = []
    for task in tasks:
        process = multiprocessing.Process(target=run_task, name=task.__module__, args=(task,))
        processes.append(process)
        process.start()

    if len(sys.argv) > 1:
        sys.argv[0] = "manage.py"
        process = multiprocessing.Process(target=manage.main(sys.argv), name="manage.py")
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    print('Controller is stopping...')

if __name__ == '__main__':
    main()
