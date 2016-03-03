import numpy as np
import sys
import os
import os.path as op
import shutil
import mne
import scipy.io as sio
from src import utils


LINKS_DIR = utils.get_links_dir()
SUBJECTS_DIR = utils.get_link_dir(LINKS_DIR, 'subjects', 'SUBJECTS_DIR')
FREE_SURFER_HOME = utils.get_link_dir(LINKS_DIR, 'freesurfer', 'FREESURFER_HOME')
BLENDER_ROOT_DIR = op.join(LINKS_DIR, 'mmvt')

TASK_MSIT, TASK_ECR = range(2)
HEMIS = utils.HEMIS
STAT_AVG, STAT_DIFF = range(2)
STAT_NAME = {STAT_DIFF: 'diff', STAT_AVG: 'avg'}


def montage_to_npy(montage_file, output_file):
    sfp = mne.channels.read_montage(montage_file)
    np.savez(output_file, pos=np.array(sfp.pos), names=sfp.ch_names)


def electrodes_csv_to_npy(ras_file, output_file, bipolar=False, delimiter=','):
    data = np.genfromtxt(ras_file, dtype=str, delimiter=delimiter)
    data = fix_str_items_in_csv(data)
    # Check if the electrodes coordinates has a header
    try:
        header = data[0, 1:].astype(float)
    except:
        data = np.delete(data, (0), axis=0)

    pos = data[:, 1:].astype(float)
    if bipolar:
        names = []
        pos_biploar, pos_org = [], []
        for index in range(data.shape[0]-1):
            elc_group1, elc_num1 = elec_group_number(data[index, 0])
            elc_group2, elc_num12 = elec_group_number(data[index+1, 0])
            if elc_group1==elc_group2:
                names.append('{}-{}'.format(data[index+1, 0],data[index, 0]))
                pos_biploar.append(pos[index] + (pos[index+1]-pos[index])/2)
                pos_org.append([pos[index], pos[index+1]])
        pos = np.array(pos_biploar)
        pos_org = np.array(pos_org)
    else:
        names = data[:, 0]
        pos_org = []
    if len(set(names)) != len(names):
        raise Exception('Duplicate electrodes names!')
    if pos.shape[0] != len(names):
        raise Exception('pos dim ({}) != names dim ({})'.format(pos.shape[0], len(names)))
    print(np.hstack((names.reshape((len(names), 1)), pos)))
    np.savez(output_file, pos=pos, names=names, pos_org=pos_org)


def fix_str_items_in_csv(csv):
    lines = []
    for line in csv:
        fix_line = list(map(lambda x: str(x).replace('"', ''), line))
        if not np.all([len(v)==0 for v in fix_line[1:]]):
            lines.append(fix_line)
    return np.array(lines)


def elec_group_number(elec_name, bipolar=False):
    if bipolar:
        elec_name2, elec_name1 = elec_name.split('-')
        group, num1 = elec_group_number(elec_name1, False)
        _, num2 = elec_group_number(elec_name2, False)
        return group, num1, num2
    else:
        ind = np.where([int(s.isdigit()) for s in elec_name])[-1][0]
        num = int(elec_name[ind:])
        group = elec_name[:ind]
        return group, num


def read_electrodes(electrodes_file):
    elecs = np.load(electrodes_file)
    for (x, y, z), name in zip(elecs['pos'], elecs['names']):
        print(name, x, y, z)


def read_electrodes_data(elecs_data_dic, conditions, montage_file, output_file_name, from_t=0, to_t=None,
                         norm_by_percentile=True, norm_percs=(1,99)):
    for cond_id, (field, file_name) in enumerate(elecs_data_dic.iteritems()):
        d = sio.loadmat(file_name)
        if cond_id == 0:
            data = np.zeros((d[field].shape[0], to_t - from_t, 2))
        times = np.arange(0, to_t*2, 2)
        # todo: Need to do some interpulation for the MEG
        data[:, :, cond_id] = d[field][:, times]
        # time = d['Time']
    if norm_by_percentile:
        norm_val = max(map(abs, [np.percentile(data, norm_percs[ind]) for ind in [0,1]]))
    else:
        norm_val = max(map(abs, [np.max(data), np.min(data)]))
    data /= norm_val
    sfp = mne.channels.read_montage(montage_file)
    avg_data = np.mean(data, 2)
    colors = utils.mat_to_colors(avg_data, np.percentile(avg_data, 10), np.percentile(avg_data, 90), colorsMap='RdBu', flip_cm=True)
    np.savez(output_file_name, data=data, names=sfp.ch_names, conditions=conditions, colors=colors)


def read_electrodes_positions(subject, bipolar=False, copy_to_blender=True):
    rename_and_convert_electrodes_file(subject)
    electrodes_folder = op.join(SUBJECTS_DIR, subject, 'electrodes')
    csv_file = op.join(electrodes_folder, '{}_RAS.csv'.format(subject))
    if not op.isfile(csv_file):
        print('No electrodes coordinates file! {}'.format(csv_file))
        return None

    output_file_name = 'electrodes{}_positions.npz'.format('_bipolar' if bipolar else '')
    output_file = op.join(SUBJECTS_DIR, subject, 'electrodes', output_file_name)
    electrodes_csv_to_npy(csv_file, output_file, bipolar)
    if copy_to_blender:
        blender_file = op.join(BLENDER_ROOT_DIR, subject, output_file_name)
        shutil.copyfile(output_file, blender_file)
    return output_file


def rename_and_convert_electrodes_file(subject):
    subject_elec_fname_pattern = op.join(SUBJECTS_DIR, subject, 'electrodes', '{subject}_RAS.{postfix}')
    subject_elec_fname_csv_upper = subject_elec_fname_pattern.format(subject=subject.upper(), postfix='csv')
    subject_elec_fname_csv = subject_elec_fname_pattern.format(subject=subject, postfix='csv')
    subject_elec_fname_xlsx_upper = subject_elec_fname_pattern.format(subject=subject.upper(), postfix='xlsx')
    subject_elec_fname_xlsx = subject_elec_fname_pattern.format(subject=subject, postfix='xlsx')

    if op.isfile(subject_elec_fname_csv_upper):
        os.rename(subject_elec_fname_csv_upper, subject_elec_fname_csv)
    elif op.isfile(subject_elec_fname_xlsx_upper):
        os.rename(subject_elec_fname_xlsx_upper, subject_elec_fname_xlsx)
    if op.isfile(subject_elec_fname_xlsx):
        utils.csv_from_excel(subject_elec_fname_xlsx, subject_elec_fname_csv)


def create_electrode_data_file(subject, task, from_t, to_t, stat, conditions, bipolar, moving_average_win_size=0):
    input_file = op.join(SUBJECTS_DIR, subject, 'electrodes', 'electrodes_data.mat')
    output_file = op.join(BLENDER_ROOT_DIR, subject, 'electrodes{}_data_{}.npz'.format(
            '_bipolar' if bipolar else '', STAT_NAME[stat]))
    if task==TASK_ECR:
        read_electrodes_data_one_mat(input_file, conditions, stat, output_file,
            electrodeses_names_fiels='names', field_cond_template = '{}_ERP', from_t=from_t, to_t=to_t,
            moving_average_win_size=moving_average_win_size)# from_t=0, to_t=2500)
    elif task==TASK_MSIT:
        if bipolar:
            read_electrodes_data_one_mat(input_file, conditions, stat, output_file,
                electrodeses_names_fiels='electrodes_bipolar', field_cond_template = '{}_bipolar_evoked',
                from_t=from_t, to_t=to_t, moving_average_win_size=moving_average_win_size) #from_t=500, to_t=3000)
        else:
            read_electrodes_data_one_mat(input_file, conditions, stat, output_file,
                electrodeses_names_fiels='electrodes', field_cond_template = '{}_evoked',
                from_t=from_t, to_t=to_t, moving_average_win_size=moving_average_win_size) #from_t=500, to_t=3000)


def calc_colors(data, norm_by_percentile, norm_percs, threshold, cm_big, cm_small, flip_cm_big, flip_cm_small):
    data_max, data_min = utils.get_data_max_min(data, norm_by_percentile, norm_percs)
    data_minmax = max(map(abs, [data_max, data_min]))
    print('data minmax: {}'.format(data_minmax))
    colors = utils.mat_to_colors_two_colors_maps(data, threshold=threshold,
        x_max=data_minmax, x_min = -data_minmax, cm_big=cm_big, cm_small=cm_small,
        default_val=1, flip_cm_big=flip_cm_big, flip_cm_small=flip_cm_small)
    return colors
    # colors = utils.mat_to_colors(stat_data, -data_minmax, data_minmax, color_map)


def check_montage_and_electrodes_names(montage_file, electrodes_names_file):
    sfp = mne.channels.read_montage(montage_file)
    names = np.loadtxt(electrodes_names_file, dtype=np.str)
    names = set([str(e.strip()) for e in names])
    montage_names = set(sfp.ch_names)
    print(names-montage_names)
    print(montage_names-names)


def read_electrodes_data_one_mat(mat_file, conditions, stat, output_file_name, electrodeses_names_fiels,
        field_cond_template, from_t=0, to_t=None, norm_by_percentile=True, norm_percs=(3, 97), threshold=0,
        color_map='jet', cm_big='YlOrRd', cm_small='PuBu', flip_cm_big=False, flip_cm_small=True,
        moving_average_win_size=0):
    # load the matlab file
    d = sio.loadmat(mat_file)
    # get the labels names
    labels = d[electrodeses_names_fiels]
    #todo: change that!!!
    if len(labels) == 1:
        labels = [str(l[0]) for l in labels[0]]
    else:
        labels = [str(l[0][0]) for l in labels]
    # Loop for each condition
    for cond_id, cond_name in enumerate(conditions):
        field = field_cond_template.format(cond_name)
        # initialize the data matrix (electrodes_num x T x 2)
        if cond_id == 0:
            data = np.zeros((d[field].shape[0], to_t - from_t, 2))
        # times = np.arange(0, to_t*2, 2)
        # todo: Need to do some interpulation for the MEG
        cond_data = d[field] # [:, times]
        cond_data_downsample = utils.downsample_2d(cond_data, 2)
        data[:, :, cond_id] = cond_data_downsample[:, from_t:to_t]

    data = utils.normalize_data(data, norm_by_percentile, norm_percs)
    if stat == STAT_AVG:
        stat_data = np.squeeze(np.mean(data, axis=2))
    elif stat == STAT_DIFF:
        stat_data = np.squeeze(np.diff(data, axis=2))
    else:
        raise Exception('Wrong stat value!')

    if moving_average_win_size > 0:
        # data_mv[:, :, cond_id] = utils.downsample_2d(data[:, :, cond_id], moving_average_win_size)
        stat_data_mv = utils.moving_avg(stat_data, moving_average_win_size)

    colors = calc_colors(stat_data, norm_by_percentile, norm_percs, threshold, cm_big, cm_small,
                         flip_cm_big, flip_cm_small)
    colors_mv = calc_colors(stat_data_mv, norm_by_percentile, norm_percs, threshold, cm_big, cm_small,
                            flip_cm_big, flip_cm_small)
    # np.savez(output_file_name, data=data, names=labels, conditions=conditions, colors=colors)
    np.savez(output_file_name, data=data, stat=stat_data_mv, names=labels, conditions=conditions, colors=colors_mv)


def main(subject, bipolar, conditions, task, from_t_ind, to_t_ind, stat, add_activity=True):
    # *) Read the electrodes data
    electrodes_file = read_electrodes_positions(subject, bipolar=bipolar)
    if electrodes_file and add_activity:
        create_electrode_data_file(subject, task, from_t_ind, to_t_ind, stat, conditions, bipolar)
    # misc
    # check_montage_and_electrodes_names('/homes/5/npeled/space3/ohad/mg79/mg79.sfp', '/homes/5/npeled/space3/inaivu/data/mg79_ieeg/angelique/electrode_names.txt')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        subject = sys.argv[1]
    else:
        subject = 'mg96'
    print('subject: {}'.format(subject))
    utils.make_dir(op.join(BLENDER_ROOT_DIR, subject))
    task = TASK_MSIT
    if task==TASK_ECR:
        conditions = ['happy', 'fear']
    elif task==TASK_MSIT:
        conditions = ['noninterference', 'interference']
    else:
        raise Exception('unknown task id!')
    from_t, to_t = -500, 2000
    from_t_ind, to_t_ind = 500, 3000
    bipolar = False
    stat = STAT_DIFF
    add_activity = False

    main(subject, bipolar, conditions, task, from_t_ind, to_t_ind, stat, add_activity)
    print('finish!')