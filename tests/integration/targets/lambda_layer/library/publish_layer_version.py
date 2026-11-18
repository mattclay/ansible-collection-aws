from __future__ import annotations

import pathlib
import typing as t

import boto3

from ansible.module_utils.basic import AnsibleModule

if t.TYPE_CHECKING:
    from types_boto3_apigateway import Client


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='str', required=True),
            path=dict(type='path', required=True),
        ),
    )

    client: Client = boto3.client('lambda')
    client.publish_layer_version(
        LayerName=module.params['name'],
        Content=dict(
            ZipFile=pathlib.Path(module.params['path']).read_bytes(),
        ),
    )

    module.exit_json()


if __name__ == '__main__':
    main()
