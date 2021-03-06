'''
Created on 8 Apr 2017

@author: Andrew Roth
'''
import pypeliner
import pypeliner.managed as mgd

import biowrappers.components.io.tsv.tasks as tsv_tasks
import biowrappers.components.io.vcf.tasks as vcf_tasks
import biowrappers.components.ngs.samtools.tasks as samtools_tasks
import biowrappers.components.variant_calling.utils as utils

import tasks


def create_single_sample_workflow(bam_file, ref_genome_fasta_file, out_file, chromosomes=None, split_size=int(1e7)):
    regions = utils.get_bam_regions(bam_file, split_size, chromosomes=chromosomes)

    workflow = pypeliner.workflow.Workflow()

    workflow.setobj(obj=pypeliner.managed.TempOutputObj('config', 'regions'), value=regions)

    workflow.transform(
        name='build_mpileup',
        axes=('regions',),
        ctx={'mem': 2, 'mem_retry_increment': 2, 'num_retry': 3},
        func=samtools_tasks.mpileup,
        args=(
            mgd.InputFile(bam_file),
            mgd.TempOutputFile('split.mpileup', 'regions'),
        ),
        kwargs={
            'ref_genome_fasta_file': mgd.InputFile(ref_genome_fasta_file),
            'region': mgd.TempInputObj('config', 'regions'),
        },
    )

    workflow.transform(
        name='run_pileup2snp',
        axes=('regions',),
        ctx={'mem': 8, 'mem_retry_increment': 2, 'num_retry': 3},
        func=tasks.run_pileup2snp,
        args=(
            mgd.TempInputFile('split.mpileup', 'regions'),
            mgd.TempOutputFile('region.tsv.gz', 'regions'),
        ),
    )

    workflow.transform(
        name='merge',
        axes=(),
        ctx={'mem': 2, 'mem_retry_increment': 2, 'num_retry': 3},
        func=tsv_tasks.concatenate_tables,
        args=(
            mgd.TempInputFile('region.tsv.gz', 'regions'),
            mgd.OutputFile(out_file),
        ),
    )

    return workflow


def create_somatic_workflow(
        normal_bam_file,
        tumour_bam_file,
        ref_genome_fasta_file,
        out_file,
        chromosomes=None,
        split_size=int(1e7)):

    regions = utils.get_bam_regions(normal_bam_file, split_size, chromosomes=chromosomes)

    workflow = pypeliner.workflow.Workflow()

    workflow.setobj(obj=pypeliner.managed.TempOutputObj('config', 'regions'), value=regions)

    workflow.transform(
        name='run_somatic',
        axes=('regions',),
        ctx={'mem': 6, 'mem_retry_increment': 2, 'num_retry': 3},
        func=tasks.run_somatic,
        args=(
            mgd.InputFile(normal_bam_file),
            mgd.InputFile(tumour_bam_file),
            mgd.InputFile(ref_genome_fasta_file),
            mgd.TempOutputFile('region.vcf.gz', 'regions'),
            mgd.TempInputObj('config', 'regions'),
            mgd.TempSpace('varscan_tmp', 'regions'),
        ),
    )

    workflow.transform(
        name='merge',
        axes=(),
        ctx={'mem': 2, 'mem_retry_increment': 2, 'num_retry': 3},
        func=vcf_tasks.concatenate_vcf,
        args=(
            mgd.TempInputFile('region.vcf.gz', 'regions'),
            mgd.OutputFile(out_file),
        ),
    )

    return workflow
