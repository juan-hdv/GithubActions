#!/bin/sh
python3 save_formated_pr_body.py "$pr_body"> result.txt
FORMATTED_BODY=$(cat result.txt)
