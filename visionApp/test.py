from SAMI.pathway import Pathway
import logging
import os


logging.basicConfig(filename='../app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pathway():

    print(os.getcwd())
    # "C:\Users\ghari\Documents\OPS\SAMI\datasets\archive\sami_data\results\markers\cerebellum_2_WT_single_marker.csv"
    # cerebellum_marker.csv
    selected_file = "cerebellum_2_WT_single_marker.csv"

    omics = "metabolomics"
    pathways_folder = "C:/Users/ghari/Documents/OPS/SAMI/datasets/archive/sami_data/results/pathways"
    makers_folder = "C:/Users/ghari/Documents/OPS/SAMI/datasets/archive/sami_data/results/markers"
    region = selected_file.replace('_marker.csv', '')
    logger.info(f"region: {region}")
    logger.info(f"omics: {omics}")
    logger.info(f"pathways_folder: {pathways_folder}")
    logger.info(f"makers_folder: {makers_folder}")
    pathways_folder = os.path.join(pathways_folder, region)
    #make dir if it doesnt exist
    if not os.path.exists(pathways_folder):
        os.makedirs(pathways_folder)
    pathway = Pathway(region, omics, pathways_folder, makers_folder)
    pathway.findpathway()


if __name__ == '__main__':
    test_pathway()