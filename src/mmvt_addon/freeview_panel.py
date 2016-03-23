import bpy
import mmvt_utils as mu
import numpy as np
import os.path as op
import time
from sys import platform as _platform

MAC_FREEVIEW_CMD = '/Applications/freesurfer/Freeview.app/Contents/MacOS/Freeview'

bpy.types.Scene.freeview_listen_to_keyboard = bpy.props.BoolProperty(default=False)
bpy.types.Scene.freeview_listener_is_running = bpy.props.BoolProperty(default=False)


def save_cursor_position():
    root = mu.get_user_fol()
    point = bpy.context.scene.cursor_location * 10.0
    freeview_cmd = 'freeview --ras {} {} {} tkreg\n'.format(point[0], point[1], point[2]).encode()
    if FreeviewPanel.freeview_queue:
        FreeviewPanel.freeview_queue.put(freeview_cmd)
    freeview_fol = op.join(root, 'freeview')
    mu.make_dir(freeview_fol)
    np.savetxt(op.join(freeview_fol, 'edit.dat'), point)
    cursor_position = np.array(bpy.context.scene.cursor_location) * 10
    ret = mu.conn_to_listener.send_command(dict(cmd='slice_viewer_change_pos',data=dict(
        position=cursor_position)))
    # if not ret:
    #     mu.message(None, 'Listener was stopped! Try to restart')


def goto_cursor_position():
    root = mu.get_user_fol()
    point = np.genfromtxt(op.join(root, 'freeview', 'edit.dat'))
    bpy.context.scene.cursor_location = point / 10.0


class FreeviewKeyboardListener(bpy.types.Operator):
    bl_idname = 'ohad.freeview_keyboard_listener'
    bl_label = 'freeview_keyboard_listener'
    bl_options = {'UNDO'}
    press_time = time.time()

    def modal(self, context, event):
        if time.time() - self.press_time > 1 and bpy.context.scene.freeview_listen_to_keyboard and \
                event.type not in ['TIMER', 'MOUSEMOVE', 'WINDOW_DEACTIVATE', 'INBETWEEN_MOUSEMOVE', 'TIMER_REPORT', 'NONE']:
            self.press_time = time.time()
            print(event.type)
            if event.type == 'LEFTMOUSE':
                save_cursor_position()
            else:
                pass
        return {'PASS_THROUGH'}

    def invoke(self, context, event=None):
        if not bpy.context.scene.freeview_listener_is_running:
            context.window_manager.modal_handler_add(self)
            bpy.context.scene.freeview_listener_is_running = True
        bpy.context.scene.freeview_listen_to_keyboard = not bpy.context.scene.freeview_listen_to_keyboard
        return {'RUNNING_MODAL'}


class FreeviewGotoCursor(bpy.types.Operator):
    bl_idname = "ohad.freeview_goto_cursor"
    bl_label = "Goto Cursor"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        goto_cursor_position()
        return {"FINISHED"}


class FreeviewSaveCursor(bpy.types.Operator):
    bl_idname = "ohad.freeview_save_cursor"
    bl_label = "Save Cursor"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        save_cursor_position()
        return {"FINISHED"}


class SliceViewerOpen(bpy.types.Operator):
    bl_idname = "ohad.slice_viewer"
    bl_label = "Slice Viewer"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        mri_fname = op.join(mu.get_user_fol(), 'freeview', 'orig.mgz')
        cursor_position = np.array(bpy.context.scene.cursor_location) * 10.0
        ret = mu.conn_to_listener.send_command(dict(cmd='open_slice_viewer',data=dict(
            mri_fname=mri_fname, position=cursor_position)))
        if not ret:
            mu.message(self, 'Listener was stopped! Try to restart')
        return {"FINISHED"}


class FreeviewOpen(bpy.types.Operator):
    bl_idname = "ohad.freeview_open"
    bl_label = "Open Freeview"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        root = mu.get_user_fol()
        sig = op.join(root, 'freeview', 'sig_subject.mgz')
        sig_cmd = '' #'-v {}:colormap=heat' if op.isfile(sig) else ''
        T1 = op.join(root, 'freeview', 'T1.mgz')#'orig.mgz')
        aseg = op.join(root, 'freeview', '{}+aseg.mgz'.format(bpy.context.scene.atlas))
        lut = op.join(root, 'freeview', '{}ColorLUT.txt'.format(bpy.context.scene.atlas))
        electrodes = self.get_electrodes_groups(root)
        freeview_app = MAC_FREEVIEW_CMD if _platform == "darwin" else 'freeview'
        cmd = '{} {} "{}":opacity=0.3 "{}":opacity=0.05:colormap=lut:lut="{}" -c {}'.format(freeview_app, sig_cmd, T1, aseg, lut, electrodes)
        print(cmd)
        FreeviewPanel.freeview_queue = mu.run_command_in_new_thread(cmd)
        return {"FINISHED"}

    def get_electrodes_groups(self, root):
        groups = set([obj.name[:3] for obj in bpy.data.objects['Deep_electrodes'].children])
        groups_files = ''
        for group in groups:
            groups_files += '"{}" '.format(op.join(root, 'freeview', '{}.dat'.format(group)))
        return groups_files



class FreeviewPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Freeview Panel"
    addon = None
    freeview_queue = None

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=0)
        row.operator(FreeviewOpen.bl_idname, text="Freeview", icon='PARTICLES')
        row = layout.row(align=0)
        row.operator(FreeviewGotoCursor.bl_idname, text="Goto Cursor", icon='HAND')
        row.operator(FreeviewSaveCursor.bl_idname, text="Save Cursor", icon='FORCE_CURVE')
        row = layout.row(align=0)
        row.operator(SliceViewerOpen.bl_idname, text="Slice Viewer", icon='PARTICLES')
        if not bpy.context.scene.freeview_listen_to_keyboard:
            layout.operator(FreeviewKeyboardListener.bl_idname, text="Listen to keyboard", icon='COLOR_GREEN')
        else:
            layout.operator(FreeviewKeyboardListener.bl_idname, text="Stop listen to keyboard", icon='COLOR_RED')


def init(addon):
    FreeviewPanel.addon = addon
    bpy.context.scene.freeview_listen_to_keyboard = False
    bpy.context.scene.freeview_listener_is_running = False
    register()


def register():
    try:
        unregister()
        bpy.utils.register_class(FreeviewGotoCursor)
        bpy.utils.register_class(FreeviewSaveCursor)
        bpy.utils.register_class(FreeviewOpen)
        bpy.utils.register_class(FreeviewPanel)
        bpy.utils.register_class(SliceViewerOpen)
        bpy.utils.register_class(FreeviewKeyboardListener)
        print('Freeview Panel was registered!')
    except:
        print("Can't register Freeview Panel!")


def unregister():
    try:
        bpy.utils.unregister_class(FreeviewGotoCursor)
        bpy.utils.unregister_class(FreeviewSaveCursor)
        bpy.utils.unregister_class(FreeviewOpen)
        bpy.utils.unregister_class(FreeviewPanel)
        bpy.utils.unregister_class(SliceViewerOpen)
        bpy.utils.unregister_class(FreeviewKeyboardListener)
    except:
        pass
        # print("Can't unregister Freeview Panel!")