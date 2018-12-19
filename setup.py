from distutils.core import setup

setup(name="udon",
      description="Simple helpers for python apps",
      version="0.6.0",
      author="Eric Faurot",
      author_email="eric@faurot.net",
      url="https://github.com/ericfaurot/udon",
      classifiers = [
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: ISC License (ISCL)",
          "Operating System :: OS Independent",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      packages=[ "udon", "udon.tests" ])
