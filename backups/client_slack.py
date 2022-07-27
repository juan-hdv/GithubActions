from http import HTTPStatus
import json
import requests
import re


class RequestException(Exception):
    def __init__(self, code: int, message: str = "", errors: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message


def send_request(url: str, method: str,  headers: dict, **kwargs):
    response = None
    data = None
    try:
        if method.upper() == "POST":
            response = requests.post(url, headers=headers, **kwargs)
            data = response.text
        elif method.upper() == "GET":
            response = requests.get(url, headers=headers, **kwargs)
            data = response.json()

        if response.status_code != HTTPStatus.OK:
            raise Exception()

        return data

    except Exception:
        code = -1 if response is None else response.status_code # noqa
        raise RequestException(
            code=code,
            message=f"{method} failure. url={url} response_status_code={code} args={kwargs} response={data}",  # noqa
        )


class SlackClient:
    URL = "https://hooks.slack.com/services/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" # noqa

    def publish_message(self, message: str):
        headers = {"Content-type": "application/json"}
        data = {"text": message}

        send_request(self.URL, method="POST", headers=headers, json=data)


class GithubClient:
    TOKEN = "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"
    URL = "https://api.github.com/repos/NomadHealth/nomad-env/pulls"

    def __init__(self) -> None:
        self.pull_requests = []

    @property
    def results(self):
        return self.pull_requests

    def get_pull_requests(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.TOKEN}",
            }
        self.pull_requests = send_request(
            self.URL, method="GET", headers=headers
        )

        return self

    def compact_pull_requests(self, terms: str):
        """
        auto_merge": null
        """
        result = []
        for pr in self.pull_requests:
            # if pr.get("draft"):
            #     continue
            if not terms or any([t in pr.get("title") for t in terms]):
                record = dict(
                    url=pr.get("html_url", ""),
                    id=pr.get(id, ""),
                    state=pr.get("state", ""),
                    body=pr.get("body", ""),
                    created=pr.get("created_at"),
                )
                result.append(record)
        self.pull_requests = result

        return self

    def _get_pr_jira_link(self, pr_jira_code, jira_urls):
        return "https://nomadhealth.atlassian.net/browse/OOO-888"

    def _format_body(self, body: str) -> str:
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
        match = re.match("# Changes\n(.+)\n:robot: auto generated pull request(.+)", body) # noqa
        result = match.group(1)
        jira_urls = match.group(2)

        return jira_urls

        # Get each of the PR info
        pr_re = re.compile("(+ \@\w+ .* \[#\d+\]\(https\:\/\/github.com\/NomadHealth.+\)\n?)")
        match = pr_re.match(result)

        result_string = ""
        k = 1
        while k <= pr_re.groups:
            match = re.match("+ (@\w+) (.*) (\[#\d+\]\(https\:\/\/github.com\/NomadHealth.+\))", pr_re.group(k))
            owner = match.group(1)
            description = match.group(2)
            pr_jira_code = match.group(3)

            # Get the jira ticket in the description
            match = re.match("\[[a-zA-Z]+-[0-9]+\]", pr_jira_code)
            pr_jira_link = self._get_pr_jira_link(pr_jira_code, jira_urls)

            description = description.replace(pr_jira_code, f"[{pr_jira_code}]({pr_jira_link})")
            result_string += f"{pr_jira_code} {description} {owner}\n"

        return result_string

    def format_pull_requests(self):
        result = []
        for pr in self.pull_requests:
            pr["body"] = f"*************** {pr.get('body', '')} *************"
            result.append(pr.get("body", ""))

        self.pull_requests = result
        return self


if __name__ == '__main__':
    demo = True
    if demo:

        github = GithubClient()
        prs = github.get_pull_requests()\
                    .compact_pull_requests(terms=["nomad-flask"])\
                    #.format_pull_requests()
        "Promote", "from dev1 to prod1" "nomad-web-app", "nomad-flask"
        # print(f"****** PULL REQUEST ({len(prs.results)})", prs.results)

        message = "\n".join(json.dumps(pr) for pr in prs.results)
        print(message)

        slack = SlackClient()
        message = f"Following {len(prs.results)} PRs deployed:\n\n{message}" 
        slack.publish_message(message)

    else:
        github = GithubClient()
        body = """
        # Changes
        - @qianshi508 Create draft job crated and updated signal for ML inference [#11234](https://github.com/NomadHealth/nomad-flask/pull/11234)
        - @AgustinJimenezBDev [CXJD-147] Add more params to application completed tracking event [#11231](https://github.com/NomadHealth/nomad-flask/pull/11231)
        - @AgustinJimenezBDev [CXJD-149] - Add more parameters to job viewed tracking event [#11241](https://github.com/NomadHealth/nomad-flask/pull/11241)

        :robot: auto generated pull request


        [CXJD-147]: https://nomadhealth.atlassian.net/browse/CXJD-147?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
        [CXJD-149]: https://nomadhealth.atlassian.net/browse/CXJD-149?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
        """

        match = re.match("# Changes\n(.+)\n:robot: auto generated pull request\n(.+)", body)
        result = match.group(0)
        #jira_urls = match.group(2)

        # result = github._format_body(body)
        # print("Result:", result)
