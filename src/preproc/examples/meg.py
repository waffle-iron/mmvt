import argparse
import os.path as op
import shutil

from src.preproc import meg as meg
from src.utils import utils
from src.utils import args_utils as au
from src.utils import preproc_utils as pu

LINKS_DIR = utils.get_links_dir()
MEG_DIR = utils.get_link_dir(LINKS_DIR, 'meg')
FMRI_DIR = utils.get_link_dir(utils.get_links_dir(), 'fMRI')


def read_epoches_and_calc_activity(subject, mri_subject):
    args = meg.read_cmd_args(['-s', subject, '-m', mri_subject])
    args.function = ['calc_stc_per_condition', 'calc_labels_avg_per_condition', 'smooth_stc', 'save_activity_map']
    args.pick_ori = 'normal'
    args.colors_map = 'jet'
    meg.run_on_subjects(args)


def calc_single_trial_labels_msit(subject, mri_subject):
    args = meg.read_cmd_args(['-s', subject, '-m', mri_subject])
    args.task = 'MSIT'
    args.atlas = 'laus250'
    args.function = 'calc_stc_per_condition,calc_single_trial_labels_per_condition'
    args.t_tmin = -0.5
    args.t_tmax = 2
    args.single_trial_stc = True
    args.fwd_no_cond = False
    args.files_includes_cond = True
    args.constrast = 'interference'
    meg.run_on_subjects(args)


def calc_mne_python_sample_data(args):
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        # atlas='laus250',
        contrast='audvis',
        fname_format='{subject}_audvis-{ana_type}.{file_type}',
        fname_format_cond='{subject}_audvis_{cond}-{ana_type}.{file_type}',
        conditions=['LA', 'RA'],
        read_events_from_file=True,
        t_min=-0.2, t_max=0.5,
        extract_mode=['mean_flip', 'mean', 'pca_flip']
    ))
    meg.call_main(args)


def calc_mne_python_sample_data_stcs_diff(args):
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        contrast = 'audvis',
        fname_format = '{subject}_audvis-{ana_type}.{file_type}',
        fname_format_cond = '{subject}_audvis_{cond}-{ana_type}.{file_type}',
        conditions = ['LA', 'RA']
    ))
    smooth = False
    fname_format, fname_format_cond, conditions = meg.init(args.subject[0], args, args.mri_subject[0])
    stc_template_name = meg.STC_HEMI_SMOOTH if smooth else meg.STC_HEMI
    stc_fnames = [stc_template_name.format(cond=cond, method=args.inverse_method[0], hemi='lh') for cond in conditions.keys()]
    output_fname = stc_template_name.format(cond='diff', method=args.inverse_method[0], hemi='lh')
    meg.calc_stc_diff(*stc_fnames, output_fname)


def calc_msit(args):
    # python -m src.preproc.meg -s ep001 -m mg78 -a laus250 -t MSIT
    #   --contrast interference --t_max 2 --t_min -0.5 --data_per_task 1 --read_events_from_file 1
    #   --events_file_name {subject}_msit_nTSSS_interference-eve.txt --cleaning_method nTSSS
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        task='MSIT',
        function=args.real_function,
        data_per_task=True,
        atlas='laus250',
        contrast='interference',
        cleaning_method='nTSSS',
        t_min=-0.5,
        t_max=2,
        # calc_epochs_from_raw=True,
        read_events_from_file=True,
        # remote_subject_meg_dir='/autofs/space/sophia_002/users/DARPA-MEG/project_orig_msit',
        events_file_name='{subject}_msit_nTSSS_interference-eve.txt',
        reject=False,
        # save_smoothed_activity=True,
        # stc_t=1189,
        morph_to_subject = 'fsaverage5',
        extract_mode=['mean_flip', 'mean', 'pca_flip']
    ))
    meg.call_main(args)


def calc_msit_stcs_diff(args):
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        task='MSIT',
        data_per_task=True,
        contrast='interference',
        cleaning_method='nTSSS'))
    smooth = False
    fname_format, fname_format_cond, conditions = meg.init(args.subject[0], args, args.mri_subject[0])
    stc_template_name = meg.STC_HEMI_SMOOTH if smooth else meg.STC_HEMI
    stc_fnames = [stc_template_name.format(cond=cond, method=args.inverse_method[0], hemi='lh') for cond in conditions.keys()]
    output_fname = stc_template_name.format(cond='diff', method=args.inverse_method[0], hemi='lh')
    meg.calc_stc_diff(*stc_fnames, output_fname)


def morph_stc(args):
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        task='MSIT',
        data_per_task=True,
        contrast='interference',
        cleaning_method='nTSSS'))
    morph_to_subject = 'ab' # 'fsaverage5'
    fname_format, fname_format_cond, conditions = meg.init(args.subject[0], args, args.mri_subject[0])
    meg.morph_stc(conditions, morph_to_subject, args.inverse_method[0], args.n_jobs)


def crop_stc_no_baseline(subject, mri_subject):
    args = meg.read_cmd_args(['-s', subject, '-m', mri_subject])
    args.fname_format = '{subject}_02_f2-35_all_correct_combined'
    args.inv_fname_format = '{subject}_02_f2-35-ico-5-meg-eeg'
    args.stc_t_min = -0.1
    args.stc_t_max = 0.15
    args.base_line_max = None
    meg.run_on_subjects(args)


def check_files_names(subject, mri_subject):
    args = meg.read_cmd_args(['-s', subject, '-m', mri_subject])
    args.fname_format = '{subject}_02_f2-35_all_correct_combined'
    args.inv_fname_format = '{subject}_02_f2-35-ico-5-meg-eeg'
    args.function = 'print_names'
    meg.run_on_subjects(args)


def calc_subcorticals(subject, mri_subject):
    '''-s ep001 -m mg78 -f calc_evoked -t MSIT --contrast interference --cleaning_method nTSSS --data_per_task 1 --read_events_from_file 1 --t_min -0.5 t_max 2.0
    -s ep001 -m mg78 -f make_forward_solution,calc_inverse_operator -t MSIT --contrast interference --cleaning_method nTSSS --data_per_task 1 --fwd_calc_subcorticals 1 --inv_calc_subcorticals 1 --remote_subject_dir="/autofs/space/lilli_001/users/DARPA-Recons/ep001"
    -s ep001 -m mg78 -f calc_sub_cortical_activity,save_subcortical_activity_to_blender -t MSIT -i lcmv --contrast interference --cleaning_method nTSSS --data_per_task 1
    '''
    pass


def calc_rest(args):
    # '-s hc029 -a laus125 -t rest -f calc_evoked,make_forward_solution,calc_inverse_operator --reject 0 --remove_power_line_noise 0 --windows_length 1000 --windows_shift 500 --remote_subject_dir "/autofs/space/lilli_001/users/DARPA-Recons/hc029"''
    # '-s hc029 -a laus125 -t rest -f calc_stc_per_condition,calc_labels_avg_per_condition --single_trial_stc 1 --remote_subject_dir "/autofs/space/lilli_001/users/DARPA-Recons/hc029"'
    # '-s subject-name -a atlas-name -t rest -f rest_functions' --l_freq 8 --h_freq 13 --windows_length 500 --windows_shift 100
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        atlas='laus125',
        function='rest_functions',
        task='rest',
        cleaning_method='tsss',
        reject=False, # Should be True here, unless you are dealling with bad data...
        remove_power_line_noise=True,
        l_freq=3, h_freq=80,
        windows_length=500,
        windows_shift=100,
        inverse_method='MNE',
        remote_subject_dir='/autofs/space/lilli_001/users/DARPA-Recons/{subject}',
        # This properties are set automatically if task=='rest'
        # calc_epochs_from_raw=True,
        # single_trial_stc=True,
        # use_empty_room_for_noise_cov=True,
        # windows_num=10,
        # baseline_min=0,
        # baseline_max=0,
    ))
    meg.call_main(args)


def load_fieldtrip_volumetric_data(args):
    # http://www.fieldtriptoolbox.org/reference/ft_sourceinterpolate
    # http://www.fieldtriptoolbox.org/reference/ft_sourceplot
    # https://github.com/fieldtrip/fieldtrip/blob/master/ft_sourceplot.m
    # https://github.com/fieldtrip/fieldtrip/blob/master/ft_sourceinterpolate.m
    import scipy.io as sio
    import nibabel as nib
    from src.preproc import fMRI
    import numpy as np

    overwrite = True
    output_fname = op.join(MEG_DIR, args.subject[0], 'sourceInterp.nii')
    if not op.isfile(output_fname) or overwrite:
        fname = op.join(MEG_DIR, args.subject[0], 'sourceInterp.mat')
        # load Matlab/Fieldtrip data
        mat = sio.loadmat(fname, squeeze_me=True, struct_as_record=False)
        ft_data = mat['sourceInterp']
        data = ft_data.stat2
        t1 = nib.load(op.join(MEG_DIR, args.subject[0], 'nihpd_asym_10.0-14.0_t1w.nii'))
        affine = t1.affine
        nib.save(nib.Nifti1Image(data, affine), output_fname)
    surface_output_template = op.join(MEG_DIR, args.subject[0], 'sourceInterp_{hemi}.mgz')
    if not utils.both_hemi_files_exist(surface_output_template) or overwrite:
        fMRI.project_volume_to_surface(args.subject[0], output_fname)
        for hemi in utils.HEMIS:
            shutil.move(op.join(FMRI_DIR, args.subject[0], 'sourceInterp_{}.mgz'.format(hemi)),
                        op.join(MEG_DIR, args.subject[0], 'sourceInterp_{}.mgz'.format(hemi)))
    fMRI.calc_fmri_min_max(args.subject[0], surface_output_template, norm_percs=(3, 97), symetric_colors=True)
    print('asdf')

def calc_functional_rois(args):
    # -s DC -a laus250 -f find_functional_rois_in_stc --stc_name right-MNE-1-15 --label_name_template "precentral*" --inv_fname right-inv --threshold 99.5
    args = meg.read_cmd_args(dict(
        subject=args.subject,
        mri_subject=args.mri_subject,
        atlas='laus125',
        function='find_functional_rois_in_stc',
        inverse_method='MNE',
        stc_name='right-MNE-1-15',
        label_name_template='precentral*',
        inv_fname='right-inv',
        threshold=99.5
    ))
    meg.call_main(args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MMVT')
    parser.add_argument('-s', '--subject', help='subject name', required=True, type=au.str_arr_type)
    parser.add_argument('-m', '--mri_subject', help='mri subject name', required=False, default=None,
                        type=au.str_arr_type)
    parser.add_argument('-i', '--inverse_method', help='inverse_method', required=False, default='MNE',
                        type=au.str_arr_type)
    parser.add_argument('-f', '--function', help='function name', required=True)
    parser.add_argument('-r', '--real_function', help='function name', required=False, default='all')
    args = utils.Bag(au.parse_parser(parser))
    if not args.mri_subject:
        args.mri_subject = args.subject
    locals()[args.function](args)
    # for subject, mri_subject in zip(args.subject, args.mri_subject):
    #     locals()[args.function](subject, mri_subject)
