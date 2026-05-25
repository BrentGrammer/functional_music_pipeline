# Composition App UX Decisions

## Overview

This document captures the current UX decisions for the composition app mockup.

The app allows users to compose music by arranging musical phrases inside voices. A phrase contains:

- A list of motifs
- A transform pipeline

Motifs are sequences of tones. Transforms are operations such as:

- Reverse
- Invert
- Accelerando
- Crescendo

The design goal is to keep the main composition view fast, uncluttered, and mostly drag-and-drop driven.

---

# Core Mental Model

## Voice

A voice is a horizontal lane that contains phrases.

Users should be able to place phrases horizontally within a voice and reorder them.

## Phrase

A phrase is the main object placed inside a voice lane.

A phrase contains:

- Phrase name
- Motif list
- Transform pipeline

A phrase and its transforms should be treated as one grouped unit.

## Motif

A motif is a named musical idea or sequence of tones.

Motifs belong inside phrases.

## Transform

A transform is an operation applied to the phrase’s motif list or musical output.

Transforms belong inside phrases, not as separate blocks in the voice lane.

---

# Main Composition View

## Voice Lane Purpose

The voice lane should answer this question:

> What phrases happen, in what order, in this voice?

The voice lane should not become a full editor for every phrase.

## Phrase Block Content

The phrase block should stay compact.

Each phrase block should show only:

- Phrase name
- Motif names
- Transform names in pipeline order

Example:

```text
[ Phrase A                         ⋯ ]
Motifs: motif 1, motif 2, motif 3
Pipeline: reverse → invert → crescendo
```

## No Expandable Phrase Blocks

Phrase blocks should not expand or collapse inside the voice lane.

Reasons:

- Keeps the voice lane clean
- Avoids covering nearby phrases
- Avoids visual clutter when a voice contains many phrases
- Keeps editing behavior separate from arrangement behavior

---

# Editing Model

## Use a Side Inspector

Clicking a phrase should open a side inspector.

The side inspector is the primary place for editing phrase details.

The side inspector should update when the user clicks a different phrase.

This allows the workflow:

1. Click Phrase A
2. Edit Phrase A in the side inspector
3. Click Phrase B
4. Side inspector updates to Phrase B
5. Edit Phrase B

The user should not need to close anything between phrase edits.

## Why Side Inspector Instead of Modal

A side inspector is preferred because:

- It keeps the voice lane visible
- It allows quick switching between phrases
- It supports iterative editing
- It does not interrupt the composition workflow
- It avoids repeated open/close modal behavior

A modal would give more space, but it would interrupt the workflow too much for routine phrase editing.

## When to Use a Modal

Modals should be reserved for deeper or secondary tasks, such as:

- Editing detailed transform parameters
- Browsing a large transform library
- Confirming destructive actions if undo is unavailable
- Viewing a large preview
- Exporting or saving reusable material

---

# Side Inspector Content

The side inspector should show the selected phrase.

It should allow editing:

- Phrase name
- Motif list
- Motif order
- Transform list
- Transform order
- Transform parameters
- Phrase preview or result

Example structure:

```text
Phrase A

Motifs
[ motif 1   ⋮ ]
[ motif 2   ⋮ ]
[ motif 3   ⋮ ]
[ + Add motif ]

Transforms
[ reverse      ⋮ ]
[ invert       ⋮ ]
[ crescendo    ⋮ ]
[ + Add transform ]

Preview / Result
...
```

---

# Drag-and-Drop Philosophy

The app should remain mostly drag-and-drop driven.

Drag-and-drop should be used for spatial and ordering actions.

Menus should only be used for actions that are not naturally drag-based.

## Drag-and-Drop Actions

Users should be able to:

- Drag phrases horizontally within the same voice
- Drag phrases into another voice
- Reorder motifs inside the side inspector
- Reorder transforms inside the side inspector
- Drag transforms from a transform palette into a phrase
- Drag motifs from a motif list into a phrase

## Menu Actions

Menus should be used for non-spatial actions.

Phrase menu actions should include:

- Rename
- Duplicate
- Delete

Possible future actions:

- Copy
- Save as reusable phrase
- Mute phrase
- Bypass transforms
- Lock phrase

The menu should not include actions that already have better direct interactions.

Do not include:

- Edit
- Move to voice

Reasons:

- Clicking the phrase already opens the side inspector
- Dragging the phrase already moves it between voices

---

# Phrase Card Interaction

## Recommended Phrase Card Layout

```text
[ ⋮⋮  Phrase A                         ⋯ ]
      Motifs: motif 1, motif 2, motif 3
      Pipeline: reverse → invert
```

## Phrase Card Elements

### Drag Handle

The drag handle should be used to move the phrase.

This reduces conflicts between:

- Clicking to select
- Opening the side inspector
- Opening the menu
- Renaming
- Dragging

### Phrase Body

Clicking the phrase body should:

- Select the phrase
- Open the side inspector
- Update the side inspector if it is already open

### Dot Menu

The dot menu should open phrase-specific actions.

The menu should contain:

```text
Rename
Duplicate
Delete
```

### Right Click

Right click can open the same phrase menu.

Right click should be optional, not required.

Reasons:

- Some users will not discover right click
- Right click is weaker on touch devices
- A visible dot menu is more discoverable

---

# Rename Behavior

## Rename Should Be in the Dot Menu

Rename should be triggered from the phrase dot menu.

This avoids conflicts between:

- Dragging
- Clicking
- Double-clicking
- Text selection

The rename interaction should be explicit.

## Rename Flow

When the user selects:

```text
⋯ → Rename
```

The phrase title becomes an editable input.

Example:

```text
[      [Phrase A________]              ✓  ✕ ]
```

## Rename Controls

While renaming:

- Enter saves
- Escape cancels
- Checkmark saves
- X cancels
- Clicking outside saves

## Dragging During Rename

Dragging should be disabled for that phrase while rename mode is active.

This is the chosen behavior.

Dragging should not cancel rename.

Reason:

- Dragging while editing could cause surprising data loss
- Disabling drag during rename is simpler and safer
- Rename mode should temporarily lock that phrase

## Phrase Menu During Rename

While renaming, the dot menu should be hidden or disabled for that phrase.

The phrase should have only two modes:

```text
Normal:
[ ⋮⋮  Phrase A                         ⋯ ]

Renaming:
[      [Phrase A________]              ✓  ✕ ]
```

---

# Delete Behavior

## Delete Location

Delete should live inside the phrase dot menu.

Example:

```text
⋯ → Delete
```

Delete should not be a permanently visible button on the phrase card.

Reasons:

- Prevents accidental deletion
- Keeps phrase card uncluttered
- Keeps destructive actions out of the main flow

## Delete Confirmation

Preferred behavior:

- Support undo
- Do not show a heavy confirmation dialog for every delete

If undo is not implemented yet, use a simple confirmation.

Example:

```text
Delete Phrase A?
Cancel | Delete
```

## Delete Menu Placement

Delete should be visually separated from other menu items.

Example:

```text
Rename
Duplicate
---
Delete
```

---

# Duplicate Behavior

Duplicate should live in the phrase dot menu.

Example:

```text
⋯ → Duplicate
```

Duplicating should create a copy of the phrase with:

- Same motif list
- Same transform pipeline
- Same transform parameters
- New phrase identity
- Modified name

Example name:

```text
Phrase A copy
```

The duplicate should appear near the original phrase, probably immediately after it in the same voice.

---

# Move Behavior

## Moving Within a Voice

Users should drag the phrase to reorder it horizontally within the same voice.

Do not use a menu action for this.

## Moving Across Voices

Users should drag the phrase into another voice row.

Do not use a "Move to voice" menu item unless accessibility or fallback support is needed later.

## Future Accessibility Fallback

A future version could add a menu-based move option for keyboard/accessibility support.

Example:

```text
Move to voice...
```

But this should not be part of the first version unless needed.

---

# Transform UX

## Transforms Belong to Phrases

Transforms should be part of the phrase, not separate timeline blocks.

A phrase should be understood as:

```text
Phrase = Motifs |> Transform |> Transform |> Transform
```

## Show Transform Summary in Phrase Block

The phrase block should show only transform names.

Example:

```text
Pipeline: reverse → invert → crescendo
```

Do not show transform parameters inside the phrase block.

## Edit Transforms in Side Inspector

Transform editing should happen in the side inspector.

Users should be able to:

- Add transforms
- Remove transforms
- Reorder transforms
- Edit transform parameters
- Bypass or disable a transform in the future

## Transform Parameters

Simple parameters can expand inline inside the side inspector.

Complex transform parameter editing can use a modal or larger editor.

---

# Motif UX

## Show Motif Summary in Phrase Block

The phrase block should show motif names only.

Example:

```text
Motifs: motif 1, motif 2, motif 3
```

Do not show full motif contents in the phrase block.

## Edit Motifs in Side Inspector

Motif editing should happen in the side inspector.

Users should be able to:

- Add motifs
- Remove motifs
- Reorder motifs
- Possibly preview motifs

---

# Transform Palette

The "Score Transforms" area should act more like a transform palette or library.

It should contain available transforms such as:

```text
[ reverse ] [ invert ] [ accelerando ] [ crescendo ]
```

Users can drag transforms from this area into a phrase or into the selected phrase’s transform list.

Applied transforms should live inside the phrase, not in the global palette.

---

# Motif Library

The motif list area should act as the available motif library.

Users can drag motifs from the motif library into a phrase.

The phrase stores references or copies of selected motifs, depending on the app’s data model.

The top global motif row should be a library / reference palette, not the primary editing place.

The phrase editor should be the main place where motifs are added, created, ordered, and used.

Global motif row

### Editing Global Motifs

Motifs are global reusable objects

A phrase does not own motif contents.
A phrase only stores references to motifs:

The global motif list owns the actual motif data:
So if the user edits “Rising Third” globally, every phrase using it updates automatically.

Phrase editor should only manage usage/order
Inside the phrase side panel, the user can:

Add existing motif to phrase
Remove motif from phrase
Reorder motifs in phrase

But they should not edit the motif’s musical contents there.

So the side panel motif section becomes:

```text
Motifs in this phrase
[ :: Rising Third     remove ]
[ :: Turn Figure      remove ]
[ :: Cadence Cell     remove ]
[ + Add Motif ] (Cancel | Create)
```

(The `::` is the handle to drag order)

#### Motif Editor

User clicks a motif in the global motif row:

[ Motif A ] [ Motif B ] [ Motif C ]

Then a modal opens:

<!-- prettier-ignore -->
┌──────────────────────────────────────────────┐
│ Edit Motif: Rising Third                 X   │
├──────────────────────────────────────────────┤
│ Name                                         │
│ [ Rising Third                            ]  │
│                                              │
│ Tones                                        │
│                                              │
│ #  Frequency Hz      Duration sec   ⋯    │   |
│ :: [ 440.0      ]    [ 1.0      ]   ⋯    │   |
│ :: [ 493.88     ]    [ 0.75     ]   ⋯    |   |
│ :: [ 523.25     ]    [ 1.3      ]   ⋯    │   |
│                                              │
│  [ + Add Tone ]                              │
│                                              │
├──────────────────────────────────────────────┤
│                        Cancel   Save         │
└──────────────────────────────────────────────┘

- `::` is a drag handle to rearrange order of tones.
- `...` is the menu that has options: Delete | Duplicate

---

# Recommended Initial Phrase Menu

The first version of the phrase menu should contain only:

```text
Rename
Duplicate
---
Delete
```

Avoid adding extra actions until there is a clear need.

---

# Recommended First Version Behavior

## Main View

- Show voices as horizontal lanes
- Show phrases as compact cards
- Show phrase name
- Show motif names
- Show transform pipeline names
- Keep phrase cards non-expandable

## Phrase Selection

- Click phrase card to select it
- Open or update the side inspector

## Dragging

- Drag phrase by drag handle
- Reorder phrases horizontally
- Move phrases across voices
- Reorder motifs in side inspector
- Reorder transforms in side inspector

## Dot Menu

- Rename
- Duplicate
- Delete

## Rename

- Trigger from dot menu
- Convert title to input
- Disable dragging for that phrase while renaming
- Enter saves
- Escape cancels
- Clicking outside saves

## Side Inspector

- Edit motif list
- Edit transform list
- Add/remove/reorder motifs
- Add/remove/reorder transforms
- Edit transform parameters
- Show preview/result if useful

---

# Implementation Notes

## Drag Handle

Use a dedicated drag handle on the phrase card.

This avoids event conflicts.

Example:

```text
[ ⋮⋮  Phrase A                         ⋯ ]
```

## Rename State

Each phrase can track whether it is currently renaming.

Example:

```ts
isRenaming: boolean;
```

When `isRenaming` is true:

- Disable dragging for that phrase
- Hide or disable the dot menu
- Show the editable title input
- Show save/cancel controls

## Selection State

Track selected phrase separately.

Example:

```ts
selectedPhraseId: string | null;
```

Clicking a phrase sets the selected phrase and updates the side inspector.

## Drag State

Dragging should be disabled for a phrase when:

- It is being renamed
- It is locked in the future
- A modal or blocking editor is active, if needed

## Side Inspector State

The side inspector should show the currently selected phrase.

If no phrase is selected, it can show:

```text
Select a phrase to edit motifs and transforms.
```

---

# Key Design Principles

## Keep the Voice Lane Clean

The voice lane is for arranging phrases, not deep editing.

## Keep Editing Close to Context

The side inspector allows editing while keeping the composition visible.

## Prefer Drag-and-Drop for Spatial Actions

Use dragging for anything related to position or order.

## Prefer Menus for Non-Spatial Actions

Use menus for actions like rename, duplicate, and delete.

## Avoid Hidden Required Interactions

Right click can be supported, but visible controls should exist.

## Avoid Interaction Conflicts

Use a drag handle and explicit rename mode to avoid conflicts between clicking, dragging, and editing.

## Keep the First Version Small

Start with the minimum phrase menu:

```text
Rename
Duplicate
Delete
```

Add more actions later only when needed.
