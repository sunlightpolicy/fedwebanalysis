import csv
import multiprocessing as mp
import sys
import requests
import time
import smtplib
import subprocess
import paramiko
import os
import subprocess

# set up connection to ec2
key = paramiko.RSAKey.from_private_key_file(".ssh/sun_key.pem") # putting link to pem file on the first instance itself??
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# private ip of the controlling EC2
scanner_private_ip = '172.30.0.69'

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246'}


# capture each url
def capture(url):
    global headers
    
    try:
        r = requests.get(url, headers=headers)
        status = r.status_code
        
        if (status == 200):
            r = requests.get('https://web.archive.org/save/'+url)
            sys.stdout.write("200: " + url + "\n")
        elif (r.status_code != 404):
            r = requests.get('https://web.archive.org/save/'+r.url)
            sys.stdout.write(str(status) + ": " + url + ", " + r.url + "\n")            
        else:
            sys.stdout.write(str(status) + ": " + url + "\n")
            
    except:
        sys.stdout.write("ERROR: " + url + "\n")


# run the program!
if __name__ == '__main__':
    input_file = sys.argv[1]
    output_file = input_file + "_output.csv"
    
    with open(input_file) as csvfile:
        data_list = []
        read = csv.reader(csvfile)
        data = list(read)
        for elm in data:
            data_list.append(str(elm[0]))
    csvfile.close
    
    start_time = time.time()
    pool = mp.Pool(3)
    result = pool.map(capture, [url for url in data_list])
    pool.close()

    final_message = str("--- %s seconds ---" % (time.time() - start_time)+"\n")

    # create an output file of messages
    with open(output_file,'w') as output: # append the site to the crawled url
        writer=csv.writer(output,delimiter=",")
        writer.writerow([final_message])
    output.close()

    # transfer the output file back to the EC2 which made the call
    # then upload the file to the instance we desire to run virtually
    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user/uploads", '')
    first_arg = os.path.join(r"/home/ec2-user", str(output_file))

    # ./transfer_file.sh "/home/ec2-user/uploads/trinberg_urls.csv" "ec2-user@172.31.30.127:/home/ec2-user/downloads"
    subprocess.call(["chmod", "+x", "transfer_file.sh"])
    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

    # connect/ssh to an instance
    #try:
    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
    client.connect(hostname="54.166.131.120", username="ec2-user", pkey=key) # putting the information of the other instance??

    sys.exit()
