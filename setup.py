from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="corona_br_bot",
    version="0.0.1",
    author="Vagner Pagotti",
    author_email="pagotti@example.com",
    description="Um bot do Telegram que informa dados de casos do covid-19",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/pagotti/corona-bot',
    packages=find_packages(exclude=('tests', 'docs')),
    keywords=['bot', 'covid-19'],
    install_requires=[
        'pytz',
        'telegram',
        'matplotlib',
        'beautifulsoup4',
        'Pillow'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        'Programming Language :: Python :: 3.7',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)