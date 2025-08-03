from setuptools import setup, find_packages

setup(
	name='meta_vision3d',
	version='1.0',
	author='Hari Krishna Reddy Golamari',
	author_email='golamari.h@ufl.edu',
	packages=find_packages(exclude=('tests', 'docs', 'resources')),
	setup_requires=['pytest-runner'],
	tests_require=['pytest']	
)

