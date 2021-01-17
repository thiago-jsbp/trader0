#!/usr/bin/env bash

old_IFS=$IFS
export IFS=
export PYTHONWARNINGS='ignore'

cd ..
rm -f .halt
#rm -fR data logs
mkdir -p data logs

timestamp=$(date -u +'%Y.%m.%d.%Z.%H.%M.%S')
stderr='logs/.stderr'; stdout='logs/.stdout'
echo $'\n'"$timestamp" >> $stdout
echo $'\n'"$timestamp" >> $stderr

python3 -Bm src.bot 1>>$stdout 2>>$stderr &
export IFS=$old_IFS
