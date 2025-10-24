#!/usr/bin/python
# Copyright (C) 2016 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = '''
---
module: cloudwatch_event
short_description: Manage scheduled CloudWatch Events
description:
    - Manage scheduled CloudWatch Events.
author:
    - Matt Clay (@mattclay) <matt@mystile.com>
requirements:
    - boto3
options:
    rule_name:
        description:
            - The unique name of the rule.
        required: true
        type: str
    function_name:
        description:
            - The Lambda function to invoke when the rule is triggered.
        required: true
        type: str
    schedule_expression:
        description:
            - The schedule to use for the rule.
        required: true
        type: str
    description:
        description:
            - Description of the rule.
        type: str
        default: ''
    state:
        description:
            - If C(enabled) the rule will exist and be enabled.
            - If C(disabled) the rule will exist and be disabled.
            - If C(absent) the rule will not exist.
        choices:
            - enabled
            - disabled
            - absent
        default: enabled
        type: str
'''

EXAMPLES = '''
cloudwatch_event:
    region: us-east-1
    rule_name: my_rule
    schedule_expression: rate(5 minutes)
    function_name: my_function_name:some_alias
'''

import uuid

from ..module_utils.aws import AwsModule


def main():
    argument_spec = dict(
        rule_name=dict(required=True, type='str'),
        function_name=dict(required=True, type='str'),
        schedule_expression=dict(required=True, type='str'),
        description=dict(required=False, default='', type='str'),
        state=dict(required=False, default='enabled', type='str', choices=['enabled', 'disabled', 'absent']),
    )

    module = AwsModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    em = EventsModule(module, module.check_mode, module.params)

    error, changed, result = em.run()

    if error is None:
        module.exit_json(changed=changed, meta=result)
    else:
        module.fail_json(msg=error, meta=result)


class EventsModule:
    def __init__(self, module: AwsModule, check_mode: bool, params: dict) -> None:
        self.module = module
        self.check_mode = check_mode
        self.params = params
        self.events = module.client.events

    def run(self):
        account_id = self.module.account_id
        region = self.module.region

        if not self.params['function_name'].startswith('arn:aws:iam:'):
            self.params['function_name'] = 'arn:aws:lambda:%s:%s:function:%s' % (region, account_id, self.params['function_name'])

        choice_map = dict(
            enabled=self.function_present,
            disabled=self.function_present,
            absent=self.function_absent,
        )

        return choice_map.get(self.params['state'])()

    def function_present(self):
        remote_rule = self.get_rule()

        if remote_rule is None:
            return self.put_rule()

        return self.put_rule(remote_rule)

    def function_absent(self):
        raise Exception('FIXME: not implemented')

    def get_rule(self):
        try:
            return self.events.describe_rule(Name=self.params['rule_name'])
        except self.events.exceptions.ResourceNotFoundException:
            return None

    def put_rule(self, remote_rule=None):
        local_rule = dict(
            Name=self.params['rule_name'],
            ScheduleExpression=self.params['schedule_expression'],
            State=self.params['state'].upper(),
            Description=self.params['description'],
        )

        data = {}

        if remote_rule is None:
            rule_changed = True
            target_changed = True
        else:
            rule_changed = any(k for k in local_rule if local_rule[k] != remote_rule.get(k, ''))
            targets = self.events.list_targets_by_rule(Rule=self.params['rule_name'])['Targets']
            targets = [target for target in targets if target['Arn'] == self.params['function_name']]
            target_changed = not bool(targets)
            data.update(remote_rule)

        data.update(local_rule)

        if rule_changed and not self.check_mode:
            self.events.put_rule(**local_rule)

        if target_changed and not self.check_mode:
            self.events.put_targets(
                Rule=self.params['rule_name'],
                Targets=[
                    dict(
                        Id=str(uuid.uuid4()),
                        Arn=self.params['function_name'],
                    ),
                ],
            )

        results = dict(
            rule_name=data['Name'],
            schedule_expression=data['ScheduleExpression'],
            state=data['State'].lower(),
            description=data['Description'],
        )

        if 'Arn' in data:
            more = dict(
                rule_arn=data['Arn'],
            )

            results.update(more)

        if rule_changed or target_changed:
            return None, True, results

        return None, False, results


if __name__ == '__main__':
    main()
