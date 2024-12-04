import os
import numpy as np
import pandas as pd
import scanpy as sc
import anndata as ad
from .utils import *
import re
import logging
from log_listener import worker_configurer
import pickle
logger = logging.getLogger(__name__)

#load .csv data and return .h5ad files
def csv2h5ad(dict_compound_type, data_reading_path, data_saving_path, split=True, log_queue=None):
    # worker_configurer(log_queue)
    for file, compound_type in dict_compound_type.items():

        logger.info(f'csv2h5ad processing {file}')
        data_temp = pd.read_parquet(os.path.join(data_reading_path, file))
        data_temp =data_temp.rename(columns={'tissue_id':'region'})
        data_temp['region'] = data_temp['region'].astype(str)
        # x	y	region	G00014, compounds starts from 3rd column
        feat_cols = data_temp.columns[3:]
        data_temp = data_temp[data_temp[feat_cols].sum(axis=1)!=0]
        nodefeats = data_temp[feat_cols]
        nodefeats = np.array(nodefeats)
        data_temp['obsindex'] = data_temp['x'].astype(str)+"x"+data_temp['y'].astype(str)
        xs=data_temp["x"]
        ys=data_temp["y"]
        xs=np.array(xs)
        ys=np.array(ys)
        pos=np.stack((xs,ys), axis=-1)
        adata=sc.AnnData(X=nodefeats,dtype='float32')
        obs=data_temp.set_index('obsindex')[['region']]
        adata.obs=obs
        adata.obsm['spatial'] = pos
        var = pd.DataFrame({'omics':compound_type},index=data_temp[feat_cols].columns)
        adata.var = var
        adata.raw = adata
        
        # adata.write(os.path.join(data_saving_path,f'{split_file[0]}_{split_file[1]}.h5ad'))
        if split==True:
            unique_id=data_temp['region'].unique().tolist()
            for i in range(len(unique_id)):
                adata_sub=adata[adata.obs['region']==unique_id[i]].copy()
                adata_sub.write(os.path.join(data_saving_path,f'{unique_id[i]}_{compound_type}.h5ad'))
    logger.info(f'csv2h5ad completed')

                    
#merge omics data by coordinates and return .h5ad file
def pooldata(dict_compound_type, data_reading_path, data_saving_path, split=True, log_queue=None):
    error_message  =""
    adata_dict={}
    for file, compound_type in dict_compound_type.items():
        logger.info(f'pool step processing {file}')          
        # print("converting", os.path.join(data_path, file))
        data_temp = pd.read_parquet(os.path.join(data_reading_path, file))
        data_temp =data_temp.rename(columns={'tissue_id':'region'})
        data_temp['region'] = data_temp['region'].astype(str)
        feat_cols = data_temp.columns[3:]
        data_temp = data_temp[data_temp[feat_cols].sum(axis=1)!=0]
        nodefeats = data_temp[feat_cols]
        nodefeats = np.array(nodefeats)
        data_temp['obsindex'] = data_temp['x'].astype(str)+"x"+data_temp['y'].astype(str)

        adata_temp=sc.AnnData(X=nodefeats,dtype='float32')
        obsindex = pd.DataFrame(index=data_temp['obsindex'])
        adata_temp.obs = obsindex
        varindex = pd.DataFrame(index=data_temp[feat_cols].columns)
        adata_temp.var = varindex
        adata_temp.raw = adata_temp
        # adding all the lipids, metabolites, glycans to a dictionary
        adata_dict[compound_type]=adata_temp

    #remove duplicate columns between metabolomics and lipidomics from metabolomics
    # common_elements = list(set(adata_dict['metabolomics'].var.index.to_list()).intersection(adata_dict['lipidomics'].var.index.to_list()))
    # adata_dict['metabolomics']=adata_dict['metabolomics'][:,~adata_dict['metabolomics'].var.index.isin(common_elements)]

    # adata_dict
    # Pickle the adata_dict
    # with open(os.path.join(data_saving_path, r'C:\Users\ghari\Documents\OPS\SAMI\adata_dict.pkl'), 'wb') as f:
    #     pickle.dump(adata_dict, f)

    # manually overriding pixel mis alignment
    # adata_dict['lipids'].obs = adata_dict['sm'].obs 

    # combining all the regions of same type of omics data
    adata=ad.concat(adata_dict,join='inner',axis=1,label='omics')

    # the concatenation usually happens on the basis of the index, so if the index is not same then the data will not be concatenated
    # so we need to check if the data is concatenated or not
    # if its empty and the pixes are same, then we can do a blind merge and give a warning to user
    same_pixles = True
    if len(adata.obs.index) == 0:
        error_message = "No common pixels found in the data, So performing BLIND merge, please check the data post clustering"
        logger.warning("mismatch, no common pixels found in the data")
        logger.warning("Attempting to perform BLIND merge")
        # resetting all omics indexes to one common index
        given_omics = list(adata_dict.keys())
        logger.info(f"given omics: {given_omics}")
        for i in range(1, len(given_omics)):
            logger.info(f"checking if {given_omics[i]} has same pixels as {given_omics[0]}")
            logger.info(f"pixel count for {given_omics[i]} and {given_omics[0]} \
                            is {len(adata_dict[given_omics[i]].obs.index)} and {len(adata_dict[given_omics[0]].obs.index)}")
            if len(adata_dict[given_omics[i]].obs.index) == len(adata_dict[given_omics[0]].obs.index):

                adata_dict[given_omics[i]].obs == adata_dict[given_omics[0]].obs
            else:
                same_pixles = False
                break
        
    if not same_pixles:
        logger.warning("pixel count is different in both the datasets, BLIND merge is not possible")
        error_message = "Pixel count is different in both the datasets, BLIND merge is not possible"
        return error_message

    adata=ad.concat(adata_dict,join='inner',axis=1,label='omics')


    obs=data_temp.set_index('obsindex')[['region']]
    obs=obs[obs.index.isin(adata.obs.index)]
    adata.obs=obs
    adata.obsm['spatial']=adata.obs.reset_index()['obsindex'].str.split('x',expand=True).astype(np.float64).to_numpy()
    
    if split==True:
        unique_id=data_temp['region'].unique().tolist()
        for i in range(len(unique_id)):
            adata_sub=adata[adata.obs['region']==unique_id[i]].copy()
            
            # # writing only if it have more than 1 omics, because single omics data is already written in csv2h5ad step
            if len(adata_sub.var['omics'].unique())>1:
                # logger.info(f'writing {adata_sub.var["omics"].unique()}')
                adata_sub.write(os.path.join(data_saving_path,f'{unique_id[i]}_pool.h5ad'))
    
    # this contains all tissues and all omics data
    adata.write(os.path.join(data_saving_path,f'All_tissues_pool.h5ad'))
    logger.info(f'pooling completed')

    return error_message

# def handle_naming(id):

#     id = str(id)
#     region = id.split('_')[0]
#     modality = ''.join(id.split('_')[1:])
#     return region + '_' + modality
    



# def pooldata(data_path,pattern,split=False):
#     adata_dict={}
#     for file in os.listdir(data_path):
#         name, ext = os.path.splitext(file)
#         print(name)
#         if '_norm' in name:
#         # if re.match(pattern,file):
#             split_file = name.split('_')
#             print("converting", os.path.join(data_path, file))
#             data_temp = pd.read_parquet(os.path.join(data_path, file))
#             data_temp =data_temp.rename(columns={'tissue_id':'region'})
#             feat_cols = data_temp.columns[3:]
#             data_temp = data_temp[data_temp[feat_cols].sum(axis=1)!=0]
#             nodefeats = data_temp[feat_cols]
#             nodefeats = np.array(nodefeats)
#             data_temp['obsindex'] = data_temp['x'].astype(str)+"x"+data_temp['y'].astype(str)

#             adata_temp=sc.AnnData(X=nodefeats,dtype='float32')
#             obsindex = pd.DataFrame(index=data_temp['obsindex'])
#             adata_temp.obs = obsindex
#             varindex = pd.DataFrame(index=data_temp[feat_cols].columns)
#             adata_temp.var = varindex
#             adata_temp.raw = adata_temp

#             print(split_file[1])

#             adata_dict[split_file[1]]=adata_temp

#     #remove duplicate columns between metabolomics and lipidomics from metabolomics
#     # common_elements = list(set(adata_dict['lip'].var.index.to_list()).intersection(adata_dict['sm'].var.index.to_list()))
#     # adata_dict['lip']=adata_dict['lip'][:,~adata_dict['lip'].var.index.isin(common_elements)]
#     # print(type(adata_dict['lip']))

#     #merge dataset
#     adata=ad.concat(adata_dict,join='inner',axis=1,label='omics')

#     #reset annotation
#     obs=data_temp.set_index('obsindex')[['region']]
#     obs=obs[obs.index.isin(adata.obs.index)]
#     adata.obs=obs
#     adata.obsm['spatial']=adata.obs.reset_index()['obsindex'].str.split('x',expand=True).astype(np.float64).to_numpy()
    
#     if split==True:
#         unique_id=data_temp['region'].unique().tolist()
#         for i in range(len(unique_id)):
#             adata_sub=adata[adata.obs['region']==unique_id[i]].copy()
#             adata_sub.write(os.path.join(data_path,f'{unique_id[i]}_pool.h5ad'))
        
#     adata.write(os.path.join(data_path,f'{split_file[0]}_pool.h5ad'))

    

    


