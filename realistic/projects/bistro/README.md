# Bistro-Demo-Tweaked

Bistro demo project for [Godot](https://github.com/godotengine/godot) showcasing lighting and high quality assets.

![Bistro-Demo-Tweaked](https://github.com/user-attachments/assets/8b624fae-4969-4d5e-949c-75d30eed53c6)

Includes [Godot-Human-For-Scale](https://github.com/Jamsers/Godot-Human-For-Scale) to run around the level, and an interface for changing the time of day, resolution scaling, and quality scaling. Appropriate objects in the level are set to dynamic and are physics enabled, to see the effects of lighting on dynamic objects as well.

## Usage

1. Clone or download this repository.
1. Download [Godot 4.4](https://godotengine.org/releases/4.4/) and open the repository folder with Godot.
1. To run the project, click the Run Project button, found on the upper right corner of Godot's interface.

[![Godot 4.4](https://img.shields.io/badge/Godot-4.4-478cbf?style=for-the-badge&logo=godot-engine&logoColor=white)](https://godotengine.org/releases/4.4/)

> [!NOTE]  
> When opening the project for the first time, you may notice hundreds of modified `*.res` files in your source control. This is a quirk of the Godot importer and these changes can be safely discarded once project has already been opened once.

## Releases

You can download builds for Windows, Mac, and Linux from the releases page.

[![Bistro-Demo-Tweaked GitHub release](https://img.shields.io/github/v/release/Jamsers/Bistro-Demo-Tweaked?style=for-the-badge)](https://github.com/Jamsers/Bistro-Demo-Tweaked/releases/latest)

## Controls

| Action | Mouse/Keyboard |  Controller (Xbox) |
| - | :-: | :-: |
| **Capture/uncapture mouse** | ESCAPE | START |
| **Hide/unhide control panel UI** | H | D-pad Left |
|  |  |  |
| **Move** | W-A-S-D | Left Stick |
| **Sprint** (Toggle) | SHIFT | Left Stick Button |
| **Jump** | SPACE | A |
| **Noclip** | TILDE (~) | D-pad Up |
|  |  |  |
| **Switch third person/first person** | V | BACK |
| **Zoom/focus** (Toggle) | Right Click | Left Trigger |

## Editor Options

* Use the Light Change Utility node to change lighting scenarios in the editor.  

    ![Light Change Utility](https://github.com/Jamsers/Bistro-Demo-Tweaked/assets/39361911/09c0a406-e942-467e-8ecc-fb2eafc55f4e)
  
* Includes a profiler to see performance details. [RAM counter not available in release builds](https://docs.godotengine.org/en/stable/classes/class_performance.html#enumerations).  
    You can turn music on or off in the editor.  

    ![UI Toggles](https://github.com/Jamsers/Bistro-Demo-Tweaked/assets/39361911/6d39b553-558b-4a63-8551-5e76681a9e90)

## License

Unless stated otherwise within the [**`ATTRIBUTION`**](ATTRIBUTION) file or directly alongside specific files/folders, the following licenses apply:

**Code:** Licensed under the MIT license.  
[![MIT license](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE-CODE)

**Assets:** Licensed under the CC BY 4.0 license.  
[![CC BY 4.0 license](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg?style=for-the-badge)](LICENSE-ASSETS)

Please refer to the respective license files for full details.

## Credits

Developed by [John James Gutib](https://github.com/Jamsers).

Built from [Lumberyard Bistro Reference Scene](https://github.com/godotengine/godot/issues/74965) by [Logan Preshaw](https://github.com/WickedInsignia).  
Lumberyard Bistro Reference Scene is [Amazon Lumberyard Bistro](https://developer.nvidia.com/orca/amazon-lumberyard-bistro), by [Amazon Lumberyard](https://aws.amazon.com/lumberyard/), ported to Godot by Logan Preshaw.  

Music is [Bright Bistro](https://www.youtube.com/watch?v=W8CFKvLtBaI) and [Blissful Bistro](https://www.youtube.com/watch?v=N8L46km_EOg), by [Aaron James Gutib](https://www.youtube.com/@Anuron01/).  

Uses [Godot-Human-For-Scale](https://github.com/Jamsers/Godot-Human-For-Scale) by [John James Gutib](https://github.com/Jamsers).

Please refer to the [**`ATTRIBUTION`**](ATTRIBUTION) file for full details.
