# NeuroCanvas

An **incomplete application scaffold** for an emotion-to-art project. The repository contains a Flask route layer, configuration, a React application shell and dependency lists. It does not contain the implementations needed to run the proposed art-generation workflow.

## What is present

- [app.py](app.py): routes for accounts, emotion analysis, artwork, narratives and memory, plus SocketIO setup.
- [src/config.py](src/config.py): configuration for the proposed services.
- [frontend/src/App.tsx](frontend/src/App.tsx): React routing and theme setup.
- [requirements.txt](requirements.txt) and [frontend/package.json](frontend/package.json): Python and frontend dependencies.

These files describe interfaces and wiring; they do not establish that the corresponding features work.

## What is missing

The backend imports six modules absent from the repository:

```text
src/database.py
src/emotion_analyzer.py
src/art_generator.py
src/narrative_generator.py
src/memory_system.py
src/websocket_handler.py
```

The React shell also imports untracked pages, components, a store, contexts and hooks. Frontend entry files are missing. Installing dependencies or supplying an API key will not resolve these missing-source errors.

## Development status

```bash
git clone https://github.com/Zinga18018/NeuroCanvas-AI-Art-Generator.git
cd NeuroCanvas-AI-Art-Generator
```

Start by restoring or implementing the missing modules and frontend entrypoints, then add tests before attempting a full launch. The earlier `python app.py` / `npm start` instructions are not a complete working setup for this checkout. No model/API call, application run or browser test is claimed here.

There are no committed model weights, evaluation records or timing scripts supporting emotion accuracy, generation speed, interaction latency or narrative-coherence figures. The earlier performance numbers and example interactions should not be treated as measured results. No brainwave acquisition or working art output is demonstrated by this source.

EEG input, VR/AR, collaborative creation, music integration and a mobile app were proposed directions, not implemented features.

## License and acknowledgments

[MIT License](LICENSE), with the existing NeuroCanvas copyright notice.

The concept was inspired by neuromorphic-computing and brain–computer-interface research and by multimodal AI tooling. Thanks to the open-source AI community. Contributions should distinguish implemented behavior from planned components and include reproducible tests.
