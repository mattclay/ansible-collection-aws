# Copyright (C) 2016 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


def dictfilter(item, keys):
    return dict((k, item[k]) for k in item if k in keys)


class FilterModule(object):
    def filters(self):
        return dict(
            dictfilter=dictfilter,
        )
