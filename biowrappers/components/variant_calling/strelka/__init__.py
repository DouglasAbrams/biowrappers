from pypeliner.workflow import Workflow

import csv
import pypeliner
import pysam

from biowrappers.components.variant_calling.utils import default_chromosomes

import biowrappers.components.variant_calling.utils as utils
import biowrappers.components.io.vcf.tasks as vcf_tasks
import tasks


def create_strelka_workflow(
        normal_bam_file,
        tumour_bam_file,
        ref_genome_fasta_file,
        indel_vcf_file,
        snv_vcf_file,
        chromosomes=default_chromosomes,
        split_size=int(1e7),
        use_depth_thresholds=True):

    workflow = Workflow()

    workflow.transform(
        name='get_chromosomes',
        func=get_chromosomes,
        ret=pypeliner.managed.TempOutputObj('chrom_dummy', 'chrom'),
        args=(pypeliner.managed.InputFile(tumour_bam_file),),
        kwargs={'chromosomes': chromosomes},
    )

    workflow.transform(
        name='split_chromosomes',
        axes=('chrom',),
        func=get_coords,
        ret=pypeliner.managed.TempOutputObj('coord_dummy', 'chrom', 'coord'),
        args=(
            pypeliner.managed.InputFile(tumour_bam_file),
            pypeliner.managed.TempInputObj('chrom_dummy', 'chrom'),
            split_size
        )
    )

    workflow.transform(
        name='count_fasta_bases',
        ctx={'mem': 2, 'num_retry': 3, 'mem_retry_increment': 2},
        func=tasks.count_fasta_bases,
        args=(
            pypeliner.managed.InputFile(ref_genome_fasta_file),
            pypeliner.managed.TempOutputFile('ref_base_counts.tsv')
        )
    )

    workflow.transform(
        name='get_known_chromosomes_sizes',
        ctx={'local': True},
        func=get_known_chromosome_sizes,
        ret=pypeliner.managed.TempOutputObj('known_sizes', 'chrom', axes_origin=[]),
        args=(
            pypeliner.managed.InputFile(tumour_bam_file),
            pypeliner.managed.TempInputFile('ref_base_counts.tsv'),
            chromosomes
        )
    )

    workflow.transform(
        name='call_somatic_variants',
        axes=('chrom', 'coord'),
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=tasks.call_somatic_variants,
        args=(
            pypeliner.managed.InputFile(normal_bam_file),
            pypeliner.managed.InputFile(tumour_bam_file),
            pypeliner.managed.InputFile(ref_genome_fasta_file),
            pypeliner.managed.TempOutputFile('somatic.indels.unfiltered.vcf', 'chrom', 'coord'),
            pypeliner.managed.TempOutputFile('somatic.indels.unfiltered.vcf.window', 'chrom', 'coord'),
            pypeliner.managed.TempOutputFile('somatic.snvs.unfiltered.vcf', 'chrom', 'coord'),
            pypeliner.managed.TempOutputFile('strelka.stats', 'chrom', 'coord'),
            pypeliner.managed.TempInputObj('chrom_dummy', 'chrom'),
            pypeliner.managed.TempInputObj('coord_dummy', 'chrom', 'coord'),
            pypeliner.managed.TempInputObj('known_sizes', 'chrom')
        )
    )

    workflow.transform(
        name='add_indel_filters',
        axes=('chrom',),
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=tasks.filter_indel_file_list,
        args=(
            pypeliner.managed.TempInputFile('somatic.indels.unfiltered.vcf', 'chrom', 'coord'),
            pypeliner.managed.TempInputFile('strelka.stats', 'chrom', 'coord'),
            pypeliner.managed.TempInputFile('somatic.indels.unfiltered.vcf.window', 'chrom', 'coord'),
            pypeliner.managed.TempOutputFile('somatic.indels.filtered.vcf', 'chrom'),
            pypeliner.managed.TempInputObj('chrom_dummy', 'chrom'),
            pypeliner.managed.TempInputObj('known_sizes', 'chrom')
        ),
        kwargs={'use_depth_filter': use_depth_thresholds}
    )

    workflow.transform(
        name='add_snv_filters',
        axes=('chrom',),
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=tasks.filter_snv_file_list,
        args=(
            pypeliner.managed.TempInputFile('somatic.snvs.unfiltered.vcf', 'chrom', 'coord'),
            pypeliner.managed.TempInputFile('strelka.stats', 'chrom', 'coord'),
            pypeliner.managed.TempOutputFile('somatic.snvs.filtered.vcf', 'chrom'),
            pypeliner.managed.TempInputObj('chrom_dummy', 'chrom'),
            pypeliner.managed.TempInputObj('known_sizes', 'chrom')
        ),
        kwargs={'use_depth_filter': use_depth_thresholds}
    )

    workflow.transform(
        name='merge_indels',
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=vcf_tasks.concatenate_vcf,
        args=(
            pypeliner.managed.TempInputFile('somatic.indels.filtered.vcf', 'chrom'),
            pypeliner.managed.TempOutputFile('somatic.indels.filtered.vcf.gz')
        )
    )

    workflow.transform(
        name='merge_snvs',
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=vcf_tasks.concatenate_vcf,
        args=(
            pypeliner.managed.TempInputFile('somatic.snvs.filtered.vcf', 'chrom'),
            pypeliner.managed.TempOutputFile('somatic.snvs.filtered.vcf.gz')
        )
    )

    workflow.transform(
        name='filter_indels',
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=vcf_tasks.filter_vcf,
        args=(
            pypeliner.managed.TempInputFile('somatic.indels.filtered.vcf.gz'),
            pypeliner.managed.TempOutputFile('somatic.indels.passed.vcf')
        )
    )

    workflow.transform(
        name='filter_snvs',
        ctx={'mem': 4, 'num_retry': 3, 'mem_retry_increment': 2},
        func=vcf_tasks.filter_vcf,
        args=(
            pypeliner.managed.TempInputFile('somatic.snvs.filtered.vcf.gz'),
            pypeliner.managed.TempOutputFile('somatic.snvs.passed.vcf')
        )
    )

    workflow.transform(
        name='finalise_indels',
        func=vcf_tasks.finalise_vcf,
        args=(
            pypeliner.managed.TempInputFile('somatic.indels.passed.vcf'),
            pypeliner.managed.OutputFile(indel_vcf_file)
        )
    )

    workflow.transform(
        name='finalise_snvs',
        func=vcf_tasks.finalise_vcf,
        args=(
            pypeliner.managed.TempInputFile('somatic.snvs.passed.vcf'),
            pypeliner.managed.OutputFile(snv_vcf_file)
        )
    )

    return workflow


def get_chromosomes(bam_file, chromosomes=None):

    chromosomes = _get_chromosomes(bam_file, chromosomes)

    return dict(zip(chromosomes, chromosomes))


def _get_chromosomes(bam_file, chromosomes=None):
    bam = pysam.Samfile(bam_file, 'rb')

    if chromosomes is None:
        chromosomes = bam.references

    else:
        chromosomes = chromosomes

    return [str(x) for x in chromosomes]


def get_coords(bam_file, chrom, split_size):

    coords = {}

    bam = pysam.Samfile(bam_file, 'rb')

    chrom_lengths = dict(zip(bam.references, bam.lengths))

    length = chrom_lengths[chrom]

    lside_interval = range(1, length + 1, split_size)

    rside_interval = range(split_size, length + split_size, split_size)

    for coord_index, (beg, end) in enumerate(zip(lside_interval, rside_interval)):
        coords[coord_index] = (beg, end)

    return coords


def get_known_chromosome_sizes(bam_file, size_file, chromosomes):
    chromosomes = _get_chromosomes(bam_file, chromosomes)

    sizes = {}

    with open(size_file, 'r') as fh:
        reader = csv.DictReader(fh, ['path', 'chrom', 'known_size', 'size'], delimiter='\t')

        for row in reader:
            if row['chrom'] not in chromosomes:
                continue

            sizes[row['chrom']] = int(row['known_size'])

    return sizes
