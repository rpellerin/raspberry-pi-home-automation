#!/bin/bash

SYSLOG=$(/usr/bin/tail -n 500 /var/log/syslog)
/bin/sleep 120
/usr/bin/curl -s -o /dev/null http://localhost:8080/0/action/snapshot
/bin/echo -e "So you know... ($(/bin/date))\n\n$SYSLOG" | /usr/bin/mail -s "Rpi turned on (with syslog) - after 120s" root &
/bin/sleep 25
/usr/bin/curl -s "https://smsapi.free-mobile.fr/sendmsg"
