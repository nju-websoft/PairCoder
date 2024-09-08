import pathlib
import os
from os import listdir
from os.path import abspath, dirname, join, isfile
import glob

from dynaconf import Dynaconf


current_dir = os.getcwd()
setting_dir = current_dir + '/src/'

toml_files = list(pathlib.Path(join(setting_dir)).rglob('*.toml'))
global_settings = Dynaconf(
    envvar_prefix=False,
    merge_enabled=True,
    settings_files=toml_files,
)


def get_settings():
    return global_settings
