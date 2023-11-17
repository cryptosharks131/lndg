import django, multiprocessing
from datetime import datetime
from gui.lnd_deps import lightning_pb2_grpc as lnrpc
from gui.lnd_deps.lnd_connect import lnd_connect
from os import environ
from time import sleep
environ['DJANGO_SETTINGS_MODULE'] = 'lndg.settings'
django.setup()
from gui.models import LocalSettings
from trade import serve_trades

def trade():
    stub = lnrpc.LightningStub(lnd_connect())
    serve_trades(stub)

def check_setting():
    if LocalSettings.objects.filter(key='LND-ServeTrades').exists():
        return int(LocalSettings.objects.filter(key='LND-ServeTrades')[0].value)
    else:
        LocalSettings(key='LND-ServeTrades', value='0').save()
        return 0

def main():
    while True:
        current_value = None
        try:
            while True:
                    db_value = check_setting()
                    if current_value != db_value:
                        if db_value == 1:
                            print(f"{datetime.now().strftime('%c')} : [P2P] : Starting the p2p service...")
                            django.db.connections.close_all()
                            p2p_thread = multiprocessing.Process(target=trade)
                            p2p_thread.start()
                        else:
                            if 'p2p_thread' in locals() and p2p_thread.is_alive():
                                print(f"{datetime.now().strftime('%c')} : [P2P] : Stopping the p2p service...")
                                p2p_thread.terminate()
                    current_value = db_value
                    sleep(2)  # polling interval
        except Exception as e:
            print(f"{datetime.now().strftime('%c')} : [P2P] : Error running p2p service: {str(e)}")
        finally:
            if 'p2p_thread' in locals() and p2p_thread.is_alive():
                print(f"{datetime.now().strftime('%c')} : [P2P] : Removing any remaining processes...")
                p2p_thread.terminate()       
            sleep(20)

if __name__ == '__main__':
    main()