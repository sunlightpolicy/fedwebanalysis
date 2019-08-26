import csv
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from web_monitoring import internetarchive
import xml.etree.ElementTree as ET
import sys
from web_monitoring import internetarchive
import time
import smtplib
import paramiko
import os
import subprocess
import re

# set up connection to ec2
key = paramiko.RSAKey.from_private_key_file(".ssh/sun_key.pem") # putting link to pem file on the first instance itself??
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# private ip of the controlling EC2
scanner_private_ip = '172.30.0.69'

# Define an output set to output sys.stdout.write to
results = []

later = set()
not_recorded = set()
seen_both = set()
seen_url = set()
#python sitemap_url_scraper_ice.py "[2016,1,1,2017,1,19]" "https://www.ice.gov" "ice_urls.csv" "ice_403_postpose.csv" "ice_all_urls.csv"

# outputs boolean whether WayBack archive in requested range exists
def wayback_exist (url, dates):
    #print("Inside simplify function")    
    try:
        with internetarchive.WaybackClient() as client:
            # sys.stdout.write("inside wayback\n")
            # sys.stdout.flush()
            
            # print("made it internetarchive")
            # dump returns ALL instances within the date-range that page has been documented in the Archive
            # list_versions calls the CDX API from internetarchive.py from the webmonitoring repo

            dump = client.list_versions(url, from_date=datetime(dates[0], dates[1], dates[2]), to_date=datetime(dates[3], dates[4], dates[5]))

            # sys.stdout.write("dump worked\n")
            # sys.stdout.flush()
 
            # get the versions if Archive contains data in the requested range
            try:
                versions = list(dump)
                return True
            except:
                # sys.stdout.write("inner try failed\n")
                # sys.stdout.flush()
                #print("inner try failed")
                return False
        
    except: 
        # sys.stdout.write("outer try failed\n")
        # sys.stdout.flush()
        return False


# returns boolean if domain matches interest
def desired_domain (url, domain):
    #print("Inside desired_domain function")
    #print("domain: " + domain + "\n")
    return (url [0 : (url.find(".gov") + 4)] == domain)


# returns a simplified url
def simplify (url):
    #print("Inside simplify function")
    #print(url)
    if ('?language=' in url):
        url = url [0 : (url.find("?language="))]

    if ('?page=' in url): 
        url = url [0 : url.find("?page=")]
            
    if ('.html#' in url):
        url = url [0 : (url.find(".html#") + 5)]
    
    #print(url + "\n")
    return url

# returns whether url should be discared or not
def desired (url):
    #print("Inside desired method")
    
    IGNORED_EXTENSIONS = [
        # images
        'mng', 'pct', 'bmp', 'gif', 'jpg', 'jpeg', 'png', 'pst', 'psp', 'tif',
        # 'tiff', 'ai', 'drw', 'dxf', 'eps', 'ps', 'svg',
    
        # audio
        'mp3', 'wma', 'wav'
        # 'ogg','ra', 'aac', 'mid', 'au', 'aiff',
    
        # video
        'mp4', 'mpg', 'swf', 'wmv','m4a', 'm4v',
        #'qt', 'rm','3gp', 'asf', 'asx', 'avi', 'mov', 'flv',
    
        # office suites
        'xls', 'xlsx', 'ppt', 'pptx', 'pps', 'doc', 'docx'
        # 'odt', 'ods', 'odg','odp',
    
        # other
        'css', 'pdf', 'exe', 'bin', 'rss', 'zip', 'rar',
    ]
    
    DENIED = ["plugins", 'farsi', "espanol", "spanish", "chinese", "vietnamese",
        "korean", "tagalog", "russian", "arabic", "creole", "french",
        "portugese", "polish", "japanese", "italian", "german"
    ]
    
    if ( (url == '') or (len(url) < 2) or (url[0] == '#') or (url[1] == '/') or (url[0] == '?') ):
        #print("inside False 1\n")
        return False
    elif any(unwanted_term in url for unwanted_term in DENIED):
        #print("inside False 2\n")
        return False
    elif any(unwanted_term in url for unwanted_term in IGNORED_EXTENSIONS):
        #print("inside False 3\n")
        return False
    else:
        #print("inside True\n")
        return True


# fix format
def fix_format (url, domain): # if it is a link such as "/....."
    #print("Inside fix_format function")
    #print(url)
    if (url[0] == '/'):
        url = domain+url # add the prefix of the main domain
    #print(url + "\n")
    return url

# find depth and stop search if greater than a particular depth
def URLDepth (url):
    if (url.count('/') > 8):
        return False
    else:
        return True


# checks the url and returns whether worth searching or not
def check (url, canonical_url, dates, domain):
    global seen_both
    
    #print("Inside check function")
    # lowercase everything
    url = url.lower()
    
    # if it a domain we want
    if ( desired_domain(url, domain) ):

        #sys.stdout.write("URLDepth domain: " + str(URLDepth(url)) + "\n")
        #sys.stdout.flush()
        
        # determine if depth is okay
        if (URLDepth(url)):

            # if it doesn't have undesired key terms
            if ( desired(url) ):
                # simplify the url
                url = simplify( fix_format(url, domain) )    
                
                # if we haven't seen either the canonical nor url forms 
                if ( ((canonical_url in seen_both) == False) and ((url in seen_both) == False) ):
    
                    #print("unseen url")

                    # sys.stdout.write("wayback exist: " + str(wayback_exist(url, dates)) +"\n")
                    # sys.stdout.flush()
                    
                    # if the wayback page exists
                    if ( wayback_exist(url, dates) ):
                        #print("wayback exists\n")
                        #print("wayback exists")
                        return {'go_ahead': True, 'url': url, 'canonical_url': canonical_url}

                    # else:
                        #sys.stdout.write("wayback does not exist\n")
                        # sys.stdout.flush()

                # else:
                    # sys.stdout.write("seen")
                    # sys.stdout.flush()

            # else:
                # sys.stdout.write("undesired depth: " + str(URLDepth(url)))
                # sys.stdout.flush()

    # else:
        # sys.stdout.write("undesired url: " + url)
        # sys.stdout.flush()
        
    #print("no wayback or not worth considering\n")                 
    return {'go_ahead': False, 'url': url, 'canonical_url': canonical_url}         

# run file: python sitemap_url_scraper_cms.py "[2016,1,1,2017,1,19]" "https://www.ice.gov" "ice_urls.csv" "ice_403_postpose.csv" "ice_all_urls.csv"
if __name__ == '__main__':
#def main():
    dates = sys.argv[1].replace('[', ' ').replace(']', ' ').replace(',', ' ').split() # dates = [2016,1,1,2017,1,19]
    dates = [int(i) for i in dates]
    domain = sys.argv[2] # url = https://www.nih.gov/; domain = "https://www.hhs.gov"
    output_file = sys.argv[3] # output_file = 'hhs_urls.csv'
    postpone_file = sys.argv[4] # postpone_file = "ice_403_postpose.csv"
    excluded_file = sys.argv[5] # excluded_file = "ice_all_urls.csv"

    endings = ["sitemap-Research-Statistics-Data-and-Systems.xml",
               "sitemap-Regulations-and-Guidance.xml",
               "sitemap-Outreach-and-Education.xml",
               "sitemap-OpenPayments.xml",
               "sitemap-Newsroom.xml",
               "sitemap-mmrr.xml",
               "sitemap-Medicare-Medicaid-Coordination.xml",
               "sitemap-Medicare.xml",
               "sitemap-Center.xml",
               "sitemap-CCIIO.xml",
               "sitemap-About-CMS.xml"]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246'}

    for p in range(len(endings)):
        # acquire sitemap information
        r = requests.get(domain + "/" + endings[p], headers=headers) 
        xml_text = r.text
        #xml_text = urllib.request.urlopen(r).read()
        ET_text = ET.fromstring(xml_text)

        
        for i in range(len(ET_text)):
        #t0 = time.time()
        # for i in range(10):
            #print("here1")
            url_to_search = str(ET_text[i][0].text)
            #print(url_to_search) ########################################
            results.append(url_to_search + "\n")
            sys.stdout.write(url_to_search + "\n")
            #sys.stdout.flush()

            try:
                time.sleep(.510)
                r = requests.get(url_to_search, headers=headers)
                status = r.status_code

                results.append("status: " + str(status) + "\n")
                sys.stdout.write("status: " + str(status) + "\n")
                #sys.stdout.flush()

                if (status == 403):
                    later.add(url)
                elif (status != 404):
                    # real url
                    url = (r.url).lower()

                    results.append(url + "\n")
                    sys.stdout.write(url + "\n")
                    #sys.stdout.flush()
                    
                    # get the html
                    raw_html = r.content
                    
                    # parse the data with soup
                    soup = BeautifulSoup(raw_html, 'html.parser')
                           
                    # get canonical url
                    links = soup.find_all('link', rel='canonical')
                    canonical_url = url
                    
                    if (len(links) > 0):
                            for link in links:
                                canonical_url = link['href']
                        
                    # determine whether we need to search the url
                    [go_ahead, url, canonical_url] = check(url, canonical_url, dates, domain).values()
                            
                # add the terms to relevant lists, saying we've seen them
                seen_both.update([url, canonical_url, url_to_search])
						
                if go_ahead:
                    results.append("go ahead\n\n")
                    sys.stdout.write("go ahead\n\n")
                    #sys.stdout.flush()
                    seen_url.add(url)
                else:
                    results.append("NOT PROCEEDING\n\n")
                    sys.stdout.write("NOT PROCEEDING\n\n")
                    #sys.stdout.flush()
                    not_recorded.add(url)

            except:
                #print("failed")
                not_recorded.add(url)
                results.append("failed\n\n")
                sys.stdout.write("failed\n\n")
                #sys.stdout.flush()
        # t1 = time.time()
        # sys.stdout.write("ten urls: " + str(t1-t0) + "\n")
        
    # write everything in seen_url to csv of analyzed
    with open(output_file,'w') as output:
        writer=csv.writer(output, delimiter=',', lineterminator='\n',)
        for link in seen_url:
            writer.writerow([link]) # write it to the wayback existing urls
    output.close()

    with open(postpone_file,'w') as output:
        writer=csv.writer(output, delimiter=',', lineterminator='\n',)
        for link in later:
            writer.writerow([link]) # write it delayed urls
    output.close()

    with open(excluded_file,'w') as output:
        writer=csv.writer(output, delimiter=',', lineterminator='\n',)
        for link in not_recorded:
            writer.writerow([link]) # write it to excluded
    output.close()

    dom = re.search('https://www.(.*).gov', domain).group(1)

    sys_output_file = "scraped_urls_" + str(dom) + "_output.csv"

    # create an output file of messages
    with open(sys_output_file,'w', newline='') as output: # append the site to the crawled url
        writer=csv.writer(output)
        for item in results:
            writer.writerow([item])
    output.close()    

    # TRANSFER SYS_OUTPUT FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    filepath_dest = os.path.join(r"/home/ec2-user/uploads", str(output_file))
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(sys_output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANSFER OUTPUT FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    filepath_dest = os.path.join(r"/home/ec2-user/uploads", str(output_file))
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANFER POSTPONE FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    filepath_dest = os.path.join(r"/home/ec2-user/uploads", str(output_file))
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(postpone_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANFER EXCLUDED FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    filepath_dest = os.path.join(r"/home/ec2-user/uploads", str(output_file))
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(excluded_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # connect/ssh to an instance
    #try:
    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
    client.connect(hostname="54.166.131.120", username="ec2-user", pkey=key) # putting the information of the other instance??

    sys.exit()
