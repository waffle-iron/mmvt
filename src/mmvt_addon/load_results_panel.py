try:
    import bpy
    import bpy_extras
    import mmvt_utils as mu
    IN_BLENDER = True
except:
    from src.mmvt_addon import mmvt_utils as mu
    IN_BLENDER = False
    pass

try:
    import mne
    MNE_EXIST = True
except:
    MNE_EXIST = False

import os.path as op
import shutil
import glob


def _addon():
    return LoadResultsPanel.addon


if IN_BLENDER:
    bpy.types.Scene.nii_label_prompt = bpy.props.StringProperty(description='')
    bpy.types.Scene.nii_label_output = bpy.props.StringProperty(description='')


    class LoadResultsPanel(bpy.types.Panel):
        bl_space_type = "GRAPH_EDITOR"
        bl_region_type = "UI"
        bl_context = "objectmode"
        bl_category = "mmvt"
        bl_label = "Load Results"
        addon = None
        init = False

        def draw(self, context):
            if LoadResultsPanel.init:
                load_results_draw(self, context)


    class LoadEvokesFile(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
        bl_idname = "mmvt.load_evokes_file"
        bl_label = "Load evokes file"

        filename_ext = '.fif'
        filter_glob = bpy.props.StringProperty(default='*.fif', options={'HIDDEN'}, maxlen=255)

        def execute(self, context):
            import_evokes(self.filepath)
            return {'FINISHED'}



    class ChooseSTCFile(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
        bl_idname = "mmvt.choose_stc_file"
        bl_label = "Choose STC file"

        filename_ext = '.stc'
        filter_glob = bpy.props.StringProperty(default='*.stc', options={'HIDDEN'}, maxlen=255)

        def execute(self, context):
            stc_fname = self.filepath
            user_fol = mu.get_user_fol()
            stc_fol = mu.get_fname_folder(stc_fname)
            if stc_fol != op.join(user_fol, 'meg'):
                other_hemi_stc_fname = op.join(stc_fol, '{}.stc'.format(mu.get_other_hemi_label_name(mu.namebase(stc_fname))))
                shutil.copy(stc_fname, op.join(user_fol, 'meg', mu.namebase_with_ext(stc_fname)))
                shutil.copy(other_hemi_stc_fname, op.join(user_fol, 'meg', mu.namebase_with_ext(other_hemi_stc_fname)))
                _addon().init_meg_activity_map()
            _, _, label, hemi = mu.get_hemi_delim_and_pos(mu.namebase(stc_fname))
            bpy.context.scene.meg_files = label
            return {'FINISHED'}


    class ChooseNiftiiFile(bpy.types.Operator, bpy_extras.io_utils.ExportHelper):
        bl_idname = "mmvt.choose_niftii_file"
        bl_label = "Choose niftii file"
        filename_ext = '.*' # '.nii.gz'
        filter_glob = bpy.props.StringProperty(default='*.*', options={'HIDDEN'}, maxlen=255) # nii.gz
        running = False
        fmri_file_template = ''
        _timer = None

        def execute(self, context):
            _addon().clear_colors()
            self.fmri_file_template, hemi, other_hemi = load_surf_files(self.filepath[:-2])
            if hemi == '':
                bpy.context.scene.nii_label_prompt = "Can't determine the hemi!"
                return {'RUNNING_MODAL'}
            self.fmri_npy_template_fname = op.join(mu.get_user_fol(), 'fmri', 'fmri_{}.npy'.format(
                mu.namebase(self.fmri_file_template)))
            print('Waiting for both hemi files to be created ({})'.format(self.fmri_npy_template_fname))
            if self.fmri_file_template != '':
                bpy.context.scene.nii_label_output = 'Loading nii file...'
                ChooseNiftiiFile.running = True
                context.window_manager.modal_handler_add(self)
                self._timer = context.window_manager.event_timer_add(0.1, context.window)
            else:
                bpy.context.scene.nii_label_prompt = 'Please select the nii file for the {} hemi'.format(
                    'right' if hemi == 'lh' else 'left')
            return {'RUNNING_MODAL'}

        def modal(self, context, event):
            if event.type == 'TIMER' and ChooseNiftiiFile.running:
                if mu.both_hemi_files_exist(self.fmri_npy_template_fname):
                    _addon().plot_fmri_file(self.fmri_file_template)
                    if mu.get_parent_fol(self.filepath) != op.join(mu.get_user_fol(), 'fmri'):
                        clean_nii_temp_files(self.fmri_file_template)
                    ChooseNiftiiFile.running = False
                    bpy.context.scene.nii_label_output = ''
                    self.cancel(context)
            return {'PASS_THROUGH'}

        def cancel(self, context):
            if self._timer:
                context.window_manager.event_timer_remove(self._timer)
                self._timer = None
                ChooseNiftiiFile.running = False
            return {'CANCELLED'}


    def load_results_draw(self, context):
        layout = self.layout
        if MNE_EXIST:
            layout.operator(ChooseSTCFile.bl_idname, text="Load stc file", icon='LOAD_FACTORY').filepath=op.join(
                mu.get_user_fol(), 'meg', '*.stc')
            layout.operator(LoadEvokesFile.bl_idname, text="Load evokes file", icon='LOAD_FACTORY').filepath=op.join(
                mu.get_user_fol(), 'meg', '*ave.fif')
        if bpy.context.scene.nii_label_output == '':
            layout.operator(ChooseNiftiiFile.bl_idname, text="Load surface nii file", icon='LOAD_FACTORY').filepath = op.join(
                mu.get_user_fol(), 'fmri', '*.nii*')
            if bpy.context.scene.nii_label_prompt != '':
                layout.label(text=bpy.context.scene.nii_label_prompt)
        else:
            layout.label(text=bpy.context.scene.nii_label_output)

    def init(addon):
        LoadResultsPanel.addon = addon
        mu.make_dir(op.join(mu.get_user_fol(), 'meg'))
        bpy.context.scene.nii_label_prompt = ''
        bpy.context.scene.nii_label_output = ''
        register()
        LoadResultsPanel.init = True


    def register():
        try:
            unregister()
            bpy.utils.register_class(LoadResultsPanel)
            bpy.utils.register_class(ChooseSTCFile)
            bpy.utils.register_class(ChooseNiftiiFile)
            bpy.utils.register_class(LoadEvokesFile)
        except:
            print("Can't register LoadResults Panel!")


    def unregister():
        try:
            bpy.utils.unregister_class(LoadResultsPanel)
            bpy.utils.unregister_class(ChooseSTCFile)
            bpy.utils.unregister_class(ChooseNiftiiFile)
            bpy.utils.unregister_class(LoadEvokesFile)
        except:
            pass


def build_local_fname(nii_fname, user_fol):
    if mu.get_hemi_from_fname(mu.namebase_with_ext(nii_fname)) == '':
        local_fname = mu.get_label_for_full_fname(nii_fname)
        # local_fname = '{}.{}.{}'.format(mu.namebase(nii_fname), hemi, mu.file_type(nii_fname))
    else:
        local_fname = mu.namebase_with_ext(nii_fname)
    return op.join(user_fol, 'fmri', local_fname)


def load_surf_files(nii_fname, run_fmri_preproc=True, user_fol=''):
    fmri_file_template = ''
    if user_fol == '':
        user_fol = mu.get_user_fol()
    nii_fol = mu.get_fname_folder(nii_fname)
    # hemi = mu.get_hemi_from_fname(mu.namebase(nii_fname))
    # if hemi == '':
    hemi, fmri_hemis = mu.get_hemi_from_full_fname(nii_fname)
    if hemi == '':
        hemi = mu.find_hemi_using_vertices_num(nii_fname)
        if hemi == '':
            return '', ''
    # fmri_hemis = mu.get_both_hemis_files(nii_fname)
    local_fname = build_local_fname(nii_fname, user_fol)
    mu.make_dir(op.join(user_fol, 'fmri'))
    if nii_fol != op.join(user_fol, 'fmri'):
        mu.make_link(nii_fname, local_fname, True)
    other_hemi = mu.other_hemi(hemi)
    other_hemi_fname = fmri_hemis[other_hemi]
    # todo: if the other hemi file doens't exist, just create an empty one
    if op.isfile(other_hemi_fname):
        local_other_hemi_fname = build_local_fname(other_hemi_fname, user_fol)
        if nii_fol != op.join(user_fol, 'fmri'):
            mu.make_link(other_hemi_fname, local_other_hemi_fname, True)
        fmri_file_template = mu.get_template_hemi_label_name(mu.namebase_with_ext(local_fname))
        if run_fmri_preproc:
            mu.run_mmvt_func(
                'src.preproc.fMRI', 'load_surf_files', flags='--fmri_file_template "{}"'.format(fmri_file_template))
            # cmd = '{} -m  -s {} -f  --fmri_file_template "{}" --ignore_missing 1'.format(
            #     bpy.context.scene.python_cmd, mu.get_user(), fmri_file_template)
            # mu.run_command_in_new_thread(cmd, False, cwd=mu.get_mmvt_code_root())
    else:
        print("Couldn't find the other hemi file! ({})".format(other_hemi_fname))
    return fmri_file_template, hemi, other_hemi


def clean_nii_temp_files(fmri_file_template, user_fol=''):
    if user_fol == '':
        user_fol = mu.get_user_fol()
    file_type = mu.file_type(fmri_file_template)
    file_temp = op.join(user_fol, 'fmri', '{}'.format(
        fmri_file_template.replace('{hemi}', '?h')[:-len(file_type)]))
    mu.delete_files('{}{}'.format(file_temp, file_type))
    mu.delete_files('{}{}'.format(file_temp, 'mgz'))


def import_evokes(evokes_fname):
    import importlib
    import mne
    mu.add_mmvt_code_root_to_path()
    from src.preproc import meg
    importlib.reload(meg)

    opt_trans_files = glob.glob(op.join(mu.get_parent_fol(evokes_fname), '*.fif'))
    trans_files = meg.filter_trans_files(opt_trans_files)
    trans_file = mu.select_one_file(trans_files, template='*.fif', files_desc='MRI-Head transformation')
    args = mu.get_remote_subject_info_args()
    evokes = mne.read_evokeds(evokes_fname)
    events_keys = [ev.comment for ev in evokes]
    meg.read_sensors_layout(mu.get_user(), args, info=evokes[0].info, trans_file=trans_file)
    meg.save_evokes_to_mmvt(evokes, events_keys, mu.get_user())
    _addon().import_meg_sensors()
    _addon().add_data_to_meg_sensors()
    # _addon().load_all_panels()
    _addon().show_meg_sensors()