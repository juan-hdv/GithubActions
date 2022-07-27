import sys
from datetime import datetime, timezone
import re


class Formatter:

    URL_UNKNOWN = "http://unknown"
    PATTERN_USER = "@[a-zA-Z0-9_-]+"  # noqa #605
    PATTERN_JIRA_CODE = "[a-zA-Z]+-[0-9]+"  # noqa #605
    PATTERN_GITHUB_CODE = "#\d+?"  # noqa #605
    PATTERN_GITHUB_URL = "\(https\:\/\/github\.com\/NomadHealth.+?\)" # noqa #605

    def __init__(self, body) -> None:
        self.body = body

    def error(self, comment=None):
        msg = "Formatting Error:: PR body format not recognized!"
        msg = f"{msg} {comment if comment else ''}"
        msg = f"[{msg}]\n\n{self.body}"

        return msg

    def get_pr_jira_url(self, pr_jira_code, jira_urls_list):
        """ Get the Jira link from the bottom of the body (jira_urls) """
        result = self.URL_UNKNOWN
        for url in jira_urls_list:
            match = re.match(rf"^\[{pr_jira_code}\]:\s*(.+)$", url)
            if match:
                result = match.group(1)
                break

        return result

    def format_body(self) -> str:
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
        if not self.body:
            self.error("Starting formatting... ")

        # Get the text with the list of PRs
        match = re.match(r"^\s*# Changes(.+):robot: auto generated pull request(.+)$", self.body, re.DOTALL) # noqa
        if not match:
            return self.error("NOT found: robot: auto generated pull request...")

        result = match.group(1)
        jira_urls_list = (
            match.group(2).replace(" ", "").replace("`", "").split("\n")
        )
        jira_urls_list = [x for x in jira_urls_list if x.strip("\n ") not in ["\n", ""]]  # noqa

        # Get each of the PR's info
        pr_matches = re.findall(rf"\s*(-\s{self.PATTERN_USER}.*?\[{self.PATTERN_GITHUB_CODE}\]{self.PATTERN_GITHUB_URL})\n?", result, re.DOTALL)  # noqa
        if not pr_matches:
            return self.error(f"PR Partterns not found... ")

        date_obj = datetime.now(timezone.utc)
        date_str = date_obj.strftime("%m/%d/%Y at %H:%M")
        result_string = (
            f"*There was a Production deployment on {date_str} (UTC). It contained the following tickets:*\n\n"  # noqa
            # f"Jira Code | Description | @ Owner | Github Url\n"
            # f"---------   -----------   -------   ----------\n"
        )
        for pr in pr_matches:
            match = re.match(rf"\s*(-\s+{self.PATTERN_USER}.*?\[{self.PATTERN_GITHUB_CODE}\]{self.PATTERN_GITHUB_URL})", pr)  # noqa
            if not match:
                continue

            match = re.match(rf"-\s*({self.PATTERN_USER})\s+(\[{self.PATTERN_JIRA_CODE}\])?(.*?)\[({self.PATTERN_GITHUB_CODE})\]({self.PATTERN_GITHUB_URL})", pr) # noqa
            owner = match.group(1)
            owner = owner.replace("@", "@ ") if owner else "@ unknown"

            pr_jira_code = match.group(2) or "Unknown"
            pr_jira_code = pr_jira_code.strip("][")

            description = match.group(3) or ""
            description = description.strip()

            pr_github_code = match.group(4) or "Unknown"

            pr_github_url = match.group(5) or self.URL_UNKNOWN
            pr_github_url = pr_github_url.strip(")(\n ")

            pr_jira_url = self.get_pr_jira_url(pr_jira_code, jira_urls_list)

            result_string += f"• <{pr_jira_url}|[{pr_jira_code}]> {description} {owner} <{pr_github_url}|[PR: {pr_github_code}]>\n"  # noqa

        return result_string


if __name__ == '__main__':
    # body = sys.argv[1]
    body = """
# Changes
- @stevenbellnomad [SAR-1137] Typo fix [#11323](https://github.com/NomadHealth/nomad-flask/pull/11323)
- @jeancalderon-nomadhealth Fix vaccine records sync [#11322](https://github.com/NomadHealth/nomad-flask/pull/11322)
- @tinawang01 [SAR-1137] Adding promoted jobs in job digest [#11290](https://github.com/NomadHealth/nomad-flask/pull/11290)

:robot: auto generated pull request


[SAR-1137]: https://nomadhealth.atlassian.net/browse/SAR-1137?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
[SAR-1137]: https://nomadhealth.atlassian.net/browse/SAR-1137?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ    
"""
    fmt = Formatter(body)
    print(fmt.format_body())
