import re
import time
import asyncio
from groq import Groq
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from core.config_manager import config
from core.types import RequestComplexity
from core.ui import console
from core.database import log_conversation, add_memory, search_memories, get_recent_conversations, get_all_skills
from tools.schedule import load_schedule, save_schedule
from tools.skill_manager import register_skill, execute_skill

# Initialize Groq / Local LLM Client dynamically
client_args = {"api_key": config.GROQ_API_KEY.strip()}
if getattr(config, "GROQ_BASE_URL", None):
    client_args["base_url"] = config.GROQ_BASE_URL.strip()
client = Groq(**client_args)
messages = [{"role": "system", "content": config.SYSTEM_PROMPT}]

from core.text_utils import clean_display_text


async def get_jarvis_response(user_input: str, request_complexity: RequestComplexity, depth: int = 0) -> str:
    """
    Get response from Groq LLM with persistent SQLite database memory and dynamic skills.
    Spawns speech feedback as soon as text is generated.
    """
    from audio.music_player import play_music_task, stop_music
    from audio.tts import speak_jarvis
    from tools.dashboard_manager import show_dashboard, hide_dashboard
    from tools.space_dashboard_manager import show_space_dashboard, hide_space_dashboard

    # Log user input to DB (if not a system/internal callback)
    if not user_input.startswith("[SYSTEM:"):
        log_conversation("user", user_input)

    # Search for matching memories in SQLite
    matched_memories = search_memories(user_input, limit=3)
    memory_context = ""
    if matched_memories:
        memory_context = "\n\nRECALLED MEMORIES (Use this context if relevant to the request):\n"
        for category, content in matched_memories:
            memory_context += f"- [{category}]: {content}\n"

    # Dynamic Schedule Routing: Only load/inject schedule context if user request is schedule-related.
    is_sched_related = any(kw in user_input.lower() for kw in [
        "schedule", "exam", "date", "calendar", "todo", "time", "plan", 
        "appointment", "meeting", "day", "week", "tomorrow", "today", 
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "|", "update", "routine", "class", "event"
    ])
    
    if is_sched_related:
        sched = load_schedule()
    else:
        sched = "[Schedule not loaded - Request does not require schedule access]"
        
    current_time_str = time.strftime("%A, %Y-%m-%d %H:%M:%S")
    
    # Add context about request complexity to system prompt
    complexity_hint = ""
    if request_complexity == RequestComplexity.CLARIFICATION:
        complexity_hint = "\n[User's request needs clarification - ask 1-2 specific questions]"
    elif request_complexity == RequestComplexity.TUTORIAL:
        complexity_hint = "\n[User wants step-by-step guidance - ask if ready to proceed]"
    elif request_complexity == RequestComplexity.SIMPLE:
        complexity_hint = "\n[User wants a direct answer - provide complete response without questions]"

    # Advanced J.A.R.V.I.S. features prompt injection
    features_prompt = """
    
ADDITIONAL CAPABILITIES:
1. LONG-TERM MEMORY: You can store permanent memories for the user. If the user tells you to remember something, you MUST include: [[ADD_MEMORY: <category> | <fact to remember>]].
2. DYNAMIC SKILL COMPILATION: If the user asks for a capability or custom feature you do NOT have in REGISTERED SKILLS, DO NOT automatically generate it or write a python script. Instead, you MUST ask the user for permission first (e.g., "I don't have that capability registered, sir. Would you like me to try generating a custom skill for this?"). ONLY if the user explicitly gives permission in a subsequent turn (e.g., "Yes, go ahead" or "Yes, do it"), you should write the python script using the exact tag: [[GENERATE_SKILL: <name> | <description> | <complete python code>]]. The python code should define a `def run():` function returning a string. IMPORTANT: The python code MUST use ONLY Python's built-in standard libraries (e.g., urllib.request, json, subprocess, os, datetime, math, re). NEVER use or import third-party packages.
3. SKILL EXECUTION: You can run a previously generated skill by outputting: [[EXECUTE_SKILL: <name>]].
4. SIDEBAR DASHBOARD: If the user asks to open/show the weather/time/schedule dashboard, you MUST include: [[SHOW_DASHBOARD]]. If the user asks to close/hide it, include: [[HIDE_DASHBOARD]]. If the user asks to open/show the space/satellite/orbit tracker dashboard, you MUST include: [[SHOW_SPACE_DASHBOARD]]. If they ask to close/hide it, include: [[HIDE_SPACE_DASHBOARD]].
"""

    # Fetch registered skills dynamically
    skills_list = get_all_skills()
    skills_context = ""
    if skills_list:
        skills_context = (
            "\nREGISTERED SKILLS:\n"
            "If the user asks for information that can be answered or retrieved by any of these skills, you MUST immediately call them using [[EXECUTE_SKILL: <name>]] in your response. "
            "DO NOT ask for permission first, and do not explain that you are running it - just execute it immediately. "
            "IMPORTANT: The tag MUST contain ONLY the exact name of the registered skill as listed (e.g. [[EXECUTE_SKILL: get_weather]]). DO NOT append any arguments, parameters, colons or pipes inside the tag (e.g. do NOT output [[EXECUTE_SKILL: get_weather|Badulla]]). The skill will automatically parse the user query to find the location.\n"
        )
        for name, desc in skills_list:
            skills_context += f"- {name}: {desc}\n"

    current_system = (
        config.SYSTEM_PROMPT
        + features_prompt
        + skills_context
        + f"\nCurrent Date & Time: {current_time_str}\nSchedule: {sched}"
        + complexity_hint
        + memory_context
    )

    # Dynamically build messages chain from recent 6 items in DB to maintain session context
    recent_logs = get_recent_conversations(limit=6)
    messages_chain = [{"role": "system", "content": current_system}]
    for role, content in recent_logs:
        messages_chain.append({"role": role, "content": content})

    # If the user input was not logged, we still append it to the active chain
    if user_input.startswith("[SYSTEM:") and (not messages_chain or messages_chain[-1]["content"] != user_input):
        messages_chain.append({"role": "user", "content": user_input})

    response_text = ""
    try:
        is_ollama_local = False
        if getattr(config, "GROQ_BASE_URL", None) and "11434" in config.GROQ_BASE_URL:
            is_ollama_local = True

        if is_ollama_local:
            import json
            import urllib.request
            
            # Inject prompt reminder to help smaller local models trigger the action tags reliably
            local_messages = [msg.copy() for msg in messages_chain]
            if local_messages and local_messages[-1]["role"] == "user":
                local_messages[-1]["content"] += "\n(Remember: if asked to open/show/hide the weather/time/schedule dashboard, you MUST include [[SHOW_DASHBOARD]] or [[HIDE_DASHBOARD]] in your response. Output the tags exactly as specified.)"
                
            url = "http://localhost:11434/api/chat"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": config.LLM_MODEL,
                "messages": local_messages,
                "stream": True
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
            
            with Live(console=console, refresh_per_second=12) as live:
                with urllib.request.urlopen(req, timeout=120) as response:
                    for line in response:
                        if line:
                            chunk = json.loads(line.decode("utf-8"))
                            delta = chunk.get("message", {}).get("content", "")
                            response_text += delta
                            display_text = clean_display_text(response_text)
                            live.update(Panel(Markdown(display_text), title="Jarvis", border_style="cyan"))
        else:
            completion = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages_chain,
                stream=True,
                max_tokens=1024,
            )

            with Live(console=console, refresh_per_second=12) as live:
                for chunk in completion:
                    if chunk.choices[0].delta.content:
                        delta = chunk.choices[0].delta.content
                        response_text += delta
                        display_text = clean_display_text(response_text)
                        live.update(Panel(Markdown(display_text), title="Jarvis", border_style="cyan"))

        # Log assistant response to DB
        log_conversation("assistant", response_text)

        if "[IGNORE]" in response_text or "[SKIP]" in response_text:
            return response_text

        # Speak intermediate/conversational intro immediately before carrying out tasks
        display_text = clean_display_text(response_text)
        
        if display_text:
            await speak_jarvis(display_text)

        # Process internal tags
        # 1. Schedule update
        match_sched = re.search(r"\[\[UPDATE_SCHEDULE:(.*?)\]\]", response_text, re.DOTALL)
        if match_sched:
            new_schedule = match_sched.group(1).strip()
            save_schedule(new_schedule)

        # 2. Play music (non-blocking)
        match_play = re.search(r"\[\[PLAY_MUSIC:(.*?)\]\]", response_text)
        if match_play:
            query = match_play.group(1).strip()
            asyncio.create_task(play_music_task(query))

        # 3. Stop music
        if "[[STOP_MUSIC]]" in response_text:
            stop_music()

        # 4. Add Memory
        match_mem = re.search(r"\[\[ADD_MEMORY:(.*?)\|(.*?)\]\]", response_text, re.DOTALL)
        if match_mem:
            category = match_mem.group(1).strip()
            content = match_mem.group(2).strip()
            add_memory(category, content)
            console.print(f"[bold green]System:[/] Saved memory to category [{category}]")

        # 5. Generate Skill
        match_skill = re.search(r"\[\[GENERATE_SKILL:(.*?)\|(.*?)\|(.*?)\]\]", response_text, re.DOTALL)
        if match_skill:
            name = match_skill.group(1).strip()
            description = match_skill.group(2).strip()
            code = match_skill.group(3).strip()
            code = re.sub(r"^```python\s*", "", code)
            code = re.sub(r"\s*```$", "", code)
            register_skill(name, description, code)
            await speak_jarvis(f"Sir, I have successfully compiled the skill '{name}'.")

        # 5a. Show / Hide Dashboard
        if "[[SHOW_DASHBOARD]]" in response_text:
            show_dashboard()
            
        if "[[HIDE_DASHBOARD]]" in response_text:
            hide_dashboard()

        if "[[SHOW_SPACE_DASHBOARD]]" in response_text:
            show_space_dashboard()

        if "[[HIDE_SPACE_DASHBOARD]]" in response_text:
            hide_space_dashboard()

        # 6. Execute Skill (depth check to allow up to 4 retries for self-healing)
        match_exec = re.search(r"\[\[EXECUTE_SKILL:(.*?)\]\]", response_text)
        if match_exec and depth < 4:
            skill_name = match_exec.group(1).strip()
            
            # Check if user has interrupted with a new text/voice query in the middle of execution
            from main import input_queue
            from audio.stt import transcribe_audio
            if not input_queue.empty():
                input_type, data = input_queue.get_nowait()
                user_msg = ""
                if input_type == "text":
                    user_msg = data
                elif input_type == "voice":
                    with console.status("[yellow]Processing voice interrupt...[/]"):
                        user_msg = transcribe_audio(data) or ""
                
                if user_msg.strip():
                    console.print(f"[bold red]System:[/] Task interrupted by user input: '{user_msg}'")
                    if any(word in user_msg.lower() for word in ["stop", "cancel", "no", "exit", "halt"]):
                        await speak_jarvis("Understood sir, aborting the current task.")
                        return "[Task Aborted]"
                    else:
                        await speak_jarvis("Aborting the current task to address your new request, sir.")
                        # Reset depth to 0 and process the new query
                        return await get_jarvis_response(user_msg, request_complexity, depth=0)
            console.print(f"[bold cyan]System:[/] Executing skill: {skill_name}")
            
            result = await asyncio.to_thread(execute_skill, skill_name)
            console.print(f"[bold cyan]System:[/] Execution Output: {result}")
            
            if "Error" in result:
                # Check for interruption again before self-healing loop retries
                if not input_queue.empty():
                    input_type, data = input_queue.get_nowait()
                    user_msg = ""
                    if input_type == "text":
                        user_msg = data
                    elif input_type == "voice":
                        with console.status("[yellow]Processing voice interrupt...[/]"):
                            user_msg = transcribe_audio(data) or ""
                    if user_msg.strip():
                        console.print(f"[bold red]System:[/] Task interrupted by user input: '{user_msg}'")
                        if any(word in user_msg.lower() for word in ["stop", "cancel", "no", "exit", "halt"]):
                            await speak_jarvis("Understood sir, aborting the current task.")
                            return "[Task Aborted]"
                        else:
                            await speak_jarvis("Aborting the current task to address your new request, sir.")
                            return await get_jarvis_response(user_msg, request_complexity, depth=0)

                console.print(f"[bold red]System:[/] Self-healing triggered.")
                await speak_jarvis("Sir, the execution failed with an error. I am rewriting the code to self-heal and try again.")
                follow_up_prompt = (
                    f"[SYSTEM: Skill '{skill_name}' execution failed with: {result}. "
                    "Please analyze this error, rewrite the skill code to fix the bug using the "
                    "[[GENERATE_SKILL: ...]] tag, and run it again using [[EXECUTE_SKILL: ...]]. "
                    "You must succeed. Do not give up.]"
                )
            else:
                follow_up_prompt = f"[SYSTEM: Skill '{skill_name}' execution completed. Output: {result}]"
            return await get_jarvis_response(follow_up_prompt, request_complexity, depth + 1)

        return response_text
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_msg = f"Sir, I encountered an internal error: {e}"
        console.print(f"[bold red]LLM Error:[/] {e}")
        return error_msg
