# Prompt: Reels Script Generator

Generate a structured script for an Instagram Reel.

## Brand Profile
{brand_profile}

## Post Details
- Theme: {theme}
- Audio reference: {audio_ref_description}
- Hashtags: {hashtags}

## Instructions

Write a Reels script with three sections:
1. **Intro (0–3s)**: Hook statement or question to stop the scroll
2. **Body (3–25s)**: Core content — steps, tips, or story. Each beat is one short sentence (max 7 words on screen)
3. **CTA (last 3–5s)**: Clear call to action

If audio reference is provided, include a "Music Style" section describing the audio mood and how it matches the content pacing.

## Output format

Output a Markdown document with this structure:

# Reel Script: {theme}

## Intro (0–3s)
[hook text]

## Body
[Beat 1]: ...
[Beat 2]: ...
...

## CTA
[call to action]

## Caption
[Full Instagram caption with hashtags at end]

{audio_section_placeholder}

Output ONLY the Markdown document. No extra explanation.
