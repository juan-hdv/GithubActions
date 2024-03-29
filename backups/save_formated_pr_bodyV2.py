import json
from enum import IntEnum
from datetime import datetime, timezone
import re
import sys


class SlackMessageFormater:
    """
    Receives a list of texts
    and created a slack json object with blocks
    """
    def __init__(self, text_list: list) -> None:
        self.text_list = text_list
        self.formated_list = {"blocks": []}

    def add_divider(self):
        divider = {"type": "divider"}
        self.formated_list.append(divider)

        return self.formated_list

    def add_element(self, text_element: str):
        self.formated_list.append(self.format_element(text_element))
        return self.formated_list

    def format_element(self, text_line: str) -> dict:
        result = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text_line,
            }
        }
        return result

    def format_list(self) -> dict:
        for element in self.text_list:
            self.formated_list["blocks"].append(self.format_element(element))

        return self.formated_list


NOMAD_JIRA_URL = "https://nomadhealth.atlassian.net/browse/"


class FormatterError(IntEnum):

    def __new__(cls, value, description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.description = description

        return obj

    # Informative
    SUCCESS = 0, "Formating successful"

    # Errors
    EMPTY_BODY = 300, "Empty body: PR has an empty body"
    ROBOT_SIGN_MISSING = 320, "Missing sign: robot: auto generated pull request"
    TITLE_MISSING = 340, "Missing title: Missing # Changes"
    PATTERN_NOT_FOUND = 360, "Pattern not found: - @user ... [GithubCode](GithubUrl)"

    # Warnings
    NOT_ALL_PROCESSED = 400, "Not all the PRs in the body matched the expected format"


class Formatter:

    MAX_MESSSAGE_CHARACTERS = 1900

    # https://confluence.atlassian.com/adminjiraserver/changing-the-project-key-format-938847081.html
    PATTERN_JIRA_CODE = "[a-zA-Z][a-zA-Z0-9_]+-[0-9]+"  # noqa #605

    URL_UNKNOWN = "http://unknown"
    PATTERN_USER = "@[a-zA-Z0-9_-]+"  # noqa #605
    PATTERN_GITHUB_CODE = "#\d+"  # noqa #605
    PATTERN_GITHUB_URL = "\(https\:\/\/github\.com\/NomadHealth.+?\)" # noqa #605

    def __init__(self, body) -> None:
        self.body = body
        self.matched_pr_number = 0
        self.expected_pr_number = 0

    def clean_characters(self, text, characters):
        for c in characters:
            text = text.replace(c, "")
        return text

    def error(self, error: FormatterError):
        if error.value == FormatterError.SUCCESS:
            msg = "\n"
            if self.matched_pr_number < self.expected_pr_number:
                warn = FormatterError.NOT_ALL_PROCESSED
                err = f"Formatting Warning [{warn.value}] :: {warn.description}"
                line = '⎯'*(len(err)//3)
                msg = f"\n\n{line}\n{err}\n"
            return msg

        err = f"Formatting Error [{error.value}] :: {error.description}"
        line = '⎯'*(len(err)//3)
        msg = f"{self.body}\n\n{line}\n{err}\n"

        return msg

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

        Output: Slack Blocks
        There was a Production deployment on MM-DD-YYYY at HH:MM:SS.
        It contained the following tickets:
        [Link 1] Description 1 - PR owner
        [Link 2] Description 2 - PR owner
        """
        text_to_parse = self.body.strip()
        if not len(text_to_parse):
            return self.error(FormatterError.EMPTY_BODY)

        text_to_parse = self.clean_characters(text_to_parse, "`'\"][")
        text_to_parse = text_to_parse.replace("\r\n", "\n").replace("\r", "\n")

        # Get the text with the list of PRs
        sections = text_to_parse.split(":robot: auto generated pull request")
        if len(sections) <= 1:
            return self.error(FormatterError.ROBOT_SIGN_MISSING)

        text_to_parse = sections[0]
        sections = text_to_parse.split("# Changes")
        if len(sections) <= 1:
            return self.error(FormatterError.TITLE_MISSING)

        text_to_parse = text_to_parse.lstrip().rstrip()

        # Get each of the PR's info
        pr_matches = re.findall(rf"\s*(-\s{self.PATTERN_USER}.*?{self.PATTERN_GITHUB_CODE}{self.PATTERN_GITHUB_URL})\n?", text_to_parse, re.DOTALL)  # noqa
        if not pr_matches:
            return self.error(FormatterError.PATTERN_NOT_FOUND)

        self.expected_pr_number = text_to_parse.count("\n")
        self.matched_pr_number = len(pr_matches)

        date_obj = datetime.now(timezone.utc)
        date_str = date_obj.strftime("%m/%d/%Y at %H:%M")
        result_string_list = []
        for pr in pr_matches:
            match = re.match(rf"\s*-\s+({self.PATTERN_USER})\s+(.*)({self.PATTERN_GITHUB_CODE})({self.PATTERN_GITHUB_URL})", pr) # noqa
            if not match:
                return self.error(FormatterError.PATTERN_NOT_FOUND)

            owner = match.group(1)
            owner = owner.replace("@", "@ ") if owner else "@ Unknown"

            description = match.group(2) or ""
            description = description.strip()

            matches = re.findall(rf"({self.PATTERN_JIRA_CODE})", description)
            jira_codes_string = ""
            for jira_code in matches:
                jira_code_upper = jira_code.upper()
                jira_url = f"{NOMAD_JIRA_URL}{jira_code_upper}"
                jira_codes_string += f"<{jira_url}|[{jira_code_upper}]> "

            jira_codes_string = jira_codes_string.rstrip()
            if not jira_codes_string:
                jira_codes_string += f"<{self.URL_UNKNOWN}|[Unknown]>"

            pr_github_code = match.group(3) or "Unknown"
            pr_github_url = match.group(4) or self.URL_UNKNOWN
            pr_github_url = pr_github_url.strip(")(\n ")

            result_string_list.append(
                f"• {jira_codes_string}: {description} {owner} <{pr_github_url}|[PR: {pr_github_code}]>\n"
            )  # noqa

        # result_string_list = result_string_list.extend(
        #     self.error(FormatterError.SUCCESS)
        # )

        # result_string = (
        #     f"\nThere was a Production deployment on {date_str} (UTC), "
        #     f"containing the following tickets:\n\n"
        # )

        slack_formater = SlackMessageFormater(result_string_list)
        slack_formater.format_list()

        return slack_formater.formated_list


if __name__ == '__main__':
    #body = sys.argv[1]
    body = """
# Changes
- @gafalcon AH-7/Create respiratory therapist in house checklist assesment [#11372](https://github.com/NomadHealth/nomad-flask/pull/11372)
- @gafalcon AH-28/Migration to update ah jobs covid reqs from MSPs reqs [#11301](https://github.com/NomadHealth/nomad-flask/pull/11301)
- @stevenbellnomad [SAR-1160] Add new Worker for Celery [#11398](https://github.com/NomadHealth/nomad-flask/pull/11398)
- @varunvenkatesh123 Facility Template Delete API [#11395](https://github.com/NomadHealth/nomad-flask/pull/11395)
- @dummerbd Remove outdated certifications adapter [#11396](https://github.com/NomadHealth/nomad-flask/pull/11396)
- @blackwood-nomad AH-9: add Radiology Technologist Assessment [#11386](https://github.com/NomadHealth/nomad-flask/pull/11386)
- @tinawang01 [AH-29] Support certification-dependent state license validation for Cath Lab [#11353](https://github.com/NomadHealth/nomad-flask/pull/11353)
- @gafalcon AH-50/Change Rad tech and Cath Lab Tech Labels [#11360](https://github.com/NomadHealth/nomad-flask/pull/11360)
- @dummerbd ZT-363 Update codeowners [#11394](https://github.com/NomadHealth/nomad-flask/pull/11394)
- @dummerbd [ZT-360] Refactor application adapter service to support saving credentials [#11367](https://github.com/NomadHealth/nomad-flask/pull/11367)
- @eakman-nomad fix: updates version of nomad-env SRE-642 [#11392](https://github.com/NomadHealth/nomad-flask/pull/11392)
- @zhang8128 [CXJD-120] Public Job Details API [#11185](https://github.com/NomadHealth/nomad-flask/pull/11185)
- @djru Updated readme for job robotix [#11380](https://github.com/NomadHealth/nomad-flask/pull/11380)

:robot: auto generated pull request


[SAR-1160]: https://nomadhealth.atlassian.net/browse/SAR-1160?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
[AH-29]: https://nomadhealth.atlassian.net/browse/AH-29?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
[ZT-360]: https://nomadhealth.atlassian.net/browse/ZT-360?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
"""
    fmt = Formatter(body)
    slack_content = fmt.format_body()
    print(json.dumps(slack_content))
    # print(fmt.format_body())
