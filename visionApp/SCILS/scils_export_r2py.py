import os
import sys
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
    inno_path = os.path.dirname(base_path)
    R_HOME = os.path.join(inno_path, r"R-4.3.3")
    path = os.path.join(inno_path, r"R-4.3.3\bin\x64")
    os.environ["R_HOME"] = R_HOME
    os.environ["PATH"] += path + ";" + os.environ["R_HOME"]
    logger.info("running in executable mode")
except Exception as e:
    os.environ["R_HOME"] = r"C:\Program Files\R\R-4.3.3"
    os.environ["PATH"] += (
        r"C:\Program Files\R\R-4.3.3\bin\x64" + ";" + os.environ["R_HOME"]
    )
    logger.info("running in dev mode")
import logging
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter

import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from rpy2.robjects import r
import logging
import queue
# from log_listener import listener_process, worker_configurer

def run_scils_export(params, log_queue, message_queue):

    # worker_configurer(log_queue)

    try:
        base_path = sys._MEIPASS
        libraries_path = os.path.dirname(base_path)
        libraries_path = os.path.join(libraries_path, r"R-4.3.3/win-library/4.3")
        libraries_path = str(libraries_path).replace("\\", "/")
    except:
        base_path = os.path.abspath(r"C:\Users\ghari\Documents\OPS\UI\metavision3d_app\visionApp\SCILS")
        libraries_path = "C:/Program Files/R/R-4.3.3/win-library/4.3"

    source_r_file = 'C:/Users/ghari/Documents/OPS/UI/metavision3d_app/visionApp/SCILS/ScilsExport.R'
    # running commands
    logger.info("running scils export")
    logger.info(f"params: {params}")

    try:

        r(f'scils_file_path <- "{params["scils_file_path"]}"')
        r(f'save_path <- "{params["save_path"]}"')
        r(f'peaklist_name <- "{params["peaklist_name"]}"')
        r(f'Sys.setenv("SCILSMSSERVER_LICENSE" = "{params["license_key"]}")')
        r_output = "C:/Users/ghari/Documents/OPS/UI/metavision3d_app/visionApp/SCILS/R_output.txt"
        r(f'r_output_filename <- "{r_output}"')
        logger.info("parameters commands executed")

        logger.info("running source")
        r(f"source('{source_r_file}')")
        message_queue.put({"message" : "success", "output_file": r_output})
        logger.info("source executed")
        return r_output
    
    except Exception as e:
        logger.error(f"Error: {e}")
        message_queue.put({"message" : "failed"})
        return None
    



if __name__ == "__main__":

    params = {'scils_file_path': 'C:/Users/ghari/Documents/OPS/scils_Export/05012024_glygly_fullset.slx', 
     'save_path': 'C:/Users/ghari/Documents/OPS/scils_Export/export.csv', 
     'peaklist_name': 'glycans_rr',
     'license_key': '130-2448274819-17'}
    run_scils_export(params)