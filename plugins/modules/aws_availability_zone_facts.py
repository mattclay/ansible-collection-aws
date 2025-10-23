#!/usr/bin/python
# Copyright (C) 2016 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


DOCUMENTATION = '''
---
module: aws_availability_zone_facts
short_description: Return information about availability zones
description:
    - Return information about availability zones.
author:
    - Matt Clay (@mattclay) <matt@mystile.com>
requirements:
    - boto3
'''

EXAMPLES = '''
aws_availability_zone_facts:
'''

from ..module_utils.aws import AwsModule

from ansible.module_utils.common.dict_transformations import camel_dict_to_snake_dict


def main():
    argument_spec = {}

    module = AwsModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    lm = AwsAvailabilityZoneFactsModule(module, module.check_mode, module.params)

    error, facts = lm.run()

    if error is None:
        module.exit_json(changed=False, ansible_facts=facts)
    else:
        module.fail_json(msg=error, ansible_facts=facts)


class AwsAvailabilityZoneFactsModule:
    def __init__(self, module: AwsModule, check_mode: bool, params: dict) -> None:
        self.module = module
        self.check_mode = check_mode
        self.params = params
        self.ec2 = module.client.ec2

    def run(self):
        zones = self.ec2.describe_availability_zones()['AvailabilityZones']
        zones = [camel_dict_to_snake_dict(z) for z in zones]

        facts = dict(
            aws_availability_zones=zones,
        )

        return None, facts


if __name__ == '__main__':
    main()
