# lndg
Lite GUI web interface to analyze lnd data and manage your node with automation.

## Setup
1. Run bitcoind
2. Run lnd
3. Build required python file for your system to interact with lnd grpc (rpc + router), instructions here: [here](https://github.com/lightningnetwork/lnd/blob/master/docs/grpc/python.md#setup-and-installation)
4. Clone respository
5. Place the 4 output files from step 3 inside the repository at `lndg/gui/`
6. Due to some parts running as a web app and some as standalone the following is also required:<br />
  a. Make copy of `rpc_pb2_grpc.py`, naming it `rpc_pb2_grpc_jobs.py` within the same folder.<br />
  b. Rename `router_pb2.py`, naming it `router_pb2_rebalancer.py`.<br />
  c. Rename `router_pb2_grpc.py`, naming it `router_pb2_grpc_rebalancer.py`.<br />
  d. Replace `import rpc_pb2 as rpc__pb2` with `from . import rpc_pb2 as rpc__pb2` in the following file: `rpc_pb2_grpc.py` <br />
8. A settings file is required at lndg/settings.py (default django setting file + 'gui' + 'rest_framework' + 'qr_code' added to your installed apps inside the file) - generate your own or use the default one from the django github repo [here](https://github.com/django/django/blob/main/django/conf/project_template/project_name/settings.py-tpl)
9. Make migrations and migrate all database objects (python manage.py makemigrations && python manage.py migrate)
10. Run the server via chosen webserver or via python development server (python manage.py runserver IP:PORT)

## Backend Data Refreshes
The file `jobs.py` inside lndg/gui/ serves to update the backend database with the most up to date information.  This reduces the amount of calls made when a user refreshes the front end and enables the rest api usage to fetch data from your lnd node.

You will need to setup a systemd/crontab (linux) or task scheduler (windows) to run this file at your specified refresh interval.  A refresh of 15-60 seconds is advisable for the best experience and may depend on how quickly your machine is capable of handling the file execution.

## Automated Rebalancing
The file `rebalancer.py` inside lndg/gui/ serves to rebalance any channels that meet the specifications set on your lndg dashboard.  Default values are set upon the first run of the rebalancer file.  You can review this file to find the default values.

You will need to setup a systemd/crontab (linux) or task scheduler (windows) to run this file at your specified refresh interval.  A refresh of 15-60 seconds is advisable for the best experience and may depend on how quickly your machine is capable of handling the file execution.

## API Backend
The following data can be accessed at the /api endpoint: `payments`, `invoices`, `forwards`, `channels`, and `rebalancer`

## Preview Screens
![image](https://user-images.githubusercontent.com/38626122/132701345-7129e4e5-09b8-483e-96eb-bf003171ed3f.png)
![image](https://user-images.githubusercontent.com/38626122/132701473-33611c23-cb91-4496-a9ee-c276f1b35f34.png)
![image](https://user-images.githubusercontent.com/38626122/132701498-5cefa10f-00b3-45e3-9a38-e6512d47b750.png)
![image](https://user-images.githubusercontent.com/38626122/132701518-41e585ae-bac3-413b-a6a2-c202e20fd7f9.png)
![image](https://user-images.githubusercontent.com/38626122/132701532-a129f74f-ee6e-4f03-89c8-e82eef775ab1.png)

### Opens In Separate Screens
![image](https://user-images.githubusercontent.com/38626122/132701553-bbab3f27-ac72-4de6-9591-506c6740579b.png)
![image](https://user-images.githubusercontent.com/38626122/132861336-3cb02cad-2b09-4548-8186-a93b2482c40d.png)

