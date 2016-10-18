#! /usr/bin/python3  

usage_str = '''Usage: {} <transform_file> <data_file> <output_file>

Creates a new file that combines the transform information of the 
<transform_file> with the data of the <data_file>. Both of the input
files must have the same sampling grid.

Useful for correcting processing steps that don't properly preserve
transform information.'''

#
# This script requires Python 3.X
# MINC commands used: mincreshape, minc_modify_header, mincinfo.
#
import subprocess, sys, math, tempfile, os

def usage(argv):
    print(usage_str.format(argv[0]))
    exit(-1)

def run_command(arguments):
    res = b''
    try:
        res = subprocess.check_output(arguments)
    except subprocess.CalledProcessError as e:
        print("Command {} failed".format(' '.join(arguments)))
        print(e.returncode, e.output)
    return res.decode('unicode_escape')

def get_directions(directions):
    result = []
    for dimname in directions.keys():
        result.append(('-' if directions[dimname] < 0 else '+') + 
                      dimname[0] + 'direction')
    return result

if len(sys.argv) < 4:
    usage(sys.argv)

xfm_file = sys.argv[1]
data_file = sys.argv[2]
output_file = sys.argv[3]

# We need to restructure the data into our output file, using the 
# original dimension ordering 

xfm_names = run_command(['mincinfo', '-vardims', 'image', xfm_file]).split()

xfm_lengths = {}
xfm_steps = {}
xfm_starts = {}
xfm_cosines = {}
xfm_dirs = {}
for dimname in xfm_names:
    xfm_lengths[dimname] = int(run_command(['mincinfo', '-dimlength',
                                            dimname, xfm_file]))
    data_length = int(run_command(['mincinfo', '-dimlength', dimname,
                                   data_file]))
    if data_length != xfm_lengths[dimname]:
        print("Sampling grids do not match!\n")

    xfm_steps[dimname] = float(run_command(['mincinfo', '-attvalue',
                                            dimname + ':step', xfm_file]))

    xfm_dirs[dimname] = math.copysign(1, xfm_steps[dimname])

    xfm_starts[dimname] = float(run_command(['mincinfo', '-attvalue',
                                             dimname + ':start', xfm_file]))

    if dimname[1:] == "space":
        # Get the direction cosines.
        output = run_command(['mincinfo', '-attvalue', 
                              dimname + ':direction_cosines', xfm_file])
        xfm_cosines[dimname] = list(map(float, output.split()))


# Create a tempfile for our intermediate step.
handle, temp_file = tempfile.mkstemp()
os.close(handle)

# Now create the new output file by reshaping the data file according to
# the transform file:

run_command(['mincreshape', '-clobber', '-dimorder', ','.join(xfm_names)] +
             [data_file, temp_file])

run_command(['mincreshape'] + get_directions(xfm_dirs) + [temp_file, output_file])

for dimname in xfm_names:
    run_command(['minc_modify_header', '-dinsert', 
                 dimname + ':step=' + str(xfm_steps[dimname]), output_file])
    run_command(['minc_modify_header', '-dinsert', 
                 dimname + ':start=' + str(xfm_starts[dimname]), output_file])
    cosines = xfm_cosines.get(dimname, [])
    if cosines:
        run_command(['minc_modify_header', '-dinsert', 
                     dimname + ':direction_cosines=' + 
                     ','.join(map(str, xfm_cosines[dimname])), output_file])

os.remove(temp_file)
