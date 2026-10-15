---
name: audit
description: "Audit or critique a product flow, journey, workflow, funnel, onboarding path, checkout path, settings path, screen, or multi-step product experience by capturing screenshots first, then reporting UX, design, and accessibility findings from that evidence. Default to an inline report; use a canvas for a visual walkthrough when requested or clearly implied by the ongoing task. Use when the user asks to audit, review, critique, inspect, assess, analyze, evaluate, or give feedback on a product experience."
---

# Audit

Use this skill when the user wants to audit, review, critique, inspect, assess, analyze, evaluate, or give feedback on a product flow, journey, funnel, onboarding path, checkout path, settings path, screen, or other product experience.

Recognize that intent from the ongoing task; the user need not name the audit skill.

The output is not a loose opinion. The output is:

- Screenshots of the flow
- Those screenshots presented in a report or a visual walkthrough on the user's chosen canvas
- A numbered step list
- UX and design findings tied to steps or screenshots
- Accessibility risks tied to steps or screenshots
- Clear limits on what could not be checked from screenshots alone

## Critical Overrides

- Refer to the Plugin router [$index](../index/SKILL.md) before proceeding.
- Follow [$critical-overrides](../../references/critical-overrides.md).

## User Context

Before starting, load [$user-context](../user-context/SKILL.md) and run its preflight script when local shell access is available.

Use saved product URLs, Figma files, screenshots, reference images, codebase paths, Storybook, tokens, design systems, brand assets, component refs, browser preferences, and share targets as grounding material when relevant.

Do not inspect every saved reference. Inspect only what the current task needs.

## Route

Before auditing:

1. Identify the product or surface.
2. Identify the flow or task.
3. Choose the capture tool.
4. Capture the flow.
5. Save and inspect each screenshot.
6. Present the accepted screenshots and findings in the user's chosen format, defaulting to an inline report.

Output rules:

- Honor the output format and canvas already stated or clearly implied by the ongoing task. Proceed without reasking settled choices; if a canvas walkthrough is chosen but its destination is unclear, ask only which canvas to use.
- If no output format is established, default to a concise inline report with screenshots rendered in the chat.
- Saving screenshots and notes in the workspace is an internal implementation detail. Do not ask the user to choose a local folder.
- Let the user choose a report with screenshots or a visual walkthrough: screenshots laid out step by step on a canvas, with notes beside each screen.
- Only if no output format has been established or declined, offer a canvas walkthrough at most once. With no established tool preference, ask: `Would you like these screenshots laid out step by step on a canvas, with notes for each screen?`
- Within that single offer, suggest Figma or another design tool only when the user's request or relevant saved context or memory indicates they use it and available tools can create the walkthrough. Tool availability alone is not a reason to promote it; saved tool usage alone does not select a canvas output.
- If the user chooses a canvas walkthrough, follow their chosen tool's skills to arrange the screenshots and notes in flow order. Return a link and concise summary inline; include a full inline report only if requested.

Capture rules:

- Follow the Browser Choice rule in [$index](../index/SKILL.md#browser-choice).
- If none of those can capture valid screenshots or control the flow, stop and report the blocker.

Browser capture order:

1. Load the Browser skill before browser work.
2. Connect to the browser and use the current tab when it already shows the target.
3. Do not reload or navigate away unless the audit needs a fresh start.
4. Observe the visible state before acting.
5. Before each click, type, or key press, use the latest DOM snapshot to target one clear control.
6. After each action, take the cheapest fresh check that proves what changed: DOM for structure, screenshot for visual state.
7. Save and inspect the accepted screenshot before using it as audit evidence.

Canvas rules:

- Load the chosen tool's skills before creating or editing the canvas.
- Keep a local copy of every screenshot even when the canvas succeeds.
- Do not upload a screenshot until the saved local file has been inspected and accepted.
- The walkthrough is not done until the screenshots and notes are visibly placed on the canvas.
- Render or inspect the canvas and confirm every flow step has the correct screenshot and its notes visible together in flow order.
- If an image is missing, misplaced, blank, or only uploaded as an unused asset, fix it before handoff.
- If the chosen tool cannot create the canvas or place images, return the inline audit and explain the missing capability.

Evidence rules:

- Use only evidence captured in the current audit run.
- Do not use memory, prior chats, old traces, cached screenshots, or prior generated artifacts as audit evidence unless the user explicitly provides them.
- Do not audit until the product, flow, and capture tool are known.
- Do not claim full accessibility compliance from screenshots alone.

## Capture And Audit The Flow

You are an expert design, UX, and accessibility auditor. For each step in the flow, capture what the user sees, observe how the screen behaves, inspect the screenshot, and write audit notes before moving on.

Follow [references/design-audit-framework.md](references/design-audit-framework.md) when deciding what to inspect and how to describe strengths, UX issues, accessibility risks, limits, and recommendations.

Screenshot source rule:

- Use the screenshot you actually saw.
- Save that exact screenshot to the local audit folder.
- Open or inspect the saved file before accepting it.
- If the saved file shows the wrong window, wrong state, blank page, crop, or loading screen, reject it and capture again.
- When a canvas is the destination, upload that accepted local file.
- After upload, verify the canvas shows the same step.
- Do not replace a Browser, Chrome, or Computer Use screenshot with an OS screenshot unless you first prove the saved file shows the same window and state.

For every step:

1. Move to the next step in the requested flow.
2. Wait until the screen is loaded and visually stable.
3. Check for loading spinners, blank areas, login walls, error pages, blocked states, cookie dialogs, and half-rendered content.
4. Capture the screenshot.
5. Inspect the screenshot before accepting it.
6. Reject the screenshot if it is blank, loading, cropped, blocked, or showing the wrong state.
7. Observe behavior that matters for the audit, such as navigation, focus, loading, validation, error handling, empty states, motion, and whether the next action is clear.
8. Write notes for that step.
9. In the notes, report strengths, UX issues, accessibility risks, and any limits that made the step difficult to audit.
10. Save accepted screenshots with numbered names, such as `01-start.png`, `02-form-filled.png`, and `03-confirmation.png`.
11. Inspect the saved screenshot file before upload or handoff.
12. Keep each accepted screenshot and its notes together for the report or canvas walkthrough.
13. If the user requested a canvas walkthrough, add each accepted screenshot and its notes to the canvas immediately.

Default inline report:

- Render accepted screenshots in flow order.
- Keep the report pithy: overall verdict, numbered steps, highest-impact changes, and evidence limits.
- Tie every finding to the screenshot or step that supports it.

If the user requested a canvas walkthrough:

- Place screenshots in order, left to right on the same row, with 200px between each one. Go to a new row every 15 screenshots, and separate those rows by 600px.
- Underneath the screenshot, add text with the Step number and its name, and notes.
- Keep a local folder copy even when the canvas succeeds.
- Give the walkthrough a title and group its assets in a section or equivalent container supported by the chosen tool.

Acceptance checks:

- Every important step in the requested flow has a valid screenshot or a named blocker.
- Screenshots are saved in order.
- Screenshots are visible in the chosen output: inline in the report or arranged in flow order on the canvas.
- For a canvas walkthrough, every accepted screenshot and its notes are visibly placed together in flow order and verified on the completed canvas.
- Every note points to the screenshot or step it describes.
- Notes explain strengths, UX issues, accessibility risks, and evidence limits when those apply.
- Accessibility risks say what can be seen from screenshots and what still needs testing.
- The final screenshot set and notes are enough to support the requested audit.

Blockers:

- The flow cannot be completed.
- A required step cannot be screenshotted.
- The source changes in a way that makes the flow unclear.
- Screenshots cannot be saved or displayed in the chosen output.
- Notes cannot be written.
- The requested claim would require evidence that screenshots cannot provide.
- Do not claim an audit if the actual flow could not be accessed and captured. Help Center pages, web searches, and other indirect evidence are research, not an audit.

## Final Response

After the flow is captured and notes are written, list every step in the final response.

The final step list MUST include:

- step number
- short description of the step
- general health of that step

Also include where the full output was saved or placed.

Keep the language direct. Do not use broad design jargon when a plain phrase works.
