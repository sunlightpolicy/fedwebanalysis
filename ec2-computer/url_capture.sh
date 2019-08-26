#!/bin/bash
screen -S url_capture python url_capture.py $1
screen -S url_capture -X quit