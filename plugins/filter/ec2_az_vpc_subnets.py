# Copyright (C) 2016 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

def ec2_az_vpc_subnets(zones, subnet, name):
    return [dict(
        cidr=map_zone_to_subnet(z, subnet),
        az=z,
        resource_tags=dict(
            Name=name,
        ),
    ) for z in zones]


def map_zone_to_subnet(zone, subnet):
    position = ord(zone[-1:]) - ord('a')
    return subnet % position


class FilterModule(object):
    def filters(self):
        return dict(
            ec2_az_vpc_subnets=ec2_az_vpc_subnets,
        )
