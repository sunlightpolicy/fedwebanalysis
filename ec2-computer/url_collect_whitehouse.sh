#!/bin/bash
screen -S url_collect_wh python sitemap_url_scraper_whitehouse.py $1 $2 $3 $4 $5
screen -S url_collect_wh -X quit