from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from helpers import error, login_required, success
from werkzeug.exceptions import default_exceptions
from tempfile import mkdtemp
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from datetime import datetime
from pathlib import Path, PurePath
import subprocess
import io
import sys
import os
import random, string
from werkzeug.utils import secure_filename
import boto3
import botocore
import paramiko
import re

from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run_flow, argparser
from oauth2client.file import Storage
from googleapiclient.discovery import build

import google.oauth2.credentials
import google_auth_oauthlib.flow

from apiclient import errors
from apiclient.http import MediaFileUpload, MediaIoBaseDownload


app = Flask(__name__)

#   WEBSITE ADDRESS : http://54.166.131.120.xip.io:2000/login
#  https://developers.google.com/identity/protocols/OAuth2WebServer

CLIENT_ID = '717997199910-pa2mdmvfegtnupg52dqbi3althhhd7oj.apps.googleusercontent.com'
CLIENT_SECRET = 'TPNzso1c7NKwLk7m_ISHYkEa'
SCOPES = ['https://www.googleapis.com/auth/drive']

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

UPLOAD_FOLDER = '/uploads'
domain_to_run = None
file_to_scan = None
scanner_private_ip = "172.30.0.204"
domain_list = ["cbp", "cms", "dhs", "drugabuse", "fda", "fema",
               "healthcare", "hhs", "ice", "ihs", "justice",
               "marketplace", "medicaid", "medicare", "state",
               "treasury", "usa", "uscis", "va", "whitehouse",
               "womenshealth", "marketplace.cms"]

filename_array = []
filepath_array = []

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMPLATES_AUTO_RELOAD'] = True
Session(app)

drive = None # global drive service instance

# set up connection to ec2
key = paramiko.RSAKey.from_private_key_file(".ssh/sun_key.pem") # putting link to pem file on the first instance itself??
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())


# helper method that creates a folder in the main directory given a title
def create_folder(title):
    global drive
    file_metadata = {
        'name': str(title),
        'mimeType': 'application/vnd.google-apps.folder'
    }
    file = drive.files().create(
        body=file_metadata,
        fields='id'
    ).execute()

    return file.get('id')

"""Insert new file.

Args:
    service: Drive API service instance.
    title: Title of the file to insert, including the extension.
    description: Description of the file to insert.
    parent_id: Parent folder's ID.
    mime_type: MIME type of the file to insert.
    filename: Filename of the file to insert.
Returns:
    Inserted file metadata if successful, None otherwise.
"""
# helper method that inserts a file in a folder if a folder was aleady created
# that day, or creates a folder and inserts the file in it
def upload(service, pathtofile, description, parent_id, mime_type, filename):
    global drive
    mime_type = 'text/csv'
    d = datetime.today()
    folder_name = str(d.year)+"-"+str(d.month)+"-"+str(d.day)

    try:
        ids = []
        page_token = None
        search_query = "mimeType='application/vnd.google-apps.folder' and name contains '"+folder_name+"'"

        while True:
            response = drive.files().list(
                q=search_query,
                spaces='drive',
                fields='nextPageToken, files(id, name)',
                pageToken=page_token
            ).execute()
            for file in response.get('files', []):
                ids.append(file.get('id'))
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break    

        if ids:
            parent_id = ids[0]
        else:
            parent_id = create_folder(folder_name)

    except:
        parent_id = create_folder(folder_name)
        
    file_metadata = {
        'name': filename,
        'parents': [parent_id]
    }

    media = MediaFileUpload(
        pathtofile,
        mimetype=mime_type
    )
    
    try:
        file = drive.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        return file.get('id')
    except:
        #print ('An error occurred: %s')
        return "error"


# helper method that puts credenitals in dict form
def credentials_to_dict(credentials):
  return {'token': credentials.token,
          'refresh_token': credentials.refresh_token,
          'token_uri': credentials.token_uri,
          'client_id': credentials.client_id,
          'client_secret': credentials.client_secret,
          'scopes': credentials.scopes}


@app.route('/')
@login_required
def index():
    return redirect(url_for("dashboard"))


@app.route('/runningprograms', methods=["GET", "POST"])
@login_required
def runningprograms():
    global key
    global client

    attached = set()
    detached = set()


    client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??

    command = "./list_processes.sh"
    stdin, stdout, stderr = client.exec_command("chmod +x list_processes.sh", get_pty=True) # run two commands, first client.exec_command(chmod +x cmds.sh) then client.exec_command(./cmds.sh)
    stdin, stdout, stderr = client.exec_command(command, get_pty=True)
    
    stdout = str(stdout.read(), 'utf-8')

    attached_count = stdout.count("Attached")

    filtering = stdout.replace(" ", "").replace("Attached", "").replace("Detached","").replace("Therearescreenson:", "").replace("Thereisascreenon:", "")
    output_list = filtering.split("()")
    output_list.remove(output_list[len(output_list) - 1])

    for i in range(len(output_list)):
        if (i < attached_count):
            attached.add(output_list[i].strip())
        else:
            detached.add(output_list[i].strip())

    # client.close()

    if request.method == "POST":

        process_to_kill = (request.form['submit_button']).strip()

        if process_to_kill:

            # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
            #client.connect(hostname="18.209.14.99", username="ec2-user", pkey=key) # putting the information of the other instance??

            # Execute a command to scan after connecting/ssh to an instance
            command_2 = "./kill_process.sh '" + process_to_kill + "'"
            stdin, stdout, stderr = client.exec_command("chmod +x kill_process.sh", get_pty=True) # run two commands, first client.exec_command(chmod +x cmds.sh) then client.exec_command(./cmds.sh)
            stdin, stdout, stderr = client.exec_command(command_2, get_pty=True)
            
            return success("A process with ID " + str(process_to_kill) + " has been terminated.", 200)

        else:
            return render_template("runningprograms.html", attached=attached, detached=detached)

    else:
        return render_template("runningprograms.html", attached=attached, detached=detached)
   

@app.route("/oauth2callback/")
def oauth2callback():
    global drive
    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    drive = build('drive', 'v3', credentials=credentials)

    return redirect(url_for("dashboard"))


def try_upload():
    global drive
    global filename_array
    global filepath_array
    
    # upload unuploaded files if the process has completed
    for i, file_unuploaded in enumerate(filename_array):
        try:
            filepath_unuploaded = filepath_array[i]
            
            file_id = upload (drive, filepath_unuploaded,
                "upload", None, None, file_unuploaded)
            
            filename_array.remove(file_unuploaded)
            filepath_array.remove(filepath_unuploaded)
        except:
            continue


@app.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    global drive
    global domain_to_run
    global file_to_scan
    global scanner_private_ip
    global key
    global client
    global filename_array
    global filepath_array
    global domain_list

    if request.method == "POST":

        submitted = request.form['submit_button']

        if submitted == 'upload':

            try:
                file = request.files['file']

                # get the file's name (incl ext) and filepath, save it to EC2 locally
                filename = secure_filename(file.filename)
                filepath = os.path.join(r"/home/ec2-user/uploads", str(filename))
                file.save(filepath)

                # add the file to drive
                file_id = upload (drive, filepath, "upload", None, None, filename)

            except:
                return error("file not specified", 403)

            return success("A file named " + str(filename) + " and id " + str(file_id) +
                    " has been uploaded to drive.", 200)

        elif ( (submitted == 'trinberg') or
            (submitted == 'rbergman') or
            (submitted == 'customupload') ):

            if (submitted == 'customupload'):

                try:
                    file = request.files['file']
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(r"/home/ec2-user/uploads", str(filename))
                    file.save(filepath)

                    file_id = upload(drive, filepath, "upload", None, None, filename)
                except:
                    return error("File not specified", 403)
            else:
                # get a list of url uploads for the corresponding acct
                try:
                    file_ids = []
                    page_token = None
                    name = submitted + "_urls.csv"
                    search_query = "mimeType='text/csv' and name = '"+name+"'"

                    while True:
                        response = drive.files().list(
                            orderBy='createdTime desc',
                            q=search_query,
                            spaces='drive',
                            fields='nextPageToken, files(id, name)',
                            pageToken=page_token
                        ).execute()
                        for file in response.get('files', []):
                            file_ids.append(file)
                        page_token = response.get('nextPageToken', None)
                        if page_token is None:
                            break
                    file_id = file_ids[0].get('id') # get the file's id
                    filename = file_ids[0].get('name') # get the file's name
                except:
                    return error("No lists have been added for this "+str(submitted)+
                                 " account. Upload a list and try again. The list name must have "+
                                 str(submitted)+" in its title to be found.", 403)
                
            #try:
            # download the file locally
            filepath = os.path.join(r"/home/ec2-user/uploads", str(filename))
            
            request_2 = drive.files().get_media(fileId=file_id)
            fh = io.FileIO(filepath, 'wb')
            downloader = MediaIoBaseDownload(fh, request_2)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

            # then upload the file to the instance we desire to run virtually
            filepath_dest = os.path.join(r"/home/ec2-user", str(filename))
            second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
            first_arg = os.path.join(r"/home/ec2-user/uploads", str(filename))

            # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
            subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

            # connect/ssh to an instance
            #try:
            # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
            client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??

            # might need a thread
            # https://stackoverflow.com/questions/5974463/ssh-client-with-paramiko

            # add file_name to un_uploaded set
            output_filename = filename+"_output.csv"
            output_filepath = os.path.join(r"/home/ec2-user/uploads", str(output_filename))
    
            # output_file_id = upload (drive, filepath, "upload", None, None, filename)

            filename_array.append(str(output_filename))
            filepath_array.append(output_filepath)

            # Execute a command to scan after connecting/ssh to an instance
            command = "./url_capture.sh '" + str(filename) + "'"
            stdin, stdout, stderr = client.exec_command("chmod +x url_capture.sh", get_pty=True) # run two commands, first client.exec_command(chmod +x cmds.sh) then client.exec_command(./cmds.sh)
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            # sys.stdout.write( str(stdout.read()) )

            #return str(stdout.read())

            return success("Processing has started on the " + str(submitted) +
                           " file having id " + str(file_id), 200)
                           
            #return filename + "_" + output_filename
    
            # close the client connection once the job is done
            # client.close()
            #except:
                # sys.stdout.write( "failed" )
             #   return error("Unable to complete url capture on"+str(submitted)+
             #                    " account.", 403)
            
            # return(str(stdout.read()))
            #return success("processing has been started on the " + str(submitted) +
            #        " file having id " + str(file_id), 200)

        elif submitted in domain_list:        
            domain_to_run = submitted

            # get the name of the program to run
            program_to_run = str(request.form["options"])

            # get the date input values
            date_start = str(request.form["date_start"])
            date_end = str(request.form["date_end"])

            # check if the provided date is valid
            year_start = int(date_start[0:4])
            month_start = int(date_start[5:7])
            day_start = int(date_start[8:10])

            year_end= int(date_end[0:4])
            month_end = int(date_end[5:7])
            day_end = int(date_end[8:10])

            # if its an invalid date, get to an error message
            if (year_start > year_end):
                return error("invalid date range", 403)
            if (year_start == year_end):
                if (month_start > month_end):
                    return error("invalid date range", 403)
                if (month_start == month_end):
                    if (day_start >= day_end):
                        return error("invalid date range", 403)

            date_formated = ( "[" + str(year_start) + "," + str(month_start) +
                            "," + str(day_start) + "," + str(year_end) + "," +
                            str(month_end) + "," + str(day_end) + "]" )

            # get input values needed for term_count
            count_all_last_option = str(request.form.get("count_all_last_option"))
            if count_all_last_option == "on":
                count_all_last_option = "all"
            else:
                count_all_last_option = "last"

            capture_option = str(request.form.get("capture_option"))
            if capture_option == "on":
                capture_option = "now"
            else:
                capture_option = "later"

            unique_domains = ["cms", "state", "whitehouse"]
            single_domains = ["drugabuse", "healthcare", "hhs", "ihs", "medicaid",
                              "medicare", "treasury", "usa", "va", "womenshealth",
                              "marketplace.cms"]
            two_pages = ["ice", "cbp", "dhs", "uscis"]
            

            # URL COLLECT
            # connect/ssh to an instance
            #try:
            # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
            client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??

            if program_to_run == "scrape_url":

                if domain_to_run in unique_domains:
                    prep = "chmod +x url_collect_" + str(domain_to_run) + ".sh"
                    command = ("./url_collect_" + str(domain_to_run) + ".sh '" + str(date_formated) + "' " +
                                "'https://www." + str(domain_to_run) + ".gov' " +
                                "'" + str(domain_to_run) + "_urls.csv' " +
                                "'" + "403_postpone_" + str(domain_to_run) + ".csv' " +
                                "'" + "all_urls_" + str(domain_to_run) + ".csv'")
                              
                elif domain_to_run in single_domains:
                    prep = "chmod +x url_collect_single.sh"
                    command = ("./url_collect_single.sh '" + str(date_formated) + "' " +
                                "'https://www." + str(domain_to_run) + ".gov' " +
                                "'" + str(domain_to_run) + "_urls.csv' " +
                                "'" + "403_postpone_" + str(domain_to_run) + ".csv' " +
                                "'" + "all_urls_" + str(domain_to_run) + ".csv'")

                else:
                    if domain_to_run in two_pages:
                        pg_cnt = 2
                    elif domain_to_run == "justice":
                        pg_cnt = 5
                    elif domain_to_run == "fema":
                        pg_cnt = 11
                    else:
                        if domain_to_run == "fda":
                            pg_cnt = 29
                    
                    prep = "chmod +x url_collect_multiple_sitemaps.sh"
                    command = ("./url_collect_multiple_sitemaps.sh '" + str(pg_cnt) +
                                "' '" + str(date_formated) + "' " + "'https://www." +
                                str(domain_to_run) + ".gov' " +
                                "'" + str(domain_to_run) + "_urls.csv' " +
                                "'" + "403_postpone_" + str(domain_to_run) + ".csv' " +
                                "'" + "all_urls_" + str(domain_to_run) + ".csv'")

                # name output files
                stdout_output_file_name = "scraped_urls_" + str(domain_to_run) + "_output.csv"
                output_filename = str(domain_to_run) + "_urls.csv"
                postpone_file_name = "403_postpone_" + str(domain_to_run) + ".csv"
                all_file_name = "all_urls_" + str(domain_to_run) + ".csv"

                # add output files from controlf to un_uploaded set
                stdout_output_filepath = os.path.join(r"/home/ec2-user/uploads", str(stdout_output_file_name))
                output_filepath = os.path.join(r"/home/ec2-user/uploads", str(output_filename))
                postpone_filepath = os.path.join(r"/home/ec2-user/uploads", str(postpone_file_name))
                all_filepath = os.path.join(r"/home/ec2-user/uploads", str(all_file_name))

                filename_array.append(str(stdout_output_file_name))
                filename_array.append(str(output_filename))
                filename_array.append(str(postpone_file_name))
                filename_array.append(str(all_file_name))

                filepath_array.append(stdout_output_filepath)
                filepath_array.append(output_filepath)
                filepath_array.append(postpone_filepath)
                filepath_array.append(all_filepath)

                # Execute a command to scan after connecting/ssh to an instance
                stdin, stdout, stderr = client.exec_command(prep, get_pty=True) # run two commands, first client.exec_command(chmod +x cmds.sh) then client.exec_command(./cmds.sh)
                stdin, stdout, stderr = client.exec_command(command, get_pty=True)
                #return str(stderr.read())
                #return sys.stdout.write( str(stdout.read()) )

                #return str(stdout.read())
                #return command
                
                return success(("On " + str(domain_to_run) + " we are running " +
                    program_to_run + " with start date " + date_start +
                    " and end date " + date_end + "."), 200)

            elif program_to_run == "controlf":
                # CONTROLF
                # get the files for controlf from gdrive
                # have an upload place for terms

                # get the input file from Drive
                try:
                    file_ids = []
                    page_token = None
                    linked_text = str(submitted) + "_urls.csv"
                    search_query = ("mimeType='text/csv' and name = '" + linked_text + "'")

                    while True:
                        response = drive.files().list(
                            orderBy='createdTime desc',
                            q=search_query,
                            spaces='drive',
                            fields='nextPageToken, files(id, name)',
                            pageToken=page_token
                        ).execute()
                        for file in response.get('files', []):
                            file_ids.append(file)
                        page_token = response.get('nextPageToken', None)
                        if page_token is None:
                            break
                    input_file_id = file_ids[0].get('id') # get the file's id
                    input_file_name = file_ids[0].get('name') # get the file's name
                except:
                    return error("No urls have been collected for this "+str(submitted)+
                                 " domain. Run 'url collect' prior to searching for terms." +
                                 "The file name must begin with '" + str(submitted) +
                                 "_urls' in its title to be found.", 403)
                    
                #try:
                # download the file locally
                filepath = os.path.join(r"/home/ec2-user/uploads", str(input_file_name))
                
                request_2 = drive.files().get_media(fileId=input_file_id)
                fh = io.FileIO(filepath, 'wb')
                downloader = MediaIoBaseDownload(fh, request_2)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

                # then upload the file to the instance we desire to run virtually
                filepath_dest = os.path.join(r"/home/ec2-user", str(input_file_name))
                second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                first_arg = os.path.join(r"/home/ec2-user/uploads", str(input_file_name))

                # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                # connect/ssh to an instance
                #try:
                # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                # get the term_input file from Drive
                try:
                    file_ids = []
                    page_token = None
                    linked_text = str(submitted) + "_terms.csv"
                    search_query = ("mimeType='text/csv' and name = '" + linked_text + "'")

                    while True:
                        response = drive.files().list(
                            orderBy='createdTime desc',
                            q=search_query,
                            spaces='drive',
                            fields='nextPageToken, files(id, name)',
                            pageToken=page_token
                        ).execute()
                        for file in response.get('files', []):
                            file_ids.append(file)
                        page_token = response.get('nextPageToken', None)
                        if page_token is None:
                            break
                    terms_file_id = file_ids[0].get('id') # get the file's id
                    terms_file_name = file_ids[0].get('name') # get the file's name
                except:
                    return error("No terms file has been collected for this "+str(submitted)+
                                 " domain. Upload a file of terms prior to searching for terms." +
                                 "The file name must begin with '" + str(submitted) +
                                 "_terms' in its title to be found.", 403)
                    
                #try:
                # download the file locally
                filepath = os.path.join(r"/home/ec2-user/uploads", str(terms_file_name))
                
                request_2 = drive.files().get_media(fileId=terms_file_id)
                fh = io.FileIO(filepath, 'wb')
                downloader = MediaIoBaseDownload(fh, request_2)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()

                # then upload the file to the instance we desire to run virtually
                filepath_dest = os.path.join(r"/home/ec2-user", str(terms_file_name))
                second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                first_arg = os.path.join(r"/home/ec2-user/uploads", str(terms_file_name))

                # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                # connect/ssh to an instance
                #try:
                # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                # name output files
                sys_output_filename = "controlf_" + str(input_file_name) + "_output.csv"
                output_file_name = (str(submitted) + "_controlf_output_" +
                                    str(date_start) + "_" + str(date_end) + ".csv")
                body_output_file_name = (str(submitted) + "_controlf_body_output_" +
                                         str(date_start) + "_" + str(date_end) + ".csv")
                last_in_range_file_name = "controlf_" + str(input_file_name) + "_last_in_range.csv"
                counts_file_name = "controlf_" + str(input_file_name) + "_counts.csv"

                # add output files from controlf to un_uploaded set
                sys_output_filepath = os.path.join(r"/home/ec2-user/uploads", str(sys_output_filename))
                output_filepath = os.path.join(r"/home/ec2-user/uploads", str(output_file_name))
                body_output_filepath = os.path.join(r"/home/ec2-user/uploads", str(body_output_file_name))
                last_in_range_filepath = os.path.join(r"/home/ec2-user/uploads", str(last_in_range_file_name))
                counts_filepath = os.path.join(r"/home/ec2-user/uploads", str(counts_file_name))
                
                filename_array.append(str(sys_output_filename))
                filename_array.append(str(output_file_name))
                filename_array.append(str(body_output_file_name))
                filename_array.append(str(last_in_range_file_name))
                filename_array.append(str(counts_file_name))
                                  
                filepath_array.append(sys_output_filepath)
                filepath_array.append(output_filepath)
                filepath_array.append(body_output_filepath)
                filepath_array.append(last_in_range_filepath)
                filepath_array.append(counts_filepath)
                
                prep = "chmod +x controlf.sh"
                command = ("./controlf.sh '" + str(input_file_name) +
                            "' '" + str(output_file_name) + "' " +
                            "'" + str(body_output_file_name) + "' " +
                            "'" + str(terms_file_name) + "' " +
                            "'" + str(date_formated) + "' " +
                            "'" + str(count_all_last_option) + "' " +
                            "'" + str(capture_option) + "'")

                # Execute a command to scan after connecting/ssh to an instance
                stdin, stdout, stderr = client.exec_command(prep, get_pty=True) # run two commands, first client.exec_command(chmod +x cmds.sh) then client.exec_command(./cmds.sh)
                stdin, stdout, stderr = client.exec_command(command, get_pty=True)
                # sys.stdout.write( str(stdout.read()) )

                #return str(stdout.read())

                return success(("On " + domain_to_run + " we are running " +
                        program_to_run + " with start date " + date_start +
                        " and end date " + date_end +
                        ". Additional options for term_count are count_all_last=" +
                        str(count_all_last_option) + " and capture_option=" +
                        str(capture_option) + ". Our input file for this program is " +
                        str(input_file_name) + ". Terms file is " + str(terms_file_name) + "."), 200)
                                      

            else:
                if program_to_run == "term_count":
                    # COMPARE TERMS
                    # get the needed input_files
                    try:
                        file_ids = []
                        page_token = None
                        linked_text = str(submitted) + "_controlf_output"
                        search_query = ("mimeType='text/csv' and name contains '" + linked_text + "'")

                        while True:
                            response = drive.files().list(
                                orderBy='createdTime desc',
                                q=search_query,
                                spaces='drive',
                                fields='nextPageToken, files(id, name)',
                                pageToken=page_token
                            ).execute()
                            for file in response.get('files', []):
                                file_ids.append(file)
                            page_token = response.get('nextPageToken', None)
                            if page_token is None:
                                break
                        input_file_counts_second_file_id = file_ids[0].get('id') # get the file's id
                        input_file_counts_first_file_id = file_ids[1].get('id') # get the file's id
                        input_file_counts_second_filename = file_ids[0].get('name') # get the file's name
                        input_file_counts_first_filename = file_ids[1].get('name') # get the file's name

                        file_ids = []
                        page_token = None
                        linked_text = str(submitted) + "_controlf_body_output"
                        search_query = ("mimeType='text/csv' and name contains '" + linked_text + "'")

                        while True:
                            response = drive.files().list(
                                orderBy='createdTime desc',
                                q=search_query,
                                spaces='drive',
                                fields='nextPageToken, files(id, name)',
                                pageToken=page_token
                            ).execute()
                            for file in response.get('files', []):
                                file_ids.append(file)
                            page_token = response.get('nextPageToken', None)
                            if page_token is None:
                                break
                        input_body_cnts_second_file_id = file_ids[0].get('id') # get the file's id
                        input_body_cnts_first_file_id = file_ids[1].get('id') # get the file's id
                        input_body_cnts_second_filename = file_ids[0].get('name') # get the file's name
                        input_body_cnts_first_filename = file_ids[1].get('name') # get the file's name
                    except:
                        return error("There does not exist two time ranged term file for "+str(submitted)+
                                     " domain. Make sure you have run term finder for two distinct ranges first." +
                                     " Note that the progam automatically chooses the most recent files with "+
                                     "the file name beginning '" + str(submitted) +
                                     "_controlf_output' in its title to be found. There must also " +
                                     "exist body_output files which are automatically generated when the output files " +
                                     "of the term finder are generated.", 403)
                        
                    #try:
                    # download the file locally
                    filepath1 = os.path.join(r"/home/ec2-user/uploads", str(input_file_counts_first_filename))
                    
                    request_2 = drive.files().get_media(fileId=input_file_counts_first_file_id)
                    fh = io.FileIO(filepath1, 'wb')
                    downloader = MediaIoBaseDownload(fh, request_2)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # then upload the file to the instance we desire to run virtually
                    filepath_dest = os.path.join(r"/home/ec2-user", str(input_file_counts_first_filename))
                    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                    first_arg = os.path.join(r"/home/ec2-user/uploads", str(input_file_counts_first_filename))

                    # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                    # connect/ssh to an instance
                    #try:
                    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                    client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                    filepath2 = os.path.join(r"/home/ec2-user/uploads", str(input_file_counts_second_filename))
                    
                    request_2 = drive.files().get_media(fileId=input_file_counts_second_file_id)
                    fh = io.FileIO(filepath2, 'wb')
                    downloader = MediaIoBaseDownload(fh, request_2)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # then upload the file to the instance we desire to run virtually
                    filepath_dest = os.path.join(r"/home/ec2-user", str(input_file_counts_second_filename))
                    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                    first_arg = os.path.join(r"/home/ec2-user/uploads", str(input_file_counts_second_filename))

                    # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                    # connect/ssh to an instance
                    #try:
                    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                    client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                    filepath3 = os.path.join(r"/home/ec2-user/uploads", str(input_body_cnts_first_filename))
                    
                    request_2 = drive.files().get_media(fileId=input_body_cnts_first_file_id)
                    fh = io.FileIO(filepath3, 'wb')
                    downloader = MediaIoBaseDownload(fh, request_2)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # then upload the file to the instance we desire to run virtually
                    filepath_dest = os.path.join(r"/home/ec2-user", str(input_body_cnts_first_filename))
                    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                    first_arg = os.path.join(r"/home/ec2-user/uploads", str(input_body_cnts_first_filename))

                    # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                    # connect/ssh to an instance
                    #try:
                    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                    client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                    filepath4 = os.path.join(r"/home/ec2-user/uploads", str(input_body_cnts_second_filename))
                    
                    request_2 = drive.files().get_media(fileId=input_body_cnts_second_file_id)
                    fh = io.FileIO(filepath4, 'wb')
                    downloader = MediaIoBaseDownload(fh, request_2)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # then upload the file to the instance we desire to run virtually
                    filepath_dest = os.path.join(r"/home/ec2-user", str(input_body_cnts_second_filename))
                    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                    first_arg = os.path.join(r"/home/ec2-user/uploads", str(input_body_cnts_second_filename))

                    # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                    # connect/ssh to an instance
                    #try:
                    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                    client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                    # get the term_input file from Drive
                    try:
                        file_ids = []
                        page_token = None
                        linked_text = str(submitted) + "_terms.csv"
                        search_query = ("mimeType='text/csv' and name = '" + linked_text + "'")

                        while True:
                            response = drive.files().list(
                                orderBy='createdTime desc',
                                q=search_query,
                                spaces='drive',
                                fields='nextPageToken, files(id, name)',
                                pageToken=page_token
                            ).execute()
                            for file in response.get('files', []):
                                file_ids.append(file)
                            page_token = response.get('nextPageToken', None)
                            if page_token is None:
                                break
                        terms_file_id = file_ids[0].get('id') # get the file's id
                        terms_file_name = file_ids[0].get('name') # get the file's name
                    except:
                        return error("No terms file has been collected for this "+str(submitted)+
                                     " domain. Upload a file of terms prior to searching for terms." +
                                     "The file name must have " + str(submitted) +
                                     "and '_terms' in its title to be found.", 403)
                        
                    #try:
                    # download the file locally
                    filepath = os.path.join(r"/home/ec2-user/uploads", str(terms_file_name))
                    
                    request_2 = drive.files().get_media(fileId=terms_file_id)
                    fh = io.FileIO(filepath, 'wb')
                    downloader = MediaIoBaseDownload(fh, request_2)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                    # then upload the file to the instance we desire to run virtually
                    filepath_dest = os.path.join(r"/home/ec2-user", str(terms_file_name))
                    second_arg = os.path.join("ec2-user@"+str(scanner_private_ip)+":/home/ec2-user", '')
                    first_arg = os.path.join(r"/home/ec2-user/uploads", str(terms_file_name))

                    # ./transfer_file.sh /home/ec2-user/uploads/trinberg_urls.csv ec2-user@172.30.0.204:/home/ec2-user/trinberg_urls.csv
                    subprocess.check_call(['./transfer_file.sh', first_arg, second_arg])

                    # connect/ssh to an instance
                    #try:
                    # Here 'ubuntu' is user name and 'instance_ip' is public IP of EC2
                    client.connect(hostname="34.207.218.193", username="ec2-user", pkey=key) # putting the information of the other instance??


                    # name output files
                    output_file_name = (str(submitted) + "_term_comparison_output.csv")
                    output_percentages_file_name = (str(submitted) + "_term_comparison_output_percents.csv")

                    # add output files from controlf to un_uploaded set
                    output_filepath = os.path.join(r"/home/ec2-user/uploads", str(output_file_name))
                    output_percentages_filepath = os.path.join(r"/home/ec2-user/uploads", str(output_percentages_file_name))

                    filename_array.append(str(output_file_name))
                    filename_array.append(str(output_percentages_file_name))
                                      
                    filepath_array.append(str(output_filepath))
                    filepath_array.append(str(output_percentages_filepath))

            
                    # get the files for term_counter from gdrive
                    prep = "chmod +x term_count.sh"
                    command = ("./term_count.sh '" + str(input_file_counts_first_filename) +
                                "' '" + str(input_file_counts_second_filename) + "' " + 
                                "'" + str(input_body_cnts_first_filename) + "' " +
                                "'" + str(input_body_cnts_second_filename) + "' " +
                                "'" + str(output_file_name) + "' " +
                                "'" + str(output_percentages_file_name) + "' " +
                                "'" + str(terms_file_name) + "'")

                    # Execute a command to scan after connecting/ssh to an instance
                    stdin, stdout, stderr = client.exec_command(prep, get_pty=True) # run two commands, first client.exec_command(chmod +x cmds.sh) then client.exec_command(./cmds.sh)
                    stdin, stdout, stderr = client.exec_command(command, get_pty=True)
                    # sys.stdout.write( str(stdout.read()) )

                    #return str(stdout.read())

                    return success(("On " + domain_to_run + " we are running " +
                        program_to_run + " with start date " + date_start +
                        " and end date " + date_end +
                        ". Additional options for term_count are count_all_last=" +
                        str(count_all_last_option) + " and capture_option=" +
                        str(capture_option) + ". Our input file is " +
                        str(input_file_counts_first_filename) + " and " + str(input_file_counts_second_filename) + "." +
                        " Other files we are using are " + str(input_body_cnts_first_filename) + " and " +
                        str(input_body_cnts_second_filename) + ". Terms file is " + str(terms_file_name) + "."), 200)
                        
                else:
                    return error("Something didn't work out.", 403)

            #return ":"+str(request.args)+":"+str(date_start)+":"
            #return (":" + str(domain_to_run) + ":" + str(date_start) +":")

            # scape for urls or count terms on URLs

            # return success("we will now scape or count terms on " + str(submitted), 200)
    
        else:
            try_upload()
            return render_template("dashboard.html")

    else:
        try_upload()
        return render_template("dashboard.html")

	
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not(request.form.get("username") == "wip" and request.form.get("password") == "roadsaretar"):
            return error("Invalid username and/or password", 403)
        else:
            session["user_id"] = "wip"
            # Redirect user to home page
            flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
                'client_secrets.json',
                scopes=SCOPES
            )
            flow.redirect_uri = url_for('oauth2callback', _external=True)
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                #login_hint='wipalerts2019@gmail.com',
                include_granted_scopes='true'
            )

            session['state'] = state
            return redirect(authorization_url)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        flash('UPLOAD UPLOADED FILES')
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect(url_for("login"))


def errorhandler(e):
    """Handle error"""
    return error(e.name, e.code)


if __name__ == "__main__":
    #https://stackoverflow.com/questions/14814201/can-i-serve-multiple-clients-using-just-flask-app-run-as-standalone
    app.run(host="0.0.0.0", port=2000, debug=True)

    # listen for errors
    for code in default_exceptions:
        app.errorhandler(code)(errorhandler)
