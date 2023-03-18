#!/bin/bash -ex

filename="$1"

date
echo "On `date`" | mail -s "Door opened" -A "$filename" root@localhost
date
echo 'Email sent'
