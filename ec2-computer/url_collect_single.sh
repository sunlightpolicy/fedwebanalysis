#!/bin/bash
screen -S url_collect_single python sitemap_url_scraper.py $1 $2 $3 $4 $5
screen -S url_collect_single -X quit