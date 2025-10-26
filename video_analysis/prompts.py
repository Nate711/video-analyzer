#!/usr/bin/env python3
"""Different prompts for video analysis comparison"""

PROMPTS = {
    "original": """
Analyze this first person view video of someone doing a chore and break it down into distinct parts/segments.

The goal is to use the parts to extract clips showing key moments of the chore being done.

Note that the person may be using tools to manipulate objects. The pink and red tools are not butterfly knives but instead graspers.

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

Note that the person may be using tools to manipulate objects. The pink and red tools are not butterfly knives but instead graspers.

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

Note that the person may be using tools to manipulate objects. The pink and red tools are not butterfly knives but instead graspers.

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

Note that the person may be using tools to manipulate objects. The pink and red tools are not butterfly knives but instead graspers.

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
    "grasp_analysis": """
Analyze this first person view video focusing on how the person grasps and manipulates objects during the task.

If the person is using a tool to grasp something, describe how the tool grasps the object. Do not describe the person's hand if a tool is being used.

For each distinct grasp or manipulation, identify:

Grasp types to look for:
- Power grasp: Whole hand wrapped around object (e.g., gripping a handle, holding a bottle)
- Precision grasp: Using 2-3 fingers for fine control (e.g., pinching, picking small items)
- Palmar grasp: Object held against palm with fingers (e.g., holding a phone, flat object)
- Lateral/key grasp: Thumb pressing against side of index finger (e.g., holding a key, card)
- Hook grasp: Fingers curled to carry/hold (e.g., carrying a bag handle)
- Tip grasp: Using fingertips only (e.g., picking up small objects)
- Awkward/improper grasp: Unusual or inefficient grip that may indicate difficulty

For each segment where a grasp occurs or changes, provide:
- Start time (MM:SS format) - when grasp begins or changes
- End time (MM:SS format) - when grasp ends or changes again
- Activity name: "[Grasp Type] - [Object]" (e.g., "Precision Grasp - Lid", "Power Grasp - Bottle")
- Description: Brief description of what they're doing with this grasp and whether it appears effective or if they're struggling

Return ONLY a JSON array with this structure:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Grasp Type - Object",
    "description": "What they're doing with this grasp"
  }
]

No text before or after the JSON.
""",
    "volleyball": """
Analyze this volleyball game video and identify key plays and player actions.

For each significant play, segment the video to capture:

Player Actions to Identify:
- Serve: Player serving the ball to start a rally
- Spike/Hit: Player jumping and hitting the ball aggressively downward over the net
- Serve Receive: Player passing a served ball (often with platform/forearms)
- Dig: Player passing a spiked ball (defensive save, often low to ground)
- Set: Player using fingertips to set up a teammate for attack (usually overhead)
- Block: Player(s) jumping at net with hands up to block opponent's attack
- Free Ball: Player hitting ball over net without jumping (not a spike)

For each segment, identify:
- The player performing the action described by clothing (shirt and shorts color/style) and position like middle blocker, outside hitter, etc.
- The specific action being performed
- The outcome if visible (successful/unsuccessful, point scored, error, etc.)

Segment timing:
- Start a few seconds before the action begins (to show setup/approach)
- End a few seconds after completion (to show result)

For each play segment, provide:
- Start time (MM:SS format)
- End time (MM:SS format)
- Activity name: "[Player] - [Action]" (e.g., "Player #7 - Spike", "Back row - Dig", "Setter - Set")
- Description: Brief description of what happens (e.g., "Player attempts spike from right side, ball goes out", "Successful dig keeps rally alive")

Return ONLY a JSON array with this structure:
[
  {
    "start_time": "00:00",
    "end_time": "00:15",
    "activity": "Player - Action",
    "description": "What happens in this play"
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
