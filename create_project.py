#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Scaffolding Script (v3)

This script interactively scaffolds a new software project based on user input.
It is designed to be run from the command line and has no external dependencies
beyond a standard Python 3 installation.

Features:
- **Language Support:** Scaffolds projects for Python, C++, Rust, and Dart/Flutter.
- **Tooling:**
    - Initializes a Git repository and creates a language-specific .gitignore.
    - Integrates with the GitHub CLI ('gh') to create a remote repository.
    - Generates configuration files for VS Code (.vscode).
    - Adds configuration support for GitHub Copilot.
    - Creates a basic CI workflow for GitHub Actions.
- **AI Developer Integration:**
    - Configures project-specific files for AI tools like Gemini, Cursor, and Claude.
    - Allows enabling various Model Context Protocol (MCP) servers, including custom
      ones for building, file system access, and code analysis.
- **Configuration:**
    - Uses a central config file (~/.dev_scripter/config.ini) to store your
      details like GitHub username and API keys, so you only enter them once.
- **Documentation:**
    - Generates a `doc/GETTING_STARTED.md` file in each new project, detailing
      the setup and outlining the next steps for the developer.

Usage:
1. Save this script as `create_project.py`.
2. Make it executable: `chmod +x create_project.py`
3. Run it from the directory where you want to create your new project: `./create_project.py`
"""

import os
import sys
import json
import subprocess
import configparser
from pathlib import Path
from datetime import datetime

# --- Constants ---
CONFIG_DIR = Path.home() / ".dev_scripter"
CONFIG_FILE = CONFIG_DIR / "config.ini"
SUMMARY_LOG = []
NEXT_STEPS = []

# --- Helper Functions for User Interaction ---

def print_header(title):
    """Prints a formatted header to the console."""
    print("\n" + "=" * (len(title) + 4))
    print(f"  {title}  ")
    print("=" * (len(title) + 4) + "\n")

def ask_question(prompt, default=None):
    """Asks a simple text question."""
    prompt_suffix = f" [{default}]" if default else ""
    answer = input(f"▶ {prompt}{prompt_suffix}: ")
    return answer.strip() or default

def select_one(prompt, options):
    """Prompts the user to select one option from a list."""
    print(f"▶ {prompt}:")
    for i, option in enumerate(options, 1):
        print(f"  {i}) {option}")
    while True:
        try:
            choice = int(input("  Enter number: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print("  Invalid choice. Please try again.")
        except ValueError:
            print("  Please enter a valid number.")

def select_many(prompt, options):
    """Prompts the user to select multiple options from a list."""
    print(f"▶ {prompt} (e.g., '1 3 4', or 'all'):")
    for i, option in enumerate(options, 1):
        print(f"  {i}) {option}")
    while True:
        try:
            raw_input = input("  Enter numbers separated by spaces: ").lower()
            if not raw_input:
                return []
            if raw_input == 'all':
                return options
            choices = [int(c.strip()) for c in raw_input.split()]
            if all(1 <= c <= len(options) for c in choices):
                return [options[c - 1] for c in choices]
            else:
                print("  Invalid choice detected. Please try again.")
        except ValueError:
            print("  Please enter valid numbers separated by spaces.")

def confirm(prompt):
    """Asks a yes/no question."""
    answer = input(f"▶ {prompt} [y/N]: ").lower().strip()
    return answer == 'y'

def run_command(command, cwd, capture_output=False, env=None):
    """Runs a command in a subprocess and handles errors."""
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            check=True,
            text=True,
            capture_output=capture_output,
            env=process_env
        )
        return result
    except FileNotFoundError:
        print(f"  [ERROR] Command not found: {command[0]}. Is it installed and in your PATH?")
        return None
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Command failed: {' '.join(command)}")
        if e.stdout: print(f"  STDOUT: {e.stdout}")
        if e.stderr: print(f"  STDERR: {e.stderr}")
        return None

# --- Configuration Management ---

def get_or_create_config():
    """Reads the global config file, creating it if it doesn't exist."""
    CONFIG_DIR.mkdir(exist_ok=True)
    config = configparser.ConfigParser()

    if not CONFIG_FILE.is_file():
        print("First time setup: Creating global config file...")
        config['USER'] = {'name': 'Your Name', 'email': 'you@example.com', 'github_username': ''}
        config['API_KEYS'] = {
            'gemini': 'YOUR_GEMINI_API_KEY_HERE',
            'anthropic': 'YOUR_ANTHROPIC_API_KEY_HERE',
            'notion': 'YOUR_NOTION_API_KEY_HERE',
            'github_personal_access_token': 'YOUR_GITHUB_PAT_HERE'
        }
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        print(f"  Config file created at: {CONFIG_FILE}")
        print("  Please edit this file to add your details and API keys.")
        sys.exit(0)

    config.read(CONFIG_FILE)

    if not config['USER'].get('github_username'):
        print("Configuration incomplete.")
        gh_user = ask_question("Please enter your GitHub username (for creating repos)")
        if gh_user:
            config['USER']['github_username'] = gh_user
            with open(CONFIG_FILE, 'w') as f:
                config.write(f)

    return config

# --- File Generation ---

def write_file(path, content):
    """Writes content to a file, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n")
    print(f"  ✓ Created {path}")

def get_gitignore_content(language):
    """Returns .gitignore content for a given language."""
    common = """
# General
.DS_Store
*.swp
*.swo
.env
.idea/
build/
dist/

# Scripter Config
/.dev_scripter/
"""
    lang_specific = {
        "Python": """
# Python
__pycache__/
*.pyc
*.pyo
venv/
.pytest_cache/
""",
        "C++": """
# C++
*.o
*.out
*.exe
*.dll
*.so
*.a
CMakeLists.txt.user
**/CMakeCache.txt
**/CMakeFiles/
""",
        "Rust": """
# Rust
/target/
""",
        "Dart/Flutter": """
# Flutter
.dart_tool/
.packages
"""
    }
    return (common + lang_specific.get(language, "")).strip()

def get_vscode_extensions(settings):
    """Returns recommended VS Code extensions."""
    exts = {
        "Python": ["ms-python.python", "ms-python.vscode-pylance", "charliermarsh.ruff"],
        "C++": ["ms-vscode.cpptools", "ms-vscode.cmake-tools"],
        "Rust": ["rust-lang.rust-analyzer", "vadimcn.vscode-lldb"],
        "Dart/Flutter": ["Dart-Code.dart-code", "Dart-Code.flutter"]
    }
    base = ["github.vscode-pull-request-github", "ms-vscode.remote-containers"]
    
    selected_tools = settings.get('ai_tools', [])
    if "Gemini" in selected_tools: base.append("Google.gemini")
    if "Cursor" in selected_tools: base.append("cursor.cursor-vscode")
    if "Claude" in selected_tools: base.append("Anthropic.anthropic-vscode")
    if "GitHub Copilot" in selected_tools: base.extend(["github.copilot", "github.copilot-chat"])
    
    final_exts = base + exts.get(settings['language'], [])
    return json.dumps({"recommendations": sorted(list(set(final_exts)))}, indent=2)

def get_ci_workflow(settings):
    """Generates a basic GitHub Actions CI workflow."""
    lang = settings['language']
    workflow = {
        "Python": """
name: Python CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Test with pytest
      run: pip install pytest && pytest
""",
        "C++": """
name: C++ CI with CMake
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Configure CMake
      run: cmake -B ${{github.workspace}}/build -DCMAKE_BUILD_TYPE=Release
    - name: Build
      run: cmake --build ${{github.workspace}}/build --config Release
    - name: Test
      working-directory: ${{github.workspace}}/build
      run: ctest -C Release
""",
        "Rust": """
name: Rust CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Build
      run: cargo build --verbose
    - name: Run tests
      run: cargo test --verbose
""",
        "Dart/Flutter": """
name: Flutter CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: subosito/flutter-action@v2
      with:
        channel: 'stable'
    - name: Install dependencies
      run: flutter pub get
    - name: Analyze project
      run: flutter analyze
    - name: Run tests
      run: flutter test
"""
    }
    return workflow.get(lang, "# No CI workflow generated for this language yet.")

def get_copilot_config():
    """Returns a basic .github/copilot/config.yml content."""
    return """
# Configuration for GitHub Copilot
github:
  copilot:
    # Exclude specified files and directories from Copilot's context
    excluded:
      - "**/doc/**"
      - "**/.env"
      - "**/GETTING_STARTED.md"
"""

# --- Language Scaffolding ---

def scaffold_python(project_path, settings):
    print_header("Scaffolding Python Project")
    run_command([sys.executable, "-m", "venv", "venv"], cwd=project_path)
    SUMMARY_LOG.append("* **Python Setup:** `venv` with `requirements.txt`.")
    
    reqs = []
    if confirm("Add 'pytest' for testing?"):
        reqs.append("pytest")
        (project_path / "tests").mkdir()
        write_file(project_path / "tests" / "test_sample.py", "def test_example():\n    assert True\n")

    pkgs = select_many("Select common packages to add:", ["pydantic", "requests", "rich"])
    reqs.extend(pkgs)
    
    if reqs:
        write_file(project_path / "requirements.txt", "\n".join(sorted(reqs)))
        SUMMARY_LOG.append(f"* **Python Packages:** `{', '.join(sorted(reqs))}`.")
        NEXT_STEPS.append("Install Python dependencies: `source venv/bin/activate` followed by `pip install -r requirements.txt`.")

def scaffold_cpp(project_path, settings):
    print_header("Scaffolding C++ Project")
    (project_path / "src").mkdir()
    (project_path / "include").mkdir()
    
    main_content = """
#include <iostream>
int main() {
    std::cout << "Hello, C++ World!" << std::endl;
    return 0;
}"""
    write_file(project_path / "src" / "main.cpp", main_content)

    cmake_content = f"""
cmake_minimum_required(VERSION 3.15)
project({settings['project_name']} VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

add_executable(${{PROJECT_NAME}} src/main.cpp)
"""
    
    use_qt = confirm("Set up with Qt support?")
    if use_qt:
        SUMMARY_LOG.append("* **C++ Setup:** CMake with Qt Test support.")
        cmake_content += """
find_package(Qt6 COMPONENTS Widgets Test REQUIRED)
target_link_libraries(${PROJECT_NAME} PRIVATE Qt6::Widgets)

# Add Qt Test setup
enable_testing()
add_executable(run_tests tests/test_main.cpp)
target_link_libraries(run_tests PRIVATE Qt6::Test)
qt_add_test(run_tests run_tests)
"""
        (project_path / "tests").mkdir()
        write_file(project_path / "tests" / "test_main.cpp", """
#include <QtTest/QtTest>
class SampleTest: public QObject {
    Q_OBJECT
private slots:
    void testSample() {
        QVERIFY(true);
    }
};
QTEST_MAIN(SampleTest)
#include "test_main.moc"
""")
        NEXT_STEPS.append("Ensure you have Qt 6 installed and your environment is configured for CMake to find it.")

    else:
        if confirm("Set up with GoogleTest for testing?"):
            SUMMARY_LOG.append("* **C++ Setup:** CMake with GoogleTest.")
            cmake_content += """
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip
)
FetchContent_MakeAvailable(googletest)

enable_testing()
add_executable(run_tests tests/test_main.cpp)
target_link_libraries(run_tests PRIVATE gtest_main)
include(GoogleTest)
gtest_discover_tests(run_tests)
"""
            (project_path / "tests").mkdir()
            write_file(project_path / "tests" / "test_main.cpp", """
#include <gtest/gtest.h>
TEST(SampleTest, AssertionTrue) {
    ASSERT_TRUE(true);
}""")
            NEXT_STEPS.append("Run `ctest` from your build directory to execute tests.")

    write_file(project_path / "CMakeLists.txt", cmake_content)

def scaffold_rust(project_path, settings):
    print_header("Scaffolding Rust Project")
    if not run_command(["rustc", "--version"], cwd="."): return
    # Use 'cargo init' to initialize in the existing directory
    run_command(["cargo", "init"], cwd=project_path)
    
    SUMMARY_LOG.append("* **Rust Setup:** Initialized with `cargo init`.")
    
    crates = select_many("Select common crates to add:", ["serde --features derive", "tokio --features full", "anyhow", "clap --features derive"])
    if crates:
        for crate in crates:
            run_command(["cargo", "add"] + crate.split(), cwd=project_path)
        SUMMARY_LOG.append(f"* **Rust Crates:** `{', '.join(c.split()[0] for c in crates)}`.")
        NEXT_STEPS.append("Run `cargo build` to build the project.")

def scaffold_flutter(project_path, settings):
    print_header("Scaffolding Dart/Flutter Project")
    if not run_command(["flutter", "--version"], cwd="."): return
    run_command(["flutter", "create", str(project_path)], cwd=Path("."))
    SUMMARY_LOG.append("* **Flutter Setup:** Initialized with `flutter create`.")
    
    pkgs = select_many("Select common packages to add:", ["http", "provider", "sqflite", "path_provider"])
    if pkgs:
        for pkg in pkgs:
            run_command(["flutter", "pub", "add", pkg], cwd=project_path)
        SUMMARY_LOG.append(f"* **Flutter Packages:** `{', '.join(pkgs)}`.")
        NEXT_STEPS.append("Run `flutter run` to start your application.")

# --- AI Tooling & MCP Configuration ---

def configure_ai_tools(project_path, settings, config):
    print_header("Configuring AI Developer Tools")
    
    all_servers = {
        "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"}},
        "sequential-thinking": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]},
        "notion": {"command": "npx", "args": ["-y", "mcp-server-notion"], "env": {"NOTION_API_KEY": "${env:NOTION_API_KEY}"}},
        "Context7": {"command": "npx", "args": ["-y", "@upstash/context7-mcp"]},
        "taskmaster-ai": {"command": "npx", "args": ["-y", "--package=task-master-ai", "task-master-ai"], "env": {
            "GEMINI_API_KEY": "${env:GEMINI_API_KEY}", "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}"}},
        "build-system": {"command": "echo", "args": ["build-system-mcp-not-implemented"], "description": "MCP for building/running the project."},
        "filesystem": {"command": "npx", "args": ["-y", "mcp-server-filesystem", "--root", "."], "description": "MCP for sandboxed file system access."},
        "code-ast": {"command": "echo", "args": ["ast-mcp-not-implemented"], "description": "MCP for Abstract Syntax Tree code analysis."}
    }
    
    build_commands = {
        "C++": "cmake --build ./build",
        "Rust": "cargo build",
        "Dart/Flutter": "flutter build",
        "Python": "echo 'No build step for python'"
    }
    all_servers["build-system"]["args"] = build_commands[settings['language']].split()
    all_servers["build-system"]["command"] = all_servers["build-system"]["args"].pop(0)

    enabled_servers = select_many("Select MCP servers to enable:", list(all_servers.keys()))
    if not enabled_servers:
        return

    SUMMARY_LOG.append(f"* **Enabled MCPs:** `{', '.join(enabled_servers)}`.")
    NEXT_STEPS.append("Some MCP servers require Node.js. Run `npm install` in the project root if you encounter `npx` errors.")
    
    if "taskmaster-ai" in enabled_servers:
        NEXT_STEPS.append("IMPORTANT: To complete Taskmaster AI setup, run the following command in your terminal: `npx -y task-master-ai init`")
        SUMMARY_LOG.append("* **AI Config:** Taskmaster AI configured. Manual initialization required (see next steps).")

    mcp_config_obj = {name: all_servers[name] for name in enabled_servers}
    
    selected_tools = settings.get('ai_tools', [])

    if "Gemini" in selected_tools:
        gemini_config = {"contextFileName": "GEMINI.md", "mcpServers": mcp_config_obj}
        write_file(project_path / ".gemini" / "settings.json", json.dumps(gemini_config, indent=2))
        write_file(project_path / "GEMINI.md", f"# Gemini Context for {settings['project_name']}")
        SUMMARY_LOG.append("* **AI Config:** Generated `.gemini/settings.json`.")
    
    if "Cursor" in selected_tools:
        cursor_config_obj = json.loads(json.dumps(mcp_config_obj))
        for server in cursor_config_obj.values():
            if 'env' in server:
                for key, val in server['env'].items():
                    if val.startswith("${env:") and val.endswith("}"):
                        var_name = val[6:-1].split(":")[0]
                        config_key = var_name.replace('_PERSONAL_ACCESS_TOKEN', '').replace('_API_KEY', '').lower()
                        retrieved_key = config['API_KEYS'].get(config_key)
                        if retrieved_key and 'YOUR_' not in retrieved_key:
                            server['env'][key] = retrieved_key
                        else:
                            server['env'][key] = f"YOUR_{var_name}_HERE"
        
        cursor_full_config = {"mcpServers": cursor_config_obj}
        write_file(project_path / ".cursor" / "mcp.json", json.dumps(cursor_full_config, indent=2))
        SUMMARY_LOG.append("* **AI Config:** Generated `.cursor/mcp.json`.")
        NEXT_STEPS.append("Review `.cursor/mcp.json` and replace any placeholder API keys.")

    if "Claude" in selected_tools:
        claude_config = {"mcpServers": mcp_config_obj}
        write_file(project_path / ".claude" / "settings.json", json.dumps(claude_config, indent=2))
        SUMMARY_LOG.append("* **AI Config:** Generated `.claude/settings.json`.")

# --- Main Orchestration ---

def get_project_settings(config):
    """Gathers all project settings from the user."""
    settings = {}
    
    print_header("New Project Setup")
    settings['project_name'] = ask_question("Project Name", "my-new-project")
    settings['language'] = select_one("Select Primary Language", ["Python", "C++", "Rust", "Dart/Flutter"])
    
    settings['use_docker'] = confirm("Add Docker configuration (Dockerfile)?")
    settings['use_ci'] = confirm("Add basic GitHub Actions CI workflow?")
    settings['use_github'] = confirm("Initialize on GitHub (requires 'gh' CLI)?")
    
    settings['ai_tools'] = select_many("Configure for which AI tools?", ["Gemini", "Cursor", "Claude", "GitHub Copilot"])
    
    return settings

def main():
    """Main script execution function."""
    
    config = get_or_create_config()
    settings = get_project_settings(config)
    
    project_name = settings['project_name']
    project_path = Path(project_name)

    if project_path.exists():
        print(f"\n[ERROR] Directory '{project_name}' already exists. Aborting.")
        return

    print_header(f"Creating Project: {project_name}")
    project_path.mkdir()

    SUMMARY_LOG.append(f"* **Project:** `{project_name}`")
    SUMMARY_LOG.append(f"* **Language:** {settings['language']}")
    
    run_command(["git", "init"], cwd=project_path)
    write_file(project_path / ".gitignore", get_gitignore_content(settings['language']))

    lang_scaffolders = {
        "Python": scaffold_python,
        "C++": scaffold_cpp,
        "Rust": scaffold_rust,
        "Dart/Flutter": scaffold_flutter,
    }
    lang_scaffolders[settings['language']](project_path, settings)

    print_header("Configuring Tooling")
    
    write_file(project_path / ".vscode" / "extensions.json", get_vscode_extensions(settings))
    SUMMARY_LOG.append("* **IDE:** Generated `.vscode/extensions.json`.")
    NEXT_STEPS.append("If using VS Code, open the project and install recommended extensions when prompted.")

    if settings['use_docker']:
        write_file(project_path / "Dockerfile", f"# Dockerfile for {settings['language']} project\nFROM busybox")
        SUMMARY_LOG.append("* **Containerization:** Added a placeholder `Dockerfile`.")
    
    if settings['use_ci']:
        write_file(project_path / ".github/workflows/ci.yml", get_ci_workflow(settings))
        SUMMARY_LOG.append("* **CI/CD:** Added basic GitHub Actions workflow.")
    
    if "GitHub Copilot" in settings['ai_tools']:
        write_file(project_path / ".github/copilot/config.yml", get_copilot_config())
        SUMMARY_LOG.append("* **GitHub Copilot:** Added `.github/copilot/config.yml` to exclude files.")

    if settings['ai_tools']:
        configure_ai_tools(project_path, settings, config)
        
    if settings['use_github']:
        gh_user = config['USER']['github_username']
        if gh_user:
            if run_command(["gh", "repo", "create", f"{gh_user}/{project_name}", "--private", "-y"], cwd=project_path):
                SUMMARY_LOG.append(f"* **GitHub:** Created private repository `{gh_user}/{project_name}`.")
                NEXT_STEPS.append("Push the initial commit to GitHub: `git add . && git commit -m 'Initial commit' && git push -u origin main`.")
        else:
            print("  [Skipped] GitHub repo creation requires a username in the config.")

    print_header("Generating Final Documentation")
    
    (project_path / "doc").mkdir(exist_ok=True)
    getting_started = f"""
# Getting Started with {project_name}

This project was scaffolded on {datetime.now().strftime("%Y-%m-%d")}.
Here is a summary of the configuration and your next steps.

## Project Summary

"""
    getting_started += "\n".join(sorted(SUMMARY_LOG))
    
    if NEXT_STEPS:
        getting_started += "\n\n## Next Steps\n\n"
        for i, step in enumerate(sorted(list(set(NEXT_STEPS))), 1):
            getting_started += f"{i}. {step}\n"
            
    write_file(project_path / "doc" / "GETTING_STARTED.md", getting_started)
    
    print_header("✅ Project Scaffolding Complete!")
    print(f"Your new project is ready at: ./{project_name}")
    print(f"A summary and next steps guide has been created at: ./{project_name}/doc/GETTING_STARTED.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting.")
        sys.exit(0)