
def fetch_version():
	import os
	import os.path
	import subprocess
	repo_dir = os.path.dirname(os.path.abspath(__file__))
	git_desc = subprocess.Popen('git describe --always --tags --dirty=+ --abbrev=4',
		stdout=subprocess.PIPE, stderr=subprocess.PIPE,
		shell=True, cwd=repo_dir)
	return git_desc.communicate()[0][:-1]

# TODO : get that as $version from setuptools
__version__ = fetch_version()

