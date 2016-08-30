import gzip


def split_fastq(in_filename, out_filenames, num_reads_per_file):
    """ Split a fastq file.
    """
    
    if in_filename.endswith('.gz'):
        opener = gzip.open
    else:
        opener = open
    with opener(in_filename, 'r') as in_file:
        file_number = 0
        out_file = None
        out_file_read_count = None
        try:
            for name, seq, comment, qual in itertools.izip_longest(*[in_file]*4):
                if out_file is None or out_file_read_count == num_reads_per_file:
                    if out_file is not None:
                        out_file.close()
                    out_file = open(out_filenames[file_number], 'w')
                    out_file_read_count = 0
                    file_number += 1
                out_file.write(name)
                out_file.write(seq)
                out_file.write(comment)
                out_file.write(qual)
                out_file_read_count += 1
        finally:
            if out_file is not None:
                out_file.close()