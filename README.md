# CF_DDNS

My second Python project and the first one ready for public critique, this is a Python3 script to monitor my home WAN IP for changes and update my Cloudflare DNS records when changes happen. It's replacing a quick and dirty Bash script that does the same thing but doesn't handle unexpected results very well. My desire to start learning Python recently converged with my annoyance at that Bash script constantly sending me junk emails, and this is the result.

When run, the script looks for a file, *ip.txt*, in the same directory as the script. If not found, it writes the current WAN IP to the file and exits. If found, it reads the contents and compares them to the current WAN IP. If the WAN IP is different from the IP read from the file, the specified Cloudflare DNS entries are updated with the new IP, and an email is sent to notify me that the change happened. The email contains the old and new IPs and the results of each Cloudflare DNS record change attempt. The script then waits 60 seconds before running again.

The result of every run is written to a log file, *log.txt*, also in the same directory as the script. The log can be limited to a specific number of lines, I set it to 120 by default so only the last two hours are logged.

#### Sample Log Entries ####

>2022/12/28 13:10:50 - No change detected  
>2022/12/28 15:53:42 - No change detected  
>2022/12/28 15:54:42 - No change detected  
>2022/12/28 15:55:42 - IP changed  
>2022/12/28 15:55:42 - Old: 192.168.1.236  
>2022/12/28 15:55:42 - New: 192.168.1.242  
>2022/12/28 15:57:31 - No change detected  

#### Sample Alert Email Text ####

>From: DDNS Updater <myalertaddress@mydomain.com\>  
>To: Me <me@mydomain.com\>  
>Subject: DDNS Updated  
  
>IP changed  
>Old: 192.168.1.236  
>New: 192.168.1.242  
>server1.mydomain.com updated successfully  
>server2.mydomain.com updated successfully  

#### ENV Information ####

The information needed to update Cloudflare and send emails is stored in *.env*, located in the same directory as the script. Please refer to *sample_env* if you wish to use this script yourself.

#### Future Improvements ####

I'd like to log errors to a second log file that will be more persistent, so I can improve the script to handle those as they come up through normal use.