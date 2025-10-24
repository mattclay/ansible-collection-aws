#!/usr/bin/python
# Copyright (C) 2021 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = '''
---
module: sqs_event
short_description: Manage SQS event source mappings
description:
    - Manage SQS event source mappings.
author:
    - Matt Clay (@mattclay) <matt@mystile.com>
requirements:
    - boto3
options:
    source_arn:
        description:
            - The source ARN.
        required: true
        type: str
    function_arn:
        description:
            - The function ARN.
        type: str
    batch_size:
        description:
            - The batch size.
        type: int
        default: 1
    state:
        description:
            - If C(present) the event mapping will be created if it does not exist.
            - If C(absent) the event mapping will be deleted if it exists.
        choices:
            - present
            - absent
        default: present
        type: str
'''

EXAMPLES = '''
sqs_event:
    source_arn: "arn:aws:sqs:{{ aws_region }}:{{ aws_account_id}}:my_queue.fifo"
    function_arn: "arn:aws:lambda:{{ aws_region }}:{{ aws_account_id }}:function:my_function:{{ stage }}"
    batch_size: 1
'''

import time

from ..module_utils.aws import AwsModule


def main():
    argument_spec = dict(
        source_arn=dict(type='str', required=True),
        function_arn=dict(type='str'),
        batch_size=dict(type='int', default=1),
        state=dict(required=False, default='present', type='str', choices=['present', 'absent']),
    )

    module = AwsModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ['state', 'present', [
                'function_arn',
            ]],
        ],
    )

    lambda_client = module.client.awslambda

    source_arn = module.params['source_arn']
    function_arn = module.params['function_arn']
    state = module.params['state']

    common_attributes = dict(
        BatchSize=module.params['batch_size'],
    )

    requested_attributes = dict(FunctionName=function_arn)
    requested_attributes.update(**common_attributes)

    expected_attributes = dict(FunctionArn=function_arn)
    expected_attributes.update(**common_attributes)

    changed = False

    result = lambda_client.list_event_source_mappings(
        EventSourceArn=source_arn,
        MaxItems=2,
    )

    mappings = result.get('EventSourceMappings', [])

    if mappings:
        if len(mappings) > 1:
            module.fail_json(msg='Source has multiple mappings. This module does not support multiple mappings.')

        mapping = mappings[0]
        mapping_uuid = mapping['UUID']

        if state == 'absent':
            try:
                wait_until_ready(lambda_client, mapping)
                changed = True
            except lambda_client.exceptions.ResourceNotFoundException:
                changed = False

            if changed and not module.check_mode:
                lambda_client.delete_event_source_mapping(UUID=mapping_uuid)
        else:
            if not all(mapping[k] == v for k, v in expected_attributes.items()):
                changed = True

                if not module.check_mode:
                    kwargs = dict(UUID=mapping_uuid)
                    kwargs.update(**requested_attributes)
                    wait_until_ready(lambda_client, mapping)
                    lambda_client.update_event_source_mapping(**kwargs)
    elif state == 'present':
        changed = True

        if not module.check_mode:
            kwargs = dict(EventSourceArn=source_arn)
            kwargs.update(**requested_attributes)
            lambda_client.create_event_source_mapping(**kwargs)

    module.exit_json(changed=changed)


def wait_until_ready(lamda_client, mapping):
    for attempt in range(10):
        state = mapping['State']

        if state in ('Enabled', 'Disabled'):
            return

        time.sleep(10)

        mapping = lamda_client.get_event_source_mapping(UUID=mapping['UUID'])


if __name__ == '__main__':
    main()
