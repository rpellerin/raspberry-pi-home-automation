#!/bin/bash -ex

date
echo "On `date`" | mail -s "Door just opened!" root@localhost
date
echo 'Email sent'
