import sys
from distlock import __version__


try:
    from setuptools import setup
    from setuptools.command.test import test as TestCommand

    class PyTest(TestCommand):
        def finalize_options(self):
            TestCommand.finalize_options(self)
            self.test_args = []
            self.test_suite = True

        def run_tests(self):
            # import here, because outside the eggs aren't loaded
            import pytest
            errno = pytest.main(self.test_args)
            sys.exit(errno)

except ImportError:

    from distutils.core import setup

    def PyTest(x):
        x


setup(
    name='distlock',
    version=__version__,
    packages=['distlock'],
    keywords=['distlock', 'Redis', 'lock', 'distributed'],
    tests_require=['pytest>=2.5.0'],
    cmdclass={'test': PyTest},
    url='https://github.com/scottynomad/distlock',
    license='MIT',
    author='scottynomad',
    author_email='scott.wilson@gmail.com',
    description='Simple distributed lock primitive using Redis',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]
)
