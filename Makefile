.PHONY: all
all:

.PHONY: build
build:
	# set TMPDIR to the real path of a temporary directory (cpio will not accept symbolic links such as those found on macOS)
	$(eval TMPDIR = $(shell python -c "import os, tempfile; print(os.path.realpath(tempfile.mkdtemp()));"))
	cp -a galaxy.yml README.md "$(TMPDIR)"
	find plugins -name '*.py' | cpio -pdm "${TMPDIR}"
	ansible-galaxy collection build "$(TMPDIR)"
	rm -rf "$(TMPDIR)"
