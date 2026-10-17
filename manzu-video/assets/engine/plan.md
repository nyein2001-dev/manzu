# <Video title>: plan

Status: draft. Replace every <placeholder>; delete sections that do not apply. Scene workers read this file, `SCENE_RULES.md`,
`lib.py` and `scenes/s0_demo.py` before writing a scene.

## Audience and goal
- Viewer: <age, reading level, attention profile, what they already know>.
- After the video the viewer can: <one to three observable abilities, e.g. "find the LCM of two numbers by listing multiples">.
- Terminology rule: <language, e.g. English terms only; every abbreviation is introduced with its full form in the first 30 s>.
- Privacy: <the learner's first name is allowed in narration/captions only if the owner said so; never send narration to an external service without authorization>.

## Narrative arc
<The misconception this corrects, the aha moment, the order of ideas. One idea at a time. A prediction pause (Hold, "think") before every
reveal; one movement break (Hold, "move") if the viewer is a child. Length target: <e.g. 5-7 min>.>

## Colour mapping (one meaning per colour for the whole video)
| Colour | Meaning |
|---|---|
| CORAL | <first quantity> |
| SKY | <second quantity> |
| GOLD | <key result> |
| GREEN | <success / second kind of result> |

## Scenes
Scene ids are the keys of `SCENES` in `script.py` (`s0_...`). Narration lives only in `script.py`.
### s0_<id> (about <n> s)
<Items 0-1: what is on screen. Item 2: ... Say which spoken word triggers each visual: "tile 36 pops on 'thirty-six'". Props to draw from cairo shapes.>
### s1_<id>
<...>

## Output
Draft cache: `$EXPLAINER_WORK` (default `/tmp/explainer_work`). Final: `<project>/out/<name>.mp4` (+ `.srt`). Status label: "draft for <owner>'s review"
until the owner approves. Earlier versions are kept next to the final file with a `_v1_...` suffix.
