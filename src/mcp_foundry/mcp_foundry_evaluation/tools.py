import asyncio
import contextlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Union


# Azure AI Evaluation Imports
from azure.ai.evaluation import (
    # Agent Converter
    BleuScoreEvaluator,
    CodeVulnerabilityEvaluator,
    CoherenceEvaluator,
    ContentSafetyEvaluator,
    F1ScoreEvaluator,
    FluencyEvaluator,
    # Text Evaluators
    GroundednessEvaluator,
    HateUnfairnessEvaluator,
    IndirectAttackEvaluator,
    # Agent Evaluators
    IntentResolutionEvaluator,
    MeteorScoreEvaluator,
    ProtectedMaterialEvaluator,
    QAEvaluator,
    RelevanceEvaluator,
    RetrievalEvaluator,
    RougeScoreEvaluator,
    SelfHarmEvaluator,
    SexualEvaluator,
    SimilarityEvaluator,
    TaskAdherenceEvaluator,
    ToolCallAccuracyEvaluator,
    UngroundedAttributesEvaluator,
    ViolenceEvaluator,
    evaluate,
)
from azure.ai.projects.aio import AIProjectClient
from azure.ai.agents.models import Agent, MessageRole, MessageTextContent

# Azure Imports
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from dotenv import load_dotenv

from mcp_foundry.mcp_server import mcp

logger = logging.getLogger(__name__)

# Configure PromptFlow logging to go to stderr
def configure_promptflow_logging():
    import logging

    promptflow_logger = logging.getLogger("promptflow")
    for handler in promptflow_logger.handlers:
        promptflow_logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    promptflow_logger.addHandler(handler)
    promptflow_logger.propagate = False  # Don't propagate to root logger


# Call this function early in your script's execution
configure_promptflow_logging()

# Load environment variables
load_dotenv()

#######################
# CONFIGURATION SETUP #
#######################

# Initialize Azure AI project and Azure OpenAI connection with environment variables
try:
    # Sync credential for evaluations
    CREDENTIAL = DefaultAzureCredential()

    # Azure OpenAI model configuration
    MODEL_CONFIG = {
        "azure_endpoint": os.environ.get("AZURE_OPENAI_ENDPOINT"),
        "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
        "azure_deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT"),
        "api_version": os.environ.get("AZURE_OPENAI_API_VERSION"),
    }

    # Directory for evaluation data files
    EVAL_DATA_DIR = os.environ.get("EVAL_DATA_DIR", ".")

    # Azure AI Agent configuration
    DEFAULT_AGENT_ID = os.environ.get("DEFAULT_AGENT_ID")
    AZURE_AI_PROJECT_ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")

    # Initialization flags
    EVALUATION_INITIALIZED = True
    if not all([AZURE_AI_PROJECT_ENDPOINT, MODEL_CONFIG["azure_endpoint"]]):
        EVALUATION_INITIALIZED = False
        logger.warning("Some evaluation credentials are missing, some evaluators may not work")

    AGENT_INITIALIZED = bool(AZURE_AI_PROJECT_ENDPOINT)
    if not AGENT_INITIALIZED:
        logger.warning("AZURE_AI_PROJECT_ENDPOINT is missing, agent features will not work")

except Exception as e:
    logger.error(f"Initialization error: {str(e)}")
    CREDENTIAL = None
    AZURE_AI_PROJECT_ENDPOINT = None
    MODEL_CONFIG = None
    EVALUATION_INITIALIZED = False
    AGENT_INITIALIZED = False

# Global variables for agent client and cache
AI_CLIENT: Optional[AIProjectClient] = None
AGENT_CACHE = {}
USER_AGENT = "foundry-mcp"  # Custom user agent for Azure AI Project client


async def initialize_agent_client():
    """Initialize the Azure AI Agent client asynchronously."""
    global AI_CLIENT

    if not AGENT_INITIALIZED:
        return False

    try:
        async_credential = AsyncDefaultAzureCredential()
        AI_CLIENT = AIProjectClient(endpoint=AZURE_AI_PROJECT_ENDPOINT, credential=async_credential, user_agent=USER_AGENT)
        return True
    except Exception as e:
        logger.error(f"Failed to initialize AIProjectClient: {str(e)}")
        return False


#######################
# EVALUATOR MAPPINGS  #
#######################

# Map evaluator names to classes for dynamic instantiation
TEXT_EVALUATOR_MAP = {
    "groundedness": GroundednessEvaluator,
    "relevance": RelevanceEvaluator,
    "coherence": CoherenceEvaluator,
    "fluency": FluencyEvaluator,
    "similarity": SimilarityEvaluator,
    "retrieval": RetrievalEvaluator,
    "f1": F1ScoreEvaluator,
    "rouge": RougeScoreEvaluator,
    "bleu": BleuScoreEvaluator,
    "meteor": MeteorScoreEvaluator,
    "violence": ViolenceEvaluator,
    "sexual": SexualEvaluator,
    "self_harm": SelfHarmEvaluator,
    "hate_unfairness": HateUnfairnessEvaluator,
    "indirect_attack": IndirectAttackEvaluator,
    "protected_material": ProtectedMaterialEvaluator,
    "ungrounded_attributes": UngroundedAttributesEvaluator,
    "code_vulnerability": CodeVulnerabilityEvaluator,
    "qa": QAEvaluator,
    "content_safety": ContentSafetyEvaluator,
}

# Map agent evaluator names to classes
AGENT_EVALUATOR_MAP = {
    "intent_resolution": IntentResolutionEvaluator,
    "tool_call_accuracy": ToolCallAccuracyEvaluator,
    "task_adherence": TaskAdherenceEvaluator,
}

# Required parameters for each text evaluator
TEXT_EVALUATOR_REQUIREMENTS = {
    "groundedness": {"query": "Optional", "response": "Required", "context": "Required"},
    "relevance": {"query": "Required", "response": "Required"},
    "coherence": {"query": "Required", "response": "Required"},
    "fluency": {"response": "Required"},
    "similarity": {"query": "Required", "response": "Required", "ground_truth": "Required"},
    "retrieval": {"query": "Required", "context": "Required"},
    "f1": {"response": "Required", "ground_truth": "Required"},
    "rouge": {"response": "Required", "ground_truth": "Required"},
    "bleu": {"response": "Required", "ground_truth": "Required"},
    "meteor": {"response": "Required", "ground_truth": "Required"},
    "violence": {"query": "Required", "response": "Required"},
    "sexual": {"query": "Required", "response": "Required"},
    "self_harm": {"query": "Required", "response": "Required"},
    "hate_unfairness": {"query": "Required", "response": "Required"},
    "indirect_attack": {"query": "Required", "response": "Required", "context": "Required"},
    "protected_material": {"query": "Required", "response": "Required"},
    "ungrounded_attributes": {"query": "Required", "response": "Required", "context": "Required"},
    "code_vulnerability": {"query": "Required", "response": "Required"},
    "qa": {"query": "Required", "response": "Required", "context": "Required", "ground_truth": "Required"},
    "content_safety": {"query": "Required", "response": "Required"},
}

# Required parameters for each agent evaluator
agent_evaluator_requirements = {
    "intent_resolution": {
        "query": "Required (Union[str, list[Message]])",
        "response": "Required (Union[str, list[Message]])",
        "tool_definitions": "Optional (list[ToolDefinition])",
    },
    "tool_call_accuracy": {
        "query": "Required (Union[str, list[Message]])",
        "response": "Optional (Union[str, list[Message]])",
        "tool_calls": "Optional (Union[dict, list[ToolCall]])",
        "tool_definitions": "Required (list[ToolDefinition])",
    },
    "task_adherence": {
        "query": "Required (Union[str, list[Message]])",
        "response": "Required (Union[str, list[Message]])",
        "tool_definitions": "Optional (list[ToolCall])",
    },
}

######################
# HELPER FUNCTIONS   #
######################


def create_text_evaluator(evaluator_name: str) -> Any:
    """Create and configure an appropriate text evaluator instance."""
    if evaluator_name not in TEXT_EVALUATOR_MAP:
        raise ValueError(f"Unknown text evaluator: {evaluator_name}")

    EvaluatorClass = TEXT_EVALUATOR_MAP[evaluator_name]

    # AI-assisted quality evaluators need a model
    if evaluator_name in ["groundedness", "relevance", "coherence", "fluency", "similarity"]:
        if not MODEL_CONFIG or not all([MODEL_CONFIG["azure_endpoint"], MODEL_CONFIG["api_key"]]):
            raise ValueError(f"Model configuration required for {evaluator_name} evaluator")
        return EvaluatorClass(MODEL_CONFIG)

    # AI-assisted risk and safety evaluators need Azure credentials
    elif evaluator_name in [
        "violence",
        "sexual",
        "self_harm",
        "hate_unfairness",
        "indirect_attack",
        "protected_material",
        "ungrounded_attributes",
        "code_vulnerability",
        "content_safety",
    ]:
        if CREDENTIAL is None or AZURE_AI_PROJECT_ENDPOINT is None:
            raise ValueError(f"Azure credentials required for {evaluator_name} evaluator")
        return EvaluatorClass(credential=CREDENTIAL, azure_ai_project=AZURE_AI_PROJECT_ENDPOINT)

    # NLP evaluators don't need special configuration
    else:
        return EvaluatorClass()


def create_agent_evaluator(evaluator_name: str) -> Any:
    """Create and configure an appropriate agent evaluator instance."""
    if evaluator_name not in AGENT_EVALUATOR_MAP:
        raise ValueError(f"Unknown agent evaluator: {evaluator_name}")

    if not MODEL_CONFIG or not all([MODEL_CONFIG["azure_endpoint"], MODEL_CONFIG["api_key"]]):
        raise ValueError(f"Model configuration required for {evaluator_name} evaluator")

    EvaluatorClass = AGENT_EVALUATOR_MAP[evaluator_name]
    return EvaluatorClass(model_config=MODEL_CONFIG)


async def get_agent(client: AIProjectClient, agent_id: str) -> Agent:
    """Get an agent by ID with simple caching."""
    global AGENT_CACHE

    # Check cache first
    if agent_id in AGENT_CACHE:
        return AGENT_CACHE[agent_id]

    # Fetch agent if not in cache
    try:
        agent = await client.agents.get_agent(agent_id=agent_id)
        AGENT_CACHE[agent_id] = agent
        return agent
    except Exception as e:
        logger.error(f"Agent retrieval failed - ID: {agent_id}, Error: {str(e)}")
        raise ValueError(f"Agent not found or inaccessible: {agent_id}")


async def query_agent(client: AIProjectClient, agent_id: str, query: str) -> Dict:
    """Query an Azure AI Agent and get the response with full thread/run data."""
    try:
        # Get agent (from cache or fetch it)
        agent = await get_agent(client, agent_id)

        # Always create a new thread
        thread = await client.agents.threads.create()
        thread_id = thread.id

        # Add message to thread
        await client.agents.messages.create(thread_id=thread_id, role=MessageRole.USER, content=query)

        # Process the run
        run = await client.agents.runs.create(thread_id=thread_id, agent_id=agent_id)
        run_id = run.id

        # Poll until the run is complete
        while run.status in ["queued", "in_progress", "requires_action"]:
            await asyncio.sleep(1)  # Non-blocking sleep
            run = await client.agents.runs.get(thread_id=thread_id, run_id=run.id)

        if run.status == "failed":
            error_msg = f"Agent run failed: {run.last_error}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "thread_id": thread_id,
                "run_id": run_id,
                "result": f"Error: {error_msg}",
            }

        # Get the agent's response
        response_messages = client.agents.messages.list(thread_id=thread_id)
        response_message = None
        async for msg in response_messages:
            if msg.role == MessageRole.AGENT:
                response_message = msg

        result = ""
        citations = []

        if response_message:
            # Collect text content
            for text_message in response_message.text_messages:
                result += text_message.text.value + "\n"

            # Collect citations
            for annotation in response_message.url_citation_annotations:
                citation = f"[{annotation.url_citation.title}]({annotation.url_citation.url})"
                if citation not in citations:
                    citations.append(citation)

        # Add citations if any
        if citations:
            result += "\n\n## Sources\n"
            for citation in citations:
                result += f"- {citation}\n"

        return {
            "success": True,
            "thread_id": thread_id,
            "run_id": run_id,
            "result": result.strip(),
            "citations": citations,
        }

    except Exception as e:
        logger.error(f"Agent query failed - ID: {agent_id}, Error: {str(e)}")
        raise


def az(*args: str) -> dict:
    """Run azure-cli and return output with improved error handling"""
    cmd = [sys.executable, "-m", "azure.cli", *args, "-o", "json"]

    # Log the command that's about to be executed
    logger.info(f"Attempting to run: {' '.join(cmd)}")

    try:
        # Run with full logging
        result = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            check=False,  # Don't raise exception to see all errors
        )

        # Log the results
        logger.info(f"Command exit code: {result.returncode}")
        logger.info(f"Command stdout (first 100 chars): {result.stdout[:100] if result.stdout else 'Empty'}")
        logger.warning(f"Command stderr (first 100 chars): {result.stderr[:100] if result.stderr else 'Empty'}")

        if result.returncode != 0:
            # Command failed
            return {"error": "Command failed", "stderr": result.stderr, "returncode": result.returncode}

        try:
            # Try to parse JSON
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError as json_err:
            # JSON parsing failed
            return {
                "error": f"Failed to parse JSON: {str(json_err)}",
                "raw_output": result.stdout[:500],  # First 500 chars for debugging
            }

    except Exception as e:
        # Catch all other exceptions
        logger.error(f"Exception executing command: {str(e)}")
        return {"error": f"Exception: {str(e)}", "type": type(e).__name__}


########################
# TEXT EVALUATION TOOLS #
########################


@mcp.tool()
def list_text_evaluators() -> List[str]:
    """
    Returns a list of available text evaluator names for evaluating text outputs.
    """
    return list(TEXT_EVALUATOR_MAP.keys())


@mcp.tool()
def list_agent_evaluators() -> List[str]:
    """
    Returns a list of available agent evaluator names for evaluating agent behaviors.
    """
    return list(AGENT_EVALUATOR_MAP.keys())


@mcp.tool()
def get_text_evaluator_requirements(evaluator_name: Optional[str] = None) -> Dict:
    """
    Get the required input fields for a specific text evaluator or all text evaluators.

    Parameters:
    - evaluator_name: Optional name of evaluator. If None, returns requirements for all evaluators.
    """
    if evaluator_name is not None:
        if evaluator_name not in TEXT_EVALUATOR_MAP:
            raise ValueError(f"Unknown evaluator {evaluator_name}")
        return {evaluator_name: TEXT_EVALUATOR_REQUIREMENTS[evaluator_name]}
    else:
        return TEXT_EVALUATOR_REQUIREMENTS


@mcp.tool()
def get_agent_evaluator_requirements(evaluator_name: Optional[str] = None) -> Dict:
    """
    Get the required input fields for a specific agent evaluator or all agent evaluators.

    Parameters:
    - evaluator_name: Optional name of evaluator. If None, returns requirements for all evaluators.
    """
    if evaluator_name is not None:
        if evaluator_name not in AGENT_EVALUATOR_MAP:
            raise ValueError(f"Unknown evaluator {evaluator_name}")
        return {evaluator_name: agent_evaluator_requirements[evaluator_name]}
    else:
        return agent_evaluator_requirements


@mcp.tool()
def run_text_eval(
    evaluator_names: Union[str, List[str]],  # Single evaluator name or list of evaluator names
    file_path: Optional[str] = None,  # Path to JSONL file
    content: Optional[str] = None,  # JSONL content as a string (optional)
    include_studio_url: bool = True,  # Option to include studio URL in response
    return_row_results: bool = False,  # Option to include detailed row results
) -> Dict:
    """
    Run one or multiple evaluators on a JSONL file or content string.

    Parameters:
    - evaluator_names: Either a single evaluator name (string) or a list of evaluator names
    - file_path: Path to a JSONL file to evaluate (preferred for efficiency)
    - content: JSONL content as a string (alternative if file_path not available)
    - include_studio_url: Whether to include the Azure AI studio URL in the response
    - return_row_results: Whether to include detailed row results (False by default for large datasets)
    """
    # Save original stdout so we can restore it later
    original_stdout = sys.stdout
    # Redirect stdout to stderr to prevent PromptFlow output from breaking MCP
    sys.stdout = sys.stderr

    # Heartbeat mechanism
    import threading
    import time

    # Set up a heartbeat mechanism to keep the connection alive
    heartbeat_active = True

    def send_heartbeats():
        count = 0
        while heartbeat_active:
            count += 1
            logger.info(f"Heartbeat {count} - Evaluation in progress...")
            # Print to stderr to keep connection alive
            print(f"Evaluation in progress... ({count * 15}s)", file=sys.stderr, flush=True)
            time.sleep(15)  # Send heartbeat every 15 seconds

    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=send_heartbeats, daemon=True)
    heartbeat_thread.start()

    try:
        if not EVALUATION_INITIALIZED:
            heartbeat_active = False  # Stop heartbeat
            return {"error": "Evaluation not initialized. Check environment variables."}

        # Validate inputs
        if content is None and file_path is None:
            heartbeat_active = False  # Stop heartbeat
            return {"error": "Either file_path or content must be provided"}

        # Convert single evaluator to list for unified processing
        if isinstance(evaluator_names, str):
            evaluator_names = [evaluator_names]

        # Validate evaluator names
        for name in evaluator_names:
            if name not in TEXT_EVALUATOR_MAP:
                heartbeat_active = False  # Stop heartbeat
                return {"error": f"Unknown evaluator: {name}"}

        # Variable to track if we need to clean up a temp file
        temp_file = None

        try:
            # Determine which input to use (prioritize file_path for efficiency)
            input_file = None
            if file_path:
                # Resolve file path
                if os.path.isfile(file_path):
                    input_file = file_path
                else:
                    # Check in data directory
                    data_dir = os.environ.get("EVAL_DATA_DIR", ".")
                    alternate_path = os.path.join(data_dir, file_path)
                    if os.path.isfile(alternate_path):
                        input_file = alternate_path
                    else:
                        heartbeat_active = False  # Stop heartbeat
                        return {"error": f"File not found: {file_path} (also checked in {data_dir})"}

                # Count rows quickly using file iteration
                with open(input_file, "r", encoding="utf-8") as f:
                    row_count = sum(1 for line in f if line.strip())

            elif content:
                # Create temporary file for content string
                fd, temp_file = tempfile.mkstemp(suffix=".jsonl")
                os.close(fd)

                # Write content to temp file
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(content)

                input_file = temp_file
                row_count = content.count("\n") + (0 if content.endswith("\n") else 1)

            logger.info(f"Processing {row_count} rows for {len(evaluator_names)} evaluator(s)")

            # Prepare evaluators
            evaluators = {}
            eval_config = {}

            for name in evaluator_names:
                # Create evaluator instance
                evaluators[name] = create_text_evaluator(name)

                # Set up column mapping for this evaluator
                requirements = TEXT_EVALUATOR_REQUIREMENTS[name]
                column_mapping = {}
                for field, requirement in requirements.items():
                    if requirement == "Required":
                        column_mapping[field] = f"${{data.{field}}}"
                eval_config[name] = {"column_mapping": column_mapping}

            # Prepare evaluation args
            eval_args = {"data": input_file, "evaluators": evaluators, "evaluator_config": eval_config}

            # Add Azure AI project info if initialized
            if AZURE_AI_PROJECT_ENDPOINT and include_studio_url:
                eval_args["azure_ai_project"] = AZURE_AI_PROJECT_ENDPOINT

            eval_args["user_agent"] = USER_AGENT

            # Run evaluation with additional stdout redirection for extra safety
            with contextlib.redirect_stdout(sys.stderr):
                result = evaluate(**eval_args)

            # Prepare response
            response = {"evaluators": evaluator_names, "row_count": row_count, "metrics": result.get("metrics", {})}

            # Only include detailed row results if explicitly requested
            if return_row_results:
                response["row_results"] = result.get("rows", [])

            # Include studio URL if available
            if include_studio_url and "studio_url" in result:
                response["studio_url"] = result.get("studio_url")
            heartbeat_active = False  # Stop heartbeat
            return response

        except Exception as e:
            logger.error(f"Evaluation error: {str(e)}")
            heartbeat_active = False  # Stop heartbeat
            return {"error": str(e)}

        finally:
            # Clean up temp file if we created one
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass

            # Make sure heartbeat is stopped
            heartbeat_active = False

    finally:
        # Always restore stdout, even if an exception occurs
        sys.stdout = original_stdout
        heartbeat_active = False


@mcp.tool()
async def agent_query_and_evaluate(
    agent_id: str,
    query: str,
    evaluator_names: Optional[List[str]] = None,
    include_studio_url: bool = True,  # Option to include studio URL
) -> Dict:
    """
    Query an agent and evaluate its response in a single operation.

    Parameters:
    - agent_id: ID of the agent to query
    - query: Text query to send to the agent
    - evaluator_names: Optional list of agent evaluator names to use (defaults to all)
    - include_studio_url: Whether to include the Azure AI studio URL in the response

    Returns both the agent response and evaluation results
    """
    # Save original stdout so we can restore it later
    original_stdout = sys.stdout
    # Redirect stdout to stderr to prevent PromptFlow output from breaking MCP
    sys.stdout = sys.stderr

    # Heartbeat mechanism to keep connection alive during long operations
    import threading
    import time

    # Set up a heartbeat mechanism to keep the connection alive
    heartbeat_active = True

    def send_heartbeats():
        count = 0
        while heartbeat_active:
            count += 1
            logger.info(f"Heartbeat {count} - Evaluation in progress...")
            # Print to stderr to keep connection alive
            print(f"Evaluation in progress... ({count * 15}s)", file=sys.stderr, flush=True)
            time.sleep(15)  # Send heartbeat every 15 seconds

    # Start heartbeat thread
    heartbeat_thread = threading.Thread(target=send_heartbeats, daemon=True)
    heartbeat_thread.start()

    try:
        if not AGENT_INITIALIZED or not EVALUATION_INITIALIZED:
            heartbeat_active = False  # Stop heartbeat
            return {"error": "Services not fully initialized. Check environment variables."}

        if AI_CLIENT is None:
            success = await initialize_agent_client()
            if not success or AI_CLIENT is None:
                heartbeat_active = False  # Stop heartbeat
                return {"error": "Failed to initialize Azure AI Agent client."}

        try:
            # Query the agent (this part remains async)
            query_response = await query_agent(AI_CLIENT, agent_id, query)

            if not query_response.get("success", False):
                heartbeat_active = False  # Stop heartbeat
                return query_response

            # Get the thread and run IDs
            thread_id = query_response["thread_id"]
            run_id = query_response["run_id"]

            # Now we'll switch to synchronous mode, exactly like the GitHub example

            # Step 1: Create a synchronous client (this is what GitHub example uses)
            from azure.ai.projects import AIProjectClient  # This is the sync version
            from azure.identity import DefaultAzureCredential

            sync_client = AIProjectClient(endpoint=AZURE_AI_PROJECT_ENDPOINT, credential=DefaultAzureCredential(), user_agent=USER_AGENT)

            # Step 2: Create converter with the sync client, exactly like example
            from azure.ai.evaluation import AIAgentConverter

            converter = AIAgentConverter(sync_client)

            # Step 3: Create a temp file name
            temp_filename = "temp_evaluation_data.jsonl"

            try:
                # Step 4: Convert data synchronously, exactly as in their example
                evaluation_data = converter.convert(thread_id=thread_id, run_id=run_id)

                # Step 5: Write to file
                with open(temp_filename, "w") as f:
                    json.dump(evaluation_data, f)

                # Step 6: Default to all agent evaluators if none specified
                if not evaluator_names:
                    evaluator_names = list(AGENT_EVALUATOR_MAP.keys())

                # Step 7: Create evaluators
                evaluators = {}
                for name in evaluator_names:
                    evaluators[name] = create_agent_evaluator(name)

                # Step 8: Run evaluation, exactly as in their example
                # Use contextlib to ensure all stdout is redirected
                with contextlib.redirect_stdout(sys.stderr):
                    from azure.ai.evaluation import evaluate

                    evaluation_result = evaluate(
                        data=temp_filename,
                        evaluators=evaluators,
                        azure_ai_project=AZURE_AI_PROJECT_ENDPOINT if include_studio_url else None,
                        user_agent=USER_AGENT,
                    )

                # Step 9: Prepare response
                response = {
                    "success": True,
                    "agent_id": agent_id,
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "query": query,
                    "response": query_response["result"],
                    "citations": query_response.get("citations", []),
                    "evaluation_metrics": evaluation_result.get("metrics", {}),
                }

                # Include studio URL if available
                if include_studio_url and "studio_url" in evaluation_result:
                    response["studio_url"] = evaluation_result.get("studio_url")

                heartbeat_active = False  # Stop heartbeat
                return response

            except Exception as e:
                logger.error(f"Evaluation error: {str(e)}")
                import traceback

                logger.error(traceback.format_exc())
                heartbeat_active = False  # Stop heartbeat
                return {"error": f"Evaluation error: {str(e)}"}

            finally:
                # Clean up temp file
                if os.path.exists(temp_filename):
                    try:
                        os.remove(temp_filename)
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"Error in query and evaluate: {str(e)}")
            heartbeat_active = False  # Stop heartbeat
            return {"error": f"Error in query and evaluate: {str(e)}"}

    finally:
        # Always restore stdout, even if an exception occurs
        sys.stdout = original_stdout
        heartbeat_active = False  # Stop heartbeat


# Add this new helper function to format evaluation outputs
@mcp.tool()
def format_evaluation_report(evaluation_result: Dict) -> str:
    """
    Format evaluation results into a readable report with metrics and Studio URL.

    Parameters:
    - evaluation_result: The evaluation result dictionary from run_text_eval or agent_query_and_evaluate

    Returns a formatted report with metrics and Azure AI Studio URL if available
    """
    if "error" in evaluation_result:
        return f"❌ Evaluation Error: {evaluation_result['error']}"

    # Start the report
    report = ["# Evaluation Report\n"]

    # Add evaluator info
    evaluator = evaluation_result.get("evaluator")
    if evaluator:
        report.append(f"## Evaluator: {evaluator}\n")

    # Add metrics
    metrics = evaluation_result.get("metrics", {})
    if metrics:
        report.append("## Metrics\n")
        for metric_name, metric_value in metrics.items():
            # Format metric value based on type
            if isinstance(metric_value, (int, float)):
                formatted_value = f"{metric_value:.4f}" if isinstance(metric_value, float) else str(metric_value)
            else:
                formatted_value = str(metric_value)

            report.append(f"- **{metric_name}**: {formatted_value}")
        report.append("\n")

    # Add studio URL if available
    studio_url = evaluation_result.get("studio_url")
    if studio_url:
        report.append("## Azure AI Studio\n")
        report.append(f"📊 [View detailed evaluation results in Azure AI Studio]({studio_url})\n")

    # Return the formatted report
    return "\n".join(report)


@mcp.tool()
def run_agent_eval(
    evaluator_name: str,
    query: str,
    response: Optional[str] = None,
    tool_calls: Optional[str] = None,
    tool_definitions: Optional[str] = None,
) -> Dict:
    """
    Run agent evaluation on agent data. Accepts both plain text and JSON strings.

    Parameters:
    - evaluator_name: Name of the agent evaluator to use (intent_resolution, tool_call_accuracy, task_adherence)
    - query: User query (plain text or JSON string)
    - response: Agent response (plain text or JSON string)
    - tool_calls: Optional tool calls data (JSON string)
    - tool_definitions: Optional tool definitions (JSON string)
    """
    if not EVALUATION_INITIALIZED:
        return {"error": "Evaluation not initialized. Check environment variables."}

    if evaluator_name not in AGENT_EVALUATOR_MAP:
        raise ValueError(f"Unknown agent evaluator: {evaluator_name}")

    try:
        # Helper function to process inputs
        def process_input(input_str):
            if not input_str:
                return None

            # Check if it's already a valid JSON string
            try:
                # Try to parse as JSON
                return json.loads(input_str)
            except json.JSONDecodeError:
                # If not a JSON string, treat as plain text
                return input_str

        # Process inputs - handle both direct text and JSON strings
        query_data = process_input(query)
        response_data = process_input(response) if response else None
        tool_calls_data = process_input(tool_calls) if tool_calls else None
        tool_definitions_data = process_input(tool_definitions) if tool_definitions else None

        # If query/response are plain text, wrap them in the expected format
        if isinstance(query_data, str):
            query_data = {"content": query_data}

        if isinstance(response_data, str):
            response_data = {"content": response_data}

        # Create evaluator instance
        evaluator = create_agent_evaluator(evaluator_name)

        # Prepare kwargs for the evaluator
        kwargs = {"query": query_data}
        if response_data:
            kwargs["response"] = response_data
        if tool_calls_data:
            kwargs["tool_calls"] = tool_calls_data
        if tool_definitions_data:
            kwargs["tool_definitions"] = tool_definitions_data

        # Run evaluation
        result = evaluator(**kwargs)

        return {"evaluator": evaluator_name, "result": result}

    except Exception as e:
        logger.error(f"Agent evaluation error: {str(e)}")
        return {"error": str(e)}


########################
# AGENT SERVICE TOOLS  #
########################


@mcp.tool()
async def list_agents() -> str:
    """List available agents in the Azure AI Agent Service."""
    if not AGENT_INITIALIZED:
        return "Error: Azure AI Agent service is not initialized. Check environment variables."

    if AI_CLIENT is None:
        await initialize_agent_client()
        if AI_CLIENT is None:
            return "Error: Failed to initialize Azure AI Agent client."

    try:
        agents = AI_CLIENT.agents.list_agents()
        if not agents:
            return "No agents found in the Azure AI Agent Service."

        result = "## Available Azure AI Agents\n\n"
        async for agent in agents:
            result += f"- **{agent.name}**: `{agent.id}`\n"

        if DEFAULT_AGENT_ID:
            result += f"\n**Default Agent ID**: `{DEFAULT_AGENT_ID}`"

        return result
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return f"Error listing agents: {str(e)}"


@mcp.tool()
async def connect_agent(agent_id: str, query: str) -> Dict:
    """
    Connect to a specific Azure AI Agent and run a query.

    Parameters:
    - agent_id: ID of the agent to connect to
    - query: Text query to send to the agent

    Returns a dict with the agent's response and thread/run IDs for potential evaluation
    """
    if not AGENT_INITIALIZED:
        return {"error": "Azure AI Agent service is not initialized. Check environment variables."}

    if AI_CLIENT is None:
        await initialize_agent_client()
        if AI_CLIENT is None:
            return {"error": "Failed to initialize Azure AI Agent client."}

    try:
        response = await query_agent(AI_CLIENT, agent_id, query)
        return response
    except Exception as e:
        logger.error(f"Error connecting to agent: {str(e)}")
        return {"error": f"Error connecting to agent: {str(e)}"}


@mcp.tool()
async def query_default_agent(query: str) -> Dict:
    """
    Send a query to the default configured Azure AI Agent.

    Parameters:
    - query: Text query to send to the default agent

    Returns a dict with the agent's response and thread/run IDs for potential evaluation
    """
    if not AGENT_INITIALIZED:
        return {"error": "Azure AI Agent service is not initialized. Check environment variables."}

    if not DEFAULT_AGENT_ID:
        return {
            "error": "No default agent configured. Set DEFAULT_AGENT_ID environment variable or use connect_agent tool."
        }

    if AI_CLIENT is None:
        await initialize_agent_client()
        if AI_CLIENT is None:
            return {"error": "Failed to initialize Azure AI Agent client."}

    try:
        response = await query_agent(AI_CLIENT, DEFAULT_AGENT_ID, query)
        return response
    except Exception as e:
        logger.error(f"Error querying default agent: {str(e)}")
        return {"error": f"Error querying default agent: {str(e)}"}
