# MCP Server that interacts with Azure AI Foundry (experimental)

A Model Context Protocol server for Azure AI Foundry, providing a unified set of tools for models, knowledge, evaluation, and more.

[![GitHub watchers](https://img.shields.io/github/watchers/azure-ai-foundry/mcp-foundry.svg?style=social&label=Watch)](https://github.com/azure-ai-foundry/mcp-foundry/watchers)
[![GitHub forks](https://img.shields.io/github/forks/azure-ai-foundry/mcp-foundry.svg?style=social&label=Fork)](https://github.com/azure-ai-foundry/mcp-foundry/fork)
[![GitHub stars](https://img.shields.io/github/stars/azure-ai-foundry/mcp-foundry?style=social&label=Star)](https://github.com/azure-ai-foundry/mcp-foundry/stargazers)

[![Azure AI Community Discord](https://dcbadge.vercel.app/api/server/ByRwuEEgH4)](https://discord.gg/REmjGvvFpW)

## Important notice

MCP Server for Azure AI Foundry (experimental) has moved to the cloud, now as Foundry MCP Server (preview). Please check the official public documentation at [Get started with Foundry MCP Server (preview)](https://learn.microsoft.com/azure/ai-foundry/mcp/get-started?view=foundry&tabs=user). This GitHub repository contains the outdated information on the previous experimental server implementation, and will not be updated further. Instead, refer to the new, remotely hosted and managed Foundry MCP Server, that has the following benefits:

- **Cloud-hosted interface for AI tool orchestration**: Foundry MCP Server (preview) provides a secure, scalable endpoint for MCP-compliant clients. You don't need to deploy infrastructure, enabling seamless integration and multi-agent scenarios.
- **Identity and access control**: The server enforces authentication and authorization with Microsoft Entra ID. It performs all operations within the authenticated user's permissions (On-Behalf-Of flow).
- **Scenario-focused, extensible tools**: The MCP Server exposes a growing set of tools for read and write operations on models, deployments, evaluations, and agents in [Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/what-is-azure-ai-foundry?view=foundry). The tools are extensible, letting developers and agents interact with services without knowing backend APIs or data schemas.
- **Accelerated agent and developer productivity**: Natural language workflows (via MCP clients and large language models) enable rapid tool discovery and invocation, streamlining development and multi-agent orchestration.

The rest of this repo (including codebase) explains the now-deprecated MCP Server that interactes with Azure AI Foundry (experimental).

---

## Available Tools

### Capabilities: Models

| Category | Tool | Description |
|---|---|---|
| **Explore** | `list_models_from_model_catalog` | Retrieves a list of supported models from the Azure AI Foundry catalog. |
|  | `list_azure_ai_foundry_labs_projects` | Retrieves a list of state-of-the-art AI models from Microsoft Research available in Azure AI Foundry Labs. |
| | `get_model_details_and_code_samples` | Retrieves detailed information for a specific model from the Azure AI Foundry catalog. |
| **Build** | `get_prototyping_instructions_for_github_and_labs` | Provides comprehensive instructions and setup guidance for starting to work with models from Azure AI Foundry and Azure AI Foundry Labs. |
| **Deploy** | `get_model_quotas` | Get model quotas for a specific Azure location. |
| | `create_azure_ai_services_account` | Creates an Azure AI Services account. |
| | `list_deployments_from_azure_ai_services` | Retrieves a list of deployments from Azure AI Services. |
| | `deploy_model_on_ai_services` | Deploys a model on Azure AI Services. |
| | `create_foundry_project` | Creates a new Azure AI Foundry project. |

### Capabilities: Knowledge

| Category | Tool | Description |
|---|---|---|
| **Index** | `list_index_names` | Retrieve all names of indexes from the AI Search Service |
|  | `list_index_schemas` | Retrieve all index schemas from the AI Search Service |
|  | `retrieve_index_schema` | Retrieve the schema for a specific index from the AI Search Service |
|  | `create_index` | Creates a new index |
|  | `modify_index` | Modifies the index definition of an existing index |
|  | `delete_index` | Removes an existing index |
| **Document** | `add_document` | Adds a document to the index |
|  | `delete_document` | Removes a document from the index |
| **Query** | `query_index` | Searches a specific index to retrieve matching documents |
|  | `get_document_count` | Returns the total number of documents in the index |
| **Indexer** | `list_indexers` | Retrieve all names of indexers from the AI Search Service |
|  | `get_indexer` | Retrieve the full definition of a specific indexer from the AI Search Service |
|  | `create_indexer` | Create a new indexer in the Search Service with the skill, index and data source |
|  | `delete_indexer` | Delete an indexer from the AI Search Service by name |
| **Data Source** | `list_data_sources` | Retrieve all names of data sources from the AI Search Service |
|  | `get_data_source` | Retrieve the full definition of a specific data source |
| **Skill Set** | `list_skill_sets` | Retrieve all names of skill sets from the AI Search Service |
|  | `get_skill_set` | Retrieve the full definition of a specific skill set |
| **Content** | `fk_fetch_local_file_contents` | Retrieves the contents of a local file path (sample JSON, document etc) |
|  | `fk_fetch_url_contents` | Retrieves the contents of a URL (sample JSON, document etc) |

### Capabilities: Evaluation

| Category | Tool | Description |
|---|---|---|
| **Evaluator Utilities** | `list_text_evaluators` | List all available text evaluators. |
|  | `list_agent_evaluators` | List all available agent evaluators. |
|  | `get_text_evaluator_requirements` | Show input requirements for each text evaluator. |
|  | `get_agent_evaluator_requirements` | Show input requirements for each agent evaluator. |
| **Text Evaluation** | `run_text_eval` | Run one or multiple text evaluators on a JSONL file or content. |
|  | `format_evaluation_report` | Convert evaluation output into a readable Markdown report. |
| **Agent Evaluation** | `agent_query_and_evaluate` | Query an agent and evaluate its response using selected evaluators. End-to-End agent evaluation. |
|  | `run_agent_eval` | Evaluate a single agent interaction with specific data (query, response, tool calls, definitions). |
| **Agent Service** | `list_agents` | List all Azure AI Agents available in the configured project. |
|  | `connect_agent` | Send a query to a specified agent. |
|  | `query_default_agent` | Query the default agent defined in environment variables. |

### Capabilities: Finetuning

| Category | Tool | Description |
|---|---|---|
| **Finetuning** | `fetch_finetuning_status` | Retrieves detailed status and metadata for a specific fine-tuning job, including job state, model, creation and finish times, hyperparameters, and any errors. |
|  | `list_finetuning_jobs` | Lists all fine-tuning jobs in the resource, returning job IDs and their current statuses for easy tracking and management. |
|  | `get_finetuning_job_events` | Retrieves a chronological list of all events for a specific fine-tuning job, including timestamps and detailed messages for each training step, evaluation, and completion. |
|  | `get_finetuning_metrics` | Retrieves training and evaluation metrics for a specific fine-tuning job, including loss curves, accuracy, and other relevant performance indicators for monitoring and analysis. |
|  | `list_finetuning_files` | Lists all files available for fine-tuning in Azure OpenAI, including file IDs, names, purposes, and statuses. |
|  | `execute_dynamic_swagger_action` | Executes any tool dynamically generated from the Swagger specification, allowing flexible API calls for advanced scenarios. |
|  | `list_dynamic_swagger_tools` | Lists all dynamically registered tools from the Swagger specification, enabling discovery and automation of available API endpoints. |


## Prompt Examples

### Models

#### Explore models

- How can you help me find the right model?
- What models can I use from Azure AI Foundry?
- What OpenAI models are available in Azure AI Foundry?
- What are the most popular models in Azure AI Foundry? Pick me 10 models.
- What models are good for reasoning? Show me some examples in two buckets, one for large models and one for small models.
- Can you compare Phi models and explain differences?
- Show me the model card for Phi-4-reasoning.
- Can you show me how to test a model?
- What does free playground in Azure AI Foundry mean?
- Can I use GitHub token to test models?
- Show me latest models that support GitHub token.
- Who are the model publishers for the models in Azure AI Foundry?
- Show me models from Meta.
- Show me models with MIT license.

#### Build prototypes

- Can you describe how you can help me build a prototype using the model?
- Describe how you can build a prototype that uses an OpenAI model with my GitHub token. Don't try to create one yet.
- Recommend me a few scenarios to build prototypes with models.
- Tell me about Azure AI Foundry Labs.
- Tell me more about Magentic One
- What is Omniparser and what are potential use cases?
- Can you help me build a prototype using Omniparser?

#### Deploy OpenAI models

- Can you help me deploy OpenAI models?
- What steps do I need to take to deploy OpenAI models on Azure AI Foundry?
- Can you help me understand how I can use OpenAI models on Azure AI Foundry using GitHub token? Can I use it for production?
- I already have an Azure AI services resource. Can I deploy OpenAI models on it?
- What does quota for OpenAI models mean on Azure AI Foundry?
- Get me current quota for my AI services resource.

## Quick Start with GitHub Copilot

[![Use The Template](https://img.shields.io/static/v1?style=for-the-badge&label=Use+The+Template&message=GitHub&color=181717&logo=github)](https://github.com/azure-ai-foundry/foundry-models-playground/generate)

> [This GitHub template](https://github.com/azure-ai-foundry/foundry-mcp-playground) has minimal setup with MCP server configuration and all required dependencies, making it easy to get started with your own projects.

[![Install in VS Code](https://img.shields.io/static/v1?style=for-the-badge&label=Install+in+VS+Code&message=Open&color=007ACC&logo=visualstudiocode)](https://insiders.vscode.dev/redirect/mcp/install?name=Azure%20AI%20Foundry%20MCP%20Server&config=%7B%22type%22%3A%22stdio%22%2C%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--prerelease%3Dallow%22%2C%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2Fazure-ai-foundry%2Fmcp-foundry.git%22%2C%22run-azure-ai-foundry-mcp%22%5D%7D)

> This helps you automatically set up the MCP server in your VS Code environment under user settings.
> You will need `uvx` installed in your environment to run the server.

## Manual Setup

1. Install `uv` by following [Installing uv](https://docs.astral.sh/uv/getting-started/installation/).
1. Start a new workspace in VS Code.
1. (Optional) Create `.env` file in the root of your workspace to set environment variables.
1. Create `.vscode/mcp.json` in the root of your workspace.

    ```json
    {
        "servers": {
            "mcp_foundry_server": {
                "type": "stdio",
                "command": "uvx",
                "args": [
                    "--prerelease=allow",
                    "--from",
                    "git+https://github.com/azure-ai-foundry/mcp-foundry.git",
                    "run-azure-ai-foundry-mcp",
                    "--envFile",
                    "${workspaceFolder}/.env"
                ]
            }
        }
    }
    ```

1. Click `Start` button for the server in `.vscode/mcp.json` file.
1. Open GitHub Copilot chat in Agent mode and start asking questions.

See [More examples for advanced setup](./clients/README.md) for more details on how to set up the MCP server.

### Usage with GitHub Copilot CLI

Use the Copilot CLI to interactively add the MCP server:

```bash
/mcp add
```

Alternatively, create or edit the configuration file `~/.copilot/mcp-config.json` and add:

```json
{
  "mcpServers": {
    "mcp_foundry_server": {
      "command": "uvx",
      "args": [
        "--prerelease=allow",
        "--from",
        "git+https://github.com/azure-ai-foundry/mcp-foundry.git",
        "run-azure-ai-foundry-mcp"
      ]
    }
  }
}
```

For more information, see the [Copilot CLI documentation](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli).

## Setting the Environment Variables

To securely pass information to the MCP server, such as API keys, endpoints, and other sensitive data, you can use environment variables. This is especially important for tools that require authentication or access to external services.

You can set these environment variables in a `.env` file in the root of your project. You can pass the location of `.env` file when setting up MCP Server, and the server will automatically load these variables when it starts.

See [example .env file](./clients/python/pydantic-ai/.env.example) for a sample configuration.

| Category       | Variable                      | Required?                          | Description                                      |
| -------------- | ----------------------------- | ---------------------------------- | ------------------------------------------------ |
| **Model**      | `GITHUB_TOKEN`                | No                                 | GitHub token for testing models for free with rate limits. |
| **Knowledge**  | `AZURE_AI_SEARCH_ENDPOINT`    | Always                             | The endpoint URL for your Azure AI Search service. It should look like this: `https://<your-search-service-name>.search.windows.net/`. |
|                | `AZURE_AI_SEARCH_API_VERSION` | No                                 | API Version to use. Defaults to `2025-03-01-preview`. |
|                | `SEARCH_AUTHENTICATION_METHOD`| Always                             | `service-principal` or `api-search-key`.         |
|                | `AZURE_TENANT_ID`             | Yes when using `service-principal` | The ID of your Azure Active Directory tenant.    |
|                | `AZURE_CLIENT_ID`             | Yes when using `service-principal` | The ID of your Service Principal (app registration) |
|                | `AZURE_CLIENT_SECRET`         | Yes when using `service-principal` | The secret credential for the Service Principal. |
|                | `AZURE_AI_SEARCH_API_KEY`     | Yes when using `api-search-key`    | The API key for your Azure AI Search service.    |
| **Evaluation** | `EVAL_DATA_DIR`               | Always                             | Path to the JSONL evaluation dataset             |
|                | `AZURE_OPENAI_ENDPOINT`       | Text quality evaluators            | Endpoint for Azure OpenAI                        |
|                | `AZURE_OPENAI_API_KEY`        | Text quality evaluators            | API key for Azure OpenAI                         |
|                | `AZURE_OPENAI_DEPLOYMENT`     | Text quality evaluators            | Deployment name (e.g., `gpt-4o`)                 |
|                | `AZURE_OPENAI_API_VERSION`    | Text quality evaluators            | Version of the OpenAI API                        |
|                | `AZURE_AI_PROJECT_ENDPOINT`   | Agent services                     | Used for Azure AI Agent querying and evaluation  |

> [!NOTE]
> **Model**
> - `GITHUB_TOKEN` is used to authenticate with GitHub API for testing models. It is not required if you are exploring models from Foundry catalog.
>
> **Knowledge**
> - See [Create a search service](https://learn.microsoft.com/en-us/azure/search/search-create-service-portal) to learn more about provisioning a search service.
> - Azure AI Search supports multiple authentication methods. You can use either a **Microsoft Entra authentication** or an **Key-based authentication** to authenticate your requests. The choice of authentication method depends on your security requirements and the Azure environment you are working in.
> - See [Authenication](https://learn.microsoft.com/en-us/azure/search/search-security-overview#authentication) to learn more about authentication methods for a search service.
>
> **Evaluation**
> - If you're using **agent tools or safety evaluators**, make sure the Azure project credentials are valid.
> - If you're only doing **text quality evaluation**, the OpenAI endpoint and key are sufficient.

## License

MIT License. See LICENSE for details.
