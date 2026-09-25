"""Unit checks for freely chosen views and fixed-input separation."""
import unittest
from render_spec import validate_request, camera_at


class RenderSettingsTests(unittest.TestCase):
    def test_custom_camera_and_input_unchanged(self):
        fixed = {"steps": 180, "dt_seconds": 1/60, "camera": "overview"}
        request = validate_request({"camera": {"position": [2, 3, 4], "look_at": [0, 0, 0]}, "frames": [1, 150]}, fixed)
        self.assertEqual(request["camera"]["position"], [2, 3, 4])
        self.assertEqual(request["frames"], [1, 150])
        self.assertEqual(fixed["camera"], "overview")

    def test_top_orthogonal_camera(self):
        request = validate_request({"camera": {"position": [0, 8, 0], "look_at": [0, 0, 0],
            "up": [0, 0, -1], "projection": "orthogonal", "orthogonal_size": 5}}, {})
        self.assertEqual(request["camera"]["projection"], "orthogonal")

    def test_track_interpolation(self):
        request = validate_request({"frames": [1, 11], "camera": {"position": [0, 3, 4], "look_at": [0, 0, 0]},
            "camera_track": [{"frame": 1, "position": [0, 3, 4], "look_at": [0, 0, 0]},
                             {"frame": 11, "position": [4, 3, 0], "look_at": [0, 0, 0]}]}, {})
        self.assertEqual(camera_at(request["camera"], request["camera_track"], 6)["position"], [2, 3, 2])

    def test_invalid_requests(self):
        for arguments in ({"scene": "../outside.tscn"}, {"scene": "D:/outside.tscn"},
                          {"frames": [2, 1]}, {"frames": [1, 1]}, {"frames": [241]},
                          {"resolution": [10000, 10000]}, {"shader_code": "bad"},
                          {"camera": {"position": [0, 0, 0], "look_at": [0, 0, 0]}},
                          {"camera": {"position": [0, 8, 0], "look_at": [0, 0, 0]}},
                          {"camera": {"position": [1, 2, 3], "look_at": [0, 0, 0], "fov_degrees": float("nan")}},
                          {"camera_track": [{"frame": 1, "position": [1, 2, 3], "look_at": [0, 0, 0]}]}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                validate_request(arguments, {"steps": 240})

    def test_degenerate_intermediate_camera_rejected(self):
        with self.assertRaises(ValueError):
            validate_request({"frames": [1, 3], "camera": {"position": [-2, 0, 0], "look_at": [0, 0, 0]},
                "camera_track": [{"frame": 1, "position": [-2, 0, 0], "look_at": [0, 0, 0]},
                                 {"frame": 3, "position": [2, 0, 0], "look_at": [0, 0, 0]}]}, {})


if __name__ == "__main__":
    unittest.main()
