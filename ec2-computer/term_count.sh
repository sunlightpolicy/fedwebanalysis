#!/bin/bash
screen -S term_count python term_counter.py $1 $2 $3 $4 $5 $6 $7
screen -S term_count -X quit