import time
import requests
import json
import smtplib
from datetime import datetime
from decouple import config
from pathlib import Path
from email.message import EmailMessage

# Cloudflare Info
record_names = config('RECORD_NAMES').split(',')
record_proxied = False

WAN_IP_URL = "http://ipv4.icanhazip.com"
DATA_FILE = "{}/{}".format(str(Path(__file__).parent),"ip.txt")
LOG_FILE = "{}/{}".format(str(Path(__file__).parent),"log.txt")
MAX_LOG_LINES = 120

def write_log(*logmessages):
	with open(LOG_FILE, mode='a') as logfile:
		now = datetime.now()
		timestamp = now.strftime("%Y/%m/%d %H:%M:%S")
		for logmessage in logmessages:
			log_entry = f"{timestamp} - {logmessage}\n"
			logfile.writelines(log_entry)
	logfile.close()
	
def truncate_log():
	with open(LOG_FILE, mode='r+') as logfile:
		content = logfile.readlines()
		count = len(content)
		if count > MAX_LOG_LINES:
			with open(LOG_FILE, mode='w') as logfile:
				for line in range(count-MAX_LOG_LINES,count):
					logfile.writelines(content[line])
	logfile.close()
	
def read_data():
	with open(DATA_FILE, mode='r') as datafile:
		return datafile.readline()

def write_data(ip):
	with open(DATA_FILE, mode='w') as datafile:
		datafile.writelines(str(ip))
		datafile.close()
		
def current_ip():
	try:
		response = requests.get(WAN_IP_URL)
		if response.status_code == 200 and response.text != "None":
			return response.text
		else:
			write_log("Connected but could not get the remote IP")
	except requests.exceptions.RequestException as e:
		write_log("Could not connect to get the remote IP")
		return "None"
		
def previous_ip():
	path = Path(DATA_FILE)
	if path.is_file():
		return read_data()
	else:
		write_log(f"Previous IP not recorded, writing to {DATA_FILE}")
		write_data(current_ip())
		return "None"

def set_ip(record_name: str, current_ip: str):
	zone_id_url = f"https://api.cloudflare.com/client/v4/zones/{config('ZONE_ID')}/dns_records?name={record_name}"

	headers= {
		"Authorization": f"Bearer {config('API_TOKEN')}",
		"Content-Type": "application/json",
	}
	
	response = requests.get(zone_id_url, headers=headers)
	record_id = json.loads(response.text)['result'][0]['id']
	
	update_ip_url = f"https://api.cloudflare.com/client/v4/zones/{config('ZONE_ID')}/dns_records/{record_id}"
	
	payload = {"type": "A", "name": record_name, "content": current_ip, "proxied": record_proxied}
	response = requests.put(update_ip_url, headers=headers, data=json.dumps(payload))
	response_dict = json.loads(response.text)
	if response_dict['success']:
		return f"{record_name} updated successfully\n"

def send_email(subject: str, body: str):
	msg = EmailMessage()
	msg['Subject'] = subject
	msg['From'] = f"{config('EMAIL_SENDER_NAME')} <{config('EMAIL_SENDER_ADDRESS')}>"
	msg['To'] = config('EMAIL_RECIPIENT_ADDRESS')
	msg.set_content(body)
	with smtplib.SMTP_SSL(config('EMAIL_SERVER'), config('EMAIL_PORT')) as smtp:
		smtp.login(config('EMAIL_AUTH_ADDRESS'), config('EMAIL_AUTH_PASSWORD'))
		smtp.send_message(msg)
		
# Main
current, previous = (current_ip().rstrip('\n')), (previous_ip().rstrip('\n'))
if "None" not in { current, previous }:
	if current != previous:
		write_log("IP changed", f"Old: {previous}", f"New: {current}")
		write_data(current)
		email_body = f"IP changed\nOld: {previous}\nNew: {current}\n"
		for record_name in record_names:
			email_body += set_ip(record_name, current)
		try:
			send_email("DDNS Updated", email_body)
			write_log("Update email sent successfully")
		except:
			write_log("Update email was not sent successfully")
	elif previous != "None":
		write_log("No change detected")
	truncate_log()
