'''
Created on Nov 4, 2015

@author: Andrew Roth
'''
import gzip
import pandas as pd

from biowrappers.components.utils import flatten_input

def concatenate_tables(in_files, out_file):
    in_files = flatten_input(in_files)

    min_itemsize = _get_min_itemsize(in_files)
    
    out_store = pd.HDFStore(out_file, 'w', complevel=9, complib='blosc')
    
    for file_name in in_files:
        in_store = pd.HDFStore(file_name, 'r')
        
        for table_name in in_store.keys():
            out_store.append(table_name, in_store[table_name], min_itemsize=min_itemsize[table_name])
        
        in_store.close()
    
    out_store.close()

def _get_min_itemsize(file_list):
    
    min_sizes = {}
    
    for file_name in file_list:
        hdf_store = pd.HDFStore(file_name, 'r')
        
        for table_name in hdf_store.keys():
            if table_name not in min_sizes:
                min_sizes[table_name] = {}
            
            df = hdf_store[table_name]
            
            if df.empty:
                continue
            
            for col in df.columns:
                if df[col].dtype in [object, str]:
                    size = df[col].map(lambda x: len(x)).max()
                    
                    if pd.np.isnan(size):
                        size = 0
                    
                    if (col not in min_sizes[table_name]) or (size > min_sizes[table_name][col]):
                        min_sizes[table_name][col] = size
        
        hdf_store.close()
        
    return min_sizes

def convert_hdf5_to_tsv(in_file, key, out_file, compress=False, index=False):
    df = pd.read_hdf(in_file, key)
    
    if compress:
        f_open = gzip.open
    
    else:
        f_open = open
    
    with f_open(out_file, 'w') as fh:
        df.to_csv(fh, index=index, sep='\t')