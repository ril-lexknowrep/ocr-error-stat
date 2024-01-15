from pathlib import Path
import align.align_lines
from sys import argv

base_path = Path('\\arcanum_2023_OCR\\elkeszult_fr14')
files = base_path.glob('**/*.json')

argv.extend(['file1', 'file2', '-a', 'FR1', '-b', 'FR2',
             '-v', '0', '-o', 'alignments'])

for file in files:
    file14 = str(file)
    if '168ora' not in file14:
        continue
    file15 = file14.replace('_fr14', '_fr15')
    file16 = file15.replace('_fr15', '_fr16')

    argv[1] = file14
    argv[2] = file15
    argv[4] = 'FR14'
    argv[6] = 'FR15'
    align.align_lines.main()

    argv[1] = file15
    argv[2] = file16
    argv[4] = 'FR15'
    argv[6] = 'FR16'
    align.align_lines.main()
