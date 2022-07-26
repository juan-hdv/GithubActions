import sys
from datetime import datetime
import re


_PATTERN_USER = "@\w+"  # noqa #605
_PATTERN_JIRA_CODE = "\[([a-zA-Z]+-[0-9]+)\]"  # noqa #605
_PATTERN_GITHUB_URL = "\[#\d+?\]\(https\:\/\/github\.com\/NomadHealth.+?\)" # noqa #605


def get_pr_jira_link(pr_jira_code, jira_urls_list):
    """ Get the Jira link from the bottom of the body (jira_urls) """
    result = "http://unknown"
    for url in jira_urls_list:
        match = re.match(rf"^\[{pr_jira_code}\]:\s*(.+)$", url)
        if match:
            result = match.group(1)
            break

    return result


def format_body(body: str, timestamp) -> str:
    """
    Returns a promotion body formated

    Imput example:
    # Changes
    - @qianshi508 Create draft job crated and updated signal for ML inference [#11234](https://github.com/NomadHealth/nomad-flask/pull/11234)
    - @AgustinJimenezBDev [CXJD-147] Add more params to application completed tracking event [#11231](https://github.com/NomadHealth/nomad-flask/pull/11231)
    - @AgustinJimenezBDev [CXJD-149] - Add more parameters to job viewed tracking event [#11241](https://github.com/NomadHealth/nomad-flask/pull/11241)

    :robot: auto generated pull request


    [CXJD-147]: https://nomadhealth.atlassian.net/browse/CXJD-147?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
    [CXJD-149]: https://nomadhealth.atlassian.net/browse/CXJD-149?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ

    Output example:
    There was a Production deployment on MM-DD-YYYY at HH:MM:SS.
    It contained the following tickets:
    [Link 1] Description 1 - PR owner
    [Link 2] Description 2 - PR owner
    """

    # Get the text with the list of PRs
    match = re.match(r"^\s*# Changes(.+):robot: auto generated pull request(.+)$", body, re.DOTALL) # noqa
    result = match.group(1)
    jira_urls_list = match.group(2).replace(" ", "").split("\n")
    jira_urls_list = [x for x in jira_urls_list if x.strip() not in ["\n",""]]

    # Get each of the PR info
    pr_matches = re.findall(rf"\s*(-\s{_PATTERN_USER}.*?{_PATTERN_GITHUB_URL})\n?", result, re.DOTALL)  # noqa

    date_obj = datetime.fromtimestamp(timestamp)
    date_str = date_obj.strftime("%m/%d/%Y at %H:%M:%S")
    result_string = (
        f"There was a Production deployment on {date_str}. It contained the following tickets:\n\n"
        f"Jira Code | Description | Owner | Github Url\n"
        f"---------   -----------   -----   ----------\n"
    )
    for pr in pr_matches:
        match = re.match(rf"-\s({_PATTERN_USER})\s+{_PATTERN_JIRA_CODE}?(.*?)({_PATTERN_GITHUB_URL})", pr) # noqa
        if not match:
            continue
        owner = match.group(1)
        owner = owner.replace("@", "@ ") if owner else "@ unknown"
        pr_jira_code = match.group(2) or "Unknown"
        description = match.group(3) or ""
        pr_github_url = match.group(4) or ""
        pr_jira_link = get_pr_jira_link(pr_jira_code, jira_urls_list)

        #pr_jira_code = pr_jira_code.replace(pr_jira_code, f"[{pr_jira_code}]({pr_jira_link})") # noqa
        result_string += f"- [{pr_jira_code}]({pr_jira_link}) {description} {owner} {pr_github_url}\n\n"  # noqa

    return result_string


if __name__ == '__main__':
    #body = sys.argv[1]
    body = """
    # Changes
    - @qianshi508 Create draft job crated and updated signal for ML inference [#11234](https://github.com/NomadHealth/nomad-flask/pull/11234)
    - @AgustinJimenezBDev [CXJD-147] Add more params to application completed tracking event [#11231](https://github.com/NomadHealth/nomad-flask/pull/11231)
    - @AgustinJimenezBDev [CXJD-149] - Add more parameters to job viewed tracking event [#11241](https://github.com/NomadHealth/nomad-flask/pull/11241)

    :robot: auto generated pull request


    [CXJD-147]: https://nomadhealth.atlassian.net/browse/CXJD-147?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
    [CXJD-149]: https://nomadhealth.atlassian.net/browse/CXJD-149?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
    """

    timestamp = 1658201517
    print(format_body(body, timestamp))
