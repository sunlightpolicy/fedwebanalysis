#!/bin/bash
screen -S url_collect_cms python sitemap_url_scraper_cms.py $1 $2 $3 $4 $5
screen -S url_collect_cms -X quit