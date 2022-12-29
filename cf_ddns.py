import os
import time
import requests
import json
import smtplib
from datetime import datetime
from decouple import config
from pathlib import Path
from email.message import EmailMessage

# Cloudflare Info
api_token = config('API_TOKEN')
zone_id = config('ZONE_ID')
zone_name = config('ZONE_NAME')
record_names = config('RECORD_NAMES').split(',')
record_proxied = False

# Email Info
email_auth_addr = config('EMAIL_AUTH_ADDRESS')
email_auth_pass = config('EMAIL_AUTH_PASSWORD')
email_server = config('EMAIL_SERVER')
email_port = config('EMAIL_PORT')

# Other Variables
wan_ip_url = "http://ipv4.icanhazip.com"
data_file = os.path.realpath(os.path.dirname(__file__)) + "/ip.txt"
log_file = os.path.realpath(os.path.dirname(__file__)) + "/log.txt"
maxloglines = 120

def write_log(*logmessages):
	logfile = open(log_file, 'a')
	now = datetime.now()
	timestamp = now.strftime("%Y/%m/%d %H:%M:%S")
	for logmessage in logmessages:
		logfile.writelines([timestamp, " - ", logmessage, '\n'])
	logfile.close
	
def truncate_log():
	logfile = open(log_file, "r+")
	content = logfile.readlines()
	count = len(content)
	if count > maxloglines:
		logfile = open(log_file, "w")
		for line in range(count-maxloglines,count):
			logfile.writelines(content[line])
	logfile.close
	
def read_data():
	datafile = open(data_file, 'r')
	return datafile.readline()

def write_data(ip):
	datafile = open(data_file, 'w')
	datafile.writelines(str(ip))
	datafile.close
		
def current_ip():
	try:
		response = requests.get(wan_ip_url)
		if response.status_code == 200 and response.text != "None":
			return response.text
		else:
			write_log("Connected but could not get the remote IP")
	except requests.exceptions.RequestException as e:
		write_log("Could not connect to get the remote IP")
		return "None"
		
def previous_ip():
	path = Path(data_file)
	if path.is_file():
		return read_data()
	else:
		write_log("Previous IP not recorded, writing to " + data_file)
		write_data(current_ip())
		return "None"

def set_ip(record_name: str, current_ip: str):
	zone_id_url = (
		"https://api.cloudflare.com/client/v4/zones/%(zone_id)s/dns_records?name=%(record_name)s"
		% {"zone_id": zone_id, "record_name": record_name}
	)
	
	headers= {
		"Authorization": "Bearer " + api_token,
		"Content-Type": "application/json",
	}
	
	response = requests.get(zone_id_url, headers=headers)
	response_dict = json.loads(response.text)
	record_id = response_dict['result'][0]['id']
	
	update_ip_url = (
		"https://api.cloudflare.com/client/v4/zones/%(zone_id)s/dns_records/%(record_id)s"
		% {"zone_id": zone_id, "record_id": record_id}
	)
	
	payload = {"type": "A", "name": record_name, "content": current_ip, "proxied": record_proxied}
	response = requests.put(update_ip_url, headers=headers, data=json.dumps(payload))
	response_dict = json.loads(response.text)
	if response_dict['success']:
		return record_name + " updated successfully" + "\n"

def send_email(subject: str, body: str):
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = config('EMAIL_SENDER_NAME') + " <" + config('EMAIL_SENDER_ADDRESS') + ">"
	msg['To'] = config('EMAIL_RECIPIENT_ADDRESS')
	msg.set_content(body)

	with smtplib.SMTP_SSL(email_server, email_port) as smtp:
		smtp.login(email_auth_addr, email_auth_pass)
		smtp.send_message(msg)
		
# Main
while True:
	current, previous = (current_ip()), (previous_ip())
	if "None" not in { current, previous }:
		if current != previous:
			write_log("IP changed", "Old: " + previous.rstrip('\n'), "New: " + current.rstrip('\n'))
			write_data(current)
			email_body = "IP changed" + "\n" + "Old: " + previous.rstrip('\n') + "\n" + "New: " + current.rstrip('\n') + "\n"
			for record_name in record_names:
				email_body += set_ip(record_name, current)
			send_email("DDNS Updated", email_body)
		elif previous != "None":
			write_log("No change detected")
		truncate_log()
	time.sleep(60)