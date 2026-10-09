# CodeFetch

Quickly fetch code files from GitHub repositories with simple commands.

CodeFetch is a lightweight command-line utility and Python library designed to quickly inspect, preview, and download individual source code files directly from any GitHub repository without needing to clone full repositories.

---

## Features

- **Any User & Repository**: Fetch files from any public GitHub repository using intuitive syntax (`codefetch <owner>/<repo> <filename>`).
- **Terminal Preview**: Inspect code directly in your console with `--show` without saving it to disk.
- **Automatic Path & Case Resolution**: Automatically resolves case mismatches and finds files nested inside subdirectories.
- **Repository Discovery**: List all public repositories for any GitHub user with `--repos`.
- **Tree Exploration**: List all supported code files within a repository with `--list`.
- **Self-Updating**: Keep CodeFetch updated to the latest PyPI release with `codefetch --update`.
- **Python Library Support**: Import and use programmatically with `import codefetch as cf`.
- **Optional Persistent Defaults**: Save a default repository or user with `--set-default` if you frequently work with the same repository.
- **Zero Runtime Dependencies**: Built using only the Python standard library with zero third-party dependencies.

---

## Installation

### From PyPI

```bash
pip install codefetch-cli
```

### From GitHub

```bash
pip install git+https://github.com/InzamamulQureshi/Codefetch.git
```

### From Local Source

Clone the repository and install locally:

```bash
git clone https://github.com/InzamamulQureshi/Codefetch.git
cd Codefetch
pip install .
```

---

## Quick Start & Usage

### 1. Download Files

Fetch a single file from any GitHub repository:

```bash
# Fetch a file from any user and repository
codefetch owner/repo main.py

# Download a configuration or dataset
codefetch owner/repo data.csv
codefetch owner/repo config.yaml

# Download using explicit flags
codefetch -u owner -r repo main.py

# Save with a custom filename or destination path
codefetch owner/repo main.py -o custom_name.py
```

### 2. Preview in Terminal (Without Downloading)

Display the contents of a file directly in stdout with `-s` / `--show`:

```bash
# Preview file content in terminal
codefetch -s owner/repo main.py
codefetch -s torvalds/linux Makefile
```

### 3. Explore Repositories and Files

```bash
# List all code files in a repository
codefetch -l owner/repo
codefetch --list owner/repo

# List all public repositories for any GitHub user
codefetch -R -u username
codefetch --repos username
```

### 4. Configuration and Defaults (Optional)

By default, CodeFetch has no preset repository or user. If you frequently fetch files from the same repository, you can optionally configure defaults:

```bash
# Set a default repository (saves both user and repo)
codefetch --set-default owner/repo

# Now you can fetch files directly without typing the repo name!
codefetch main.py
codefetch -l

# View current saved configuration
codefetch --config

# Reset all configuration back to defaults (no default repository)
codefetch --reset-config
```

### 5. Self-Updating

```bash
# Update CodeFetch to the latest version published on PyPI
codefetch --update
```

---

## Python API Usage

You can also use CodeFetch programmatically within your Python scripts:

```python
import codefetch as cf

# 1. Fetch file content as a string directly in memory
makefile_text = cf.get("torvalds/linux", "Makefile")
# Or shorthand single argument syntax:
readme_text = cf.get("psf/requests/README.md")

# 2. Download a file to disk
cf.download("torvalds/linux", "Makefile", output="linux_Makefile")

# 3. List all code files in a repository
files = cf.list("torvalds/linux")
print(f"Found {len(files)} files")
```

---

## Command Reference

| Flag | Description | Example |
|---|---|---|
| `-s`, `--show` | Print file contents to terminal | `codefetch -s owner/repo main.py` |
| `-o`, `--output` | Specify destination output filename | `codefetch owner/repo main.py -o script.py` |
| `-l`, `--list` | List available code files in a repository | `codefetch -l owner/repo` |
| `-R`, `--repos` | List public repositories for a user | `codefetch -R -u username` |
| `-r`, `--repo` | Specify repository name or URL | `codefetch -r repo main.py` |
| `-u`, `--user` | Specify GitHub username or organization | `codefetch -u username -r repo main.py` |
| `-b`, `--branch` | Branch name (default: repo default branch) | `codefetch -b master owner/repo Makefile` |
| `--set-default` | Set persistent default repository | `codefetch --set-default owner/repo` |
| `--set-default-user` | Set persistent default user | `codefetch --set-default-user username` |
| `--config` | Display active configuration | `codefetch --config` |
| `--reset-config` | Reset configuration back to defaults | `codefetch --reset-config` |
| `-U`, `--update` | Update CodeFetch to latest PyPI version | `codefetch --update` |
| `-v`, `--version` | Display version information | `codefetch --version` |
| `-h`, `--help` | Display help and usage message | `codefetch --help` |

---

## Supported File Extensions

CodeFetch recognizes and lists common source and document files:

- **Data & Tables**: `.csv`, `.tsv`, `.json`, `.jsonl`, `.yaml`, `.yml`, `.toml`, `.xml`, `.ini`, `.cfg`, `.conf`, `.env`
- **Data Science**: `.ipynb`, `.py`, `.r`, `.rmd`, `.m`
- **Languages**: `.c`, `.cpp`, `.h`, `.hpp`, `.rs`, `.go`, `.java`, `.kt`, `.cs`, `.swift`, `.dart`, `.php`
- **Web**: `.html`, `.css`, `.scss`, `.js`, `.jsx`, `.ts`, `.tsx`, `.vue`, `.svelte`
- **Scripts & Systems**: `.sh`, `.bash`, `.zsh`, `.fish`, `.bat`, `.cmd`, `.ps1`, `.lua`, `.rb`, `.asm`, `.s`, `.hex`
- **Database & Schemas**: `.sql`, `.graphql`, `.gql`, `.proto`
- **Documentation**: `.md`, `.markdown`, `.rst`, `.txt`, `.tex`, `.log`
- **Build Files**: `Dockerfile`, `Makefile`, `CMakeLists.txt`, `Gemfile`, `Procfile`

---

## License

This project is licensed under the [MIT License](LICENSE).
