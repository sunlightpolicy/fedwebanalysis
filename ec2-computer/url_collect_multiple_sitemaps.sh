#!/bin/bash
screen -S url_collect_mul python sitemap_url_scraper_multiple_sitemaps.py $1 $2 $3 $4 $5 $6
screen -S url_collect_mul -X quit