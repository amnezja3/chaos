import copy
import unittest
from unittest.mock import patch

from camera_visual_instance import bind_material, instance, SCENARIOS


class CameraInstanceTest(unittest.TestCase):
    def state(self):
        state = dict(instance_id='viewer-a', operation_id='op-a', target_key='camera-a',
                     motion=dict(version=2, start=[10, 20], end=[80, 90]))
        state['feed'] = instance(state, 'alice')
        return state

    def test_material_draw_uses_actual_set_and_never_redraws(self):
        for count in (1, 2, 3, 8):
            state = self.state()
            materials = [dict(image_id=str(i)) for i in range(count)]
            with patch('camera_visual_instance.secrets.choice', return_value=materials[-1]) as draw:
                self.assertTrue(bind_material(state, materials))
                draw.assert_called_once_with(materials)
                before = copy.deepcopy(state)
                self.assertFalse(bind_material(state, materials))
                self.assertEqual(state, before)
            self.assertEqual(state['feed']['image_id'], str(count-1))

    def test_empty_set_waits_without_drawing_and_legacy_is_stable(self):
        state = self.state()
        with patch('camera_visual_instance.secrets.choice', side_effect=AssertionError('redraw')):
            self.assertFalse(bind_material(state, []))
            legacy = instance(state, 'alice', legacy=True)
        self.assertEqual(legacy['visual']['scenario'], 'legacy')
        self.assertEqual(legacy['activation_id'], 'activation-op-a')

    def test_all_visual_profiles_are_bounded_and_bound_to_grant(self):
        for scenario in SCENARIOS:
            with patch('camera_visual_instance.secrets.choice', return_value=scenario):
                state = self.state()
            profile = state['feed']
            self.assertEqual(profile['username'], 'alice')
            self.assertEqual(profile['camera_key'], 'camera-a')
            self.assertEqual(profile['visual']['scenario'], scenario)
            self.assertTrue(.65 <= profile['visual']['intensity'] <= 1)
            self.assertTrue(45 <= profile['visual']['period'] <= 90)
            self.assertEqual(profile['motion'], state['motion'])
