import json
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
    REPO_NAME_MISSING = 380, "Error :: Repository name not found: - Promote <repo-name>"


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

    def add_text(self, text_element: str = ""):
        text_section = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text_element,
            }
        }
        self.formatted_list[self.BLOCK_KEY].append(text_section)

        return self.formatted_list

    def add_list(self, text_list) -> dict:
        for text_element in text_list:
            self.add_text(text_element)

        return self.formatted_list

    def add_fields(self, fields: dict):
        field_list = []
        for key, v in fields.items():
            value = f"<{v}|{key}>" if "url" in key else v
            field_list.append({"type": "mrkdwn", "text": f"{key}: {value}"})

        fields_element = {"type": "section", "fields": field_list}

        self.formatted_list[self.BLOCK_KEY].append(fields_element)

        return self.formatted_list


class Formatter:
    # https://confluence.atlassian.com/adminjiraserver/changing-the-project-key-format-938847081.html
    PATTERN_REPO_NAME = "[a-z-/_]+"  # noqa #605
    PATTERN_JIRA_CODE = "[a-zA-Z][a-zA-Z0-9_]+-[0-9]+"  # noqa #605
    URL_UNKNOWN = "http://unknown"

    PATTERN_USER = "@[a-zA-Z0-9_-]+"  # noqa #605
    PATTERN_GITHUB_CODE = "#\d+"  # noqa #605
    PATTERN_GITHUB_URL = "\(https\:\/\/github\.com\/NomadHealth.+?\)" # noqa #605

    def __init__(
        self,
        notification_title: str,
        promotion_title: str,
        body: str,
        params: str
    ) -> None:
        self.body = body
        self.notification_title = notification_title
        self.promotion_title = promotion_title
        self.params = json.loads(params.replace("'", '"'))
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
        pr_matches = re.findall(
            rf"\s*(-\s{self.PATTERN_USER}.*?{self.PATTERN_GITHUB_CODE}{self.PATTERN_GITHUB_URL})\n?", # noqa #501
            text_to_parse,
            re.DOTALL
        )
        if not pr_matches:
            return FormatterError.PATTERN_NOT_FOUND, [self.body]

        self.expected_pr_number = text_to_parse.count("\n")
        self.matched_pr_number = len(pr_matches)

        result_string_list = []
        for pr in pr_matches:
            match = re.match(
                rf"\s*-\s+({self.PATTERN_USER})\s+(.*)({self.PATTERN_GITHUB_CODE})({self.PATTERN_GITHUB_URL})", pr) # noqa #501
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
                f"• {jira_codes_string}: {description} {owner}"
                f" <{pr_github_url}|[PR: {pr_github_code}]>\n"
            )  # noqa

        if self.matched_pr_number < self.expected_pr_number:
            return FormatterError.NOT_ALL_PROCESSED, result_string_list

        return FormatterError.SUCCESS, result_string_list

    def process_parameters(self) -> dict:
        """ Particular formating for params """
        match = re.match(
            rf"^Promote\s({self.PATTERN_REPO_NAME})\s*.*$",
            self.promotion_title,
            re.IGNORECASE
        )
        if not match:
            return FormatterError.REPO_NAME_MISSING, [self.body]

        repo_name = match.group(1)
        self.params["repo"] = f"NomadHealth/{repo_name.lower()}"

    def to_slack_format(self) -> dict:
        slack_formater = SlackMessageFormater()

        self.process_parameters()

        slack_formater.add_text(f"*{self.notification_title}*")
        slack_formater.add_fields(self.params)
        slack_formater.add_divider()

        error, pr_string_list = self._create_github_pr_string_list()

        date_obj = datetime.now(timezone.utc)
        date_str = date_obj.strftime("%m/%d/%Y at %H:%M")
        header = (
            f"\nThere was a Production deployment on {date_str} (UTC), "
            f"containing the following tickets:\n\n"
        )
        slack_formater.add_text(header)

        bottom_message = None
        if error != FormatterError.SUCCESS:
            bottom_message = f"[ {error.value} ] {error.description}"

        if error in [FormatterError.SUCCESS, FormatterError.NOT_ALL_PROCESSED]:
            slack_formater.add_list(pr_string_list)
        else:
            slack_formater.add_text(pr_string_list[0])

        if bottom_message is not None:
            slack_formater.add_text("\n")
            slack_formater.add_divider()
            slack_formater.add_text(bottom_message)

        return slack_formater.formatted_list


if __name__ == '__main__':
    notification_title = sys.argv[1]
    promotion_title = sys.argv[2]
    body = sys.argv[3]
    github_params = sys.argv[4]

    fmt = Formatter(
        notification_title=notification_title,
        promotion_title=promotion_title,
        body=body,
        params=github_params
    )
    body_content = fmt.to_slack_format()
    body_content = fmt.to_slack_format()

    print(json.dumps(body_content["blocks"]))
