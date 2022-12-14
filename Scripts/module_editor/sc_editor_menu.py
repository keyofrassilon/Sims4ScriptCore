import configparser
import os
from os.path import isfile, join

import build_buy
import objects
import services
import sims4
from date_and_time import create_time_span
from interactions.base.immediate_interaction import ImmediateSuperInteraction
from objects.components.types import LIGHTING_COMPONENT, PORTAL_COMPONENT
from objects.object_enums import ResetReason
from sims4.localization import LocalizationHelperTuning
from sims4.math import Vector3
from sims4.resources import Types
from ui.ui_dialog_notification import UiDialogNotification
from weather.weather_enums import WeatherEffectType, WeatherElementTuple, PrecipitationType, CloudType, GroundCoverType, \
    Temperature
from weather.weather_service import get_street_or_region_id_with_weather_tuning

from module_editor.sc_editor_functions import point_object_at, random_orientation, get_similar_objects, \
    rotate_selected_objects, random_scale, scale_selected_objects, reset_scale_selected, reset_scale, \
    paint_selected_object, replace_selected_object, select_object, move_selected_objects, place_selected_objects, \
    get_selected_object, select_all, zone_object_override, zone_object_override_save_state, ground_selected_objects, \
    transmog_from_selected_object, select_objects_by_room, write_objects_to_file, read_file_line, \
    delete_selected_objects, color_selected_object, distance_to_selected, center_selected_objects, \
    object_to_original, model_from_selected_object, fade_selected_object
from scripts_core.sc_input import inputbox
from scripts_core.sc_jobs import compare_room, find_all_objects_by_title, make_clean, make_dirty, object_is_dirty, \
    create_dust, create_trauma, distance_to_by_level, get_tags_from_id, \
    focus_camera_on_position
from scripts_core.sc_jobs import get_sim_info, get_object_info
from scripts_core.sc_menu_class import MainMenu
from scripts_core.sc_message_box import message_box
from scripts_core.sc_object_menu import ObjectMenu
from scripts_core.sc_script_vars import sc_Weather, sc_Vars
from scripts_core.sc_transmogrify import load_material, save_material
from scripts_core.sc_util import error_trap, ld_file_loader, clean_string


class ModuleEditorMenu(ImmediateSuperInteraction):
    filename = None
    datapath = os.path.join(os.environ['USERPROFILE'], "Data")
    directory = None
    initial_value = ""
    light_intensity = None
    light_color = None

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self.sc_editor_menu_choices = ("<font color='#009900'>Get Info</font>",
                                        "Search Objects",
                                        "Find Objects",
                                        "Select Objects",
                                        "Distance",
                                       "<font color='#009900'>Weather Menu</font>",
                                        "<font color='#000000'>Object Select Menu</font>",
                                        "<font color='#000000'>Object Delete Menu</font>",
                                        "<font color='#000000'>Object Rotate Menu</font>",
                                        "<font color='#000000'>Object Scale Menu</font>",
                                       "<font color='#000000'>Object Clone Menu</font>",
                                       "<font color='#000000'>Object Replace Menu</font>",
                                       "<font color='#000000'>Lights Menu</font>",
                                       "<font color='#000000'>Misc Menu</font>")

        self.sc_rotate_menu_choices = ("Point Object",
                              "Rotate This Object",
                              "Rotate Similar Objects",
                              "Rotate Selected Objects")

        self.sc_scale_menu_choices = ("Reset Scale",
                                    "Scale Similar Objects",
                                    "Less Scale Similar Objects",
                                    "Scale Selected Objects")

        self.sc_clone_menu_choices = ("Paint Selected Object",
                                      "Paint Selected Object Input")

        self.sc_delete_menu_choices = ("Delete Selected Objects",
                                       "Delete Similar Objects")

        self.sc_replace_menu_choices = ("Replace Similar Objects",
                                        "Replace Selected Object",
                                        "Zone Object Override",
                                        "Save Zone Objects")

        self.sc_select_menu_choices = ("Select Similar Objects",
                                       "Move Selected Objects",
                                       "Place Objects",
                                       "Place Objects At",
                                       "Ground Objects",
                                       "Center Objects",
                                       "Select All",
                                       "Save Selected Objects",
                                       "Load Objects",
                                       "Select Objects By Room")

        self.sc_lights_menu_choices = ("Show Lights In Room",
                                       "Dim Lights In Room",
                                       "Brighten Lights In Room",
                                       "Copy Light Color",
                                       "Paste Light Color",
                                       "Paste Light Color By Room",
                                       "Paste Light Color By Type")

        self.sc_misc_menu_choices = ("Color Objects",
                                     "Fade Objects",
                                       "Load Object Material",
                                       "Save Object Material",
                                       "Transmog From Selected Object",
                                       "Object To Original",
                                       "Model From Selected Object",
                                       "Focus Camera",
                                       "Find Doors",
                                       "Find Chairs",
                                       "Find TVs",
                                       "Find Stereos",
                                       "Find Routine Objects",
                                       "Find Dirty Objects",
                                       "Make Clean",
                                       "Make Dirty",
                                       "Is Dirty",
                                       "Create Dust",
                                       "Create Trauma")

        self.sc_weather_choices = ()
        self.sc_modify_weather_choices = ("Set Variable",
                                          "Set To Sunny",
                                          "Set To Cloudy",
                                          "Set To Partly Cloudy",
                                          "Set To Foggy",
                                          "Set To No Moisture",
                                          "Set To Rain",
                                          "Set To Snow")

        self.sc_reset_weather_choices = ()

        self.sc_editor_menu = MainMenu(*args, **kwargs)
        self.search_object_picker = ObjectMenu(*args, **kwargs)
        self.explorer = MainMenu(*args, **kwargs)
        self.sc_editor_select_menu = MainMenu(*args, **kwargs)
        self.sc_editor_delete_menu = MainMenu(*args, **kwargs)
        self.sc_editor_rotate_menu = MainMenu(*args, **kwargs)
        self.sc_editor_scale_menu = MainMenu(*args, **kwargs)
        self.sc_editor_clone_menu = MainMenu(*args, **kwargs)
        self.sc_editor_replace_menu = MainMenu(*args, **kwargs)
        self.sc_editor_lights_menu = MainMenu(*args, **kwargs)
        self.sc_editor_misc_menu = MainMenu(*args, **kwargs)
        self.sc_weather_menu = MainMenu(*args, **kwargs)
        self.sc_modify_weather_menu = MainMenu(*args, **kwargs)
        self.sc_reset_weather_menu = MainMenu(*args, **kwargs)
        self.sc_weather = []
        self.script_choice = MainMenu(*args, **kwargs)
        self.weather_ini()

    def _run_interaction_gen(self, timeline):
        self.sc_editor_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_editor_menu.commands = []
        self.sc_editor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Editor Menu is an extension of TOOL by TwistedMexi adding newer functionality to the mod. Editor Menu requires either TOOL or CAW installed.")

    def _menu(self, timeline):
        self.sc_editor_menu.MAX_MENU_ITEMS_TO_LIST = 12
        self.sc_editor_menu.commands = []
        self.sc_editor_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_menu.show(timeline, self, 0, self.sc_editor_menu_choices, "Editor Menu", "Make a selection.")

    def object_select_menu(self, timeline):
        self.sc_editor_select_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_select_menu.commands = []
        self.sc_editor_select_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_select_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_select_menu.show(timeline, self, 0, self.sc_select_menu_choices, "Object Select Menu", "Make a selection.")

    def object_delete_menu(self, timeline):
        self.sc_editor_delete_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_delete_menu.commands = []
        self.sc_editor_delete_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_delete_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_delete_menu.show(timeline, self, 0, self.sc_delete_menu_choices, "Delete Menu", "Make a selection.")

    def object_rotate_menu(self, timeline):
        self.sc_editor_rotate_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_rotate_menu.commands = []
        self.sc_editor_rotate_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_rotate_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_rotate_menu.show(timeline, self, 0, self.sc_rotate_menu_choices, "Object Rotate Menu", "Make a selection.")

    def object_scale_menu(self, timeline):
        self.sc_editor_scale_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_scale_menu.commands = []
        self.sc_editor_scale_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_scale_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_scale_menu.show(timeline, self, 0, self.sc_scale_menu_choices, "Object Scale Menu", "Make a selection.")

    def object_clone_menu(self, timeline):
        self.sc_editor_clone_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_clone_menu.commands = []
        self.sc_editor_clone_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_clone_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_clone_menu.show(timeline, self, 0, self.sc_clone_menu_choices, "Object Clone Menu", "Make a selection.")

    def object_replace_menu(self, timeline):
        self.sc_editor_replace_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_replace_menu.commands = []
        self.sc_editor_replace_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_replace_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_replace_menu.show(timeline, self, 0, self.sc_replace_menu_choices, "Object Replace Menu", "Make a selection.")

    def lights_menu(self, timeline):
        self.sc_editor_lights_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_lights_menu.commands = []
        self.sc_editor_lights_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_lights_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_lights_menu.show(timeline, self, 0, self.sc_lights_menu_choices, "Lights Menu", "Make a selection.")

    def misc_menu(self, timeline):
        self.sc_editor_misc_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_editor_misc_menu.commands = []
        self.sc_editor_misc_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_editor_misc_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_editor_misc_menu.show(timeline, self, 0, self.sc_misc_menu_choices, "Misc Menu", "Make a selection.")

    def weather_menu(self, timeline):
        self.sc_weather_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_weather_menu.commands = []
        self.sc_weather_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_weather_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_weather_menu.show(timeline, self, 0, self.sc_weather_choices, "Weather Menu", "Make a selection.")

    def modify_weather(self, timeline):
        self.sc_modify_weather_menu.MAX_MENU_ITEMS_TO_LIST = 10
        self.sc_modify_weather_menu.commands = []
        self.sc_modify_weather_menu.commands.append("<font color='#990000'>[Menu]</font>")
        self.sc_modify_weather_menu.commands.append("<font color='#990000'>[Reload Scripts]</font>")
        self.sc_modify_weather_menu.show(timeline, self, 0, self.sc_modify_weather_choices, "Weather Menu", "Make a selection.")

    def distance(self, timeline):
        distance_to_selected(self.target)

    def create_trauma(self, timeline):
        create_trauma(self.target)

    def find_doors(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        doors = [obj for obj in services.object_manager().get_all() if hasattr(obj, "get_disallowed_sims") and obj.has_component(PORTAL_COMPONENT)]
        if doors:
            doors.sort(key=lambda obj: distance_to_by_level(obj, sim))
            self.search_object_picker.show(doors, 0, self.target, 1, True)
        else:
            message_box(sim, None, "No objects!")

    def find_chairs(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        chairs = find_all_objects_by_title(sim, "sitliving|sitdining|sitsofa|sitlove|beddouble|bedsingle|chair|stool|hospitalexambed", outside=True)
        if chairs:
            chairs.sort(key=lambda obj: distance_to_by_level(obj, sim))
            self.search_object_picker.show(chairs, 0, self.target, 1, True)
        else:
            message_box(sim, None, "No objects!")

    def find_tvs(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        tvs = find_all_objects_by_title(sim, "television|object_tvsurface")
        if tvs:
            tvs.sort(key=lambda obj: distance_to_by_level(obj, sim))
            self.search_object_picker.show(tvs, 0, self.target, 1, True)
        else:
            message_box(sim, None, "No objects!")

    def find_routine_objects(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        if sc_Vars.routine_objects:
            sc_Vars.routine_objects.sort(key=lambda obj: distance_to_by_level(obj, sim))
            self.search_object_picker.show(sc_Vars.routine_objects, 0, self.target, 1, True)
        else:
            message_box(sim, None, "No objects!")

    def find_stereos(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        if sc_Vars.stereos_on_lot:
            sc_Vars.stereos_on_lot.sort(key=lambda obj: distance_to_by_level(obj, sim))
            self.search_object_picker.show(sc_Vars.stereos_on_lot, 0, self.target, 1, True)
        else:
            message_box(sim, None, "No objects!")

    def find_dirty_objects(self, timeline):
        if self.target.is_sim:
            sim = self.target
        else:
            client = services.client_manager().get_first_client()
            sim = client.active_sim
        if sc_Vars.dirty_objects:
            sc_Vars.dirty_objects.sort(key=lambda obj: distance_to_by_level(obj, sim))
            self.search_object_picker.show(sc_Vars.dirty_objects, 0, self.target, 1, True, None, object_is_dirty)
        else:
            message_box(sim, None, "No objects!")

    def make_clean(self, timeline):
        make_clean(self.target)

    def make_dirty(self, timeline):
        make_dirty(self.target)

    def is_dirty(self, timeline):
        if object_is_dirty(self.target):
            message_box(self.target, None, "Object Is Dirty")
            return
        message_box(self.target, None, "Object Is Not Dirty")

    def create_dust(self, timeline):
        create_dust(self.target)

    def zone_object_override(self, timeline):
        zone = services.current_zone()
        zone_object_override(zone)

    def save_zone_objects(self, timeline):
        zone = services.current_zone()
        zone_object_override_save_state(zone)

    def show_lights_in_room(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if not self.target.is_terrain:
            target = self.target

        lights = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                  if compare_room(obj, target)]
        for light in lights:
            light.fade_opacity(1, 0.0)

    def dim_lights_in_room(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if not self.target.is_terrain:
            target = self.target

        lights = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                  if compare_room(obj, target)]
        for light in lights:
            if hasattr(light, "set_user_intensity_override"):
                intensity = light.get_user_intensity_overrides()
                intensity = intensity - 0.1
                if intensity < 0.1:
                    intensity = 0.1
                color = light.get_light_color()
                light.set_user_intensity_override(float(intensity))
                light.set_light_color(color)

    def brighten_lights_in_room(self, timeline):
        client = services.client_manager().get_first_client()
        target = client.active_sim
        if not self.target.is_terrain:
            target = self.target

        lights = [obj for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT)
                  if compare_room(obj, target)]
        for light in lights:
            if hasattr(light, "set_user_intensity_override"):
                intensity = light.get_user_intensity_overrides()
                intensity = intensity + 0.1
                if intensity > 1.0:
                    intensity = 1.0
                color = light.get_light_color()
                light.set_user_intensity_override(float(intensity))
                light.set_light_color(color)

    def copy_light_color(self, timeline):
        if hasattr(self.target, "set_light_color"):
            ModuleEditorMenu.light_color = self.target.get_light_color()
            ModuleEditorMenu.light_intensity = self.target.get_user_intensity_overrides()
        else:
            message_box(None, None, "Copy Light Color", "Object is not a light!", "ORANGE")

    def paste_light_color(self, timeline):
        if hasattr(self.target, "set_light_color") and ModuleEditorMenu.light_color:
            self.target.set_user_intensity_override(ModuleEditorMenu.light_intensity)
            self.target.set_light_color(ModuleEditorMenu.light_color)
        else:
            message_box(None, None, "Paste Light Color", "Object is not a light!", "ORANGE")

    def paste_light_color_by_room(self, timeline):
        try:
            room = build_buy.get_room_id(self.target.zone_id, self.target.position, self.target.level)
        except:
            room = -1
            pass
        for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT):
            try:
                obj_room = build_buy.get_room_id(obj.zone_id, obj.position, obj.level)
            except:
                obj_room = -1
                pass
            if obj_room == room and room != -1 and obj_room != -1:
                if hasattr(obj, "set_light_color") and ModuleEditorMenu.light_color:
                    obj.set_user_intensity_override(ModuleEditorMenu.light_intensity)
                    obj.set_light_color(ModuleEditorMenu.light_color)

    def paste_light_color_by_type(self, timeline):
        for obj in services.object_manager().get_all_objects_with_component_gen(LIGHTING_COMPONENT):
            if hasattr(obj, "set_light_color") and ModuleEditorMenu.light_color and obj.definition.id == self.target.definition.id:
                obj.set_user_intensity_override(ModuleEditorMenu.light_intensity)
                obj.set_light_color(ModuleEditorMenu.light_color)

    def focus_camera(self, timeline):
        inputbox("Focus Camera At Location", "Use format [x],[y],[z]",
                         self.focus_camera_callback)

    def focus_camera_callback(self, location: str):
        location = location.replace(":", ",")
        pos = location.split(",")
        pos = Vector3(float(pos[0]), float(pos[1]), float(pos[2]))
        focus_camera_on_position(pos)

    def place_objects(self, timeline):
        position = self.target.position
        place_selected_objects(position.x, position.y, position.z)

    def place_objects_at(self, timeline):
        inputbox("Place Object At Location", "Use format [x],[y],[z]",
                         self.place_objects_at_callback)

    def place_objects_at_callback(self, location: str):
        location = location.replace(":",",")
        pos = location.split(",")
        place_selected_objects(float(pos[0]), float(pos[1]), float(pos[2]))

    def ground_objects(self, timeline):
        if self.target and not self.target.is_sim and self.target.definition.id != 816:
            ground_selected_objects(self.target)
            return
        ground_selected_objects()

    def center_objects(self, timeline):
        if self.target and not self.target.is_sim and self.target.definition.id != 816:
            center_selected_objects(self.target)
            return
        center_selected_objects()

    def color_objects(self, timeline):
        color_selected_object(self.target)

    def fade_objects(self, timeline):
        fade_selected_object(self.target)

    def load_object_material(self, timeline):
        load_material(self.target)

    def save_object_material(self, timeline):
        save_material(self.target)

    def transmog_from_selected_object(self, timeline):
        transmog_from_selected_object(self.target)

    def object_to_original(self, timeline):
        object_to_original(self.target)

    def model_from_selected_object(self, timeline):
        model_from_selected_object(self.target)

    def get_info(self, timeline):
        try:
            output = ""
            font_color = "000000"
            font_text = "<font color='#{}'>".format(font_color)
            end_font_text = "</font>"
            result = self.target
            for att in dir(result):
                if hasattr(result, att):
                    output = output + "\n(" + str(att) + "): " + clean_string(str(getattr(result, att)))

            if self.target.is_terrain:
                info_string = get_object_info(get_selected_object())
            elif self.target.is_sim:
                info_string = get_sim_info(self.target)
                message_text = info_string
            else:
                info_string = get_object_info(self.target)
            message_text = info_string.replace("[", font_text).replace("]", end_font_text)

            urgency = UiDialogNotification.UiDialogNotificationUrgency.DEFAULT
            information_level = UiDialogNotification.UiDialogNotificationLevel.PLAYER
            visual_type = UiDialogNotification.UiDialogNotificationVisualType.INFORMATION
            localized_text = lambda **_: LocalizationHelperTuning.get_raw_text(message_text)
            localized_title = lambda **_: LocalizationHelperTuning.get_object_name(self.target)
            notification = UiDialogNotification.TunableFactory().default(None,
                                                                         text=localized_text,
                                                                         title=localized_title,
                                                                         icon=None,
                                                                         secondary_icon=None,
                                                                         urgency=urgency,
                                                                         information_level=information_level,
                                                                         visual_type=visual_type,
                                                                         expand_behavior=1)
            notification.show_dialog()

            datapath = sc_Vars.config_data_location
            filename = datapath + r"\{}.log".format("object_info")
            if os.path.exists(filename):
                append_write = 'w'  # append if already exists
            else:
                append_write = 'w'  # make a new file if not
            file = open(filename, append_write)
            file.write("{}\n{}\n\nINFO:\n{}".format(self.target.__class__.__name__, info_string, output))
            file.close()

        except BaseException as e:
            error_trap(e)

    def move_selected_objects(self, timeline):
        inputbox("Move Selected Objects", "[x, z]", self.move_selected_objects_callback)

    def move_selected_objects_callback(self, move_string):
        try:
            value = move_string.split(",")
            move_selected_objects(float(value[0]), float(value[1]))
        except BaseException as e:
            error_trap(e)

    def replace_similar_objects(self, timeline):
        try:
            objects = services.object_manager().get_all()
            for obj in list(objects):
                if obj.definition.id == self.target.definition.id and not self.target.is_sim and self.target.definition.id != 816:
                    obj.reset(ResetReason.NONE, None, 'Command')
                    replace_selected_object(obj)

        except BaseException as e:
            error_trap(e)

    def replace_selected_object(self, timeline):
        if not self.target.is_sim and self.target.definition.id != 816:
            self.target.reset(ResetReason.NONE, None, 'Command')
            replace_selected_object(self.target)

    def paint_selected_object(self, info=None):
        amount = 10
        area = 5.0
        height = 0.25
        if isinstance(info, str):
            values = info.split(",")
            amount = int(values[0])
            area = float(values[1])
            height = float(values[2])
        paint_selected_object(self.target, amount, area, height)

    def paint_selected_object_input(self, timeline):
        inputbox("Paint Selected Object", "[amount, area, height]", self.paint_selected_object)

    def point_object(self, timeline):
        point_object_at(self.target)

    def rotate_this_object(self, timeline):
        if hasattr(self.target, "definition"):
            random_orientation(self.target)

    def rotate_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for obj in similar_objects:
                random_orientation(obj)

    def rotate_selected_objects(self, timeline):
        rotate_selected_objects()

    def select_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for i, obj in enumerate(similar_objects):
                if i == 0:
                    select_object(obj, True)
                else:
                    select_object(obj, False)

    def select_all(self, timeline):
        select_all()

    def select_objects_by_room(self, timeline):
        select_objects_by_room(self.target)

    def save_selected_objects(self, timeline):
        inputbox("Save Selected Objects", "Enter a filename", self.save_selected_objects_callback)

    def save_selected_objects_callback(self, filename):
        datapath = sc_Vars.config_data_location
        file = "{}.dat".format(filename)
        world_file = datapath + r"\Data\Rooms\{}".format(file)
        message_box(None, None, "File Saved", "{}".format(world_file.replace('\\', '/')))
        write_objects_to_file(world_file, 0.0, True, True)

    def load_objects(self, timeline):
        datapath = sc_Vars.config_data_location + r"\Data\Rooms"
        files = [f for f in os.listdir(datapath) if isfile(join(datapath, f))]
        if files:
            self.explorer.show(timeline, self, 0, files, "Load Objects", "Make a selection.", "load_objects_callback", True)

    def load_objects_callback(self, filename):
        datapath = sc_Vars.config_data_location
        file = "{}.dat".format(filename)
        world_file = datapath + r"\Data\Rooms\{}".format(file)
        with open(world_file, "r") as f:
            for line in f.readlines():
                read_file_line(line)

    def delete_selected_objects(self, timeline):
        delete_selected_objects()

    def delete_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for obj in similar_objects:
                obj.destroy()

    def reset_scale(self, timeline):
        if self.target.definition.id == 816:
            reset_scale_selected()
        else:
            if hasattr(self.target, "definition"):
                similar_objects = get_similar_objects(self.target.definition.id)
                for obj in similar_objects:
                    reset_scale(obj)

    def scale_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            scale = self.target.scale
            for obj in similar_objects:
                random_scale(obj, scale)

    def less_scale_similar_objects(self, timeline):
        if hasattr(self.target, "definition"):
            similar_objects = get_similar_objects(self.target.definition.id)
            for obj in similar_objects:
                random_scale(obj, 1.0, 0.25)

    def scale_selected_objects(self, timeline):
        scale_selected_objects()

    def select_objects(self, timeline):
        if self.target.definition.id != 816:
            search = str(self.target.__class__.__name__)
            ModuleEditorMenu.initial_value = search
        inputbox("Select Object On Lot", "Searches for object on active lot/zone. "
                          "Full or partial search term. Separate multiple search "
                          "terms with a comma. Will search in "
                          "tuning files and tags.",
                         self._select_objects_callback, ModuleEditorMenu.initial_value)

    def _select_objects_callback(self, search: str):
        try:
            ModuleEditorMenu.initial_value = search
            if search == "":
                return
            object_list = [obj for obj in services.object_manager().get_all() if search.lower() in str(obj).lower() or
                           search in str(obj.definition.id) or search in str(obj.id) or search.lower() in
                           str(get_tags_from_id(obj.definition.id)).lower()]
            object_list.sort(key=lambda obj: distance_to_by_level(obj, self.target))

            if len(object_list) > 0:
                message_box(None, None, "Select Object", "{} object(s) found!".format(len(object_list)), "GREEN")
                self.search_object_picker.show(object_list, 0, self.target, 1, False, select_object)
            else:
                message_box(None, None, "Select Object", "No objects found!", "GREEN")
        except BaseException as e:
            error_trap(e)

    def find_objects(self, timeline):
        if self.target.definition.id != 816:
            search = str(self.target.__class__.__name__)
            ModuleEditorMenu.initial_value = search
        inputbox("Find Object On Lot", "Searches for object on active lot/zone. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags.",
                         self._find_objects_callback, ModuleEditorMenu.initial_value)

    def _find_objects_callback(self, search: str):
        try:
            ModuleEditorMenu.initial_value = search
            if search == "":
                return
            object_list = [obj for obj in services.object_manager().get_all() if search.lower() in str(obj).lower() or
                           search in str(obj.definition.id) or search in str(obj.id) or search.lower() in
                           str(get_tags_from_id(obj.definition.id)).lower()]
            object_list.sort(key=lambda obj: distance_to_by_level(obj, self.target))

            if len(object_list) > 0:
                message_box(None, None, "Find Object", "{} object(s) found!".format(len(object_list)), "GREEN")
                self.search_object_picker.show(object_list, 0, self.target, 1, True)
            else:
                message_box(None, None, "Find Object", "No objects found!", "GREEN")
        except BaseException as e:
            error_trap(e)

    def search_objects(self, timeline):
        if self.target.definition.id != 816:
            search = str(self.target.__class__.__name__)
            ModuleEditorMenu.initial_value = search
        inputbox("Search For Object & Place", "Searches ALL game objects. Will take some time. "
                                                      "Full or partial search term. Separate multiple search "
                                                      "terms with a comma. Will search in "
                                                      "tuning files and tags. Only 512 items per search "
                                                      "will be shown.",
                         self._search_objects_callback, ModuleEditorMenu.initial_value)

    def _search_objects_callback(self, search: str):
        try:
            ModuleEditorMenu.initial_value = search
            object_list = []
            if search == "":
                return
            for key in sorted(sims4.resources.list(type=(sims4.resources.Types.OBJECTDEFINITION)), reverse=True):
                object_tuning = services.definition_manager().get(key.instance)
                if object_tuning is not None:
                    object_class = str(object_tuning.cls)
                    if search.lower() in object_class.lower() or search in str(key.instance) or search.lower() in str(get_tags_from_id(key.instance)).lower():
                        obj = objects.system.create_script_object(key.instance)
                        object_list.append(obj)

            if len(object_list) > 0:
                message_box(None, None, "Search Objects", "{} object(s) found!".format(len(object_list)), "GREEN")
                self.search_object_picker.show(object_list, 0, self.target, 1)
            else:
                message_box(None, None, "Search Objects", "No objects found!", "GREEN")
        except BaseException as e:
            error_trap(e)

    def custom_function(self, option, duration=1.0, instant=False):
        if sc_Vars.weather_function:
            sc_Vars.weather_function.weather_function(option, duration, instant)

    def set_weather(self, weather, instant=False):
        weather_service = services.weather_service()
        trans_info = {}
        now = services.time_service().sim_now
        current_temp = Temperature(int(weather.TEMPERATURE))
        end_time = now + create_time_span(hours=weather.duration)
        trans_info[int(WeatherEffectType.WIND)] = WeatherElementTuple(weather.WIND, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.WATER_FROZEN)] = WeatherElementTuple(weather.WATER_FROZEN, now, weather.WATER_FROZEN, end_time)
        trans_info[int(WeatherEffectType.WINDOW_FROST)] = WeatherElementTuple(weather.WINDOW_FROST, now, weather.WINDOW_FROST, end_time)
        trans_info[int(WeatherEffectType.THUNDER)] = WeatherElementTuple(weather.THUNDER, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.LIGHTNING)] = WeatherElementTuple(weather.LIGHTNING, now, 0.0, end_time)
        trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(weather.SNOW, now, 0.0, end_time)
        trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(weather.RAIN, now, 0.0, end_time)
        trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(weather.LIGHT_SNOWCLOUDS, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(weather.DARK_SNOWCLOUDS, now, 0.0, end_time)
        trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(weather.LIGHT_RAINCLOUDS, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(weather.DARK_RAINCLOUDS, now, 0.0, end_time)
        trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(weather.CLOUDY, now, 0.0, end_time)
        trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(weather.HEATWAVE, now, 0.0, end_time)
        trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(weather.PARTLY_CLOUDY, now, 0.0, end_time)
        trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(weather.CLEAR, now, 0.0, end_time)
        trans_info[int(GroundCoverType.SNOW_ACCUMULATION)] = WeatherElementTuple(weather.SNOW_ACCUMULATION, now, weather.SNOW_ACCUMULATION, end_time)
        trans_info[int(GroundCoverType.RAIN_ACCUMULATION)] = WeatherElementTuple(weather.RAIN_ACCUMULATION, now, weather.RAIN_ACCUMULATION, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
        trans_info[int(CloudType.SKYBOX_INDUSTRIAL)] = WeatherElementTuple(weather.SKYBOX_INDUSTRIAL, now, weather.SKYBOX_INDUSTRIAL, end_time)
        trans_info[int(WeatherEffectType.SNOW_ICINESS)] = WeatherElementTuple(weather.SNOW_ICINESS, now, weather.SNOW_ICINESS, end_time)
        trans_info[int(WeatherEffectType.SNOW_FRESHNESS)] = WeatherElementTuple(weather.SNOW_FRESHNESS, now, weather.SNOW_FRESHNESS, end_time)
        if not instant:
            sc_Vars.update_trans_info = trans_info
            sc_Vars.update_trans_duration = weather.duration
        else:
            weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
            weather_service.start_weather_event(weather_event_manager.get(186636), weather.duration)
            weather_service._trans_info = trans_info
            weather_service._send_weather_event_op()

    def build_weather(self, section, duration):
        try:
            datapath = sc_Vars.config_data_location
            filename = datapath + r"\Data\weather.ini"
            if not os.path.exists(filename):
                return
            config = configparser.ConfigParser()
            config.read(filename)
            if not config.has_section(section):
                config.add_section(section)

            config.set(section, "duration", str(duration))
            config.set(section, "WIND", "0.0")
            config.set(section, "WINDOW_FROST", "0.0")
            config.set(section, "WATER_FROZEN", "0.0")
            config.set(section, "THUNDER", "0.0")
            config.set(section, "LIGHTNING", "0.0")
            config.set(section, "TEMPERATURE", "0.0")
            config.set(section, "SNOW", "0.0")
            config.set(section, "SNOW_ACCUMULATION", "0.0")
            config.set(section, "RAIN", "0.0")
            config.set(section, "RAIN_ACCUMULATION", "0.0")
            config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
            config.set(section, "DARK_SNOWCLOUDS", "0.0")
            config.set(section, "LIGHT_RAINCLOUDS", "0.0")
            config.set(section, "DARK_RAINCLOUDS", "0.0")
            config.set(section, "CLOUDY", "0.0")
            config.set(section, "HEATWAVE", "0.0")
            config.set(section, "PARTLY_CLOUDY", "0.0")
            config.set(section, "CLEAR", "0.0")
            config.set(section, "SKYBOX_INDUSTRIAL", "0.0")
            config.set(section, "SNOW_ICINESS", "0.0")
            config.set(section, "SNOW_FRESHNESS", "0.0")

            if "awind" in section or "ahotwind" in section:
                config.set(section, "WIND", "0.5")
            elif "windstorm" in section:
                config.set(section, "WIND", "1.0")
            if "freezing" in section:
                config.set(section, "WINDOW_FROST", "1.0")
                config.set(section, "WATER_FROZEN", "1.0")
                config.set(section, "TEMPERATURE", "-3")
                config.set(section, "SNOW_ICINESS", "0.0")
                config.set(section, "SNOW_FRESHNESS", "0.0")
            elif "cold" in section:
                config.set(section, "TEMPERATURE", "-2")
            elif "cool" in section:
                config.set(section, "TEMPERATURE", "-1")
            elif "warm" in section:
                config.set(section, "TEMPERATURE", "0")
            elif "hot" in section:
                config.set(section, "TEMPERATURE", "1")
            elif "heatwave" in section:
                config.set(section, "TEMPERATURE", "2")
                config.set(section, "HEATWAVE", "1.0")
            if "thunder" in section:
                config.set(section, "WIND", "0.5")
                config.set(section, "THUNDER", "1.0")
                config.set(section, "LIGHTNING", "1.0")
            if "heavy_snow" in section or "snowstorm" in section:
                config.set(section, "SNOW", "1.0")
                config.set(section, "SNOW_ACCUMULATION", "1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "light_snow" in section:
                config.set(section, "SNOW", "0.25")
                config.set(section, "SNOW_ACCUMULATION", "0.25")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "blizzard" in section:
                config.set(section, "WIND", "1.0")
                config.set(section, "SNOW", "1.0")
                config.set(section, "SNOW_ACCUMULATION", "1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "snow" in section:
                config.set(section, "SNOW", "0.5")
                config.set(section, "SNOW_ACCUMULATION", "0.5")
                config.set(section, "LIGHT_SNOWCLOUDS", "1.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
            elif "heavy_rain" in section or "thunderstorm" in section:
                config.set(section, "RAIN", "1.0")
                config.set(section, "RAIN_ACCUMULATION", "1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "light_rain" in section:
                config.set(section, "RAIN", "0.25")
                config.set(section, "RAIN_ACCUMULATION", "0.25")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "drizzle" in section:
                config.set(section, "RAIN", "0.1")
                config.set(section, "RAIN_ACCUMULATION", "0.1")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "showers" in section or "monsoon" in section:
                config.set(section, "WIND", "0.5")
                config.set(section, "RAIN", "1.0")
                config.set(section, "RAIN_ACCUMULATION", "1.0")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            elif "rain" in section:
                config.set(section, "RAIN", "0.5")
                config.set(section, "RAIN_ACCUMULATION", "0.5")
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "1.0")
                config.set(section, "DARK_RAINCLOUDS", "1.0")
            if "sunny" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.0")
                config.set(section, "PARTLY_CLOUDY", "0.0")
                config.set(section, "CLEAR", "1.0")
            elif "fog" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "1.01")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.1")
                config.set(section, "PARTLY_CLOUDY", "0.0")
                config.set(section, "CLEAR", "0.0")
            elif "june_gloom" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.5")
                config.set(section, "LIGHT_RAINCLOUDS", "0.5")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.0")
                config.set(section, "PARTLY_CLOUDY", "0.0")
                config.set(section, "CLEAR", "0.0")
            elif "partly" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.0")
                config.set(section, "DARK_SNOWCLOUDS", "0.0")
                config.set(section, "LIGHT_RAINCLOUDS", "0.0")
                config.set(section, "DARK_RAINCLOUDS", "0.0")
                config.set(section, "CLOUDY", "0.0")
                config.set(section, "PARTLY_CLOUDY", "1.0")
                config.set(section, "CLEAR", "0.0")
            elif "cloudy" in section:
                config.set(section, "LIGHT_SNOWCLOUDS", "0.5")
                config.set(section, "DARK_SNOWCLOUDS", "0.5")
                config.set(section, "LIGHT_RAINCLOUDS", "0.5")
                config.set(section, "DARK_RAINCLOUDS", "0.5")
            if "city" in section:
                config.set(section, "SKYBOX_INDUSTRIAL", "0.25")
                config.set(section, "SNOW_ICINESS", "0.0")
                config.set(section, "SNOW_FRESHNESS", "0.25")

            with open(filename, 'w') as configfile:
                config.write(configfile)

        except BaseException as e:
            error_trap(e)

    def add_weather(self, section, duration):
        if sc_Vars.weather_function:
            sc_Vars.weather_function.add_weather(section, duration)

    def weather_ini(self):
        try:
            self.sc_weather_choices = ()
            self.sc_weather_choices = self.sc_weather_choices + ("Reset Weather",)
            self.sc_weather_choices = self.sc_weather_choices + ("Modify Weather",)
            self.sc_weather_choices = self.sc_weather_choices + ("Save Weather",)
            self.sc_weather_choices = self.sc_weather_choices + ("Get Forecast",)
            self.sc_weather_choices = self.sc_weather_choices + ("Get Weather",)
            self.sc_weather_choices = self.sc_weather_choices + ("Load Zone Weather",)
            self.sc_weather = []
            datapath = sc_Vars.config_data_location
            filename = datapath + r"\Data\weather.ini"
            if not os.path.exists(filename):
                return
            config = configparser.ConfigParser()
            config.read(filename)

            for each_section in config.sections():
                duration = config.getfloat(each_section, "duration")
                wind = config.getfloat(each_section, "WIND")
                window_frost = config.getfloat(each_section, "WINDOW_FROST")
                water_frozen = config.getfloat(each_section, "WATER_FROZEN")
                thunder = config.getfloat(each_section, "THUNDER")
                lightning = config.getfloat(each_section, "LIGHTNING")
                temperature = config.getfloat(each_section, "TEMPERATURE")
                snow = config.getfloat(each_section, "SNOW")
                snow_accumulation = config.getfloat(each_section, "SNOW_ACCUMULATION")
                rain = config.getfloat(each_section, "RAIN")
                rain_accumulation = config.getfloat(each_section, "RAIN_ACCUMULATION")
                light_snowclouds = config.getfloat(each_section, "LIGHT_SNOWCLOUDS")
                dark_snowclouds = config.getfloat(each_section, "DARK_SNOWCLOUDS")
                light_rainclouds = config.getfloat(each_section, "LIGHT_RAINCLOUDS")
                dark_rainclouds = config.getfloat(each_section, "DARK_RAINCLOUDS")
                cloudy = config.getfloat(each_section, "CLOUDY")
                heatwave = config.getfloat(each_section, "HEATWAVE")
                partly_cloudy = config.getfloat(each_section, "PARTLY_CLOUDY")
                clear = config.getfloat(each_section, "CLEAR")
                skybox_industrial = config.getfloat(each_section, "SKYBOX_INDUSTRIAL")
                snow_iciness = config.getfloat(each_section, "SNOW_ICINESS")
                snow_freshness = config.getfloat(each_section, "SNOW_FRESHNESS")

                self.sc_weather_choices = self.sc_weather_choices + (each_section,)
                self.sc_weather.append(sc_Weather(each_section,
                                                duration,
                                                wind,
                                                window_frost,
                                                water_frozen,
                                                thunder,
                                                lightning,
                                                temperature,
                                                snow,
                                                snow_accumulation,
                                                rain,
                                                rain_accumulation,
                                                light_snowclouds,
                                                dark_snowclouds,
                                                light_rainclouds,
                                                dark_rainclouds,
                                                cloudy,
                                                heatwave,
                                                partly_cloudy,
                                                clear,
                                                skybox_industrial,
                                                snow_iciness,
                                                snow_freshness))
        except BaseException as e:
            error_trap(e)

    def get_forecast(self, timeline):
        if sc_Vars.weather_function:
            street_or_region_id = get_street_or_region_id_with_weather_tuning()
            forecast = services.weather_service()._weather_info[street_or_region_id]._forecasts[0]
            forecast_name = "weather_" + str(forecast.__name__).lower().replace("forecast_","")
            sc_Vars.weather_function.weather_function(forecast_name, 120.0)

    def get_weather(self, timeline):
        if sc_Vars.weather_function:
            sc_Vars.weather_function.get_weather()

    def reset_weather(self, timeline):
        services.weather_service().reset_forecasts(False)
        self.get_forecast(timeline)

    def load_zone_weather(self, timeline):
        if sc_Vars.weather_function:
            sc_Vars.weather_function.load_weather()

    def save_weather(self, timeline):
        inputbox("Save Weather", "Saves current state of weather to weather.ini. Type in weather name to save.",
                 self.save_weather_callback)

    def save_weather_callback(self, filename):
        if sc_Vars.weather_function:
            sc_Vars.weather_function.add_weather(filename, 1.0)

    def set_variable(self, timeline):
        inputbox("Set Variable Weather", "Type in weather identifier and value separated by a comma.",
                 self.set_variable_callback, ModuleEditorMenu.initial_value)

    def set_variable_callback(self, variable):
        if not sc_Vars.weather_function:
            return
        ModuleEditorMenu.initial_value = variable
        if "weather" not in variable.lower():
            value = variable.lower().split(",")
            duration = 120
            now = services.time_service().sim_now
            if len(value) > 2:
                duration = float(value[2])
            end_time = now + create_time_span(hours=duration)
            weather_service = services.weather_service()
            trans_info = weather_service._trans_info
            current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
            weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
            weather_service.start_weather_event(weather_event_manager.get(186636), duration)

            if isinstance(value[0], str):
                trans_type = [info for info in WeatherEffectType if value[0] in str(info.name).lower()]
                trans_type = trans_type + [info for info in CloudType if value[0] in str(info.name).lower()]
                trans_type = trans_type + [info for info in PrecipitationType if value[0] in str(info.name).lower()]
                trans_type = trans_type + [info for info in GroundCoverType if value[0] in str(info.name).lower()]
                for info in trans_type:
                    if "TEMPERATURE" in str(info.name):
                        current_temp = Temperature(int(value[1]))
                    else:
                        trans_info[int(info)] = WeatherElementTuple(float(value[1]), now, float(value[1]), end_time)

            trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
            weather_service._trans_info = trans_info
            weather_service._send_weather_event_op()
        else:
            if "," in variable:
                value = variable.lower().split(",")
                sc_Vars.weather_function.weather_function(value[0], float(value[1]), True)
            else:
                sc_Vars.weather_function.weather_function(variable, 120.0, True)

    def set_to_sunny(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(1.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def set_to_cloudy(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(1.0, now, 0.0, end_time)
        trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def set_to_partly_cloudy(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(1.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def set_to_foggy(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(CloudType.LIGHT_SNOWCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_SNOWCLOUDS)] = WeatherElementTuple(1.01, now, 0.0, end_time)
        trans_info[int(CloudType.LIGHT_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.DARK_RAINCLOUDS)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLOUDY)] = WeatherElementTuple(0.1, now, 0.0, end_time)
        trans_info[int(CloudType.HEATWAVE)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.PARTLY_CLOUDY)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(CloudType.CLEAR)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def set_to_no_moisture(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now,
                                                                                              current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def set_to_rain(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(1.0, now, 0.0, end_time)
        trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now,
                                                                                              current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def set_to_snow(self, timeline):
        now = services.time_service().sim_now
        weather_service = services.weather_service()
        weather_event_manager = services.get_instance_manager(Types.WEATHER_EVENT)
        current_temp = Temperature(weather_service.get_weather_element_value((WeatherEffectType.TEMPERATURE), default=(Temperature.WARM)))
        end_time = now + create_time_span(hours=1)
        trans_info = {}
        trans_info[int(PrecipitationType.RAIN)] = WeatherElementTuple(0.0, now, 0.0, end_time)
        trans_info[int(PrecipitationType.SNOW)] = WeatherElementTuple(1.0, now, 0.0, end_time)
        trans_info[int(WeatherEffectType.TEMPERATURE)] = WeatherElementTuple(current_temp, now, current_temp, end_time)
        sc_Vars.update_trans_info = trans_info
        sc_Vars.update_trans_duration = 1.0

    def _reload_scripts(self, timeline):
        inputbox("Reload Script", "Type in directory to browse or leave blank to list all in current directory", self._reload_script_callback)

    def _reload_script_callback(self, script_dir: str):
        try:
            if script_dir == "" or script_dir is None:
                ModuleEditorMenu.directory = os.path.abspath(os.path.dirname(__file__))
                files = [f for f in os.listdir(ModuleEditorMenu.directory) if isfile(join(ModuleEditorMenu.directory, f))]
            else:
                ModuleEditorMenu.directory = script_dir
                files = [f for f in os.listdir(script_dir) if isfile(join(script_dir, f))]
            files.insert(0, "all")
            self.script_choice.show(None, self, 0, files, "Reload Script",
                                       "Choose a script to reload", "_reload_script_final", True)
        except BaseException as e:
            error_trap(e)

    def _reload_script_final(self, filename: str):
        try:
            if ModuleEditorMenu.directory is None:
                ModuleEditorMenu.directory = os.path.abspath(os.path.dirname(__file__))
            ld_file_loader(ModuleEditorMenu.directory, filename)
        except BaseException as e:
            error_trap(e)
