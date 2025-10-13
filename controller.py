import multiprocessing, sys
import jobs, rebalancer, htlc_stream, p2p, manage
import logging
logger = logging.getLogger('[Controller]')

def run_task(task):
    task()

def main():
    tasks = [jobs.main, rebalancer.main, htlc_stream.main, p2p.main]
    logger.info('Starting all LNDg processes...')

    processes = []
    for task in tasks:
        process = multiprocessing.Process(target=run_task, name=task.__module__, args=(task,))
        processes.append(process)
        process.start()

    if len(sys.argv) > 1:
        sys.argv[0] = 'manage.py'
        process = multiprocessing.Process(target=manage.main(sys.argv), name='manage.py')
        processes.append(process)
        process.start()

    for process in processes:
        process.join()
    logger.info('Stopping all LNDg processes...')

if __name__ == '__main__':
    main()
