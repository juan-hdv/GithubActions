#!/bin/sh
python3 save_formated_pr_body.py "$pr_body"> result.txt
formatted_body=$(cat result.txt)
echo "+++++ $formatted_body +++++"

