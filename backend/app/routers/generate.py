from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from app.services.github_service import GitHubService
from app.services.ollama_service import OllamaService
from app.prompts import (
    SYSTEM_FIRST_PROMPT,
    SYSTEM_SECOND_PROMPT,
    SYSTEM_THIRD_PROMPT,
    ADDITIONAL_SYSTEM_INSTRUCTIONS_PROMPT,
)
from pydantic import BaseModel
from functools import lru_cache
import re
import json
import asyncio
import os

# from app.services.claude_service import ClaudeService
# from app.core.limiter import limiter

load_dotenv()

router = APIRouter(prefix="/generate", tags=["Generate"])

# Initialize services
# claude_service = ClaudeService()
llm_service = OllamaService()

# Get default LLM provider from environment
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")  # or "ollama"

# cache github data to avoid double API calls from cost and generate
@lru_cache(maxsize=100)
def get_cached_github_data(username: str, repo: str, github_pat: str | None = None):
    # Create a new service instance for each call with the appropriate PAT
    current_github_service = GitHubService(pat=github_pat)

    default_branch = current_github_service.get_default_branch(username, repo)
    if not default_branch:
        default_branch = "main"  # fallback value

    file_tree = current_github_service.get_github_file_paths_as_list(username, repo)
    readme = current_github_service.get_github_readme(username, repo)

    return {"default_branch": default_branch, "file_tree": file_tree, "readme": readme}


class ApiRequest(BaseModel):
    username: str
    repo: str
    instructions: str = ""
    api_key: str | None = None
    github_pat: str | None = None


@router.post("/cost")
# @limiter.limit("5/minute") # TEMP: disable rate limit for growth??
async def get_generation_cost(request: Request, body: ApiRequest):
    try:
        # Get file tree and README content
        github_data = get_cached_github_data(body.username, body.repo, body.github_pat)
        file_tree = github_data["file_tree"]
        readme = github_data["readme"]

        # Calculate combined token count
        file_tree_tokens = llm_service.count_tokens(file_tree)
        readme_tokens = llm_service.count_tokens(readme)

        # Using local LLM - free to use
        cost_string = "$0.00 USD (using local LLM)"
        return {"cost": cost_string}
    except Exception as e:
        return {"error": str(e)}


def process_click_events(diagram: str, username: str, repo: str, branch: str) -> str:
    """
    Process click events in Mermaid diagram to include full GitHub URLs.
    Detects if path is file or directory and uses appropriate URL format.
    """

    def replace_path(match):
        # Extract the path from the click event
        path = match.group(2).strip("\"'")

        # Determine if path is likely a file (has extension) or directory
        is_file = "." in path.split("/")[-1]

        # Construct GitHub URL
        base_url = f"https://github.com/{username}/{repo}"
        path_type = "blob" if is_file else "tree"
        full_url = f"{base_url}/{path_type}/{branch}/{path}"

        # Return the full click event with the new URL
        return f'click {match.group(1)} "{full_url}"'

    # Match click events: click ComponentName "path/to/something"
    click_pattern = r'click ([^\s"]+)\s+"([^"]+)"'
    return re.sub(click_pattern, replace_path, diagram)


@router.post("/stream")
async def generate_stream(request: Request, body: ApiRequest):
    try:
        # Initial validation checks
        if len(body.instructions) > 1000:
            return {"error": "Instructions exceed maximum length of 1000 characters"}

        if body.repo in [
            "fastapi",
            "streamlit",
            "flask",
            "api-analytics",
            "monkeytype",
        ]:
            return {"error": "Example repos cannot be regenerated"}

        async def event_generator():
            try:
                # Get cached github data
                github_data = get_cached_github_data(
                    body.username, body.repo, body.github_pat
                )
                default_branch = github_data["default_branch"]
                file_tree = github_data["file_tree"]
                readme = github_data["readme"]

                # Send initial status
                yield f"data: {json.dumps({'status': 'started', 'message': 'Starting generation process...'})}\n\n"
                await asyncio.sleep(0.1)

                # Prepare prompts
                first_system_prompt = SYSTEM_FIRST_PROMPT
                third_system_prompt = SYSTEM_THIRD_PROMPT
                if body.instructions:
                    first_system_prompt = (
                        first_system_prompt
                        + "\n"
                        + ADDITIONAL_SYSTEM_INSTRUCTIONS_PROMPT
                    )
                    third_system_prompt = (
                        third_system_prompt
                        + "\n"
                        + ADDITIONAL_SYSTEM_INSTRUCTIONS_PROMPT
                    )

                # Phase 1: Get explanation
                yield f"data: {json.dumps({'status': 'explanation_sent', 'message': 'Analyzing repository structure...'})}\n\n"
                explanation = ""
                async for chunk in llm_service.call_o3_api_stream(
                    system_prompt=first_system_prompt,
                    data={
                        "file_tree": file_tree,
                        "readme": readme,
                        "instructions": body.instructions,
                    },
                    api_key=body.api_key,
                    reasoning_effort="medium",
                ):
                    explanation += chunk
                    yield f"data: {json.dumps({'status': 'explanation_chunk', 'chunk': chunk})}\n\n"

                if "BAD_INSTRUCTIONS" in explanation:
                    yield f"data: {json.dumps({'error': 'Invalid or unclear instructions provided'})}\n\n"
                    return

                # Phase 2: Get component mapping
                yield f"data: {json.dumps({'status': 'mapping', 'message': 'Creating component mapping...'})}\n\n"
                full_second_response = ""
                async for chunk in llm_service.call_o3_api_stream(
                    system_prompt=SYSTEM_SECOND_PROMPT,
                    data={"explanation": explanation, "file_tree": file_tree},
                    api_key=body.api_key,
                    reasoning_effort="medium",
                ):
                    full_second_response += chunk
                    yield f"data: {json.dumps({'status': 'mapping_chunk', 'chunk': chunk})}\n\n"

                # Phase 3: Generate Mermaid diagram
                yield f"data: {json.dumps({'status': 'diagram', 'message': 'Generating diagram...'})}\n\n"
                mermaid_code = ""
                async for chunk in llm_service.call_o3_api_stream(
                    system_prompt=third_system_prompt,
                    data={
                        "explanation": explanation,
                        "component_mapping": full_second_response,
                        "instructions": body.instructions,
                    },
                    api_key=body.api_key,
                    reasoning_effort="medium",
                ):
                    mermaid_code += chunk
                    yield f"data: {json.dumps({'status': 'diagram_chunk', 'chunk': chunk})}\n\n"

                # Process click events to include full GitHub URLs
                mermaid_code = process_click_events(
                    mermaid_code, body.username, body.repo, default_branch
                )

                # Send final diagram
                yield f"data: {json.dumps({'status': 'complete', 'diagram': mermaid_code})}\n\n"

            except Exception as e:
                print(f"Error in event generator: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        print(f"Error in generate_stream: {str(e)}")
        return {"error": str(e)}
