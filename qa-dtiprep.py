#!/usr/bin/env python

# Must have the following installed and on the system path:
# mricron (for dicom to nifti)
# DWIConvert (for dicom to nrrd)
# DTIPrep
# FSL

# Author: Michelle Han <mihan@stanford.edu>

#Convert nifti to nrrd
def nifti2nrrd(nifti, bvec, bval, subject, outdir):
    import os
    #command = 'DWIConvert --inputDicomDirectory %s --outputVolume %s/%s.nrrd' % (dicomdir, outdir, subject)
    command = 'DWIConvert --inputVolume %s --inputBVectors %s --inputBValues %s --conversionMode FSLToNrrd --outputVolume %s/%s.nrrd' % (nifti, bvec, bval, outdir, subject)
    os.system(command)

    return os.path.abspath('%s/%s.nrrd' %(outdir, subject))


#Run DTIPrep
def dtiprep(in_file, outdir):
    import os
    from glob import glob

    command = 'DTIPrep -w %s -c -d -p default.xml -f %s' %(in_file, outdir)
    os.system(command)

    qcfile = os.path.abspath(glob('%s/*QC*nrrd' %outdir)[0])
    xmlfile = os.path.abspath(glob('%s/*QC*xml' %outdir)[0])

    return qcfile, xmlfile


#Convert QCed nrrd to nifti
#def dicom2nrrd(dicomdir, subject, outdir):
def nrrd2nifti(subject, outdir):
    import os

    outname = '%s/%s_QCed' %(outdir, subject)
    command = 'DWIConvert --inputVolume %s.nrrd --outputBVectors %s.bvec --outputBValues %s.bval --conversionMode NrrdToFSL --outputVolume %s.nii.gz' % (outname, outname, outname, outname)
    os.system(command)

    return os.path.abspath('%s/%s_QCed.nii.gz' %(outdir, subject))



#Get volume indices to exclude
def get_excluded_vols(in_file): # in_file is the xmlqcresult file that dtiprep outputs
    f = open(in_file, 'r')
    prev_line = ''
    bad_vols = []
    for line in f:
        if 'EXCLUDE_SLICECHECK' in line and 'gradient' in prev_line:
            bad_vols.append(int(prev_line.split('_')[1][0:4]))
    prev_line = line
    f.close()

    return bad_vols  #array of integers that are volume #'s rejected by dtiprep


#Remove bad volumes from the bval and bvec files
def clean_b_files(to_remove, bval, bvec, subject, outdir):
    import os

    bval = open(bval, 'r')
    bvec = open(bvec, 'r')
    qc_bval = open('%s/%s_QCed.bval'%(outdir, subject), 'w')
    qc_bvec = open('%s/%s_QCed.bvec'%(outdir, subject), 'w')

    counter = 0
    for line in bval:
        if counter not in to_remove:
            qc_bval.write(line)
            counter += 1

    counter = 0
    for line in bvec:
        if counter not in to_remove:
            qc_bvec.write(line)
            counter += 1

    bval.close()
    bvec.close()
    qc_bval.close()
    qc_bvec.close()
    bval_return = os.path.abspath('%s/%s_QCed.bval'%(outdir, subject))
    bvec_return = os.path.abspath('%s/%s_QCed.bval'%(outdir, subject))

    return bval_return, bvec_return


#Remove bad volumes from the nifti file
def remove_vols(in_file, to_remove, subject, outdir):
    import os

    command = 'mkdir %s/temp' %outdir
    os.system(command)
    command = 'fslsplit %s %s/temp/%s_split' % (in_file, outdir, subject)
    os.system(command)

    for vol in to_remove:
        vol = str(vol)
        command = 'rm -f %s/temp/*split*%s*' % (outdir, vol)
        os.system(command)

    command = 'fslmerge -t %s/%s_QCed.nii.gz %s/temp/%s_split*' % (outdir, subject, outdir, subject) #Do we want to include a manual exclusion option here?
    os.system(command)
    command = 'rm -rf %s/temp' %outdir
    os.system(command)

    return os.path.abspath('%s/%s_QCed.nii.gz'%(outdir, subject))


#Put it all together
from argparse import ArgumentParser
if __name__ == "__main__":
    import os
    parser = ArgumentParser()
    parser.add_argument("--nifti", dest="nifti", help="nifti file")
    parser.add_argument("--bval", dest="bval", help="bval file")
    parser.add_argument("--bvec", dest="bvec", help="bvec file")
    parser.add_argument("--outdir", dest="outdir", help="output directory")
    args = parser.parse_args()

    def get_files(root_path):
        file_paths = []
        for (root, dirs, files) in os.walk(root_path):
            for name in files:
                file_paths.append(os.path.join(root_path, name))
        return file_paths

    base = '/flywheel/v0/input/'

    if not args.nifti:
        args.nifti = get_files(os.path.join(base, 'nifti'))[0]
    if not args.bval:
        args.bval = get_files(os.path.join(base, 'bval'))[0]
    if not args.bvec:
        args.bvec = get_files(os.path.join(base, 'bvec'))[0]
    if not args.outdir:
        args.outdir = '/flywheel/v0/output'

    subject = args.nifti
    subject = subject.split("/")[-1].split(".")[0]

    # run everything
    nrrd_file = nifti2nrrd(args.nifti, args.bvec, args.bval, subject, args.outdir)
    qcfile, xmlfile = dtiprep(nrrd_file, args.outdir)
    nifti = nrrd2nifti(subject, args.outdir)

#   bad_vols = get_excluded_vols(xmlfile)
#   if len(bad_vols) > 0:
#       bval, bvec = clean_b_files(bad_vols, bval, bvec, args.subject, args.outdir)
#       nifti = remove_vols(nifti, bad_vols, args.subject, args.outdir)

