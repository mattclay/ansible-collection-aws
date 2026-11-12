from __future__ import annotations

import datetime
import zipfile

from ansible.module_utils.basic import AnsibleModule


def main() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            file=dict(required=True),
        )
    )

    with zipfile.ZipFile(module.params['file']) as zf:
        info_list = zf.infolist()

    files = [
        dict(
            filename=info.filename,
            file_size=info.file_size,
            external_attr=str(oct(info.external_attr >> 16)),
            date_time=datetime.datetime(*info.date_time).isoformat(),
        )
        for info in info_list
    ]

    module.exit_json(files=files)


if __name__ == '__main__':
    main()
