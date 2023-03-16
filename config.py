import configparser
import os

repo_path = os.path.dirname(os.path.realpath(__file__))

def get_project_root():
    return repo_path

def get_config():
    config = configparser.ConfigParser()
    config.read_file(open(repo_path + '/config.txt'))
    return config
