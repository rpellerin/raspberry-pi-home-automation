# Foreword

MiniDLNA is the former name. The project is now called ReadyMedia. You can find it [here](https://sourceforge.net/projects/minidlna/).

# Install

You may install it through `apt` but you might get an old version (check with `sudo apt search minidlna`). In my case, as of February 2023, I would have gotten version 1.3.0 through `apt`, while 1.3.2 is already out, with `.webm` supported freshly added. So I decided to compile it myself from upstream.

## Manual install

```bash
# Prerequisite
sudo apt install build-essential gettext
# gettext is needed on Raspberry Pi:
# reddit.com/r/raspberry_pi/comments/9qq3y5/readymedia_12x_fails_with_cannot_stat_tdagmo_no/

# Download
wget https://nav.dl.sourceforge.net/project/minidlna/minidlna/1.3.2/minidlna-1.3.2.tar.gz
tar -xvf minidlna-1.3.2.tar.gz
cd minidlna-1.3.2

# Compile
./configure
# Based on errors you got with the above-mentioned command, you'll have to
# sudo apt install libavutil-dev libavcodec-dev libavformat-dev libjpeg-dev libsqlite3-dev libexif-dev \
#   libid3tag0-dev libogg-dev libvorbis-dev libflac-dev
# and relaunch ./configure
make

#Install
sudo make install

sudo mkdir /var/cache/minidlna
sudo mkdir /var/lib/minidlna
sudo chown minidlna:minidlna /var/cache/minidlna
sudo chown minidlna:minidlna /var/lib/minidlna
sudo chmod -R o+rX /var/lib/minidlna

# Configure
sudo cp minidlna.conf /etc/
sudo vim /etc/minidlna.conf
# friendly_name=some_nicer_name_than_the_default_hostname
# log_dir=/var/log
# media_dir=/var/lib/minidlna

# Now copy the service from this repo and start it
sudo cp systemd-services/minidlna.service /etc/systemd/system
sudo systemctl enable minidlna.service
sudo systemctl daemon-reload
sudo systemctl start minidlna.service
```
