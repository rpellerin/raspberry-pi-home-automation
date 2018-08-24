#!/bin/bash

set -u

DATE="$(date)"

args=("$@")

if [ $# -gt 0 ] && [ "${args[0]}" = "--daily" ]; then 
    # echo 'Daily alive script running...'
    echo -e "I am alive. - $DATE\n\n$(df -H /)\n\n$(systemctl status motion | cat)" | mail -s "Raspberry Pi is alive" root
    # Gives it time to finish sending emails, just in case
    sleep 15
    # echo 'Daily report sent'
    exit 0
fi

FILENAME="$(date +%s).tar.gz"
PICS_AND_VIDS="/home/pi/pics_and_vids"
PICS_AND_VIDS_BASENAME="pics_and_vids"
PICS_AND_VIDS_PARENT_DIR="/home/pi"

delete_pics_vids () {
    rm $PICS_AND_VIDS/*.jpg -f
    rm $PICS_AND_VIDS/*.mkv -f
}

# Deletes previous backups, if any
rm $PICS_AND_VIDS_PARENT_DIR/*.tar.gz -f
# sync for df to return the correct values
sync

DISK_SPACE_THRESHOLD=35
DISK_SPACE_THRESHOLD_CANT_BACKUP=$((DISK_SPACE_THRESHOLD + 10))

PERCENT_DISK_USAGE=$(df -H / | grep -vE '^Filesystem|tmpfs|cdrom' | awk '{ print $5 }' | cut -d'%' -f1)

if [ $PERCENT_DISK_USAGE -le $DISK_SPACE_THRESHOLD ]; then
    # echo "Less than $DISK_SPACE_THRESHOLD% of disk space used, doing nothing..."
    exit 0
fi

if [ $PERCENT_DISK_USAGE -ge $DISK_SPACE_THRESHOLD_CANT_BACKUP ]; then
    echo "More than $DISK_SPACE_THRESHOLD_CANT_BACKUP% of disk space used, deleting pics and vids and notifying via email..."
    echo "Little disk space left ($PERCENT_DISK_USAGE% used). CANT BACKUP. - $DATE" | mail -s "Raspberry Pi - DISK USAGE ALERT" root
    # Give time to finish sending email
    sleep 15
    delete_pics_vids
    exit 0
fi

# 2>/dev/null to suppress the output error "No such file or directory"
if [ -n "$(ls -A $PICS_AND_VIDS 2>/dev/null)" ]; then
    # Contains files (or is a file)"
    cd $PICS_AND_VIDS_PARENT_DIR
    tar -cvzf $PICS_AND_VIDS_PARENT_DIR/$FILENAME $PICS_AND_VIDS_BASENAME
    echo "Pics and vids were deleted. Here is a backup of them. - $DATE" | mail -A $FILENAME -s "Raspberry Pi - Backup" root
    delete_pics_vids
    # Give time to finish sending email
    sleep 30
    # Delete backup we just created
    rm $PICS_AND_VIDS_PARENT_DIR/$FILENAME -f
else
    # Empty (or does not exist)
    echo "Little disk space left ($PERCENT_DISK_USAGE% used). No pics or vids found though. - $DATE" | mail -s "Raspberry Pi - DISK USAGE ALERT" root
    # Give time to finish sending email
    sleep 15
fi
