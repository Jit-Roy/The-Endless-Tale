from typing import List, Optional, Dict, Any, Tuple
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from data_models import CharacterPersona, Message, Character, CharacterMemory, CharacterState, TimelineEvent, Scene, Action, CharacterEntry, CharacterExit
from gemini_client import GenerativeModel
from helpers.response_parser import parse_json_response


class CharacterManager:
    """Manager for character-related operations."""
    
    def __init__(self):
        """Initialize CharacterManager.
        
        Each character gets its own dedicated GenerativeModel (one chat session)
        created lazily on first use, with the character's persona baked in as
        system_instruction — set once, never repeated in every prompt.
        """
        # One chat session per character, keyed by name. Created in _get_or_create_model().
        self._character_models: Dict[str, GenerativeModel] = {}

    def _get_or_create_model(self, character: Character) -> GenerativeModel:
        """Return the dedicated GenerativeModel for this character.

        Creates it on first call with:
        - system_instruction = full persona (traits, background, relationships, goals)
        - temperature / top_p   = character-specific values

        Each call to generate_content() on this model is stateless — no history
        is accumulated between turns. Context is passed explicitly via memory_context.
        """
        name = character.persona.name
        if name not in self._character_models:
            self._character_models[name] = GenerativeModel(
                system_instruction=self.build_persona_context(character),
                temperature=character.persona.temperature,
                top_p=character.persona.top_p,
            )
        return self._character_models[name]
    
    def create_character(
        self, 
        persona: CharacterPersona, 
        memory: Optional[CharacterMemory] = None,
        state: Optional[CharacterState] = None
    ) -> Character:
        """
        Create a new AI character instance.
        
        Args:
            persona: CharacterPersona defining the character
            memory: Optional character memory
            state: Optional character state
            
        Returns:
            New Character instance
        """
        if memory is None:
            memory = CharacterMemory(name=persona.name)
        if state is None:
            state = CharacterState(name=persona.name)
        
        return Character(persona=persona, memory=memory, state=state)
    
    def update_character_memory(
        self,
        character: Character,
        event: TimelineEvent
    ) -> None:
        """
        Update character's memory by adding timeline event.
        
        Args:
            character: The Character to update
            event: The TimelineEvent to add to memory
        """
            
        if event is not None:
            character.memory.event.append(event)
    
    def update_character_state(
        self,
        character: Character,
        current_objective: Optional[str] = None
    ) -> None:
        """
        Update character's current state (current objective).
        
        Args:
            character: The Character to update
            current_objective: Update character's current objective
        """
        if current_objective is not None:
            character.state.current_objective = current_objective
        
    
    def build_persona_context(self, character: Character) -> str:
        """Build the character's personality context including traits, relationships, goals, and knowledge."""
        relationships_str = "\n".join([
            f"- {char}: {rel}" 
            for char, rel in character.persona.relationships.items()
        ])
        
        context = f"""You are {character.persona.name}.
        YOUR PERSONALITY:
        - Traits: {', '.join(character.persona.traits)}
        - Speaking Style: {character.persona.speaking_style}
        - Background: {character.persona.background}
        YOUR RELATIONSHIPS:
        {relationships_str}"""
        
        # Add goals if available
        if character.persona.goals:
            goals_str = "\n".join([f"- {goal}" for goal in character.persona.goals])
            context += f"\n\nYOUR GOALS & MOTIVATIONS:\n{goals_str}"
        
        # Add knowledge base if available
        if character.persona.knowledge_base:
            knowledge_items = []
            for key, value in character.persona.knowledge_base.items():
                knowledge_items.append(f"- {key}: {value}")
            knowledge_str = "\n".join(knowledge_items)
            context += f"\n\nYOUR SPECIAL KNOWLEDGE:\n{knowledge_str}"
        
        return context
    
    def build_state_context(self, character: Character) -> str:
        """Build the character's current state context including and current objective."""
        if not character.state:
            return ""
        if character.state.current_objective:
            return f"\n- Current Objective: {character.state.current_objective}"
        return ""
    
    def build_memory_context(self, character: Character, last_n_messages: Optional[int] = None) -> str:
        """Build the memory context string with actions noted from character's perceived messages.
        
        Args:
            character: The Character whose memory to build context from
            last_n_messages: Optional number of recent messages to include. If None, includes all messages.
        
        Returns:
            Formatted memory context string
        """
        context_lines = []
        if character.memory and character.memory.event:
            events = character.memory.event
            if last_n_messages is not None:
                events = events[-last_n_messages:]
            
            for event in events:
                if isinstance(event, Message):
                    if event.character == character.persona.name:
                        # This character's own messages - frame as "You said"
                        prefix = "You"
                    else:
                        prefix = event.character
                    context_lines.append(f"{prefix}: *{event.action_description}* {event.dialouge}")
                elif isinstance(event, Scene):
                    context_lines.append(f"[Scene at {event.location}]: {event.description}")
                elif isinstance(event, Action):
                    if event.character == character.persona.name:
                        # This character's own action - frame as "You"
                        context_lines.append(f"You: *{event.description}*")
                    else:
                        context_lines.append(f"{event.character}: *{event.description}*")
                elif isinstance(event, CharacterEntry):
                    if event.character == character.persona.name:
                        context_lines.append(f"[You entered]: {event.description}")
                    else:
                        context_lines.append(f"[{event.character} entered]: {event.description}")
                elif isinstance(event, CharacterExit):
                    if event.character == character.persona.name:
                        context_lines.append(f"[You left]: {event.description}")
                    else:
                        context_lines.append(f"[{event.character} left]: {event.description}")
        
        return "\n".join(context_lines)
    
    def build_decision_prompt(
        self, 
        character: Character
    ) -> str:
        """
        Build the prompt for deciding whether to speak FROM THIS CHARACTER'S PERSPECTIVE.
        Each character sees the conversation through their own lens.
        
        Args:
            character: The AICharacter making the decision
            story_context: Optional story context to guide the narrative
            
        Returns:
            The complete prompt string 
        """ 

        # Persona is already in the model's system_instruction — don't repeat it here.
        state_context = self.build_state_context(character) or " None"
        memory_context = self.build_memory_context(character, last_n_messages=10)

        prompt = f"""CURRENT STATE:{state_context}
        WHAT YOU EXPERIENCED (your perspective): {memory_context}
        DECISION:
        Based on YOUR experiences, YOUR traits, and YOUR current state, decide how you want to respond right now.
        
        THREE OPTIONS:
        1. **SPEAK** - Respond with dialogue (and accompanying action)
        2. **ACT** - React physically/emotionally WITHOUT speaking (silent action)
        3. **SILENT** - Do nothing, stay quiet
        
        WHEN TO SPEAK (high priority):
        1. **Someone greets the group or asks how everyone is doing** - It's natural to respond as friends!
        2. **Someone reveals important/concerning information** - React with your authentic concern!
        3. **You're directly addressed or mentioned** - Respond naturally!
        4. **There's been awkward silence** - Someone should break it!
        5. **The topic is highly relevant to YOU** - Share your unique perspective!
        6. **Someone needs help or support** - Friends respond to friends!
        
        WHEN TO ACT (medium priority):
        - You want to react but words feel forced or unnecessary
        - Showing emotion through body language is more powerful than speaking
        - High tension moment where silence + action is more dramatic
        - You're uncomfortable/unsure and just want to show physical reaction
        - Someone said something shocking and you need a moment to process
        - Physical reaction conveys your feeling better than words would

        WHEN TO STAY SILENT (stay quiet):
        - You JUST spoke in the last message (let others respond first)
        - Someone else already said exactly what you'd say
        - You've made the same point 2-3+ times already (don't be repetitive!)
        - **If others already reacted to danger/concern, you don't need to pile on with the SAME reaction**
        - Someone clearly wants to end a topic and you'd just push it again
        - Another character is better suited to respond to this specific topic
        - The conversation doesn't involve you and you have nothing unique to add
        - **Multiple people already said similar things - don't be the third person saying the same thing**

        SPECIAL SITUATIONS:
        - **RESPECT BOUNDARIES**: If someone has stated their position, accept it or change approach
        - **REACT TO DANGER/CONCERN**: If friend mentions pain/danger/threat, respond with concern ONLY if you have something UNIQUE to add beyond what others said
        - **WITHDRAWAL CONTEXT**: If someone needs rest after revealing something serious, acknowledge both parts
        - **DON'T GANG UP**: If another character already made your exact point, DON'T repeat it - offer a DIFFERENT suggestion or stay quiet
        - **BE INDEPENDENT**: Have your own opinions - don't just echo what others said with slightly different words
        - **NATURAL FLOW**: Sometimes "Alright, if you say so" or changing subjects IS the right move
        - **CHECK WHAT OTHERS SAID**: Look at the last 2-3 messages. If they already covered your concern, you don't need to repeat it

        OUTPUT FORMAT (strict JSON):
        
        For "speak" type:
        {{
        "type": "speak",
        "priority": 0.0 to 1.0 (how urgent/important is your response),
        "reasoning": "brief explanation of your decision",
        "dialogue": "your actual spoken words here(25-70 words)",
        "action": "physical actions/body language accompanying speech. For example: 'smiles warmly', 'leans forward eagerly', 'frowns slightly', etc. in 15-20 words"
        }}
        
        For "act" type:
        {{
        "type": "act",
        "priority": 0.0 to 1.0,
        "reasoning": "brief explanation of your decision",
        "action": "silent physical action/reaction without speaking. For example 'crosses arms and looks away', 'paces to the window nervously', 'sits down heavily with a sigh', etc. in 15-20 words"
        }}
        
        For "silent" type:
        {{
        "type": "silent",
        "priority": 0.0,
        "reasoning": "brief explanation why you're staying quiet"
        }}

        IMPORTANT:
        - For "speak": Include dialogue (required) and action 
        - For "act": Only include action (no dialogue)
        - For "silent": Only type, priority, and reasoning

        **CRITICAL - ACTION VARIETY RULES (READ THIS CAREFULLY):**
        1. **CHECK THE CONVERSATION ABOVE** - Look at your previous messages. What actions did you ALREADY do?
        2. **NEVER REPEAT ACTIONS** - If you already "leaned forward", "sat back", "crossed arms", "looked at someone" - DON'T DO IT AGAIN
        3. **PHYSICAL CONSISTENCY** - If you already sat down or leaned back, you can't lean back AGAIN. Instead: stand up, walk somewhere, gesture differently, adjust position, look away, etc.
        4. **VARIETY IS MANDATORY** - Each of your actions MUST be different from all your previous actions in this conversation
        5. **EXAMPLES OF VARIETY**:
        - First message: "leans back against sofa"
        - Second message: "sits forward suddenly" or "stands up" or "runs hand through hair"
        - Third message: "paces to the window" or "fidgets with wand" or "slumps in chair"
        - NEVER: "leans back" again after already doing it!

        - Stay COMPLETELY IN CHARACTER with your unique speaking style
        - Don't repeat what others just said - add something NEW or DON'T SPEAK
        - Keep messages realistic for casual conversation
        - If you have nothing unique to add, choose "silent" type
        - Your personality should be OBVIOUS from how you speak and act
        - Don't sound like you're giving a lecture or writing an essay
        - Use natural dialogue, contractions, and emotion
        - Show, don't tell - use actions to convey personality
        - **INDEPENDENCE**: Have your own opinions - don't just support what others said
        - **BACKING OFF**: Sometimes "Alright, fair enough" or "Suit yourself" is the perfect response
        - **RESPECTING AUTONOMY**: If someone clearly doesn't want to talk about something, that's OKAY
        - **NATURAL FLOW**: Not every topic needs resolution. Sometimes you just move on.
        - **REACT TO DANGER/CONCERN**: If your friend mentions pain, danger, or a threat - REACT! Even if they want to sleep after.
        """
        return prompt
    
    def decide_turn_response(
        self, 
        character: Character
    ) -> Tuple[str, float, str, Optional[str], Optional[str]]:
        """
        Decide whether this character should speak, act silently, or stay silent.
        Each character uses different generation settings for unique voices.
        
        Args:
            character: The Character making the decision
            
        Returns:
            Tuple of (response_type, priority, reasoning, dialouge, action)
            - response_type: "speak", "act", or "silent"
            - priority: 0.0 to 1.0
            - reasoning: Explanation of decision
            - dialouge: For "speak" = dialogue, For "act" = action, For "silent" = None
            - action: For "speak" = body_language, For "act"/"silent" = None
        """
        
        try:
            # Build prompt from THIS character's perspective
            prompt = self.build_decision_prompt(character)
            
            # Use this character's dedicated session (temperature/top_p already set at creation)
            response = self._get_or_create_model(character).generate_content(prompt)
            
            # Parse JSON response
            decision_data = parse_json_response(response.text)
            
            response_type = decision_data.get("type", "silent").lower()
            priority = decision_data.get("priority", 0.0)
            reasoning = decision_data.get("reasoning", "No reasoning provided")
            
            # Extract dialogue based on response type
            if response_type == "speak":
                dialogue = decision_data.get("dialogue", None) 
                action = decision_data.get("action", None)  
            elif response_type == "act":
                dialogue = None  # No dialogue for silent action
                action = decision_data.get("action", None)  
            else:  # silent
                dialogue = None
                action = None
            
            return (
                response_type,
                priority,
                reasoning,
                dialogue,
                action
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            # If the LLM response cannot be parsed, fall back to silence.
            return (
                "silent",
                0.0,
                f"Unable to interpret response: {e}",
                None,
                None
            )
        except Exception as e:
            return (
                "silent",
                0.0,
                f"Error generating decision: {e}",
                None,
                None
            )
    
    def broadcast_event_to_characters(self, characters: List[Character], event: TimelineEvent) -> None:
        """
        Add a TimelineEvent to all characters' events.
        This simulates all characters hearing/experiencing the event.
        
        Args:
            characters: List of all characters present
            event: The event being broadcasted
        """
        for character in characters:
            self.update_character_memory(character, event=event)