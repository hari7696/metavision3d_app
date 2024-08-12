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
from log_listener import listener_process, worker_configurer

def run_scils_export(params, log_queue, message_queue):

    worker_configurer(log_queue)

    try:
        base_path = sys._MEIPASS
        libraries_path = os.path.dirname(base_path)
        libraries_path = os.path.join(libraries_path, r"R-4.3.3/win-library/4.3")
        libraries_path = str(libraries_path).replace("\\", "/")
        logger.info(f"libraries_path: {libraries_path}")
    except:
        base_path = os.path.abspath(r"C:\Users\ghari\Documents\OPS\UI\metavision3d_app\visionApp\SCILS")
        libraries_path = "C:/Program Files/R/R-4.3.3/win-library/4.3"


    # running commands
    logger.info("running scils export")
    logger.info(f"params: {params}")


    try:
    # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = os.path.join(sys._MEIPASS , 'config')
    except Exception:
        base_path = os.path.join(*[os.getcwd(), 'visionApp', 'SCILS'])

    source_r_file =  os.path.join(base_path, 'ScilsExport.R')
    r_output = os.path.join(base_path, 'R_output.txt')

    logger.info(f"source_r_file: {source_r_file}")
    logger.info(f"r_output: {r_output}")

    source_r_file = str(source_r_file).replace("\\", "/")
    r_output = str(r_output).replace("\\", "/")

    logger.info(f"after formatting: source_r_file: {source_r_file}")
    logger.info(f"after formatting: r_output: {r_output}")

    try:
        r(f'custom_lib_path <- "{libraries_path}"')
        r(f'Sys.setenv(R_LIBS_USER = custom_lib_path)')
        r('.libPaths(c(custom_lib_path, .libPaths()))')
        logger.info(f"R libraries path set {libraries_path}")
        r(f'scils_file_path <- "{params["scils_file_path"]}"')
        r(f'save_path <- "{params["save_path"]}"')
        r(f'peaklist_name <- "{params["peaklist_name"]}"')
        r(f'Sys.setenv("SCILSMSSERVER_LICENSE" = "{params["license_key"]}")')
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