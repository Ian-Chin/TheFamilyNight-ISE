# Bus Scene Assets

Assets are separated from the original BBQ, chopping and grilling scenes.
The game canvas is 1280 x 720. The interior reference canvas is 1056 x 442.
All events play complete frames with a fixed layout.

Paths below are relative to assets:

- backgrounds/bus-scene/waiting_bus: PASAR station, yellow bus, arrow and boarding layout.
- backgrounds/bus-scene/animations: idle, mask scare, cane impact, food theft and fart attack; 48 frames each, with grid and layout metadata.
- backgrounds/bus-scene/in_bus: interior backgrounds and earlier reference images.
- characters/bus-scene: hero, driver, child, grandmother, office worker and heavy passenger animations.
- ui/bus-scene: segmented bread health bar, ingredient cards, warnings and pixel menus.
- audio/bus-scene/bgm: racing music.
- audio/bus-scene/sfx: event sounds, footsteps, jumping and arrival horn.
- sprites/bus-scene/transitions: bus wipe transition.
- sprites/bus-scene/effects: spilled ingredients, failure artwork and prop effects.
- backgrounds/bus-scene/destination: original project backdrop for the arrival transition.

Python code and bundled pygame-ce are in game/bus_runtime.
asset-index.json maps original files to their classified paths, relative to assets.

Controls: A/D to move, Space to jump. Walk beside the bus and press Enter to board.
Event responses: J for the mask, K for the cane, L for food theft and I for the fart.
Release each key before pressing it again. Every five continuous seconds outside the circle
costs one health segment. Returning resets the countdown; pausing freezes it.
During the ride, Space or P pauses and resumes the game.

Run `py -3.12 main.py --windowed` from the project directory.
A successful delivery automatically enters the original BBQ scene.
