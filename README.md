# fedwebanalysis

A Flask-based website and Python scripts automating web analysis on federal government domains for the Sunlight Foundation's Web Integrity Project. The website is designed to be hosted on an AWS EC2 instance, which calls Python programs to run on another AWS EC2 instance, and stores output onto a Google Drive account. This site structure flows from what capacities AWS provides in its free student account, so `fedwedanalysis` will work on a AWS Free Tier.

It is recommended reaching the EC2 instances via Putty and FileZilla.

## Flask EC2

* Contains `templates` folder, with HTML files of the website.
* Contains `static` folder, with CSS file of the website.
* Contains an   `uploads` folder.
* Contains your access `.pem` file for the computing instance inside your `.ssh` folder
* Contains `app.py`, `helpers.py`, and `client_secrets.json` file (from your Google OAuth access)

## Computing EC2

* Contains domain specific scraping Python programs
* Contains term finding Python program adapted highly from [Eric Nost's EDGI controlf.py](https://github.com/ericnost/EDGI)
* Contains term aggregating Python program conceptually adapted from [Eric Nost's EDGI termcount.R](https://github.com/ericnost/EDGI)
* Contains web_monitoring folder with two files `internetarchive.py` and `utils.py` taken from [a component of EDGI's Web Monitoring Project](https://github.com/edgi-govdata-archiving/web-monitoring-processing)
* Contains bash files for running each Python program
* Contains your access `.pem` file for the Flask instance inside your `.ssh` folder
