#!/bin/sh
python3 save_formated_pr_body.py "$PR_BODY">>  $GITHUB_ENV
# FORMATTED_BODY=$(cat result.txt)
echo "++ $GITHUB_ENV ++"
