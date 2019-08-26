#!/bin/bash
screen -S controlf python controlf.py $1 $2 $3 $4 $5 $6 $7
screen -S controlf -X quit