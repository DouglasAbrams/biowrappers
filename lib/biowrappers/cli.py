'''
Created on Dec 13, 2015

@author: Andrew Roth
'''
from biowrappers.components.variant_calling.utils import default_chromosomes

def add_pypeliner_args(parser):
    parser.add_argument('-c', '--cleanup_tmp_files', default=True, action='store_false')
    
    parser.add_argument('-l', '--log_dir', default='./')
    
    parser.add_argument('-m', '--max_jobs', default=1)
    
    parser.add_argument('-n', '--native_spec', default='-V -q all.q -l mem_token={mem}G,mem_free={mem}G,h_vmem={mem}G')
    
    parser.add_argument('-s', '--submit_method', choices=['asyncqsub', 'local'], default='local')

def add_variant_calling_region_args(parser):
    parser.add_argument('--chromosomes', nargs='+', default=default_chromosomes)
    
    parser.add_argument('--split_size', default=int(1e6), type=int)
    
def add_normal_tumour_bam_variant_calling_args(parser):
    parser.add_argument('-nb', '--normal_bam_file', required=True)
    
    parser.add_argument('-tb', '--tumour_bam_file', required=True)
    
    parser.add_argument('-rg', '--ref_genome_fasta_file', required=True)    

def load_pypeliner_config(args):
    config = {
        'tmpdir' : args.log_dir,
        'pretend' : False,
        'submit' : args.submit_method,
        'nativespec' : args.native_spec,
        'maxjobs' : args.max_jobs,
        'nocleanup' : not args.cleanup_tmp_files
    }
    
    return config
    
