# Copyright (C) 2016 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations

DOCUMENTATION = '''
---
module: lambda
short_description: Manage Lambda functions
description:
    - Manage Lambda functions.
author:
    - Matt Clay (@mattclay) <matt@mystile.com>
requirements:
    - boto3
options:
    function_name:
        description:
            - The name of the Lambda function.
        type: str
        required: true
        aliases:
            - name
    runtime:
        description:
            - The runtime used to execute the Lambda function.
        type: str
    role:
        description:
            - The role used to execute the Lambda function.
        type: str
    handler:
        description:
            - The name of the handler (entry point) for the Lambda function.
        type: str
    local_path:
        description:
            - Path to a ZIP file containing the code of the Lambda function.
        type: str
    description:
        description:
            - The description of the Lambda function.
        type: str
        default: ''
    timeout:
        description:
            - The timeout (in minutes) for execution of the Lambda function.
        default: 3
        type: int
    memory_size:
        description:
            - The memory limit (in MB) for execution of the Lambda function.
        default: 128
        type: int
    publish:
        description:
            - Publish the Lambda function.
        default: false
        type: bool
    qualifier:
        description:
            - The alias to use when publishing the Lambda function.
            - The version of a Lambda function to remove (or all versions if not specified).
        type: str
    state:
        description:
            - If C(present) the Lambda function will be created if it does not exist.
            - If C(absent) the Lambda function will be removed if it does not exist.
        choices:
            - present
            - absent
        default: present
        type: str
    preserve_environment:
        description:
            - Preserve the existing environment variables already configured for the Lambda function.
        default: false
        type: bool
    environment:
        description:
            - Environment variables to provide during execution of the Lambda function.
        type: dict
    layers:
        description:
            - A list of layers used by the Lambda function.
        type: list
        elements: str
    log_format:
        description:
            - The format of the Lambda function logs sent to CloudWatch.
        type: str
        default: Text
        choices:
            - JSON
            - Text
    log_group:
        description:
            - The CloudWatch log group to send the Lambda function logs to.
            - If not set, the default log group named after the function will be used.
        type: str
    application_log_level:
        description:
            - The log level filter for Lambda function log messages sent to CloudWatch.
            - Only messages at the selected level and lower are logged, with C(fatal) being the lowest level.
            - Ignored when log_format is not JSON.
        type: str
        default: info
        choices:
            - trace
            - debug
            - info
            - warn
            - error
            - fatal
    system_log_level:
        description:
            - The log level filter for Lambda system log messages sent to CloudWatch.
            - Only messages at the selected level and lower are logged, with C(warn) being the lowest level.
            - Ignored when log_format is not JSON.
        type: str
        default: info
        choices:
            - debug
            - info
            - warn
'''

EXAMPLES = '''
lambda:
    region: us-east-1
    name: my_function
    local_path: my_function.zip
    runtime: python3.15
    timeout: 60
    handler: my_function.lambda_handler
    memory_size: 128
    role: my_lambda_role
    publish: true
    qualifier: prod
    environment:
        API_KEY: some_value
'''

import base64
import hashlib
import time

from ..module_utils.aws import AwsModule


def main():
    argument_spec = dict(
        function_name=dict(required=True, type='str', aliases=['name']),
        runtime=dict(required=False, type='str'),
        role=dict(required=False, type='str'),
        handler=dict(required=False, type='str'),
        local_path=dict(required=False, default=None, type='str'),
        description=dict(required=False, default='', type='str'),
        timeout=dict(required=False, default=3, type='int'),
        memory_size=dict(required=False, default=128, type='int'),
        publish=dict(required=False, default=False, type='bool'),
        qualifier=dict(required=False, default=None, type='str'),
        state=dict(required=False, default='present', type='str', choices=['present', 'absent']),
        preserve_environment=dict(required=False, default=False, type='bool'),
        environment=dict(required=False, default=None, type='dict'),
        layers=dict(required=False, default=None, type='list', elements='str'),
        log_format=dict(required=False, default='Text', type='str', choices=['JSON', 'Text']),
        log_group=dict(required=False, default=None, type='str'),
        application_log_level=dict(required=False, default='info', type='str', choices=['trace', 'debug', 'info', 'warn', 'error', 'fatal']),
        system_log_level=dict(required=False, default='info', type='str', choices=['debug', 'info', 'warn']),
    )

    module = AwsModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ["state", "present", ["local_path", "handler", "role", "runtime"]],
        ],
    )

    lm = LambdaModule(module, module.check_mode, module.params)

    changed, result = lm.run()

    module.exit_json(changed=changed, meta=result)


class LambdaModule:
    def __init__(self, module: AwsModule, check_mode: bool, params: dict) -> None:
        self.module = module
        self.check_mode = check_mode
        self.params = params
        self.al = module.client.awslambda

    def run(self):
        if self.params['role'] and not self.params['role'].startswith('arn:aws:iam:'):
            account_id = self.module.account_id

            self.params['role'] = f'arn:aws:iam::{account_id}:role/{self.params["role"]}'

        choice_map = dict(
            present=self.function_present,
            absent=self.function_absent,
        )

        return choice_map.get(self.params['state'])()

    def function_present(self):
        qualifier = self.params['qualifier']
        remote_function = self.get_function(qualifier)

        if qualifier is not None and remote_function is None:
            # function not found by qualifier, look for $LATEST instead
            remote_function = self.get_function(None)

        if remote_function is None:
            return self.create_function()

        return self.update_function(remote_function)

    def function_absent(self):
        qualifier = self.params['qualifier']
        remote_function = self.get_function(qualifier)

        if not remote_function:
            return False, {}

        args = dict(
            FunctionName=self.params['function_name'],
        )

        if qualifier is not None:
            args.update(Qualifier=qualifier)

        if not self.check_mode:
            self.al.delete_function(**args)

        return True, args

    def get_function(self, qualifier):
        args = {}

        if qualifier is not None:
            args['Qualifier'] = qualifier

        try:
            result = self.al.get_function_configuration(
                FunctionName=self.params['function_name'],
                **args,
            )
        except self.al.exceptions.ResourceNotFoundException:
            return None

        if result.get('Layers'):
            result['Layers'] = [layer['Arn'] for layer in result['Layers']]

        return result

    def get_package(self):
        local_path = self.params['local_path']

        with open(local_path, 'rb') as f:
            local_contents = f.read()

        return local_contents

    def create_function(self):
        args = self.make_function_configuration()
        args['Code'] = self.make_function_code()
        args['Publish'] = self.params['publish']

        if not self.check_mode:
            if not args['Layers']:
                del args['Layers']

            if not args['Environment']:
                del args['Environment']

            api = self.al.create_function(**args)

            self.wait_on_create()

            result = self.make_result(api)
        else:
            result = self.make_result(args)
            result['version'] = 1

        return True, result

    def update_function(self, remote_function):
        package = self.get_package()

        local_hash = base64.b64encode(hashlib.sha256(package).digest()).decode('ascii')
        remote_hash = remote_function['CodeSha256']

        local_config = self.make_function_configuration()

        if self.params['preserve_environment']:
            local_config['Environment'] = remote_function.get('Environment')

        remote_config = {k: remote_function.get(k, None) for k in local_config}

        code_changed = local_hash != remote_hash
        config_changed = any(k for k in local_config if not self.are_equal(local_config[k], remote_config[k]))

        if self.params['publish'] and remote_function['Version'] == '$LATEST':
            # force code update (and publishing) since version found is $LATEST
            code_changed = True

        if self.params['publish'] and config_changed and not code_changed:
            # force code update (and publishing) since updating config alone doesn't support publishing
            code_changed = True

        if self.params['publish'] and remote_function['Version'] != '$LATEST' and (code_changed or config_changed):
            # when publishing changes we must update config and code since we can only publish from latest
            code_changed = True
            config_changed = True

        config = self.update_function_configuration(local_config, config_changed)
        code = self.update_function_code(code_changed)

        data = {}
        data.update(remote_function)
        data.update(config)
        data.update(code)

        result = self.make_result(data)

        if code_changed or config_changed:
            return True, result

        return False, result

    def are_equal(self, first, second):
        if isinstance(first, dict):
            if not isinstance(second, dict):
                return False

            for key in set(first) | set(second):
                if key not in first or key not in second:
                    return False

                if not self.are_equal(first[key], second[key]):
                    return False

        return first == second

    def update_function_configuration(self, args, changed):
        if changed and not self.check_mode:
            if not args['Layers']:
                del args['Layers']

            if not args['Environment']:
                del args['Environment']

            result = self.al.update_function_configuration(**args)

            self.wait_on_function()

            return result

        return args

    def wait_on_create(self):
        status = 'Pending'

        while status == 'Pending':
            time.sleep(1)
            status = self.get_function(None)['State']

    def wait_on_function(self):
        status = 'InProgress'

        while status == 'InProgress':
            time.sleep(1)
            status = self.get_function(None)['LastUpdateStatus']

    def update_function_code(self, changed):
        args = self.make_function_code()
        args['FunctionName'] = self.params['function_name']
        args['Publish'] = self.params['publish']

        if changed and not self.check_mode:
            result = self.al.update_function_code(**args)

            self.wait_on_function()

            return result

        return args

    def make_result(self, data):
        result = dict(
            function_name=data['FunctionName'],
            runtime=data['Runtime'],
            role=data['Role'],
            handler=data['Handler'],
            description=data['Description'],
            timeout=data['Timeout'],
            memory_size=data['MemorySize'],
            environment=(data.get('Environment') or {}).get('Variables') or {},
            layers=data.get('Layers'),
            log_format=data['LoggingConfig']['LogFormat'],
            log_group=data['LoggingConfig']['LogGroup'],
        )

        if data['LoggingConfig']['LogFormat'] == 'JSON':
            result.update(
                application_log_level=data['LoggingConfig']['ApplicationLogLevel'].lower(),
                system_log_level=data['LoggingConfig']['SystemLogLevel'].lower(),
            )

        if 'CodeSha256' in data:
            more = dict(
                function_arn=data['FunctionArn'],
                code_size=data['CodeSize'],
                last_modified=data['LastModified'],
                code_sha_256=data['CodeSha256'],
                version=data['Version'],
                # VpcConfig not handled
            )

            result.update(more)

        return result

    def make_function_configuration(self):
        args = {
            'FunctionName': self.params['function_name'],
            'Runtime': self.params['runtime'],
            'Role': self.params['role'],
            'Handler': self.params['handler'],
            'Description': self.params['description'],
            'Timeout': self.params['timeout'],
            'MemorySize': self.params['memory_size'],
            'Environment': None,
            'Layers': self.params['layers'],
            'LoggingConfig': {
                'LogFormat': self.params['log_format'],
                'LogGroup': self.params['log_group'] or f'/aws/lambda/{self.params["function_name"]}',
            },
            # VpcConfig not implemented
        }

        if self.params['log_format'] == 'JSON':
            args['LoggingConfig'].update(
                ApplicationLogLevel=self.params['application_log_level'].upper(),
                SystemLogLevel=self.params['system_log_level'].upper(),
            )

        if self.params['environment']:
            args['Environment'] = {
                'Variables': self.params['environment'],
            }

        return args

    def make_function_code(self):
        return {
            'ZipFile': self.get_package(),
        }


if __name__ == '__main__':
    main()
