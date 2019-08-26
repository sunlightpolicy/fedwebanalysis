#!/bin/bash
screen -S url_collect_st python sitemap_url_scraper_state.py $1 $2 $3 $4 $5
screen -S url_collect_st -X quit