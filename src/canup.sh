#!/bin/bash
# Script to make setting can up/down easier

sudo ip link set can0 down
echo "can0 set down!"

while getopts "l:" opt; do
    case "$opt" in
    l)
        sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on
        echo "can0 set up with loopback off!"
        ;;
    :)
        sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on loopback on
        echo "can0 set up with loopback on!"
        ;;
    esac
done