# Copyright (C) 2017 Matt Clay <matt@mystile.com>
# GNU General Public License v3.0+ (see LICENSE.md or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import annotations


def map_format(item, fmt, *args, **kwargs):
    d = {}
    d.update(item)
    d.update(kwargs)
    return fmt.format(*args, **d)


class FilterModule:
    def filters(self):
        return dict(
            map_format=map_format,
        )
