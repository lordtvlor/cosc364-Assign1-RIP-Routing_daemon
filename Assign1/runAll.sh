#!/bin/bash

trap "pkill -f routing_daemon.py" EXIT

python3 routing_daemon.py Configs/con_1.txt &
python3 routing_daemon.py Configs/con_2.txt &
python3 routing_daemon.py Configs/con_3.txt &
python3 routing_daemon.py Configs/con_4.txt &
python3 routing_daemon.py Configs/con_5.txt &
#python3 routing_daemon.py Configs/con_6.txt &
python3 routing_daemon.py Configs/con_7.txt

wait