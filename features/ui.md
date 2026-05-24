# Adding a UI

Adding a React UI should be treated as adding a web client plus a thin Python API, not replacing the existing CLI/core pipeline.

The current app is a Python 3.13 CLI/library with clean domain modules for composition parsing, transforms, score models, WAV, and MIDI rendering. The browser cannot
safely call that filesystem/rendering code directly, so the UI should talk to a local/server API that wraps the same pipeline the CLI already uses.

Recommended Stack

- Backend API: FastAPI + uvicorn
- Frontend: React + TypeScript
- Build tool: Vite, or create-react-router if you want React Router’s framework mode
- Routing: React Router v7
- API typing: FastAPI OpenAPI schema + generated TypeScript client/types, likely openapi-typescript
- Client data: React Router loaders/actions for route-level data, or TanStack Query for richer async/job flows
- Forms/schema: React Hook Form + Zod, or generated types from the backend to avoid duplicating schemas
- Audio preview: Start with rendered WAV playback via <audio>; add Web Audio/Tone.js only if you want browser-side auditioning
- Visualization: Canvas/SVG piano-roll timeline for motifs, phrases, voices, and transforms
- UI components: Radix/shadcn-style primitives are a good fit for sliders, dialogs, tabs, selects, transform panels
- Testing: pytest for API/core, Vitest/React Testing Library for UI, Playwright later for end-to-end render flows

Shape Of The App
The first good architecture would be:

React UI
-> FastAPI endpoints
-> existing composition parser / transformer / renderer
-> WAV or MIDI artifact

Useful first endpoints:

GET /api/transforms
POST /api/compositions/validate
POST /api/compositions/render
GET /api/renders/{render_id}
GET /api/renders/{render_id}/download

Initially POST /render can run synchronously if renders are quick. If rendering gets slower, move to job IDs with BackgroundTasks, then a real queue later.

React Router Choice
Based on current official docs, React Router v7 is the current routing direction. React’s own docs list React Router v7 as a recommended framework option, and React
Router’s docs describe v7 as a non-breaking upgrade from v6 with framework/data features.

For this project, I’d choose one of these:

1. Pragmatic first version: Vite + React + TypeScript + React Router v7 in browser/data-router mode.
   Best fit if FastAPI owns the backend.
2. More integrated React framework: create-react-router@latest.
   Better if you want SSR, route modules, loaders/actions, and a more framework-like React app. Adds Node-side complexity you probably do not need yet.

I would not start with Next.js unless you specifically want a Node full-stack app. The valuable backend already exists in Python.

Initial UI Scope
The smallest useful UI would be:

/compositions
/compositions/new
/compositions/:id
/renders/:id
/transforms

Core screens:

- Composition editor: motifs, phrases, voices, transform chain
- Transform browser: available transforms and parameters
- Preview/render panel: output format, render button, audio playback, download
- JSON import/export: keep compatibility with the CLI composition format

Important Design Constraint
The strongest long-term move is to extract the CLI render path into an application service, then have both CLI and FastAPI call it. That prevents the UI from becoming
a second implementation of the pipeline.

External source checked: official React docs and React Router docs, specifically React’s current “Creating a React App” guidance and React Router v7 documentation.

## Drag and Drop plus alternative considerations

I would not build the drag/drop system from scratch. The hard part is not “move a box with the mouse”; it is selection, keyboard access, touch behavior, collision
rules, reordering, nested drop zones, edge rendering, undo/redo, and keeping the visual state synced with the composition schema.

For this project, I see two good UI directions.

Best Fit
Use a structured lane editor first, not a fully freeform graph.

The mental model you described is mostly:

Score transforms

Voice 1: Phrase -> Motif -> Transform -> Transform -> Output
Voice 2: Phrase -> Motif -> Transform -> Transform -> Output
Voice 3: Phrase -> Motif -> Transform -> Transform -> Output

That is more constrained than Node-RED. Each voice is a row/lane, and inside each row there are ordered musical units and transform chains. Users need drag/drop, but
probably with guardrails: snap into a voice, reorder phrases, reorder transforms, move motifs between phrases, duplicate blocks, disable blocks, inspect parameters.

For that, I’d start with:

- React + TypeScript
- dnd kit for drag/drop and sortable lanes
- Zustand or reducer-based state for the composition editor
- FastAPI backend wrapping the existing Python pipeline
- Zod or generated OpenAPI types for validating client-side composition data
- SVG/canvas only for visual connector lines, not for the whole app at first

This keeps the editor close to the actual domain model: Score -> Voice -> Phrase -> Motif -> Transforms.

When To Use React Flow
Use React Flow / @xyflow/react if the UI really needs a freeform patch-cable graph:

Motif node -> inversion node -> retrograde node -> render node

React Flow gives you nodes, edges, zoom/pan, selection, minimap, custom node components, and connection handles out of the box. It is a good fit for a Node-RED-like
canvas.

The risk is that a totally free graph may be more flexible than the composition model actually supports. If the backend expects ordered voices, phrases, motifs, and
transform lists, then the UI has to translate arbitrary graph state back into a valid composition document. That can become the hardest part of the app.

My Recommendation
Start with React + dnd kit, not React Flow.

Build the first UI as a lane-based composition builder:

- Left panel: motif blocks, phrase blocks, transform palette
- Top strip: score-level transform chain
- Main canvas: one horizontal row per voice
- Inside each voice: ordered phrase/motif blocks
- Inside or attached to each block: ordered transform chain
- Right inspector: selected item parameters
- Bottom/right preview: validate, render WAV/MIDI, audio playback, download

Then add React Flow later only if the workflow evolves toward genuinely arbitrary signal routing.

Why Not Vanilla JS
Vanilla JS is fine for a tiny prototype, but I would not use it for the actual editor. This UI will need nested state, typed composition data, reusable controls,
parameter forms, drag/drop rules, validation errors, render status, and eventually undo/redo. A framework will pay for itself quickly.

Library Notes

- dnd kit is a strong choice for sortable/nested drag/drop and has React support, TypeScript support, keyboard/touch-oriented architecture, and extensibility.
- React Flow is the strong choice for node-and-edge editors; its official docs explicitly target node-based workflow editors and include drag/drop, nodes, edges,
  zooming, panning, selection, and custom node components.
- Native HTML drag/drop alone is not enough. React Flow’s own docs note that native HTML Drag and Drop is not properly supported on touch devices, and suggest pointer
  events or a library for better cross-device behavior.

Sources checked: dnd kit docs (https://dndkit.com/), React Flow docs (https://reactflow.dev/), and React Flow drag/drop example
(https://reactflow.dev/examples/interaction/drag-and-drop).

## Timeline Dragging Plan

Timeline dragging should feel continuous and analog to the user. The editor should not expose beat, quarter-note, or grid snapping as the primary interaction model. Internally, the UI and API can store small precision increments such as seconds or milliseconds, but the visual behavior should allow users to place blocks freely along the timeline.

Voice-level dragging is the best first timeline feature. Dragging a voice row horizontally should update that voice's entrance offset, so the whole voice starts later or earlier in the rendered output. This can be represented as a `start_offset_seconds` value and lowered to leading silence when calling the existing render pipeline.

Phrase-level dragging is also feasible, with one important restriction: phrases inside the same voice must not overlap. Users can move phrase blocks continuously along the timeline, but if the dragged phrase would overlap another phrase in that voice, the drop should be blocked. The UI should make the invalid placement obvious, for example by showing a disabled/drop-not-allowed icon over the dragged block while it is in the blocked region.

For the first phrase timeline version:

- Allow continuous horizontal dragging with no visible snap grid.
- Store phrase placement as a precise time offset.
- Sort phrases by start time before rendering.
- Insert silence between phrases when there is a gap.
- Block overlap instead of pushing other phrases, resizing phrases, or allowing stacked phrases within one voice.

Motif-level free timeline placement should be deferred. It would push the editor closer to a DAW/event-based model and require more complex placement, collision, transform, and rendering rules.
