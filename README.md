# CodeFetch

Quickly fetch code files from GitHub repositories with simple commands.

CodeFetch is a lightweight command-line utility designed to quickly inspect, preview, and download individual source code files directly from any GitHub repository without needing to clone full repositories.

---

## Features

- **Any User & Repository**: Fetch files from any public GitHub repository using intuitive syntax (`codefetch <user>/<repo> <filename>`).
- **Terminal Preview**: Inspect code directly in your console with `--show` without saving it to disk.
- **Automatic Path & Case Resolution**: Automatically resolves case mismatches (e.g., `exp1.c` -> `EXP1.c`) and finds files nested inside subdirectories.
- **Repository Discovery**: List all public repositories for any GitHub user with `--repos`.
- **Tree Exploration**: List all supported code files within a repository with `--list`.
- **Persistent Defaults**: Configure your preferred default repository and user with `--set-default` and `--set-default-user`.
- **No Dependencies**: Built using the Python standard library with zero third-party runtime dependencies.

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

Fetch a file from any GitHub repository:

```bash
# Fetch from a specific user and repository
codefetch InzamamulQureshi/Codefetch setup.py

# Fetch using explicit flags
codefetch -u InzamamulQureshi -r Codefetch setup.py

# Fetch from a repository under the default user
codefetch DS EXP1.c
codefetch -r DS EXP1.c

# Shorthand path syntax
codefetch DS/EXP1.c

# Fetch from the default repository
codefetch 8.1.py
```

Save to a custom filename or directory using `-o` / `--output`:

```bash
codefetch -r DS EXP1.c -o my_experiment.c
```

### 2. Preview in Terminal (Without Downloading)

Display the contents of a file directly in stdout:

```bash
# Preview file from default repository
codefetch --show 8.1.py

# Preview file from another repository
codefetch --show DS/EXP1.c

# Preview file from any user repository
codefetch --show InzamamulQureshi/Codefetch setup.py
```

### 3. Explore Repositories and Files

```bash
# List all public repositories for default user
codefetch --repos

# List all public repositories for a specific user
codefetch --repos -u InzamamulQureshi
codefetch --repos torvalds

# List code files in the default repository
codefetch --list

# List code files in another repository
codefetch -r DS --list
codefetch --list InzamamulQureshi/Codefetch
```

### 4. Configuration and Defaults

Set persistent default preferences stored in `~/.codefetch.json`:

```bash
# Set default repository
codefetch --set-default DS

# Set default user
codefetch --set-default-user InzamamulQureshi

# View current configuration
codefetch --config

# Reset configuration back to factory defaults
codefetch --reset-config
```

---

## Command Reference

| Flag | Description | Example |
|---|---|---|
| `-r`, `--repo` | Target repository name or URL | `codefetch -r DS EXP1.c` |
| `-u`, `--user` | Target GitHub user or organization | `codefetch -u octocat -r Spoon-Knife --list` |
| `-b`, `--branch` | Branch name (default: `main`) | `codefetch -b main DS EXP1.c` |
| `-s`, `--show` | Print file contents to terminal | `codefetch --show 8.1.py` |
| `-l`, `--list` | List available code files | `codefetch --list DS` |
| `-R`, `--repos` | List public repositories for user | `codefetch --repos -u InzamamulQureshi` |
| `-o`, `--output` | Specify destination output filename | `codefetch -r DS EXP1.c -o local.c` |
| `--set-default` | Set persistent default repository | `codefetch --set-default DS` |
| `--set-default-user` | Set persistent default user | `codefetch --set-default-user InzamamulQureshi` |
| `--config` | Display active configuration | `codefetch --config` |
| `--reset-config` | Reset configuration to defaults | `codefetch --reset-config` |
| `-v`, `--version` | Display version information | `codefetch --version` |
| `-h`, `--help` | Display help and usage message | `codefetch --help` |

---

## Supported File Extensions

CodeFetch recognizes and lists common source and document files:

`.py`, `.c`, `.cpp`, `.h`, `.hpp`, `.java`, `.js`, `.ts`, `.sql`, `.html`, `.css`, `.txt`, `.asm`, `.s`, `.hex`, `.json`, `.sh`, `.rs`, `.go`, `.cs`, `.ipynb`, `.md`

---

## License

This project is licensed under the [MIT License](LICENSE).
