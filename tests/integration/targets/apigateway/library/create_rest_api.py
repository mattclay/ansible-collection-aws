from __future__ import annotations

import typing as t

import boto3
import botocore.config

from ansible.module_utils.basic import AnsibleModule

if t.TYPE_CHECKING:
    from types_boto3_apigateway import Client


def main() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True, type='str'),
        )
    )

    config = botocore.config.Config(
        retries=dict(
            total_max_attempts=20,
        )
    )

    client: Client = boto3.client('apigateway', config=config)
    result = client.create_rest_api(name=module.params['name'])

    module.exit_json(id=result['id'])


if __name__ == '__main__':
    main()
