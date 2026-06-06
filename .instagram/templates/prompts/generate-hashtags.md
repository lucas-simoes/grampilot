# Prompt: Hashtag Generator

Generate an optimized Instagram hashtag set for the post described below.

## Brand Profile
{brand_profile}

## Post Details
- Theme: {theme}
- Format: {format}

## Instructions

Generate a hashtag set with exactly three tiers:
- **broad**: 8–12 tags — high-reach tags (millions of posts) related to the general topic
- **niche**: 12–16 tags — medium-reach tags (10K–500K posts) for targeted community reach  
- **branded**: 1–5 tags — the account's own branded hashtags (use from brand profile)

**Rules**:
1. Total count (broad + niche + branded) MUST NOT exceed 30
2. All hashtags must start with #
3. No spaces within a hashtag; use CamelCase or underscores for multi-word tags
4. Mix English and the brand's language tags when appropriate
5. Branded tags must match those in the brand profile

## Output format

Output ONLY a JSON object with this structure:
```json
{
  "broad": ["#tag1", "#tag2"],
  "niche": ["#tag3", "#tag4"],
  "branded": ["#brandtag"]
}
```

No explanation, no markdown fences, no other text.

Theme: {theme}
Format: {format}
