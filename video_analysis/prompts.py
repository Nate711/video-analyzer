#!/usr/bin/env python3
"""Different prompts for video analysis comparison"""

PROMPTS = {
    "original": """
Analyze this first person view video of someone doing a chore and break it down into distinct parts/segments.

The goal is to use the parts to extract clips showing key moments of the chore being done.

Key points of interest:
- User has difficulty using the tool
- User makes progress e.g. opening a door, picking a piece of clothing, opening a lid, etc

For each segment, provide:
- Start time (MM:SS format)
- End time (MM:SS format)
- Brief activity name (2-5 words)
- Short description (1 sentence)

Return ONLY a JSON array with this structure:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Activity Name",
    "description": "What happens in this segment"
  }
]

No text before or after the JSON.
""",
    "detailed": """
Analyze this first person view video of someone performing a chore. Identify and segment key moments with precise timing.

Focus on these critical moments:
- Initial setup or preparation
- Struggles or difficulties (fumbling, multiple attempts, confusion)
- Successful progress milestones (opening, closing, picking up, putting down)
- Tool usage (correct or incorrect)
- Completion of sub-tasks

For each distinct segment, provide:
- Start time (MM:SS format)
- End time (MM:SS format)
- Brief activity name (2-5 words max)
- Detailed description explaining what happens and why it's significant

Return ONLY a JSON array with this exact structure:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Activity Name",
    "description": "What happens in this segment"
  }
]

No text before or after the JSON.
""",
    "minimal": """
Break down this video into segments showing key actions and moments.

For each segment provide start time (MM:SS), end time (MM:SS), activity name, and brief description.

Return ONLY valid JSON array format:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Activity Name",
    "description": "What happens"
  }
]
""",
    "struggles_focused": """
Analyze this first person video and identify segments where the person:
1. Struggles or has difficulty with a task
2. Makes meaningful progress or achieves a goal
3. Uses tools or objects (successfully or unsuccessfully)

Segment the video to capture these key moments with context (a few seconds before and after).

For each segment, provide:
- Start time (MM:SS format)
- End time (MM:SS format)
- Activity name (2-5 words)
- Description (1 sentence explaining what happens)

Return ONLY a JSON array:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Activity Name",
    "description": "What happens in this segment"
  }
]

No text before or after the JSON.
""",
    "milestone_based": """
Analyze this video and identify milestone moments where something changes or progresses.

Milestones include:
- Starting a new sub-task
- Successfully completing an action (opening, closing, moving, placing)
- Encountering obstacles or challenges
- Achieving a goal or making visible progress

For each milestone segment, provide:
- Start time (MM:SS format) - begin a few seconds before the milestone
- End time (MM:SS format) - end a few seconds after
- Activity name (2-5 words describing the milestone)
- Description (1 sentence)

Return ONLY a JSON array with this structure:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Activity Name",
    "description": "What happens in this segment"
  }
]

No text before or after the JSON.
""",
}


def get_prompt(name: str) -> str:
    """Get a prompt by name

    Args:
        name: Name of the prompt

    Returns:
        Prompt string

    Raises:
        KeyError: If prompt name doesn't exist
    """
    return PROMPTS[name]


def list_prompts() -> list[str]:
    """Get list of available prompt names

    Returns:
        List of prompt names
    """
    return list(PROMPTS.keys())
