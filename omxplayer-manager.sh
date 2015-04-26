#!/bin/bash

SERVICE="/usr/bin/[o]mxplayer"
IS_RUNNING="n"

if ps ax | grep -v grep | grep $SERVICE > /dev/null
then
	IS_RUNNING="y"
else
	IS_RUNNING="n"
fi

if [[ $1 == "kill" ]];
then
	if [[ $IS_RUNNING == "y" ]];
	then
		kill $(ps aux | grep '/usr/bin/[o]mxplayer' | awk '{print $2}')
		echo "process killed"
	else
		echo "no process running to kill"
	fi
else
	echo $IS_RUNNING
fi