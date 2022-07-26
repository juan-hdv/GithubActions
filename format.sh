#!/bin/sh
python3 save_formated_pr_body.py "$PR_BODY"> result.txt
FORMATTED_BODY=$(cat result.txt)
echo "+++++ $FORMATTED_BODY +++++"

