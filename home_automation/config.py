import configparser
import os

repo_path = os.path.dirname(os.path.realpath(__file__))


def get_config():
    config = configparser.ConfigParser()
    config.read_file(open(repo_path + "/../config.txt"))
    return config


GOOGLE_SCRIPTS_URL = get_config().get("weatherstation", "GOOGLE_SCRIPTS_URL")
