#!/usr/bin/python
# Copyright (C) 2021 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: sqs_fifo_queue
short_description: Manage an SQS FIFO queue
description:
    - Manage an SQS FIFO queue.
author:
    - Matt Clay (@mattclay) <matt@mystile.com>
requirements:
    - boto3
options:
    name:
        description:
            - The name of the SQS FIFO queue manage.
        required: true
        type: str
    message_retention_period:
        description:
            - The length of time in seconds for which messages will be retained.
        type: int
    visibility_timeout:
        description:
            - The length of time in seconds for which retrieved messages will be invisible in the queue.
        type: int
    state:
        description:
            - If C(present) the queue will be created if it does not exist.
            - If C(absent) the queue will be deleted if it exists.
        choices:
            - present
            - absent
        default: present
        type: str
extends_documentation_fragment:
    - amazon.aws.common.modules
    - amazon.aws.region.modules
'''

EXAMPLES = '''
sqs_fifo_queue:
    name: my_queue.fifo
    message_retention_period: 3600
    visibility_timeout: 30
'''

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
        name=dict(type='str', required=True),
        message_retention_period=dict(type='int'),
        visibility_timeout=dict(type='int'),
        state=dict(required=False, default='present', type='str', choices=['present', 'absent']),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ['state', 'present', [
                'message_retention_period',
                'visibility_timeout',
            ]],
        ],
    )

    if not HAS_BOTO3:
        module.fail_json(msg=missing_required_lib('boto3'))

    region, ec2_url, aws_connect_kwargs = get_aws_connection_info(module, boto3=True)

    sqs_resource = boto3_conn(module, conn_type='resource', resource='sqs', region=region, endpoint=ec2_url, **aws_connect_kwargs)

    queue_name = module.params['name']
    state = module.params['state']

    requested_attributes = dict(
        MessageRetentionPeriod=str(module.params['message_retention_period']),
        VisibilityTimeout=str(module.params['visibility_timeout']),
    )

    changed = False

    try:
        queue = sqs_resource.get_queue_by_name(QueueName=queue_name)

        if state == 'absent':
            changed = True

            if not module.check_mode:
                queue.delete()
        else:
            if not all(queue.attributes[k] == v for k, v in requested_attributes.items()):
                changed = True

                if not module.check_mode:
                    queue.set_attributes(Attributes=requested_attributes)

    except sqs_resource.meta.client.exceptions.QueueDoesNotExist:
        if state == 'present':
            changed = True

            if not module.check_mode:
                attributes = dict(FifoQueue='true')
                attributes.update(**requested_attributes)

                sqs_resource.create_queue(
                    QueueName=queue_name,
                    Attributes=attributes,
                )

    module.exit_json(changed=changed)


if __name__ == '__main__':
    main()
