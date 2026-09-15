"""Application settings."""
from pathlib import Path
import os
import sys


SITPLANES_DIR = network_path = r"\\192.168.0.101\lab\LAB_ОБЩАЯ\05-09_Протоколы испытаний (измерений)\ЭМИ РЧ\sitplanes"


def get_root_path():
    root_path = os.path.abspath('.')

    return  Path(os.path.join(root_path))


root_path = get_root_path()#Path(sys._MEIPASS)
OUTPUT_DIR = root_path / 'output'
template_foldet_path = root_path / 'templates'






