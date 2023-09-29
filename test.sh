#!/bin/bash

cd client/data
rm -r ./*

IFS=$'\n'
for cmds in `cat ../../cmd`
do
        read -p "Press Enter to continue..."

        # Remove the ^M character from the command
        cmd=$(tr -d '\r' <<< "$cmds")

        if [  $cmd ] ; then
                echo $cmd;
                eval $cmd;
        fi
done