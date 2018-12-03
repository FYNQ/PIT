#!/bin/bash
if [ ! -d "/home/user/src/linux-stable" ]; then
    cd /home/user/src && git clone /home/user/linux-stable
    chmod +w -R /home/user/build
fi

sudo service ssh restart && bash && tail -n 100 -f /home/user/info.txt
