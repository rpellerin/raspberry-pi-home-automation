import configparser
import os

repo_path = os.path.dirname(os.path.realpath(__file__))

def get_config():
    return configparser.ConfigParser().read_file(open(repo_path + '/config.txt'))
