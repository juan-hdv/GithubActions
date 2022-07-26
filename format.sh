#!/bin/sh
python3 save_formated_pr_body.py > result.txt
FORMATTED_BODY=$(cat result.txt)
echo ---------------------------
echo FORMATTED_BODY
echo ---------------------------
