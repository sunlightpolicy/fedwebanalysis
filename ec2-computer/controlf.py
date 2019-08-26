#requirements
import csv
import numpy
import nltk
from nltk.corpus import stopwords
from nltk.collocations import *
from web_monitoring import internetarchive
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import sys
import smtplib
import paramiko
import os
import subprocess

# set up connection to ec2
key = paramiko.RSAKey.from_private_key_file(".ssh/sun_key.pem") # putting link to pem file on the first instance itself??
client_paramiko = paramiko.SSHClient()
client_paramiko.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# private ip of the controlling EC2
scanner_private_ip = '172.30.0.69'

# Define an output set to output sys.stdout.write to
results = []

# to run, in command line: python
# in python shell, compile first with: exec(open("controlf.py").read())
# to run: counter("test.csv", "counts_first.cvs", ['sex', 'gender', 'discrimination', 'discriminating', 'identity', 'stereotype', 'stereotyping'], [2016, 1,1,2017,1,1], "all")
# OR: counter("test.csv", "counts_first.cvs", ['sex', 'gender', 'discrimination', 'discriminating', 'identity', 'stereotype', 'stereotyping'], [2016, 1,1,2017,1,1], "last")


# if error relating to lxml when compiling, exit() python shell
# type into terminal: STATIC_DEPS=true sudo pip install lxml
# re-enter python shell
nltk.download("stopwords")
default_stopwords = set(nltk.corpus.stopwords.words('english'))
all_stopwords = default_stopwords

keywords = {}
final_urls={}

# counts single word terms from the decoded HTML
def count(term, visible_text):
    term = term.lower()  # normalize so as to make result case insensitive
    tally = 0
    for section in visible_text:
        for token in section.split():
            token = re.sub(r'[^\w\s]','',token)#remove punctuation
            tally += int(term == token.lower()) # instead of in do ==
    #print(term, tally)
    return tally

# counts two word phrases from the decoded HTML
def two_count (term, visible_text):
	tally = 0
	length = len(term)
	for section in visible_text:
		tokens = nltk.word_tokenize(section)
		tokens = [x.lower() for x in tokens] #standardize to lowercase
		tokens = [re.sub(r'[^\w\s]','',x) for x in tokens]
		grams=nltk.ngrams(tokens,length)
		fdist = nltk.FreqDist(grams)
		tally += fdist[term[0].lower(), term[1].lower()] #change for specific terms
	#print(term, tally)    
	return tally
	
def three_count (term, visible_text): # counts three word phrases from the decoded HTML
    tally = 0
    length = len(term)
    for section in visible_text:
        tokens=nltk.word_tokenize(section)
        tokens=[x.lower() for x in tokens]
        tokens=[re.sub(r'[^\w\s]','',x) for x in tokens]
        grams=nltk.ngrams(tokens,length)
        try:
            fdist=nltk.FreqDist(grams)
            tally+=fdist[term[0].lower(),term[1].lower(),term[2].lower()]
        except:
            pass
    #print(term, tally)
    return tally

def keyword_function(visible_text): # based on https://www.strehle.de/tim/weblog/archives/2015/09/03/1569
    keydump = [] # init empty array for keywords
    new_string = "".join(visible_text)
    words = nltk.word_tokenize(new_string)
    
    words = [word for word in words if len(word) > 1] # remove single-character tokens (mostly punctuation)
    words = [word for word in words if not word.isnumeric()]  # remove numbers
    words = [word.lower() for word in words] # lowercase all words (default_stopwords are lowercase too)
    words = [word for word in words if word not in all_stopwords] # remove stopwords
    
    fdist = nltk.FreqDist(words) # calculate frequency distribution
    for word, frequency in fdist.most_common(3): # output top 50 words
        keydump.append(word)
        
    return keydump

# sends text update that program has completed
def send_text_update():
    me = "wipalerts2019@gmail.com"
    my_password = "roadsaretar"
    you = "3177647054@txt.att.net"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Alert"
    msg['From'] = me
    msg['To'] = you

    html = '<html><body><p>Controlf has completed!</p></body></html>'
    part2 = MIMEText(html, 'html')

    msg.attach(part2)

    s = smtplib.SMTP_SSL('smtp.gmail.com')
    s.login(me, my_password)

    s.sendmail(me, you, msg.as_string())
    s.quit()
    
# method that actually does the counting and outputting to csv file       
#def counter(input_file, output_file, terms, dates, all_last, now):
if __name__ == '__main__':
    # the end date is non-inclusive, so to include June 19th, for example, you need to do 2019,6,20
    input_file = sys.argv[1] # input_file = 'ice_urls_filtered.csv'
    output_file = sys.argv[2] # output_file = "ice_counts_first.csv"
    body_output_file = sys.argv[3]

    # get and parse the terms
    #terms = sys.argv[3].replace('[', ' ').replace(']', ' ').split(",") # terms = "['sex', 'gender', 'discrimination', 'discriminating', 'identity', 'stereotype', 'stereotyping']"
    #terms = [str(i).strip() for i in terms]
    input_terms = sys.argv[4]
    with open(input_terms) as csvfile: # open up file of inputs (i.e. sites to search for keytems)
        read = csv.reader(csvfile, delimiter="|") # read and grab the input data
        data = list(read)
    csvfile.close() # close the input csv file

    terms = []
    for items in data:
        for item in items:
            terms.append(item.split(","))
    
    dates = sys.argv[5].replace('[', ' ').replace(']', ' ').replace(',', ' ').split() # dates = "[2016,1,1,2017,1,19]"
    dates = [int(i) for i in dates]
    all_last = sys.argv[6] # an indicator value for functionality
    now = sys.argv[7] # an indicator value for functionality

    counts_file_name = "controlf_" + str(input_file) + "_counts.csv"
    last_in_range_file_name = "controlf_" + str(input_file) + '_last_in_range.csv'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246'}

    for term in terms:
        results.append(str(term) + "\n")
        sys.stdout.write(str(term))
	
    #terms = ['sex', 'gender', 'discrimination', 'discriminating', 'identity', 'stereotype', 'stereotyping']
    #input_file = 'sites_to_search_keywords.csv'
	
    all_last_indic = 0 # indicator whether to grab all data in data range or just the one closest to the end date
    if (str(all_last).lower() == "all"):
        all_last_indic = 1 # indicator 1 means all has been chosen
    else:
        all_last_indic = 0 # indicator 0 means last has been chosen

    now_indic = 0
    if (str(now).lower() == "now"):
        now_indic = 0
    else:
        now_indic = 1

    with open(input_file) as csvfile: # open up file of inputs (i.e. sites to search for keytems)
        read = csv.reader(csvfile) # read and grab the input data
        data = list(read)
    csvfile.close() # close the input csv file
    
    open(counts_file_name, 'w').close() # erase existing contents of keywords.csv file
    open(last_in_range_file_name, 'w').close() # erase existing contents of keywords.csv file
    
    with open(counts_file_name, 'a', newline='') as output:
        writer = csv.writer(output)
        writer.writerow(terms)
    csvfile.close()
    
    with open(last_in_range_file_name, 'a', newline='') as output:
        writer = csv.writer(output)
        writer.writerow(terms)
        writer.writerow([])
    csvfile.close()
    
    row_count = len(data) # designate num of rows and cols for our matrix cnt of keyterms
    column_count = len(terms)
    matrix = numpy.zeros((row_count, column_count),dtype=numpy.int16) # init cnt matrix to zero
    body_matrix = numpy.zeros((row_count, 1),dtype=numpy.int16) # init cnt matrix to zero
    #print(row_count, column_count)
    
    for pos, elm in enumerate(data): # for each element of data
        thisPage = elm[0] # grab the url

        # save the url to wayback now
        if (now_indic == 1):
            try:
                r = requests.get('https://web.archive.org/save/'+thisPage)
            except:
                continue
        
        with open(counts_file_name, 'a', newline='') as output:
            writer = csv.writer(output)
            writer.writerow("")
        csvfile.close()
        
        try:
            with internetarchive.WaybackClient() as client:
                # dump returns ALL instances within the date-range that page has been documented in the Archive
                dump = client.list_versions(thisPage, from_date=datetime(dates[0], dates[1], dates[2]), to_date=datetime(dates[3], dates[4], dates[5])) # list_versions calls the CDX API from internetarchive.py from the webmonitoring repo
                #print("\n"+thisPage)
                results.append("\n"+thisPage+"\n")
                sys.stdout.write("\n"+thisPage+"\n")
                #sys.stdout.flush()
                
                achive_indicator = 0; # indicator variable to tell whether Archive has pages in the requested date range
                
                try: # get the versions if Archive contains data in the requested range
                    #versions = reversed(list(dump))
                    if (all_last_indic == 1):
                        versions = list(dump)
                    else:
                        versions = reversed(list(dump))
                    achive_indicator = 1; # indicator variable to show Archive does contain pages in requested date range
                except:
                    #print ("No archives in this range")
                    results.append("No archives in this range\n")
                    sys.stdout.write("No archives in this range\n")
                    #sys.stdout.flush()
                    with open(last_in_range_file_name, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                        writer.writerow([thisPage])
                        writer.writerow(["No archives in this range"])
                        writer.writerow([])
                    csvfile.close()
                    with open(counts_file_name, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                        writer.writerow([thisPage])
                        writer.writerow(["No archives in this range"])
                    csvfile.close()
                    matrix[pos]=999
                    #print(matrix[pos])
                    results.append(" ".join(str(x) for x in matrix[pos])+"\n")
                    sys.stdout.write(" ".join(str(x) for x in matrix[pos])+"\n")
                    #sys.stdout.flush()
                    
                if (achive_indicator == 1): # if Archive contains pages

                    for ind, version in enumerate(versions): # for each version in all the snapshots
                        
                        if ( (all_last_indic == 1) or ( (all_last_indic == 0) and (ind == 0) ) ):
                
                            temp_version = numpy.array([]) # init temp matrix
                            # GOAL: for each version, print all the version/archive_urls with instances to a matrix/csv file
                    
                            #print("\nDate: "+ str(version.date))
                            #print("Archive URL: "+ str(version.view_url))
                            
                            # if Archive snapshot was viable
                            if version.status_code == '200' or version.status_code == '-' or version.status_code == '301' or version.status_code == '302':
                                url = version.raw_url # get the Archive's url
                                
                                contents = requests.get(url, headers=headers).content.decode() # get Archive URL's raw HTML
                                contents = BeautifulSoup(contents, 'lxml')
                                
                                # remove parts of the page we don't care about
                                body=contents.find('body')
                                d=[s.extract() for s in body('footer')]
                                d=[s.extract() for s in body('header')]
                                d=[s.extract() for s in body('nav')]
                                d=[s.extract() for s in body('script')]
                                d=[s.extract() for s in body('style')]
                                d=[s.extract() for s in body.select('div > #menuh')] #FWS
                                d=[s.extract() for s in body.select('div > #siteFooter')] #FWS
                                d=[s.extract() for s in body.select('div.primary-nav')] #DOE
                                d=[s.extract() for s in body.select('div > #nav-homepage-header')] #OSHA
                                d=[s.extract() for s in body.select('div > #footer-two')] #OSHA
                                del d
                                
                                body = [text for text in body.stripped_strings] # grab the page's body text

                                word_cnt_body = 0
                                for sentence in body:
                                    words = sentence.split()
                                    word_cnt_body += len(words)

                                #sys.stdout.write(str(word_cnt_body)+"\n")
                                #sys.stdout.write(str(body)+"\n")

                                body_matrix[pos][0]=word_cnt_body
                                
                                for p,term_row in enumerate(terms): # count instances on page for each term
                                    term_row_sum = 0 # temp var to track sum for all those terms
                                    
                                    for term in term_row:
                                        if type(term) is list:
                                            if len(term)>2:
                                                page_sum=three_count(term,body)
                                            else:
                                                page_sum=two_count(term,body)
                                        else:
                                            page_sum=count(term, body)

                                        term_row_sum += page_sum
                                
                                        #print(version.date)
                                        #print(t)
                                        #print(page_sum)
                                        
                                        matrix[pos][p]=term_row_sum # put term count into matrix

                                #keywords.add(keyword_function(body)) # store the keywords and final urls
                                #final_urls.add(url)
                              
                                temp_version = numpy.append(str(version.date), matrix[pos])
                                temp_version = numpy.append(str(version.view_url), temp_version)
                                #print(temp_version)
                                
                                with open(counts_file_name, 'a', newline='') as csvfile:
                                    writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                                    writer.writerow(temp_version)
                                csvfile.close()
                             
                                if ( (all_last_indic == 0) and (ind == 0) ):
                                    #print(version.date)
                                    #print(version.raw_url)
                                    #print(matrix[pos])
                                    results.append(str(version.date)+"\n")
                                    sys.stdout.write(str(version.date)+"\n")
                                    #sys.stdout.flush()
                                    results.append(str(version.raw_url)+"\n")
                                    sys.stdout.write(str(version.raw_url)+"\n")
                                    #sys.stdout.flush()
                                    results.append(" ".join(str(x) for x in matrix[pos])+"\n")
                                    sys.stdout.write(" ".join(str(x) for x in matrix[pos])+"\n")
                                    #sys.stdout.flush()
                                    results.append("\n")
                                    sys.stdout.write("\n")
                                    #sys.stdout.flush()
                                    
                                    with open(last_in_range_file_name, 'a', newline='') as csvfile:
                                        writer = csv.writer(csvfile)
                                        writer.writerow([thisPage])
                                        writer.writerow([version.date])
                                        writer.writerow([version.raw_url])
                                        writer.writerow(matrix[pos])
                                        writer.writerow([])
                                    csvfile.close()
                    
                    if (all_last_indic == 1):   
                        #print(version.date)
                        #print(version.raw_url)
                        #print(matrix[pos])
                        results.append(str(version.date)+"\n")
                        sys.stdout.write(str(version.date)+"\n")
                        #sys.stdout.flush()
                        results.append(str(version.raw_url)+"\n")
                        sys.stdout.write(str(version.raw_url)+"\n")
                        #sys.stdout.flush()
                        results.append(" ".join(str(x) for x in matrix[pos])+"\n")
                        sys.stdout.write(" ".join(str(x) for x in matrix[pos])+"\n")
                        #sys.stdout.flush()
                        results.append("\n")
                        sys.stdout.write("\n")
                        #sys.stdout.flush()
                        
                        with open(last_in_range_file_name, 'a', newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow([thisPage])
                            writer.writerow([version.date])
                            writer.writerow([version.raw_url])
                            writer.writerow(matrix[pos])
                            writer.writerow([])
                        csvfile.close()
                    
        except:
            #print("failed ", pos)
            results.append("failed" + str(pos) +"\n")
            sys.stdout.write("failed" + str(pos) +"\n")
            #sys.stdout.flush()
            final_urls[url]=""
            matrix[pos]=999
    
    #print("\n")
    #print(matrix)
    results.append(numpy.array2string(matrix) + "\n")
    sys.stdout.write(numpy.array2string(matrix) + "\n")
    #sys.stdout.flush()
    unique, counts = numpy.unique(matrix, return_counts=True)
    results = dict(zip(unique, counts))
    #print (results)

    # for writing term counts to a csv. you will need to convert delimited text to columns and replace the first column with the list of URLs
    with open(counts_file_name, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        writer.writerow([])
        writer.writerow(["Aggregate Term Counts for Particular Sites (last in range)"])
        for row in matrix:
            writer.writerow(row)
    csvfile.close()

    # writing output for the R file
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for row in matrix:
            writer.writerow(row)
    csvfile.close()

    with open(body_output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for row in body_matrix:
            writer.writerow(row)
    csvfile.close()

    sys_output_file = "controlf_" + str(input_file) + "_output.csv"

    # create an output file of messages
    with open(sys_output_file,'w', newline='') as output: # append the site to the crawled url
        writer=csv.writer(output)
        for item in results:
            writer.writerow([str(item)])
    output.close()

    # TRANSFER SYS_OUTPUT FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(sys_output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANSFER OUTPUT FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANSFER BODY_OUTPUT FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(body_output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANSFER COUNTS FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(counts_file_name))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANSFER LAST_IN_RANGE FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(last_in_range_file_name))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # connect/ssh to an instance
    #try:
    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
    client_paramiko.connect(hostname="54.166.131.120", username="ec2-user", pkey=key) # putting the information of the other instance??

    sys.exit()
    
    #print out urls in separate file
    ''''
    with open('urls.csv','w') as output:
        writer=csv.writer(output)
        for key, value in final_urls.items():
            writer.writerow([key, value])
    output.close()
    '''

    #print out keywords in separate file
    '''
    with open("keywords.csv", "w", encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        for key, value in keywords.items():
            try:
                writer.writerow([key, value[0], value[1], value[2]])
            except IndexError:
                writer.writerow([key, "ERROR"])
    outfile.close()
    '''
