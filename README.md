# JanDive: Your Private, Local-First Research Agent

JanDive is a powerful, privacy-focused CLI tool that transforms your machine into an intelligent research agent. It leverages a local, quantized Large Language Model (LLM) to perform in-depth, multi-step research on any topic, without your data ever leaving your computer.

Designed for developers, researchers, and privacy-conscious individuals, JanDive combines the power of web search with the intelligence of an LLM to deliver comprehensive, well-structured, and cited reports.

## Why JanDive?

In an era of cloud-based AI, JanDive offers a refreshing alternative by prioritizing privacy, security, and user control.

-   **Privacy by Design**: Because everything runs locally, your queries and research topics remain completely private. There are no third-party servers, no data collection, and no risk of your information being used for training or advertising.
-   **Security First**: JanDive is built with security in mind. It features a sandboxed calculator, safe URL validation to prevent access to local resources, and respectful web scraping practices.
-   **Offline Capability**: The core LLM and calculator tools work entirely offline, making it a reliable tool for research and computation, even without an internet connection.
-   **Extensibility**: The modular, tool-based architecture allows you to easily add new capabilities, such as integrating with new APIs or searching local files.
-   **Cost-Effective**: By using a local, quantized LLM, JanDive eliminates the need for expensive API calls to cloud-based AI services.

## How It Works: The Agentic Workflow

JanDive employs an intelligent agent that mimics the research process of a human analyst. This workflow ensures that the final report is comprehensive, well-supported, and relevant to your query.

1.  **Intelligent Query Generation**: When you provide a query, JanDive doesn't just search for it directly. Instead, it uses its LLM to brainstorm and generate a set of diverse and effective search queries. This multi-query approach ensures broader coverage and uncovers information that a single query might miss.
2.  **Iterative Web Search & Scraping**: The agent then performs a web search for each generated query. It scrapes the content from the top results, filtering out boilerplate and irrelevant text to extract the most valuable information.
3.  **Context Aggregation & Synthesis**: The scraped content is aggregated into a context document. The agent then uses the LLM to read, analyze, and synthesize this information, weaving together findings from multiple sources into a coherent narrative.
4.  **Report Generation**: Finally, the agent generates a well-structured report in Markdown format, complete with an executive summary, detailed findings, and a conclusion. Crucially, every piece of information is cited with the source it came from, allowing you to trace the findings back to the original articles.

This iterative process of searching, scraping, and synthesizing allows JanDive to tackle complex questions and deliver reports with a level of depth that a simple web search cannot match.

## Features

-   **Local & Private**: 100% of the processing happens on your machine. Your data is yours.
-   **LLM-Powered Query Generation**: Uses the LLM to create multiple, high-quality search queries for more comprehensive results.
-   **Enhanced Interactive Mode**:
    -   **LLM Caching**: The LLM is loaded only once per session, making subsequent queries significantly faster.
    -   **Real-time Progress Bar**: A dynamic progress bar and spinner provide clear feedback during research.
    -   **Session Management**: View your query history and save entire research sessions to a file.
    -   **Interactive Configuration**: Adjust settings like temperature and max iterations on the fly.
-   **Robust Web Scraping**:
    -   **Smart Content Extraction**: Intelligently filters out ads, navbars, and other boilerplate.
    -   **Respectful & Safe**: Obeys `robots.txt`, rotates user agents, and validates URLs to protect your system.
-   **GPU Acceleration**: Automatically detects and utilizes NVIDIA GPUs for a significant performance boost.
-   **Offline Mode**: Use the calculator or query the LLM's base knowledge without an internet connection.
-   **Safe Calculator**: A secure, sandboxed calculator for mathematical expressions.
-   **Extensible Architecture**: Easily add new tools to expand JanDive's capabilities.

## Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/JanDive.git
    cd JanDive
    ```

2.  **Create a Virtual Environment** (Recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Enable GPU Acceleration** (Optional, for NVIDIA users):
    For a significant performance increase, install `llama-cpp-python` with CUDA support.
    ```bash
    # Uninstall the CPU version first
    pip uninstall llama-cpp-python
    # Install with CUDA support (ensure you have the CUDA Toolkit installed)
    set CMAKE_ARGS="-DLLAMA_CUDA=on"
    pip install llama-cpp-python
    ```

5.  **Download the Language Model**:
    Run the download script to fetch the quantized LLM.
    ```bash
    python download_model.py
    ```

## Usage

### Single Query Mode

For quick, one-off research tasks.

```bash
python main.py "Your research query"
```
**Example:**
```bash
python main.py "What are the key differences between microservices and monolithic architectures?"
```

### Interactive Mode

For in-depth research sessions, run the script without a query.

```bash
python main.py
```
This will launch an interactive session with LLM caching, history, and more.

**Interactive Commands:**
-   `history`: View your query history for the current session.
-   `save session`: Save your entire session to a Markdown file.
-   `config`: View and change settings like temperature and max iterations.
-   `help`: Display the help menu.
-   `exit` or `quit`: Exit the application.

### Command-Line Options
-   `--output`: Specify an output file for the report.
-   `--max-iterations`: Set the maximum number of search iterations.
-   `--temperature`: Set the temperature for LLM generation (0.0 - 1.0).
-   `--offline`: Run in offline mode (no web search).
-   `--verbose`: Enable detailed logging for debugging.
-   `--concise`: Generate a concise, bullet-point summary.

## Troubleshooting

-   **Slow Performance**: If the application is running slowly, ensure you have enabled GPU acceleration if you have an NVIDIA GPU. The initial model load can also be slow; in interactive mode, this only happens once per session.
-   **Model Not Found**: If you get an error that the model is not found, make sure you have run the `python download_model.py` script successfully.
-   **Stuck Progress Bar**: This issue has been fixed in the latest version. If you encounter it, please ensure you have the latest code.

## Project Structure

```
JanDive/
├── main.py              # CLI entry point and interactive mode logic
├── agent.py             # Core agent workflow and LLM interaction
├── download_model.py    # Script to download the LLM
├── verify_installation.py # Script to verify the installation
├── tools/
│   ├── search_tool.py   # Web search and scraping tool
│   └── calculator_tool.py # Safe calculator tool
├── models/              # Directory for the LLM (created by download script)
├── requirements.txt
└── README.md
```

## License

This project is licensed under the MIT License.
