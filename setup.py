from setuptools import setup, find_packages

setup(
    name="home_automation",
    version="0.1.0",
    packages=find_packages(include=["home_automation", "home_automation.*"]),
)
