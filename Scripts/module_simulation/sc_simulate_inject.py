from event_testing.results import TestResult
from interactions.base.super_interaction import SuperInteraction
from interactions.interaction_queue import BucketBase
from zone import Zone

from module_simulation.sc_simulate_autonomy import sc_simulate_update
from module_simulation.sc_simulate_filter import sc_filter_autonomy_actions, sc_filter_queue_actions
from scripts_core.sc_inject import safe_inject
from scripts_core.sc_script_vars import sc_Vars


@safe_inject(BucketBase, 'append')
def sc_append_super_interaction(original, self, interaction, *args, **kwargs):
    result = TestResult.NONE
    if sc_filter_autonomy_actions(self, interaction):
        result = original(self, interaction, *args, **kwargs)
    return result


@safe_inject(BucketBase, 'insert_next')
def sc_insert_next_super_interaction(original, self, interaction, **kwargs):
    result = TestResult.NONE
    if sc_filter_autonomy_actions(self, interaction):
        result = original(self, interaction, **kwargs)
    return result

@safe_inject(SuperInteraction, 'on_added_to_queue')
def sc_on_added_to_queue_inject(original, self, *args, **kwargs):
    sc_filter_queue_actions(self)
    result = original(self, *args, **kwargs)
    return result

@safe_inject(Zone, 'update')
def sc_simulate_zone_update_module(original, self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    sc_simulate_update(self)
    return result