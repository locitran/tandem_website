import os 

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # ./tandem_website

GRADIO_DIR = os.path.join(ROOT_DIR, 'gradio_app')
TMP_DIR = os.path.join(GRADIO_DIR, 'tmp')