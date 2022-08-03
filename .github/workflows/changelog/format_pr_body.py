import json
from typing import Optional
from enum import IntEnum
from datetime import datetime, timezone
import re
import sys


NOMAD_JIRA_URL = "https://nomadhealth.atlassian.net/browse/"


class FormatterError(IntEnum):

    def __new__(cls, value, description=''):
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.description = description

        return obj

    # Informative
    SUCCESS = 0, "Formating successful"

    # Warnings
    NOT_ALL_PROCESSED = 100, "Warning :: Not all the PRs in the body matched the expected format"

    # Errors
    EMPTY_BODY = 300, "Error :: Empty body: PR has an empty body"
    ROBOT_SIGN_MISSING = 320, "Error :: Missing sign: robot: auto generated pull request"
    TITLE_MISSING = 340, "Error :: Missing title: Missing # Changes"
    PATTERN_NOT_FOUND = 360, "Error :: Pattern not found: - @user ... [GithubCode](GithubUrl)"


class SlackMessageFormater:
    """
    Receives a list of texts
    and created a slack json object with blocks
    """
    BLOCK_KEY = "blocks"

    def __init__(self) -> None:
        self.formatted_list = {"blocks": []}

    def add_divider(self):
        divider = {"type": "divider"}
        self.formatted_list[self.BLOCK_KEY].append(divider)

        return self.formatted_list

    def add_element(self, text_element: str = ""):
        block_element = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text_element,
            }
        }
        self.formatted_list[self.BLOCK_KEY].append(block_element)

        return self.formatted_list

    def add_list(self, text_list) -> dict:
        for text_element in text_list:
            self.add_element(text_element)

        return self.formatted_list

    def add_fields(self, fields: dict):
        field_list = []
        for key, v in fields.items():
            value = f"<{v}|{key.upper()}>" if "url" in key else v
            field_list.append({"type": "mrkdwn", "text": f"{key}: {value}"})

        section_element = {"type": "section", "fields": field_list}

        self.formatted_list[self.BLOCK_KEY].append(section_element)

        return self.formatted_list


class Formatter:
    # https://confluence.atlassian.com/adminjiraserver/changing-the-project-key-format-938847081.html
    PATTERN_JIRA_CODE = "[a-zA-Z][a-zA-Z0-9_]+-[0-9]+"  # noqa #605

    URL_UNKNOWN = "http://unknown"
    PATTERN_USER = "@[a-zA-Z0-9_-]+"  # noqa #605
    PATTERN_GITHUB_CODE = "#\d+"  # noqa #605
    PATTERN_GITHUB_URL = "\(https\:\/\/github\.com\/NomadHealth.+?\)" # noqa #605

    def __init__(self, body: str, title: str, params: str) -> None:
        self.body = body
        self.title = title
        # self.params = json.loads(github_params)
        self.matched_pr_number = 0
        self.expected_pr_number = 0

    def _clean_characters(self, text, characters):
        for c in characters:
            text = text.replace(c, "")
        return text

    def _create_github_pr_string_list(self) -> list:
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

        Output:
            (Error, List of strings to be shown as Slack Blocks, with the content)
        There was a Production deployment on MM-DD-YYYY at HH:MM:SS.
        It contained the following tickets:
        [Link 1] Description 1 - PR owner
        [Link 2] Description 2 - PR owner
        ...
        """
        text_to_parse = self.body.strip()
        if not len(text_to_parse):
            return FormatterError.EMPTY_BODY, [self.body]

        text_to_parse = self._clean_characters(text_to_parse, "`'\"][")
        text_to_parse = text_to_parse.replace("\r\n", "\n").replace("\r", "\n")

        # Get the text with the list of PRs
        sections = text_to_parse.split(":robot: auto generated pull request")
        if len(sections) <= 1:
            return FormatterError.ROBOT_SIGN_MISSING, [self.body]

        text_to_parse = sections[0]
        sections = text_to_parse.split("# Changes")
        if len(sections) <= 1:
            return FormatterError.TITLE_MISSING, [self.body]

        text_to_parse = text_to_parse.lstrip().rstrip()

        # Get each of the PR's info
        pr_matches = re.findall(rf"\s*(-\s{self.PATTERN_USER}.*?{self.PATTERN_GITHUB_CODE}{self.PATTERN_GITHUB_URL})\n?", text_to_parse, re.DOTALL)  # noqa
        if not pr_matches:
            return FormatterError.PATTERN_NOT_FOUND, [self.body]

        self.expected_pr_number = text_to_parse.count("\n")
        self.matched_pr_number = len(pr_matches)

        result_string_list = []
        for pr in pr_matches:
            match = re.match(rf"\s*-\s+({self.PATTERN_USER})\s+(.*)({self.PATTERN_GITHUB_CODE})({self.PATTERN_GITHUB_URL})", pr) # noqa
            if not match:
                return FormatterError.PATTERN_NOT_FOUND, [self.body]

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

        if self.matched_pr_number < self.expected_pr_number:
            return FormatterError.NOT_ALL_PROCESSED, result_string_list

        return FormatterError.SUCCESS, result_string_list

    def to_slack_format(self) -> dict:
        slack_formater = SlackMessageFormater()

        slack_formater.add_element(f"*{self.title}*")
        # slack_formater.add_fields(self.params)
        slack_formater.add_divider()

        error, pr_string_list = self._create_github_pr_string_list()

        date_obj = datetime.now(timezone.utc)
        date_str = date_obj.strftime("%m/%d/%Y at %H:%M")
        header = (
            f"\nThere was a Production deployment on {date_str} (UTC), "
            f"containing the following tickets:\n\n"
        )
        slack_formater.add_element(header)

        bottom_message = None
        if error != FormatterError.SUCCESS:
            bottom_message = f"[ {error.value} ] {error.description}"

        if error in [FormatterError.SUCCESS, FormatterError.NOT_ALL_PROCESSED]:
            slack_formater.add_list(pr_string_list)
        else:
            slack_formater.add_element(pr_string_list[0])

        if bottom_message is not None:
            slack_formater.add_element("\n")
            slack_formater.add_divider()
            slack_formater.add_element(bottom_message)

        return slack_formater.formatted_list


if __name__ == '__main__':
    body = sys.argv[1]
    github_params = sys.argv[2]

    # github_params = '{ "actor": "juan-hdv", "repo": "juan-hdv/GithubActions", "ref": "refs/heads/main", "pr_url": "https://github.com/juan-hdv/GithubActions/pull/221"}'

    body="""
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
    title = "Changelog notification for a Nomad software promotion"
    title = github_params.replace("'", '"')

    fmt = Formatter(body=body, title=title, params=github_params)

    body_content = fmt.to_slack_format()

    print(json.dumps(body_content["blocks"]))
