#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project Scaffolding Script (v7)

This script interactively scaffolds a new software project based on user input.
It supports both single-language projects and complex, multi-language monorepos.

Features:
- **Project Types:**
    - **Single-Language:** Standard project structure.
    - **Multi-Language:** Creates a subdirectory for each language, each with its
      own build system, plus a top-level script to build all components.
- **Language Support:** Scaffolds projects for Python, C++, Rust, and Dart/Flutter.
- **Tooling:**
    - Initializes a Git repository with 'main' as the default branch.
    - Integrates with the GitHub CLI ('gh') to create a new remote repository
      or use an existing one gracefully.
    - Generates configuration for VS Code and GitHub Copilot.
    - Creates a CI workflow for GitHub Actions adapted for the project type.
- **AI Developer Integration:**
    - Configures project-specific files for AI tools like Gemini, Cursor, and Claude.
    - The "Build System" MCP is configured to use the top-level build script in
      multi-language projects.
- **Configuration:**
    - Uses a central config file (~/.dev_scripter/config.ini) for user details and API keys.
- **Documentation:**
    - Generates a `doc/GETTING_STARTED.md` file detailing the specific setup and next steps.

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

def get_gitignore_content(languages):
    """Returns .gitignore content for a given list of languages."""
    common = "# General\n.DS_Store\n*.swp\n*.swo\n.env\n.idea/\nbuild/\ndist/\n\n# Scripter Config\n/.dev_scripter/\n"
    lang_specific_map = {
        "Python": "# Python\n__pycache__/\n*.pyc\n*.pyo\nvenv/\n.pytest_cache/\n",
        "C++": "# C++\n*.o\n*.out\n*.exe\n*.dll\n*.so\n*.a\nCMakeLists.txt.user\n**/CMakeCache.txt\n**/CMakeFiles/\n",
        "Rust": "# Rust\n# Ignore all target directories\n**/target/\n",
        "Dart/Flutter": "# Flutter\n.dart_tool/\n.packages\n",
    }
    lang_specific_content = "\n".join(lang_specific_map.get(lang, "") for lang in languages)
    return (common + "\n" + lang_specific_content).strip()

def get_vscode_extensions(settings):
    """Returns recommended VS Code extensions for a list of languages."""
    ext_map = {
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
    
    final_exts = set(base)
    for lang in settings['languages']:
        final_exts.update(ext_map.get(lang, []))
        
    return json.dumps({"recommendations": sorted(list(final_exts))}, indent=2)

def get_ci_workflow(settings):
    """Generates a GitHub Actions workflow appropriate for the project type."""
    is_multilang = len(settings.get('languages', [])) > 1
    
    if is_multilang:
        return """
name: Multi-Language CI
on: [push, pull_request]
jobs:
  build_all:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up build environment (install dependencies if needed)
      # e.g., sudo apt-get update && sudo apt-get install -y cmake g++ ...
      run: echo "Setting up environment..."
    - name: Run top-level build script
      run: chmod +x build.sh && ./build.sh
"""
    # Fallback to single-language CI logic
    lang = settings['languages'][0] if settings.get('languages') else ''
    workflow_map = {
        "Python": "name: Python CI\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n    - uses: actions/checkout@v4\n    - name: Set up Python\n      uses: actions/setup-python@v4\n      with:\n        python-version: '3.11'\n    - name: Install dependencies\n      run: |\n        python -m pip install --upgrade pip\n        pip install -r requirements.txt\n    - name: Test with pytest\n      run: pip install pytest && pytest\n",
        "C++": "name: C++ CI with CMake\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n    - uses: actions/checkout@v4\n    - name: Configure CMake\n      run: cmake -B ${{github.workspace}}/build -DCMAKE_BUILD_TYPE=Release\n    - name: Build\n      run: cmake --build ${{github.workspace}}/build --config Release\n    - name: Test\n      working-directory: ${{github.workspace}}/build\n      run: ctest -C Release\n",
        "Rust": "name: Rust CI\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n    - uses: actions/checkout@v4\n    - name: Build\n      run: cargo build --verbose\n    - name: Run tests\n      run: cargo test --verbose\n",
        "Dart/Flutter": "name: Flutter CI\non: [push, pull_request]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n    - uses: actions/checkout@v4\n    - uses: subosito/flutter-action@v2\n      with:\n        channel: 'stable'\n    - name: Install dependencies\n      run: flutter pub get\n    - name: Analyze project\n      run: flutter analyze\n    - name: Run tests\n      run: flutter test\n"
    }
    return workflow_map.get(lang, "# No CI workflow generated for this language yet.")

def get_copilot_config():
    """Returns a basic .github/copilot/config.yml content."""
    return "# Configuration for GitHub Copilot\ngithub:\n  copilot:\n    excluded:\n      - \"**/doc/**\"\n      - \"**/.env\"\n      - \"**/GETTING_STARTED.md\"\n"

def generate_toplevel_build_script(project_path, components):
    """Generates the top-level build.sh script."""
    build_script_content = "#!/bin/bash\n# Exit immediately if a command fails.\nset -e\n"
    build_commands = {
        "C++": "cmake --build ./build",
        "Rust": "cargo build",
        "Dart/Flutter": "flutter build",
        "Python": "echo 'Python component has no build step.'"
    }
    for comp in components:
        cmd = build_commands.get(comp['lang'])
        if cmd:
            build_script_content += f"""
echo ""
echo "--- Building {comp['lang']} component ({comp['name']}) ---"
(cd {comp['name']} && {cmd})
"""
    build_script_content += '\necho ""\necho "All components built successfully!"\n'
    write_file(project_path / "build.sh", build_script_content)
    # Make it executable
    (project_path / "build.sh").chmod(0o755)

# --- Language Scaffolding ---

def scaffold_python(component_path, settings):
    print(f"  > Scaffolding Python in ./{component_path.name}")
    run_command([sys.executable, "-m", "venv", "venv"], cwd=component_path)
    SUMMARY_LOG.append(f"* **Component `{component_path.name}` (Python):** `venv` with `requirements.txt`.")
    reqs = []
    if confirm("  Add 'pytest' for this component?"):
        reqs.append("pytest")
        (component_path / "tests").mkdir()
        write_file(component_path / "tests" / "test_sample.py", "def test_example():\n    assert True\n")
    pkgs = select_many("  Select Python packages for this component:", ["pydantic", "requests", "rich"])
    reqs.extend(pkgs)
    if reqs:
        write_file(component_path / "requirements.txt", "\n".join(sorted(reqs)))

def scaffold_cpp(component_path, settings):
    print(f"  > Scaffolding C++ in ./{component_path.name}")
    (component_path / "src").mkdir()
    (component_path / "include").mkdir()
    write_file(component_path / "src" / "main.cpp", '#include <iostream>\nint main() {\n    std::cout << "Hello, C++ World!" << std::endl;\n    return 0;\n}')
    cmake_content = f"cmake_minimum_required(VERSION 3.15)\nproject({component_path.name} VERSION 1.0)\n\nset(CMAKE_CXX_STANDARD 17)\nset(CMAKE_CXX_STANDARD_REQUIRED True)\n\nadd_executable(${{PROJECT_NAME}} src/main.cpp)\n"
    if confirm("  Set up with Qt support for this component?"):
        cmake_content += "find_package(Qt6 COMPONENTS Widgets Test REQUIRED)\ntarget_link_libraries(${PROJECT_NAME} PRIVATE Qt6::Widgets)\nenable_testing()\nadd_executable(run_tests tests/test_main.cpp)\ntarget_link_libraries(run_tests PRIVATE Qt6::Test)\nqt_add_test(run_tests run_tests)\n"
        (component_path / "tests").mkdir()
        write_file(component_path / "tests" / "test_main.cpp", '#include <QtTest/QtTest>\nclass SampleTest: public QObject {\n    Q_OBJECT\nprivate slots:\n    void testSample() { QVERIFY(true); }\n};\nQTEST_MAIN(SampleTest)\n#include "test_main.moc"')
    elif confirm("  Set up with GoogleTest for this component?"):
        cmake_content += "include(FetchContent)\nFetchContent_Declare(\n  googletest\n  URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.zip\n)\nFetchContent_MakeAvailable(googletest)\n\nenable_testing()\nadd_executable(run_tests tests/test_main.cpp)\ntarget_link_libraries(run_tests PRIVATE gtest_main)\ninclude(GoogleTest)\ngtest_discover_tests(run_tests)\n"
        (component_path / "tests").mkdir()
        write_file(component_path / "tests" / "test_main.cpp", '#include <gtest/gtest.h>\nTEST(SampleTest, AssertionTrue) {\n    ASSERT_TRUE(true);\n}')
    write_file(component_path / "CMakeLists.txt", cmake_content)
    SUMMARY_LOG.append(f"* **Component `{component_path.name}` (C++):** CMake project.")

def scaffold_rust(component_path, settings):
    print(f"  > Scaffolding Rust in ./{component_path.name}")
    if not run_command(["rustc", "--version"], cwd="."): return
    run_command(["cargo", "init"], cwd=component_path)
    SUMMARY_LOG.append(f"* **Component `{component_path.name}` (Rust):** Initialized with `cargo init`.")
    crates = select_many("  Select Rust crates for this component:", ["serde --features derive", "tokio --features full", "anyhow", "clap --features derive"])
    if crates:
        for crate in crates:
            run_command(["cargo", "add"] + crate.split(), cwd=component_path)

def scaffold_flutter(component_path, settings):
    # Flutter must create its own directory.
    print(f"  > Scaffolding Flutter in ./{component_path.name}")
    if not run_command(["flutter", "--version"], cwd="."): return
    run_command(["flutter", "create", component_path.name], cwd=component_path.parent)
    SUMMARY_LOG.append(f"* **Component `{component_path.name}` (Dart/Flutter):** Initialized with `flutter create`.")
    pkgs = select_many("  Select Flutter packages for this component:", ["http", "provider", "sqflite", "path_provider"])
    if pkgs:
        for pkg in pkgs:
            run_command(["flutter", "pub", "add", pkg], cwd=component_path)

# --- AI Tooling & MCP Configuration ---

def configure_ai_tools(project_path, settings, components):
    print_header("Configuring AI Developer Tools")
    
    all_servers = {
        "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "${env:GITHUB_PERSONAL_ACCESS_TOKEN}"}},
        "sequential-thinking": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"]},
        "notion": {"command": "npx", "args": ["-y", "mcp-server-notion"], "env": {"NOTION_API_KEY": "${env:NOTION_API_KEY}"}},
        "Context7": {"command": "npx", "args": ["-y", "@upstash/context7-mcp"]},
        "taskmaster-ai": {"command": "npx", "args": ["-y", "--package=task-master-ai", "task-master-ai"], "env": {
            "GEMINI_API_KEY": "${env:GEMINI_API_KEY}", "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}"}},
        "build-system": {"command": "./build.sh", "args": [], "description": "MCP for building all project components."},
        "filesystem": {"command": "npx", "args": ["-y", "mcp-server-filesystem", "--root", "."], "description": "MCP for sandboxed file system access."},
        "code-ast": {"command": "echo", "args": ["ast-mcp-not-implemented"], "description": "MCP for Abstract Syntax Tree code analysis."}
    }
    
    if len(components) <= 1: # Single language project
        build_commands = { "C++": "cmake --build ./build", "Rust": "cargo build", "Dart/Flutter": "flutter build", "Python": "echo 'Python component has no build step.'"}
        lang = components[0]['lang'] if components else ''
        if lang in build_commands:
            all_servers['build-system']['command'] = build_commands[lang].split()[0]
            all_servers['build-system']['args'] = build_commands[lang].split()[1:]
    
    enabled_servers = select_many("Select MCP servers to enable:", list(all_servers.keys()))
    if not enabled_servers: return

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
                        retrieved_key = settings['config']['API_KEYS'].get(config_key)
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
    settings = {'config': config}
    
    print_header("New Project Setup")
    settings['project_name'] = ask_question("Project Name", "my-new-project")
    
    project_type = select_one("Select project type:", ["Single-Language", "Multi-Language"])
    all_langs = ["Python", "C++", "Rust", "Dart/Flutter"]
    if project_type == "Single-Language":
        settings['languages'] = [select_one("Select Primary Language:", all_langs)]
    else:
        settings['languages'] = select_many("Select languages to include:", all_langs)

    if not settings['languages']:
        print("\nNo languages selected. Aborting.")
        sys.exit(0)

    settings['use_docker'] = confirm("Add Docker configuration (Dockerfile)?")
    settings['use_ci'] = confirm("Add basic GitHub Actions CI workflow?")
    settings['use_github'] = confirm("Initialize on GitHub (requires 'gh' CLI)?")
    
    settings['ai_tools'] = select_many("Configure for which AI tools?", ["Gemini", "Cursor", "Claude", "GitHub Copilot"])
    
    return settings

def main():
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
    SUMMARY_LOG.append(f"* **Project Type:** {'Multi-Language' if len(settings['languages']) > 1 else 'Single-Language'}")
    
    run_command(["git", "init", "-b", "main"], cwd=project_path)
    write_file(project_path / ".gitignore", get_gitignore_content(settings['languages']))

    print_header("Scaffolding Language Components")
    language_components = []
    is_multilang = len(settings['languages']) > 1
    
    lang_scaffolders = {
        "Python": scaffold_python, "C++": scaffold_cpp,
        "Rust": scaffold_rust, "Dart/Flutter": scaffold_flutter,
    }

    for lang in settings['languages']:
        component_name = lang.lower()
        if is_multilang:
            component_name = ask_question(f"  Enter subdirectory name for {lang}", default=lang.lower())
        
        component_path = project_path / component_name if is_multilang else project_path

        if lang != "Dart/Flutter" and is_multilang:
            component_path.mkdir()
        
        lang_scaffolders[lang](component_path, settings)
        language_components.append({'name': component_name, 'lang': lang})

    print_header("Configuring Top-Level Tooling")
    
    if is_multilang:
        generate_toplevel_build_script(project_path, language_components)
        SUMMARY_LOG.append("* **Build System:** Top-level `build.sh` script created.")

    write_file(project_path / ".vscode" / "extensions.json", get_vscode_extensions(settings))
    SUMMARY_LOG.append("* **IDE:** Generated `.vscode/extensions.json` for all selected languages.")
    NEXT_STEPS.append("If using VS Code, open the project and install recommended extensions when prompted.")

    if settings['use_docker']:
        write_file(project_path / "Dockerfile", f"# Dockerfile for {project_name}\nFROM busybox")
        SUMMARY_LOG.append("* **Containerization:** Added a placeholder `Dockerfile`.")
    
    if settings['use_ci']:
        write_file(project_path / ".github/workflows/ci.yml", get_ci_workflow(settings))
        SUMMARY_LOG.append("* **CI/CD:** Added basic GitHub Actions workflow.")
    
    if "GitHub Copilot" in settings['ai_tools']:
        write_file(project_path / ".github/copilot/config.yml", get_copilot_config())
        SUMMARY_LOG.append("* **GitHub Copilot:** Added `.github/copilot/config.yml`.")

    if any(tool in settings['ai_tools'] for tool in ["Gemini", "Cursor", "Claude"]):
        configure_ai_tools(project_path, settings, language_components)
        
    if settings['use_github']:
        gh_user = config['USER'].get('github_username')
        if gh_user:
            repo_full_name = f"{gh_user}/{project_name}"
            print(f"  Checking for GitHub repository {repo_full_name}...")
            repo_check = subprocess.run(["gh", "repo", "view", repo_full_name], capture_output=True, text=True)
            if repo_check.returncode == 0:
                print(f"  ✓ Repository {repo_full_name} already exists. Using existing repository.")
                SUMMARY_LOG.append(f"* **GitHub:** Using existing repository `{repo_full_name}`.")
                subprocess.run(["git", "remote", "remove", "origin"], cwd=project_path, capture_output=True)
                run_command(["git", "remote", "add", "origin", f"https://github.com/{repo_full_name}.git"], cwd=project_path)
            else:
                print(f"  Repository does not exist. Creating...")
                if run_command(["gh", "repo", "create", repo_full_name, "--private", "-y"], cwd=project_path):
                    SUMMARY_LOG.append(f"* **GitHub:** Created new private repository `{repo_full_name}`.")
            NEXT_STEPS.append("Push the initial commit to GitHub: `git add . && git commit -m 'Initial commit' && git push -u origin main`.")
        else:
            print("  [Skipped] GitHub repo creation requires a username in the config file.")

    print_header("Generating Final Documentation")
    (project_path / "doc").mkdir(exist_ok=True)
    getting_started = f"# Getting Started with {project_name}\n\nThis project was scaffolded on {datetime.now().strftime('%Y-%m-%d')}.\nHere is a summary of the configuration and your next steps.\n\n## Project Summary\n\n"
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
        
