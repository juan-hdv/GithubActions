    notification_title = "Changelog notification for a Nomad software promotion"
    promotion_title = "aaa Promote repository-albin 1 from 2"
    github_params = """{
        'actor': 'juan-hdv',
        'repo': 'juan-hdv/GithubActions',
        'ref': 'master',
        'pr_url': 'https://github.com/juan-hdv/GithubActions/pull/246'
    }"""
    body = """
# Changes
- @varunvenkatesh123 [CXCC-1727] Set Flu Vaccine Season Field as Optional [#11525](https://github.com/NomadHealth/nomad-flask/pull/11525)
- @varunvenkatesh123 Requirement Source create API [#11319](https://github.com/NomadHealth/nomad-flask/pull/11319)
- @stevenbellnomad [SAR-1187] Use Redis locks and better tasking implementation for inst… [#11456](https://github.com/NomadHealth/nomad-flask/pull/11456)
- @jeancalderon-nomadhealth [TOFU-1918] Add flu vaccine to profile [#11522](https://github.com/NomadHealth/nomad-flask/pull/11522)
- @rickbassham [ZT-412] Add document management endpoints to nomad-flask [#11427](https://github.com/NomadHealth/nomad-flask/pull/11427)

:robot: auto generated pull request


[CXCC-1727]: https://nomadhealth.atlassian.net/browse/CXCC-1727?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
[SAR-1187]: https://nomadhealth.atlassian.net/browse/SAR-1187?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
[TOFU-1918]: https://nomadhealth.atlassian.net/browse/TOFU-1918?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ
[ZT-412]: https://nomadhealth.atlassian.net/browse/ZT-412?atlOrigin=eyJpIjoiNWRkNTljNzYxNjVmNDY3MDlhMDU5Y2ZhYzA5YTRkZjUiLCJwIjoiZ2l0aHViLWNvbS1KU1cifQ    
"""