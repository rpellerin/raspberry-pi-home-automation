#!/bin/bash -ex

subject="$1"
filename="$2"

date
if [ -z "$filename" ]; then
    # $filename is null
    echo "On `date` (no attachment)" | mail -s "$subject" root@localhost
else
    echo "On `date`" | mail -s "$subject" -A "$filename" root@localhost
fi
date
echo 'Email sent'
