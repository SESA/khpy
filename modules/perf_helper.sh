#!/bin/bash
while  pgrep qemu | grep $1 > /dev/null ; do
true
done; 
