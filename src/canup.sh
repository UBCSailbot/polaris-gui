#!/bin/bash
# Script to make setting can up/down easier

if [ "$#" -eq 0 ]; then
        sudo ip link set can0 down
        echo "can0 set down!"
        sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on loopback off
        echo "can0 set up with loopback off!"
fi

while getopts "l" opt; do
    case "$opt" in
    l)
        sudo ip link set can0 down
        echo "can0 set down!"
        sudo ip link set can0 up type can bitrate 500000 dbitrate 1000000 fd on loopback on
        echo "can0 set up with loopback on!"
        ;;
    ?)
        echo "usage: bash canup.sh [-l]"
        ;;
    esac
done

shift $((OPTIND - 1))

if [ "$#" -gt 0 ]; then 
    echo "usage: bash canup.sh [-l]"
fi