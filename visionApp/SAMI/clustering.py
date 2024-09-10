import os
import scanpy as sc
import matplotlib.pyplot as plt
plt.switch_backend('agg')
import string
import pandas as pd
import numpy as np
import logging
import harmonypy as hm
logger = logging.getLogger(__name__)
from log_listener import worker_configurer

class Clusters:
    def __init__(self, region, modality, resolution, pooled_data_folder, working_folder, log_queue=None, harmony_flag=True):
        self.log_queue = log_queue  
        self.region = region
        self.modality = modality
        self.resolution = resolution
        self.pooled_data_folder = pooled_data_folder
        self.working_folder = working_folder
        self.file_path = os.path.join(*[self.working_folder, 'results', 'clustering'])
        self.haromony_flag = harmony_flag  

    def clustering(self):

        worker_configurer(self.log_queue)
        logger.info("Clustering started")

        temp_modality = self.modality.replace('_harmony','')
        adata=sc.read(os.path.join(self.pooled_data_folder,f'{self.region}_{temp_modality}.h5ad'))

        try:
            logger.info("CLustering:  Harmony flag: {}".format(self.haromony_flag))
            sc.pp.pca(adata)
            if (len(np.unique(adata.obs['region']))>1) and self.haromony_flag == 1:
                sc.external.pp.harmony_integrate(adata,key='region',max_iter_harmony=20)
                all_pcs = adata.obsm['X_pca_harmony'].shape[1]
                n_pcs = min(20, all_pcs)
                sc.pp.neighbors(adata,use_rep = 'X_pca_harmony', n_pcs=n_pcs)
            else:
                all_pcs = adata.obsm['X_pca'].shape[1]
                n_pcs = min(20, all_pcs) 
                sc.pp.neighbors(adata,n_pcs=n_pcs)
                
            sc.tl.umap(adata, random_state= 7)
            sc.tl.leiden(adata,resolution=self.resolution, random_state= 7)
        except Exception as e:
            logger.error(f"Error in clustering core SAMI: {str(e)}")
            return

        if not os.path.exists(self.file_path):
            os.makedirs(self.file_path)


        adata.write(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}.h5ad'))
        logger.info("Clustering completed and written the output file")
    
    
    def plot_umap_cluster(self,size=50,show=False):
        adata = sc.read(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}.h5ad'))
        color='leiden'
        clusters_colors = dict(zip([str(i) for i in range(102)], sc.pl.palettes.default_102))
        colorlist=adata.obs[color].cat.categories.tolist()
        n_cluster=str(len(colorlist))

        fig, axs = plt.subplots(1, 2, figsize=(30, 10))

        sc.pl.umap(
            adata, 
            legend_loc='on data',
            color=[color], 
            palette=[v for k, v in clusters_colors.items() if k in colorlist],
            ax=axs[0],
            show=False,
        )

        sc.pl.spatial(
            adata,
            img_key=None,
            library_id=None,
            spot_size=1, #important to add to avoid error
            color=color,
            title=f'{self.region}_{self.modality}_{self.resolution}',
            size=size,
            palette=[v for k, v in clusters_colors.items() if k in colorlist],
            ax=axs[1],
            show=False
        )

        samples = np.unique(adata.obs['region']).tolist()
        for sample in samples:
            adata_sub = adata[adata.obs['region']==sample]
            x_label = np.min(adata_sub.obsm['spatial'][:,0])
            y_label = np.min(adata_sub.obsm['spatial'][:,1])
            axs[1].text(x_label,y_label, sample,fontsize=10, color='black')
        
        plt.savefig(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}_umap_{n_cluster}.png'),dpi=400)
        
        if show==False:
            plt.close()
        else:
            plt.show()

        return os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}_umap_{n_cluster}.png'), len(colorlist)
    
    def plot_cluster(self,size=50,show=False):
        adata = sc.read(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}.h5ad'))
        color='leiden'
        clusters_colors = dict(zip([str(i) for i in range(102)], sc.pl.palettes.default_102))
        colorlist=adata.obs[color].cat.categories.tolist()
        n_cluster=str(len(colorlist))
        fig, axs = plt.subplots(1, 1, figsize=(15, 10))
        sc.pl.spatial(
            adata,
            img_key=None,
            library_id=None,
            spot_size=1, #important to add to avoid error
            color=color,
            title=f'{self.region}_{self.modality}_{self.resolution}',
            size=size,
            palette=[v for k, v in clusters_colors.items() if k in colorlist],
            show=False
        )

        samples = np.unique(adata.obs['region']).tolist()
        for sample in samples:
            adata_sub = adata[adata.obs['region']==sample]
            x_label = np.min(adata_sub.obsm['spatial'][:,0])
            y_label = np.min(adata_sub.obsm['spatial'][:,1])
            axs.text(x_label,y_label, sample,fontsize=10, color='black')

        plt.savefig(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}_{n_cluster}.png'),dpi=400)
        if show==False:
            plt.close()
        else:
            plt.show()
        return os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}_{n_cluster}.png')
    
    def plot_select_cluster(self,cluster,size=50,show=False):
        adata = sc.read(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}.h5ad'))
        clusters_colors = dict(zip([str(i) for i in range(102)], sc.pl.palettes.default_102))
        
        if isinstance(cluster, int):
            cluster = [cluster]
            
        colorlist=adata.obs['leiden'].cat.categories.tolist()
        palette=[v if k in map(str,cluster) else '#A0A0A0' for k, v in clusters_colors.items()]
        fig, axs = plt.subplots(1, 1, figsize=(15, 10))
        sc.pl.spatial(
            adata,
            img_key=None,
            library_id=None,
            spot_size=1, #important to add to avoid error
            color='leiden',
            legend_loc='none',
            title=f'{self.region}_{self.modality}_{self.resolution}_{cluster}',
            size=size,
            palette=palette,
            show=False
        )

        samples = np.unique(adata.obs['region']).tolist()
        for sample in samples:
            adata_sub = adata[adata.obs['region']==sample]
            x_label = np.min(adata_sub.obsm['spatial'][:,0])
            y_label = np.min(adata_sub.obsm['spatial'][:,1])
            axs.text(x_label,y_label, sample,fontsize=10, color='black')
        plt.savefig(os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}_{cluster}.png'),dpi=400) 
        if show==False:
            plt.close()
        else:
            plt.show()

        return os.path.join(self.file_path,f'{self.region}_{self.modality}_{self.resolution}_{cluster}.png')
    
class Cluster_Integration:
    def __init__(self,adata,adata_ref, working_folder,clusterInt_specific_working_folder, log_queue=None):

        self.log_queue = log_queue
        self.adata = adata
        self.adata_ref = adata_ref
        self.working_folder = working_folder
        self.region1, self.modality1, self.resolution1 =self.splitname(adata)
        self.region2, self.modality2, self.resolution2 =self.splitname(adata_ref)
        # this is the folder where the integrated data and results will be saved
        self.clusterInt_specific_working_folder = clusterInt_specific_working_folder
        
    def integrate(self):

        worker_configurer(self.log_queue)
        logger.info("INtegration started")
        adata1 = sc.read(os.path.join(self.working_folder , self.adata))
        adata2 = sc.read(os.path.join(self.working_folder , self.adata_ref))
        var_names = adata1.var_names.intersection(adata2.var_names)
        adata1.obs['sample'] = self.region1
        adata2.obs['sample'] = self.region2

        try:
            sc.tl.ingest(adata1,adata2,obs='leiden')
        except Exception as e:
            logger.error(f"Error in integration core SAMI: {str(e)}")
            return
        
        adata1.write(os.path.join(self.clusterInt_specific_working_folder, f'{self.region1}-{self.modality1}-{self.resolution1}_integrated.h5ad'))
        adata2.write(os.path.join(self.clusterInt_specific_working_folder, f'{self.region2}-{self.modality2}-{self.resolution2}_integrated.h5ad'))
        logger.info("Integration completed and written the output file")
        
    def splitname(self,adata):
        # name,_ = os.path.splitext(adata)
        # region, modality, resolution = name.split('_')
        # return region, modality, resolution
        # changed for GUI braoder handling
        name = adata.replace('.h5ad', "")
        #region, modality, resolution = name.split('_')
        resolution = name.split('_')[-1]
        modality = name.split('_')[-2]
        region = '_'.join(name.split('_')[:-2])

        return region, modality, resolution
    
    def plot_umap_cluster(self,region, modality, res, size=50,show=False):
        adata = sc.read(os.path.join(self.clusterInt_specific_working_folder,f'{region}-{modality}-{res}_integrated.h5ad'))
        color='leiden'
        clusters_colors = dict(zip([str(i) for i in range(102)], sc.pl.palettes.default_102))
        colorlist=adata.obs[color].cat.categories.tolist()
        n_cluster=str(len(colorlist))
        fig, axs = plt.subplots(1, 2, figsize=(30, 10))

        sc.pl.umap(
            adata, 
            legend_loc='on data',
            color=[color], 
            title=region,
            palette=[v for k, v in clusters_colors.items() if k in colorlist],
            ax=axs[0],
            show=False,
        )

        sc.pl.spatial(
            adata,
            img_key=None,
            library_id=None,
            spot_size=1, #important to add to avoid error
            color=color,
            title=region,
            size=size,
            palette=[v for k, v in clusters_colors.items() if k in colorlist],
            ax=axs[1],
            show=False
        )
        samples = np.unique(adata.obs['region']).tolist()
        for sample in samples:
            adata_sub = adata[adata.obs['region']==sample]
            x_label = np.min(adata_sub.obsm['spatial'][:,0])
            y_label = np.min(adata_sub.obsm['spatial'][:,1])
            axs[1].text(x_label,y_label, sample,fontsize=10, color='black')

        plt.savefig(os.path.join(self.clusterInt_specific_working_folder,f'{region}-{modality}-{res}_umap_integrated.png'),dpi=400)

        if show==False:
            plt.close()
        else:
            plt.show()

        return os.path.join(self.clusterInt_specific_working_folder,f'{region}-{modality}-{res}_umap_integrated.png'), len(colorlist)
            
    def plot_overlap_umap(self,show=False):
        adata1 = sc.read(os.path.join(self.clusterInt_specific_working_folder,f'{self.region1}-{self.modality1}-{self.resolution1}_integrated.h5ad'))
        adata2 = sc.read(os.path.join(self.clusterInt_specific_working_folder,f'{self.region2}-{self.modality2}-{self.resolution2}_integrated.h5ad'))
        adata_concat = adata2.concatenate(adata1, batch_categories=[self.region2,self.region1])
        fig,ax = plt.subplots(figsize=(10,8))
        plt.subplots_adjust(left=0.1,right=0.7)
        sc.pl.umap(adata_concat,color='batch',title=f'{self.region1} vs {self.region2}',size=5,legend_fontsize=20,ax=ax,show=False)
        
        plt.savefig( os.path.join(self.clusterInt_specific_working_folder , f'{self.region1}-{self.modality1}-{self.resolution1}_{self.region2}-{self.modality2}-{self.resolution2}_umap_overlap.png'),dpi=200)
        if show==False:
            plt.close()
        else:
            plt.show()
        return os.path.join(self.clusterInt_specific_working_folder , f'{self.region1}-{self.modality1}-{self.resolution1}_{self.region2}-{self.modality2}-{self.resolution2}_umap_overlap.png')
            
            
    def plot_select_cluster(self,region,modality, res, cluster,size=50,show=False):
        adata = sc.read(os.path.join(self.clusterInt_specific_working_folder,f'{region}-{modality}-{res}_integrated.h5ad'))
        clusters_colors = dict(zip([str(i) for i in range(102)], sc.pl.palettes.default_102))
        
        if isinstance(cluster, int):
            cluster = [cluster]
            
        colorlist=adata.obs['leiden'].cat.categories.tolist()
        palette=[v if k in map(str,cluster) else '#A0A0A0' for k, v in clusters_colors.items()]
        fig, axs = plt.subplots(1, 1, figsize=(15, 10))
        sc.pl.spatial(
            adata,
            img_key=None,
            library_id=None,
            spot_size=1, #important to add to avoid error
            color='leiden',
            legend_loc='none',
            title=f'{region}_integrated_{cluster}',
            size=size,
            palette=palette,
            show=False
        )

        samples = np.unique(adata.obs['region']).tolist()
        for sample in samples:
            adata_sub = adata[adata.obs['region']==sample]
            x_label = np.min(adata_sub.obsm['spatial'][:,0])
            y_label = np.min(adata_sub.obsm['spatial'][:,1])
            axs.text(x_label,y_label, sample,fontsize=10, color='black')

        plt.savefig(os.path.join(self.clusterInt_specific_working_folder,f'{region}-{modality}-{res}_{cluster}.png'),dpi=400) 
        if show==False:
            plt.close()
        else:
            plt.show()


        return os.path.join(self.clusterInt_specific_working_folder,f'{region}-{modality}-{res}_{cluster}.png')