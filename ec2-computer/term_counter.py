import csv
from datetime import datetime
from bs4 import BeautifulSoup
import numpy
from urllib.parse import urlparse
import requests
import sys
import smtplib
import paramiko
import os
import subprocess

# set up connection to ec2
key = paramiko.RSAKey.from_private_key_file(".ssh/sun_key.pem") # putting link to pem file on the first instance itself??
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# private ip of the controlling EC2
scanner_private_ip = '172.30.0.69'

discarded_urls = numpy.array([], dtype=int) # init matrix to dump urls to exclude

def nineninenine_finder(data):
    global discarded_urls
    
    for pos, row in enumerate(data):
        total = 0 # init temp counter to zero
        
        for elm in row: # check each element of the row if it is a '999'
            if (elm == '999'):
                total += 1
                
        if (total == len(row)): # if every element in the row is '999'
            if ((pos in discarded_urls) == False): # if that row isn't already added to excluded urls, add it
                discarded_urls = numpy.append(discarded_urls, pos)

def data_reader(input_file):
    with open(input_file) as csvfile:
        read = csv.reader(csvfile, delimiter=' ')
        data = list(read)
    csvfile.close()
    
    return data
    
def full_term_summer(data):
    all_term_sum = numpy.array([], dtype=int) # init matrix to dump total term counts
    
    # sum the columns to determine total counts - the url and data already lines up
    for i in range(len(data[0])): # for each term
        term_sum = 0 # init the term sum to zero
        
        for pos, row in enumerate(data): # look at each row
            if ((pos in discarded_urls) == False): # if it's not a row that we out to exclude
                term_sum += int(row[i])
        
        all_term_sum = numpy.append(all_term_sum, term_sum)
    
    return all_term_sum


if __name__ == '__main__':
#def tabular_sum(input_file_counts_first, input_file_counts_second):
    input_file_counts_first = sys.argv[1]
    input_file_counts_second = sys.argv[2]
    input_body_cnts_first = sys.argv[3]
    input_body_cnts_second = sys.argv[4]
    output_file = sys.argv[5]
    output_percentages = sys.argv[6]
    #terms = sys.argv[4].replace('[', ' ').replace(']', ' ').split(",") # terms = "['sex', 'gender', 'discrimination', 'discriminating', 'identity', 'stereotype', 'stereotyping']"
    #terms = [str(i).strip() for i in terms]

    input_terms = sys.argv[7]
    with open(input_terms) as csvfile: # open up file of inputs (i.e. sites to search for keytems)
        read = csv.reader(csvfile, delimiter="|") # read and grab the input data
        data = list(read)
    csvfile.close() # close the input csv file

    terms = []
    for items in data:
        for item in items:
            terms.append(item.split(","))
        
    # read the data and obtain the numpy arrays
    data_first = data_reader(input_file_counts_first)
    data_second = data_reader(input_file_counts_second)
    body_first = data_reader(input_body_cnts_first)
    body_second = data_reader(input_body_cnts_second)
    
    # add the urls to exclude counts from
    nineninenine_finder(data_first)
    nineninenine_finder(data_second)
    
    # get the arrays of total term sums
    term_sum_first = full_term_summer(data_first)
    term_sum_second = full_term_summer(data_second)
    body_sum_first = full_term_summer(body_first)[0]
    body_sum_second = full_term_summer(body_second)[0]
    
    with open(output_file,'w', newline='') as output: # append the site to the crawled url
        writer=csv.writer(output)
        writer.writerow(terms)
        writer.writerow(term_sum_first)
        writer.writerow(term_sum_second)
    output.close()

    with open(output_percentages,'w', newline='') as output: # append the site to the crawled url
        writer=csv.writer(output)

        first_row = []
        for elm in term_sum_first:
            #sys.stdout.write(str(elm)+"\n")
            #sys.stdout.write(str(body_sum_first)+"\n")
            first_row.append(elm*100/body_sum_first)

        second_row = []
        for elm in term_sum_second:
            #sys.stdout.write(str(elm)+"\n")
            #sys.stdout.write(str(body_sum_second)+"\n")
            second_row.append(elm*100/body_sum_first)
        
        writer.writerow(terms)
        writer.writerow(first_row)
        writer.writerow(second_row)
    output.close()

    # TRANSFER OUTPUT FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    filepath_dest = os.path.join(r"/home/ec2-user/uploads", str(output_file))
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # TRANSFER OUTPUT_PERCENTAGES FILE
    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    filepath_dest = os.path.join(r"/home/ec2-user/uploads", str(output_file))
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(output_percentages))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # connect/ssh to an instance
    #try:
    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
    client.connect(hostname="54.166.131.120", username="ec2-user", pkey=key) # putting the information of the other instance??

    sys.exit()
