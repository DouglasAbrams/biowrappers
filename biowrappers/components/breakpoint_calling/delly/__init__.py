import pypeliner
import pypeliner.managed as mgd
from pypeliner.workflow import Workflow

import biowrappers.components.io.vcf.tasks as vcf_tasks
import biowrappers.components.utils as utils
import tasks


def delly_pipeline(
    normal_bam_file,
    tumour_bam_files,
    ref_genome_fasta_file,
    delly_excl_chrom,
    out_file,
    raw_data_dir,
):
    bams = list()
    for lib_id, bam_filename in tumour_bam_files.iteritems():
        bams += [utils.symlink(bam_filename, link_name='{0}.bam'.format(lib_id), link_directory=raw_data_dir)]
        utils.symlink(bam_filename+'.bai', link_name='{0}.bam.bai'.format(lib_id), link_directory=raw_data_dir)

    bams += [utils.symlink(normal_bam_file, link_name='Normal.bam', link_directory=raw_data_dir)]
    utils.symlink(normal_bam_file+'.bai', link_name='Normal.bam.bai', link_directory=raw_data_dir)

    sample_type = {'Normal': 'control'}
    for lib_id, bam_filename in tumour_bam_files.iterkeys():
        sample_type[lib_id] = 'tumor'

    workflow = Workflow()
    
    workflow.setobj(
        obj=pypeliner.managed.TempOutputObj('sample_type', 'sample_id'),
        value=sample_type,
    )

    workflow.setobj(
        obj=pypeliner.managed.OutputChunks('sv_type'),
        value=('DEL', 'DUP', 'INV', 'TRA', 'INS'),
    )

    delly_args = [
        'delly', 'call',
        '-t', mgd.Instance('sv_type'),
        '-x', delly_excl_chrom,
        '-g', ref_genome_fasta_file,
        '-o', mgd.TempOutputFile('out.bcf', 'sv_type'),
    ]

    for bam in bams:
        delly_args.append(mgd.InputFile(bam))
    
    workflow.commandline(
        name='run_delly',
        axes=('sv_type',),
        ctx={'mem': 64, 'num_retry': 2, 'mem_retry_factor': 2},
        args=tuple(delly_args),
    )

    workflow.transform(
        name='write_samples_table',
        ctx={'mem': 1},
        func=tasks.write_samples_table,
        args=(
            mgd.TempInputObj('sample_type', 'sample_id'),
            mgd.TempOutputFile('samples.tsv'),
        ),
    )

    workflow.commandline(
        name='filter_somatic',
        axes=('sv_type',),
        ctx={'mem': 4, 'num_retry': 2, 'mem_retry_factor': 2},
        args=(
            'delly', 'filter',
            '-t', mgd.Instance('sv_type'),
            '-f', 'somatic',
            '-o', mgd.TempOutputFile('somatic.bcf', 'sv_type'),
            '-s', mgd.TempInputFile('samples.tsv'),
            '-g', ref_genome_fasta_file,
            mgd.TempInputFile('out.bcf', 'sv_type'),
        ),
    )

    workflow.transform(
        name='concatenate_vcf',
        func=vcf_tasks.concatenate_bcf,
        ctx={'mem': 4, 'num_retry': 2, 'mem_retry_factor': 2},
        args=(
            mgd.TempInputFile('somatic.bcf', 'sv_type'),
            mgd.TempOutputFile('somatic.bcf'),
        ),
    )

    workflow.transform(
        name='convert_vcf',
        func=tasks.convert_vcf,
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        args=(
            mgd.TempInputFile('somatic.vcf'),
            mgd.OutputFile(out_file),
        ),
    )

    return workflow

