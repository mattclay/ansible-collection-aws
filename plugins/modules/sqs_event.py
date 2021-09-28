#!/usr/bin/python
# Copyright (C) 2021 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

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
extends_documentation_fragment:
    - amazon.aws.aws
    - amazon.aws.ec2
'''

EXAMPLES = '''
sqs_event:
    source_arn: "arn:aws:sqs:{{ aws_region }}:{{ aws_account_id}}:my_queue.fifo"
    function_arn: "arn:aws:lambda:{{ aws_region }}:{{ aws_account_id }}:function:my_function:{{ stage }}"
    batch_size: 1
'''

import time

try:
    import botocore.exceptions
except ImportError:
    botocore = None

from ansible.module_utils.basic import (
    AnsibleModule,
    missing_required_lib,
)

from ansible_collections.amazon.aws.plugins.module_utils.ec2 import (
    HAS_BOTO3,
    boto3_conn,
    ec2_argument_spec,
    get_aws_connection_info,
)


def main():
    argument_spec = ec2_argument_spec()
    argument_spec.update(dict(
        source_arn=dict(type='str', required=True),
        function_arn=dict(type='str'),
        batch_size=dict(type='int', default=1),
        state=dict(required=False, default='present', type='str', choices=['present', 'absent']),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ['state', 'present', [
                'function_arn',
            ]],
        ],
    )

    if not HAS_BOTO3:
        module.fail_json(msg=missing_required_lib('boto3'))

    region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)

    lambda_client = boto3_conn(module, conn_type='client', resource='lambda', region=region, endpoint=ec2_url, **aws_connect_kwargs)

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
            except botocore.exceptions.ClientError as ex:
                if ex.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise

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
