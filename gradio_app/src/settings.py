import os 
from zoneinfo import ZoneInfo

time_zone = ZoneInfo("Asia/Taipei")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # ./tandem_website

MOUNT_POINT = '/TANDEM-DEV'  # https://dyn.life.nthu.edu.tw/TANDEM-dev
TITLE = 'TANDEM-DIMPLE-DEV'

TANDEM_DIR = os.path.join(ROOT_DIR, 'tandem')
GRADIO_DIR = os.path.join(ROOT_DIR, 'gradio_app')
TMP_DIR = os.path.join(GRADIO_DIR, 'tmp')
JOB_DIR = os.path.join(TANDEM_DIR, 'jobs')

SASS_DIR = os.path.join(GRADIO_DIR, "sass")
ASSETS_DIR = os.path.join(GRADIO_DIR, "assets")
FIGURE_1 = os.path.join(ASSETS_DIR, 'images/figure_1.jpg')
