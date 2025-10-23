#!/usr/bin/python
# Copyright (C) 2016 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = '''
---
module: aws_account_facts
short_description: Return information about the AWS account
description:
    - Return information about the AWS account.
author:
    - Matt Clay (@mattclay) <matt@mystile.com>
requirements:
    - boto3
'''

EXAMPLES = '''
aws_account_facts:
'''

from ..module_utils.aws import AwsModule


def main():
    argument_spec = {}

    module = AwsModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    lm = AwsAccountFactsModule(module, module.check_mode, module.params)

    error, facts = lm.run()

    if error is None:
        module.exit_json(changed=False, ansible_facts=facts)
    else:
        module.fail_json(msg=error)


class AwsAccountFactsModule:
    def __init__(self, module: AwsModule, check_mode: bool, params: dict) -> None:
        self.module = module
        self.check_mode = check_mode
        self.params = params

    def run(self):
        facts = dict(
            aws_account_id=self.module.account_id,
        )

        return None, facts


if __name__ == '__main__':
    main()
