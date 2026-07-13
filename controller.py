import multiprocessing, sys, time
from datetime import datetime
import jobs, rebalancer, htlc_stream, p2p, manage
import logging
logger = logging.getLogger('[Controller]')

def run_task(task):
    task()

def main():
    logger.info('Starting all LNDg processes...')

    tasks_spec = {
        'jobs': (run_task, (jobs.main,)),
        'rebalancer': (run_task, (rebalancer.main,)),
        'htlc_stream': (run_task, (htlc_stream.main,)),
        'p2p': (run_task, (p2p.main,))
    }

    if len(sys.argv) > 1:
        sys.argv[0] = 'manage.py'
        # Pass sys.argv as args to manage.main to avoid blocking parent execution
        tasks_spec['manage.py'] = (manage.main, (sys.argv,))

    running_tasks = {}

    for name, (target, args) in tasks_spec.items():
        process = multiprocessing.Process(target=target, name=name, args=args)
        process.start()
        running_tasks[name] = {
            'target': target,
            'args': args,
            'process': process,
            'last_started': time.time(),
            'consecutive_failures': 0,
            'backoff_until': 0.0
        }

    try:
        while True:
            current_time = time.time()
            for name, info in running_tasks.items():
                process = info['process']
                
                # Check if the process is currently dead (it was running, but has stopped)
                if process.pid is not None and not process.is_alive() and info['backoff_until'] == 0.0:
                    exitcode = process.exitcode
                    uptime = current_time - info['last_started']
                    
                    if uptime < 10.0:
                        info['consecutive_failures'] += 1
                    else:
                        info['consecutive_failures'] = 0

                    backoff_delay = min(2 ** info['consecutive_failures'], 60)
                    info['backoff_until'] = current_time + backoff_delay
                    
                    logger.error(
                        f"Process {name} died (exitcode: {exitcode}, uptime: {uptime:.1f}s). "
                        f"Restarting in {backoff_delay}s (consecutive failures: {info['consecutive_failures']})."
                    )
                    
                    # Instantiate new Process object
                    info['process'] = multiprocessing.Process(target=info['target'], name=name, args=info['args'])
                
                # If a process is not running (e.g. it just died or is waiting on backoff), and backoff time has passed, start it.
                if info['process'].pid is None and current_time >= info['backoff_until']:
                    logger.info(f"Restarting process {name}...")
                    info['process'].start()
                    info['last_started'] = time.time()
                    info['backoff_until'] = 0.0

            time.sleep(2)
    except KeyboardInterrupt:
        logger.info('Controller is stopping...')
        for name, info in running_tasks.items():
            if info['process'].is_alive():
                info['process'].terminate()

if __name__ == '__main__':
    main()

