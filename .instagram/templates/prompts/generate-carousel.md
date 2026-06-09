# Prompt: Carousel Slide Copy Generator

Generate per-slide copy text for an Instagram carousel post.

## Brand Profile
{brand_profile}

## Post Details
- Theme: {theme}
- Number of slides: {slide_count}
- Hashtags for final caption: {hashtags}

## Instructions

Generate copy for each slide:
- **Slide 1 (Cover)**: Attention-grabbing headline (max 8 words), subtitle optional
- **Slides 2 through N-1 (Content)**: One focused point per slide. Short sentences. Use lists or steps when appropriate.
- **Slide N (Closing)**: Call to action — "Save", "Follow", "Share", or "Comment"

Also generate the main post caption (displayed when the carousel is viewed in feed).

## Output format

Output a JSON object with this structure:
```json
{
  "caption": "Full feed caption with hashtags appended at end",
  "slides": [
    {"slide": 1, "headline": "...", "body": "..."},
    {"slide": 2, "headline": "...", "body": "..."}
  ]
}
```

Output ONLY the JSON object. No explanation, no markdown fences.

Theme: {theme}
Slide count: {slide_count}
