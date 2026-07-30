import argparse
import re
import sys
import time
import json
import logging
import subprocess
import os
import threading
import queue
import uuid
import yaml
from pathlib import Path
from openai import OpenAI
import tiktoken
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)

MODEL_MAX_TOKENS = 32000
TIMEOUT = 600
MAX_ITER = 30
WORK_DIR = "/Workspace"
ACTIVITY_LOG_DIR = "/Workspace/logs"
DEFAULT_MAX_TOKENS = 4096
MODEL_CONFIGS = {}
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ReactAgentSystem")

def call_model(
    model_name: str,
    messages: List[Dict[str, str]],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    ) -> str:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return _call_model_once(model_name, messages)

        except Exception as e:
            last_error = e
            logging.error(
            f"Model call failed (attempt {attempt}/{max_retries}): {e}"
            )

            if attempt < max_retries:
                wait_time = backoff_factor ** (attempt - 1)
                logging.info(f"Retrying after {wait_time:.1f}s ...")
                time.sleep(wait_time)

    raise RuntimeError(
    f"All retries failed for model '{model_name}': {last_error}"
    )


def _call_model_once(
    model_name: str,
    messages: List[Dict[str, str]],
) -> str:

    cfg = MODEL_CONFIGS.get(model_name, {})
    api_key = cfg.get("api_key") or os.getenv("API_KEY") or ""
    base_url = (cfg.get("base_url") or os.getenv("BASE_URL") or "http://localhost:8000/v1")

    if model_name == "gpt-5.2-high":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            max_completion_tokens=DEFAULT_MAX_TOKENS,
            reasoning_effort="high",
        )
        return completion.choices[0].message.content

    elif model_name == "gpt-5.2-low":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
            model="gpt-5.2",
            messages=messages,
            max_completion_tokens=DEFAULT_MAX_TOKENS,
            reasoning_effort="low",
        )
        return completion.choices[0].message.content
    elif model_name == "Meta-Llama-3-3-70B-Instruct":
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        return completion.choices[0].message.content
    elif model_name.startswith("claude-sonnet"):
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key, base_url=base_url)
        max_tokens = DEFAULT_MAX_TOKENS
        system_prompt = None#############
        filtered_messages = []
        for m in messages:
            if m.get("role") == "system" and system_prompt is None:
                system_prompt = m.get("content", "")
            else:
                filtered_messages.append(m)
        kwargs = {
        "model": model_name,
        "messages": filtered_messages,
        "max_tokens": max_tokens,
        }
        if system_prompt:
            kwargs["system"] = system_prompt##############
        # kwargs = {
        #     "model": model_name,
        #     "messages": messages,
        #     "max_tokens": max_tokens,
        # }
        if model_name.endswith("thinking"):
            budget = max(1024, min(2048, max_tokens))
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": budget,
            }
        response = client.messages.create(**kwargs)
        texts = []
        for block in response.content:
            if block.type == "text":
                texts.append(block.text)

        return "".join(texts)
    elif model_name.startswith("gemini-"):
        from google import genai
        from google.genai import types

        client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            base_url=base_url,
            api_version="v1beta",
        ),
        vertexai=False,
        )

        thinking_level = "high" if model_name.endswith("high") else "low"
        role_map = {
        "user": "user",
        "assistant": "model",
        "system": "user",
        }

        contents = []
        for m in messages:
            role = role_map.get(m["role"], "user")
            contents.append(
                types.Content(
                role=role,
                parts=[{"text": m["content"]}]
            )
        )
        response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            max_output_tokens=DEFAULT_MAX_TOKENS,
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level
            ),
        ),
        )
        texts = []
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    texts.append(part.text)

        return "".join(texts)
    else:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        STREAM_MODELS = {
            "qwen3.5-27b",
            "qwen3.5-35b-a3b",
            "qwen3.5-122b-a10b",
            "qwen3.5-397b-a17b",
            "qwen3.5-35b-a3b-wo-thinking",
            "qwen3.5-122b-a10b-wo-thinking",
            "qwen3.5-397b-a17b-wo-thinking",
            "qwen3-8b",
            "qwen3-14b",
            "qwen3-32b",
            "deepseek-v3.2",
            "glm-4.7",
            "kimi-k2.5",
        }

        if model_name in STREAM_MODELS:
            enable_thinking = not model_name.endswith("-wo-thinking")
            completion = client.chat.completions.create(
                model=model_name.replace("-wo-thinking", ""),
                messages=messages,
                max_tokens=DEFAULT_MAX_TOKENS,
                extra_body={"enable_thinking": enable_thinking},
                stream=True,
            )

            reasoning_parts = []
            answer_parts = []

            for chunk in completion:
                delta = chunk.choices[0].delta

                if hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning_parts.append(delta.reasoning_content)

                if hasattr(delta, "content") and delta.content:
                    answer_parts.append(delta.content)

            return "".join(answer_parts)

        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=DEFAULT_MAX_TOKENS,
        )
        return completion.choices[0].message.content
class VLLMAdapter:
    def __init__(self, model_cfg: dict):
        self.cfg = model_cfg

    def _generate(self, messages: List[Dict[str, str]], stop: Optional[List[str]] = None, **kwargs) -> str:
        content = call_model(
        model_name=self.cfg["name"],
        messages=messages,
        )

        return content
    
    def _log_activity(self, content: str):
        try:
            os.makedirs(ACTIVITY_LOG_DIR, exist_ok=True)
            with open(os.path.join(ACTIVITY_LOG_DIR, "agent_activities.txt"), "a", encoding="utf-8") as log_file:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file.write(f"[{timestamp}] {content}\n")
        except Exception as e:
            logger.error(f"fail to log activity: {str(e)}")

class TerminalManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.log_file = ACTIVITY_LOG_DIR + "/terminal_log.json"
        self.init_log()
        
    def init_log(self):
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                json.dump({
                    "start_time": datetime.now().isoformat(),
                    "sessions": {}
                }, f)
    
    def log_session(self, session_id: str, action: str, details: dict = None):
        with open(self.log_file, 'r+') as f:
            log_data = json.load(f)
            if session_id not in log_data["sessions"]:
                log_data["sessions"][session_id] = {
                    "created": datetime.now().isoformat(),
                    "updates": []
                }
            log_data["sessions"][session_id]["updates"].append({
                "time": datetime.now().isoformat(),
                "action": action,
                "details": details or {}
            })
            f.seek(0)
            json.dump(log_data, f, indent=2)
            f.truncate()
    
    def create_session(self, session_id: str = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
        if session_id in self.sessions:
            return session_id
        self.sessions[session_id] = {
            "status": "idle",
            "last_command": None,
            "output": "",
            "process": None,
            "log_file": ACTIVITY_LOG_DIR + f"/terminal_{session_id}.log",
            "created": datetime.now().isoformat(),
            "error_queue": queue.Queue(), 
            "output_queue": queue.Queue(), 
        }
        with open(self.sessions[session_id]["log_file"], 'w') as f:
            f.write(f"Terminal Session {session_id} started at {datetime.now()}\n")
        self.log_session(session_id, "created")
        return session_id
    
    def _run_long_command(self, session_id: str, command: str):
        session = self.sessions[session_id]
        
        try:
            process = subprocess.Popen(
                command,cwd=WORK_DIR,shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,bufsize=1,universal_newlines=True
            )
            session["process"] = process
            
            time.sleep(0.5)  
            returncode = process.poll()
            
            if returncode is not None and returncode != 0:
                stdout, stderr = process.communicate()
                error_output = stderr.strip() if stderr else stdout.strip()
                if not error_output:
                    error_output = f"process exit with code: {returncode}"
                
                session["error_queue"].put(error_output)
                session["status"] = "error"
                session["error"] = error_output
                session["end_time"] = datetime.now().isoformat()
                
                with open(session["log_file"], 'a') as f:
                    f.write(f"Command failed: {error_output}\n")
                
                self.log_session(session_id, "command_failed", {
                    "command": command,
                    "exit_code": returncode,
                    "error": error_output
                })
                return
            
            session["status"] = "executing"
            
            def read_output(stream, is_stderr=False):
                try:
                    for line in iter(stream.readline, ''):
                        if line:
                            session["output_queue"].put({
                                "type": "stderr" if is_stderr else "stdout",
                                "content": line,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            with open(session["log_file"], 'a') as log:
                                prefix = "[ERROR] " if is_stderr else ""
                                log.write(f"{prefix}{line}")
                            
                            session["output"] += line
                except Exception as e:
                    session["error_queue"].put(f"read output error: {str(e)}")
            
            stdout_thread = threading.Thread(
                target=read_output, 
                args=(process.stdout, False),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_output, 
                args=(process.stderr, True),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            process.wait()
            
            session["status"] = "completed" if process.returncode == 0 else "error"
            session["end_time"] = datetime.now().isoformat()
            session["exit_code"] = process.returncode
            
            if process.returncode != 0:
                session["error_queue"].put(f"process exit with code: {process.returncode}")
            
            self.log_session(session_id, "command_completed", {
                "command": command,
                "exit_code": process.returncode
            })
            
        except Exception as e:
            error_msg = f"run command error: {str(e)}"
            session["error_queue"].put(error_msg)
            session["status"] = "error"
            session["error"] = error_msg
            session["end_time"] = datetime.now().isoformat()
            
            with open(session["log_file"], 'a') as f:
                f.write(f"run command error: {error_msg}\n")
            
            self.log_session(session_id, "command_error", {
                "command": command,
                "error": error_msg
            })
    
    def execute_command(self, session_id: str, command: str, command_type: str = "one_time") -> str:
        if session_id not in self.sessions:
            self.create_session(session_id)
        session = self.sessions[session_id]
        safety_check = self._check_command_safety(command)
        if safety_check != "safe":
            self.log_session(session_id, "command_rejected", {
                "command": command,
                "reason": safety_check
            })
            # print("ok9")
            return f"command rejected: {safety_check}"
        
        session["status"] = "executing"
        session["last_command"] = command
        session["command_type"] = command_type
        session["start_time"] = datetime.now().isoformat()
        session["output"] = ""  
        
        while not session["error_queue"].empty():
            session["error_queue"].get()
        while not session["output_queue"].empty():
            session["output_queue"].get()
        
        with open(session["log_file"], 'a') as f:
            f.write(f"\n[{datetime.now()}] $ {command}\n")
        try:
            if command_type == "long_running":
                thread = threading.Thread(
                    target=self._run_long_command, 
                    args=(session_id, command),
                    daemon=True
                )
                thread.start()
                
                
                time.sleep(1)
                
                if not session["error_queue"].empty():
                    error_msg = session["error_queue"].get()
                    session["status"] = "error"
                    session["error"] = error_msg
                    session["end_time"] = datetime.now().isoformat()
                    
                    self.log_session(session_id, "command_failed", {
                        "command": command,
                        "error": error_msg
                    })
                    
                    return f"command rejected: {error_msg}"
                else:
                    if session.get("process") and session["process"].poll() is not None:
                        returncode = session["process"].returncode
                        if returncode != 0:
                            error_msg = f"process exit with code: {returncode}"
                            session["status"] = "error"
                            session["error"] = error_msg
                            session["end_time"] = datetime.now().isoformat()
                            
                            self.log_session(session_id, "command_failed", {
                                "command": command,
                                "exit_code": returncode
                            })
                            
                            return f"command failed: {error_msg}"
                
                self.log_session(session_id, "command_started", {
                    "command": command,
                    "type": command_type
                })
                
                return f"Command executed successfully! (Running in background,terminal_id: {session_id})"
            
            else:
                result = subprocess.run(
                    command,
                    cwd=WORK_DIR,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT
                )
                
                stdout_text = result.stdout.strip()
                stderr_text = result.stderr.strip()
                if stdout_text:
                    output = f"{Fore.GREEN}{stdout_text}{Style.RESET_ALL}"
                    with open(session["log_file"], 'a') as f:
                        f.write(stdout_text + "\n")
                else:
                    output = ""

                if stderr_text:
                    with open(session["log_file"], 'a') as f:
                        f.write("Error: " + stderr_text + "\n")
                    output += f"\n{Fore.RED}{Style.BRIGHT}Error:{stderr_text}{Style.RESET_ALL}"

                if not output:
                    with open(session["log_file"], 'a') as f:
                        f.write(" One-time command executed successfully.\n")
                    output = f"{Fore.GREEN}{Style.BRIGHT} One-time command executed successfully.{Style.RESET_ALL}"
                
                session["output"] = output
                session["status"] = "completed" if result.returncode == 0 else "error"
                session["end_time"] = datetime.now().isoformat()
                
                if result.returncode != 0:
                    session["error"] = output
                
                self.log_session(session_id, "command_completed", {
                    "command": command,
                    "exit_code": result.returncode
                })
                
                return output
        
        except subprocess.TimeoutExpired:
            session["status"] = "timeout"
            session["end_time"] = datetime.now().isoformat()
            self.log_session(session_id, "command_timeout", {"command": command})
            return "error: one_time command timeout"
        
        except Exception as e:
            session["status"] = "error"
            session["error"] = str(e)
            session["end_time"] = datetime.now().isoformat()
            self.log_session(session_id, "command_error", {
                "command": command,
                "error": str(e)
            })
            return f"error: {str(e)}"
    
    def get_session_status(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            return {"error": f"session {session_id} not found"}
        
        session = self.sessions[session_id]
        
        latest_error = None
        if not session["error_queue"].empty():
            latest_error = session["error_queue"].get()
            session["error"] = latest_error
            if session["status"] == "executing":
                session["status"] = "error"
                session["end_time"] = datetime.now().isoformat()
        
        status_info = {
            "session_id": session_id,
            "status": session["status"],
            "last_command": session.get("last_command"),
            "command_type": session.get("command_type"),
            "start_time": session.get("start_time"),
            "end_time": session.get("end_time"),
            "log_file": session["log_file"]
        }
        
        if latest_error:
            status_info["latest_error"] = latest_error
        
        if session.get("exit_code") is not None:
            status_info["exit_code"] = session["exit_code"]
        
        return status_info
    
    def get_session_output(self, session_id: str, tail_lines: int = 20) -> str:
        if session_id not in self.sessions:
            return f"error: session {session_id} not found"
        
        session = self.sessions[session_id]
        
        new_output = ""
        while not session["output_queue"].empty():
            output_item = session["output_queue"].get()
            new_output += output_item["content"]
        
        if new_output:
            with open(session["log_file"], 'a') as f:
                f.write(new_output)
            session["output"] += new_output
        
        log_file = session["log_file"]
        
        try:
            if tail_lines > 0:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    return ''.join(lines[-tail_lines:])
            else:
                with open(log_file, 'r') as f:
                    return f.read()
        except Exception as e:
            return f"error: read log file {log_file} failed: {str(e)}"
    
    def terminate_session(self, session_id: str) -> str:
        """terminate session"""
        if session_id not in self.sessions:
            return f"error: session {session_id} not found"
        
        session = self.sessions[session_id]
        
        if session["status"] == "executing" and session.get("process"):
            try:
                if os.name == 'nt':  # Windows
                    subprocess.run(
                        f'taskkill /F /T /PID {session["process"].pid}',
                        cwd=WORK_DIR,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:  # Linux/macOS
                    session["process"].terminate()
                    try:
                        session["process"].wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        session["process"].kill()
                
                session["status"] = "terminated"
                session["end_time"] = datetime.now().isoformat()
                self.log_session(session_id, "terminated")
                return f"session {session_id} terminated"
            except Exception as e:
                session["status"] = "termination_failed"
                self.log_session(session_id, "termination_failed", {"error": str(e)})
                return f"error: terminate session {session_id} failed: {str(e)}"
        else:
            return f"session {session_id} not executing command"
    
    def _check_command_safety(self, command: str) -> str:
        DANGEROUS_COMMANDS = [
            "rm", "del", "erase", "rd", "rmdir", "shred", "wipe",
            "shutdown", "reboot", "halt", "poweroff", "init", "kill",
            "format", "mkfs", "dd", "fdisk", "parted",
            # "iptables", "route",
            "taskkill", "pkill", "killall"
            # "mv", "move", "rename"
        ]
        
        DANGEROUS_PATTERNS = [
            # r"/(root|etc|usr|sbin|boot|dev|proc|sys|windows)",  
        ]
        
        command_lower = command.lower()
        for dangerous_cmd in DANGEROUS_COMMANDS:
            if command_lower.startswith(dangerous_cmd) or f" {dangerous_cmd} " in command_lower:
                return f"error: command contains dangerous operation '{dangerous_cmd}'"
        
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, command_lower):
                return f"error: command contains dangerous pattern '{pattern}'"
        
        return "safe"
terminal_manager = TerminalManager()

system_prompt = """You are a agent having command line tools to complete the task BY YOURSELF. You MUST take actions step by step. Each action must be a single step using only one tool.
You have access to the following tools:
["terminal_execute", "terminal_status", "terminate_output"]
Your current working directory is """+ WORK_DIR +""".

When you use a tool, you MUST follow format1.
format1:
Analysis: Assessment and analysis of the current status and current goal
Gaps: The gap and challenges between current status and current goal
Plan: The next 3 steps to be taken
Action name: the action to take, should be one of ["terminal_execute", "terminal_status", "terminate_output"]
Action Input: {"terminal_id": "1", "command": "ls", "command_type": "one_time" or "long_running"}

When you have actually finished your task, you only output Final Answer in format2 in time.
format2:
Final Answer: your final answer to the user.

DO NOT assume any Action Result of any action. DO NOT output Action and Final Answer or Observation at the same time.
Never give up until you finish the task.
"""
# Actively think and percieve the current status before take action.
class ReactAgentSystem:
    def __init__(self, model_name: str):
        # self.model_cfg = load_model_config(model_name)
        self.model_cfg = {"name": model_name}
        self.llm = VLLMAdapter(self.model_cfg)

    def _clean_think_tags(self, text: str) -> str:
        if not text:
            return text
        cleaned = re.sub(r"<think>.*?</think>","",text,flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
        if cleaned != text:
            logger.debug("🧹 Cleaned <think> content")
        return cleaned
    # -------------------------------------------------------------------
    def invoke(self, user_input: str) -> str:
        # return model_response str
        user_input_windowed = self.windowed_input(user_input)
        logger.info(f"User Input: {user_input_windowed[0:input_len]}")
        self.llm._log_activity(f"User Input: {user_input_windowed}")
        message = []
        system_message = {"role": "system", "content": system_prompt}
        message.append(system_message)
        user_message = {"role": "user", "content": user_input_windowed}
        message.append(user_message)
        try:
            response_content = self.llm._generate(message)
            # response_content:str
            self.llm._log_activity(f"model_response: {response_content}")
            cleaned_response = self._clean_think_tags(response_content)
            return cleaned_response
        except Exception as e:
            error_msg = f"response_error: {str(e)}"
            logger.error(error_msg)
            self.llm._log_activity(f"response_error: {str(e)}")
            return "request_error"

    def before_parse_response(self, cleaned_string:str)->str:
        final_answer_count = len(re.findall(r'\bFinal Answer:\b', cleaned_string))
        action_name_count = len(re.findall(r'\bAction name\b', cleaned_string))
        action_input_count = len(re.findall(r'\bAction Input\b', cleaned_string))
        if (final_answer_count > 1 or action_name_count > 1 or action_input_count > 1):
            raise ValueError("Multiple Final Answers, Action names, or Action Inputs found.")
        if (re.search(r'Final Answer:\s*\S+', cleaned_string) and action_name_count == 0):
            final_answer_match = re.search(r'Final Answer:\s*(.*?)(?=\n\n|\nAction|\nAnalysis|$)', cleaned_string, re.DOTALL)
            if final_answer_match:
                final_answer_content = final_answer_match.group(1).strip()
            return "finished"
        if (action_name_count == 1 and action_input_count == 1 and final_answer_count == 0):
            return self.parse_response_choose(cleaned_string)
    
        raise ValueError("Unknown invalid action format.")

    # def get_token_count(self, text: str) -> int:
    #     encoding = tiktoken.get_encoding("cl100k_base") 
    #     return len(encoding.encode(text))
    def get_token_count(self, text: str) -> int:
        if not text:
            return 0

        byte_length = len(text.encode('utf-8'))
        char_length = len(text)

        non_ascii_count = (byte_length - char_length) / 2
        ascii_count = char_length - non_ascii_count

        estimated_tokens = (ascii_count / 3.8) + (non_ascii_count * 1.5)
        return int(estimated_tokens * 1.1)

    def windowed_input(self, user_input: str) -> str:
        current_tokens = self.get_token_count(user_input + "Previous Actions:" + str(chat_history))
        model_limit = self.model_cfg.get("max_tokens", MODEL_MAX_TOKENS) - 4096
    
        temp_history = chat_history.copy()
        while temp_history and current_tokens > model_limit:
            removed_item = temp_history.pop(0)
            current_tokens -= self.get_token_count(str(removed_item))
    
        return user_input + "\nPrevious Actions: " + str(temp_history)
    def parse_response_choose(self, response_content: str)->str:
        """parse response_content to action"""
        def extract_balanced_braces(text: str) -> Optional[str]:
            if not text.startswith('{'):
                return None
            stack = []
            result = []
            for i, char in enumerate(text):
                result.append(char)
                if char == '{':
                    stack.append('{')
                elif char == '}':
                    if stack:
                        stack.pop()
                    else:
                        return None
                if not stack:
                    return ''.join(result)
            return None
        try:
            result = {}
            patterns = {
            'Analysis': r'Analysis:\s*(.*?)(?=\n\s*Gaps:|\n\s*Plan:|\n\s*Action name:|\n\s*Action Input:|$)',
            'Gaps': r'Gaps:\s*(.*?)(?=\n\s*Analysis:|\n\s*Plan:|\n\s*Action name:|\n\s*Action Input:|$)',
            'Plan': r'Plan:\s*(.*?)(?=\n\s*Analysis:|\n\s*Gaps:|\n\s*Action name:|\n\s*Action Input:|$)',
            'Action name': r'Action name:\s*(.*?)(?=\n\s*Analysis:|\n\s*Gaps:|\n\s*Plan:|\n\s*Action Input:|$)',
            'Action Input': r'Action Input:\s*(\{.*\})'
            }
            flags = re.DOTALL
    
            for key, pattern in patterns.items():
                match = re.search(pattern, response_content, flags)
                if match:
                    if key == 'Action Input':
                        action_input_text = match.group(1)
                        json_str = extract_balanced_braces(action_input_text)
                        if json_str:
                            result[key] = json_str
                        else:
                            raise ValueError(f"Action Input does not contain valid JSON format")
                    else:
                        result[key] = match.group(1).strip()
                else:
                    result[key] = ""
            if result['Action name'] and not result['Action Input']:
                raise ValueError("Action name found but Action Input is missing.")
            elif not result["Action name"]:
                raise ValueError("Action name is missing.")
            
            if result['Action name'] == 'terminal_execute':
                result['Action Result'] = self.terminal_execute(result['Action Input'])
                chat_history.append(result)
                logger.info(result['Action Result'])
                return result['Action Result']
            elif result['Action name'] == 'terminal_status':
                result['Action Result'] = self.terminal_status(result['Action Input'])
                chat_history.append(result)
                logger.info(result['Action Result'])
                return result['Action Result']
            elif result['Action name'] == 'terminal_output':
                result['Action Result'] = self.terminal_output(result['Action Input'])
                chat_history.append(result)
                logger.info(result['Action Result'])
                return result['Action Result']
            else:
                raise ValueError(f"Unknown Action name: {result['Action name']}")
        except Exception as e:
            self._handle_parse_error(e)
    def _handle_parse_error(self, error: Exception) -> str:
        """return error_description"""
        msg = str(error)
        logger.warning(f"Error captured: {msg[:100]}")
        self.llm._log_activity(f"Error captured: {msg}")
        error_description ="Your previous action has not executed successfully as your response did not follow the format!"\
            f"Error details: {msg[:500]}"
        return error_description

        
    def terminal_execute(self, action_input: str) -> str:
        """
        Control a terminal to execute commands.Every time you can only execute ONE command!!Format: {"terminal_id": "1", "command": "ls", "command_type": "one_time" or "long_running"}
        USE "long_running" when the command need to actively run continuously,especially for the commands about port.
        """
        try:
            json_part = action_input
            print(json_part)
            try:
                action_input = json.loads(json_part)
                terminal_id = action_input.get('terminal_id', '1')
                cmd = action_input.get('command', '')
                cmd_type = action_input.get('command_type', 'one_time')
                return terminal_manager.execute_command(terminal_id, cmd, cmd_type)
            except json.JSONDecodeError:
                return "Error: JSON format error, check the command input."
        except Exception as e:
            self.llm._log_activity(f"Error captured: {str(e)}")
            return f"Error: {str(e)}"
    def terminal_status(self, action_input: str) -> str:
        """Check the status of a terminal.Format: "[terminal_id]" """
        try:
            json_part = action_input
            try:
                action_input = json.loads(json_part)
                terminal_id = action_input.get('terminal_id', '1')
                return terminal_manager.get_session_status(terminal_id)
            except json.JSONDecodeError:
                return "Error: JSON format error, check the command input."
        except Exception as e:
            self.llm._log_activity(f"Action Error captured: {str(e)}")
            return f"Error: {str(e)}"
    def terminal_output(self, action_input: str) -> str:
        """Check the output of a terminal.Format: "[terminal_id]" """
        try:
            json_part = action_input
            try:
                action_input = json.loads(json_part)
                terminal_id = action_input.get('terminal_id', '1')
                return terminal_manager.get_session_output(terminal_id)
            except json.JSONDecodeError:
                return "Error: JSON format error, check the command input."
        except Exception as e:
            self.llm._log_activity(f"Action Error captured: {str(e)}")
            return f"Error: {str(e)}"    
    
chat_history = []
input_len = 0
# user_input = "Write a python script to count the number of files and list them in the current work directory.Write the result into /Workspace/logs/file_count.txt"
user_input = "List all python file in current dictory"
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model-name",
        required=True,
    )
    parser.add_argument(
        "--task",
        default=user_input,
    )
    args = parser.parse_args()

    agent = ReactAgentSystem(model_name=args.model_name)
    user_input = args.task
    
    input_len = len(user_input)
    max_iter = MAX_ITER
    iter_count = 1
    agent.llm._log_activity("="*50)
    agent.llm._log_activity("Start")
    while iter_count < max_iter:
        agent.llm._log_activity("="*25)
        agent.llm._log_activity(f"Round {iter_count}")
        agent.llm._log_activity("="*25)

        logger.info("="*25 + f"Round {iter_count}" + "="*25)
        cleaned_response = agent.invoke(user_input)
        print(cleaned_response)
        logcleaned = f"{Fore.BLUE}{cleaned_response}{Style.RESET_ALL}"
        logger.info(logcleaned)
        try:
            action_result = agent.before_parse_response(cleaned_response)
            if action_result == "finished":
                break
        except ValueError as e:
            error_description = agent._handle_parse_error(e)
            agent.llm._log_activity(error_description)
        
        iter_count += 1
    agent.llm._log_activity("End")
    agent.llm._log_activity("="*50)
