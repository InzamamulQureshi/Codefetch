"""
CodeFetch CLI
Quickly fetch code files from GitHub repositories with simple commands.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_OWNER = None
DEFAULT_REPO = None
DEFAULT_BRANCH = "main"

CONFIG_FILE = Path.home() / ".codefetch.json"

# Supported code, data, and config extensions
CODE_EXTENSIONS = {
    # Data & Tables
    ".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".toml",
    ".xml", ".ini", ".cfg", ".conf", ".env", ".properties",
    # Python & Data Science
    ".py", ".pyw", ".ipynb", ".r", ".rmd", ".m",
    # C / C++ / Systems
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx", ".rs", ".go",
    # JVM & .NET
    ".java", ".kt", ".kts", ".scala", ".cs", ".fs", ".vb",
    # Web & Frontend
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".vue", ".svelte", ".php",
    # Mobile & Apple
    ".swift", ".dart",
    # Scripts & Shells
    ".sh", ".bash", ".zsh", ".fish", ".bat", ".cmd", ".ps1", ".psm1",
    ".lua", ".rb", ".pl", ".pm",
    # Assembly & Hardware
    ".asm", ".s", ".hex", ".v", ".sv", ".vhdl", ".vhd",
    # Database & Schema
    ".sql", ".graphql", ".gql", ".proto",
    # Documents & Text
    ".txt", ".text", ".md", ".markdown", ".rst", ".tex", ".log"
}

# Recognized extensionless or special build files
NAMED_FILES = {
    "dockerfile", "makefile", "gemfile", "procfile", "vagrantfile",
    "cmakelists.txt", "jenkinsfile", "license"
}

HELP_MESSAGE = """\
CodeFetch - Download single code files from GitHub without cloning entire repos.

USAGE:
  codefetch <owner>/<repo> <filename>      Download a file from any GitHub repository
  codefetch <filename>                     Download a file (requires default repository)

QUICK EXAMPLES:
  Download a file:
    codefetch torvalds/linux Makefile        Save Makefile to current directory
    codefetch owner/repo main.py             Save main.py from a repository
    codefetch owner/repo data.csv -o out.csv Save with a custom output filename

  View code in terminal (without downloading):
    codefetch -s owner/repo main.py          Display main.py in terminal
    codefetch -s torvalds/linux Makefile     Display Makefile in terminal

  Browse files and repositories:
    codefetch -l owner/repo                  List all code files in a repository
    codefetch -R -u <username>               List all public repositories of a user
    codefetch -R <username>                  List all public repositories of a user

SETTINGS & DEFAULTS (Optional):
  codefetch --set-default <owner/repo>     Set a permanent default repository
  codefetch --set-default-user <username>  Set a permanent default GitHub user
  codefetch --config                       View current saved settings
  codefetch --reset-config                 Clear saved settings

OPTIONS:
  -s, --show             View file contents in terminal instead of saving
  -o, --output <file>    Custom filename or path to save the downloaded file
  -l, --list [repo]      List available code files in a repository
  -R, --repos [user]     List all public repositories for a user
  -r, --repo <name>      Specify repository name or URL
  -u, --user <name>      Specify GitHub username
  -b, --branch <name>    Specify branch name (default: main)
  -v, --version          Show version number
  -h, --help             Show this help guide
"""


def load_config():
    """Load configuration from environment variables and local config file."""
    config = {
        "owner": os.environ.get("CODEFETCH_USER", DEFAULT_OWNER),
        "repo": os.environ.get("CODEFETCH_REPO", DEFAULT_REPO),
        "branch": os.environ.get("CODEFETCH_BRANCH", DEFAULT_BRANCH),
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    if saved.get("owner"):
                        config["owner"] = saved["owner"]
                    if saved.get("repo"):
                        config["repo"] = saved["repo"]
                    if saved.get("branch"):
                        config["branch"] = saved["branch"]
        except Exception:
            pass
    return config


def save_config(owner=None, repo=None, branch=None):
    """Save configuration to ~/.codefetch.json."""
    config = load_config()
    if owner:
        config["owner"] = owner
    if repo:
        config["repo"] = repo
    if branch:
        config["branch"] = branch
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False


def get_headers():
    """Get HTTP headers for GitHub requests."""
    headers = {
        "User-Agent": "codefetch",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(url):
    """Fetch and decode JSON from a URL."""
    request = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_repo_identifier(repo_str, default_owner=None):
    """Extract (owner, repo) from a repository flag, name, or URL."""
    if not repo_str:
        return default_owner, None
    repo_str = repo_str.strip()
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git|/.*)?$",
        repo_str,
        re.IGNORECASE,
    )
    if m:
        return m.group(1), m.group(2)
    if "/" in repo_str:
        parts = repo_str.split("/", 1)
        return parts[0], parts[1].removesuffix(".git")
    return default_owner, repo_str.removesuffix(".git")


def get_repo_tree(owner, repo, branch="main"):
    """Fetch the Git tree for a repository, with fallback to master if main is absent."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    try:
        return get_json(url)
    except urllib.error.HTTPError as e:
        if e.code == 404 and branch == "main":
            url_master = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
            try:
                return get_json(url_master)
            except Exception:
                pass
        raise


def get_user_repos(owner):
    """Fetch public repositories for a given GitHub owner."""
    url = f"https://api.github.com/users/{owner}/repos?per_page=100&sort=updated"
    try:
        return get_json(url)
    except Exception:
        return []


def list_repos(owner=None, default_repo=None):
    """List all public repositories for the owner."""
    if not owner:
        print("Error: No GitHub user specified.\n")
        print("Usage:")
        print("  codefetch -R <username>")
        print("  codefetch -R -u <username>")
        return

    try:
        repos = get_user_repos(owner)
        if not repos:
            print(f"No public repositories found for user '{owner}'.")
            return

        print(f"Repositories for '{owner}':\n")
        for r in repos:
            name = r.get("name", "")
            desc = r.get("description") or ""
            is_def = " (default)" if default_repo and name.lower() == default_repo.lower() else ""
            marker = "*" if is_def else "-"
            desc_text = f" - {desc}" if desc else ""
            print(f"  {marker} {name}{is_def}{desc_text}")

        print("\nCommands:")
        print(f"  codefetch -l {owner}/<repo>                  List files in a repository")
        print(f"  codefetch {owner}/<repo> <filename>          Download a file from a repository")
        print(f"  codefetch --set-default {owner}/<repo>       Set default repository")

    except urllib.error.HTTPError as e:
        print(f"Could not list repositories: HTTP {e.code}")
    except urllib.error.URLError:
        print("Could not connect to GitHub.")
    except Exception as e:
        print(f"Could not list repositories: {e}")


def list_files(owner, repo, branch="main"):
    """List code files in a repository."""
    if not owner or not repo:
        print("Error: No repository specified to list.\n")
        print("Usage:")
        print("  codefetch -l <owner>/<repo>")
        print("  codefetch -u <owner> -r <repo> -l")
        return

    try:
        data = get_repo_tree(owner, repo, branch)
        if data.get("truncated"):
            print("Warning: GitHub returned a truncated file list.")

        files = []
        for item in data.get("tree", []):
            if item.get("type") != "blob":
                continue

            path = item.get("path", "")
            base_name = path.rsplit("/", 1)[-1].lower()
            suffix = ""
            if "." in base_name:
                suffix = "." + base_name.rsplit(".", 1)[-1]

            if suffix in CODE_EXTENSIONS or base_name in NAMED_FILES:
                files.append(path)

        files.sort(key=str.lower)

        if not files:
            print(f"No supported code files found in {owner}/{repo}.")
            return

        print(f"Available files in {owner}/{repo} ({branch}):\n")
        for i, path in enumerate(files, 1):
            print(f"{i:>3}. {path}")

        print(f"\nTotal: {len(files)} files")

    except urllib.error.HTTPError as e:
        print(f"Could not list files for {owner}/{repo}: HTTP {e.code}")
    except urllib.error.URLError:
        print("Could not connect to GitHub.")
    except Exception as e:
        print(f"Could not list files for {owner}/{repo}: {e}")


def get_stem(name):
    """Extract filename stem by stripping supported code extensions."""
    name_lower = name.lower()
    for ext in CODE_EXTENSIONS:
        if name_lower.endswith(ext):
            return name[:-len(ext)]
    return name


def resolve_file_in_tree(tree_data, target_filename):
    """
    Search tree for target_filename:
    1. Exact match (case-insensitive) on full path
    2. Exact match (case-insensitive) on basename
    3. Match without extension (e.g. 'main' -> 'main.py')
    """
    blobs = [item["path"] for item in tree_data.get("tree", []) if item.get("type") == "blob"]
    target_clean = target_filename.strip("/\\").lower()
    target_base = target_clean.rsplit("/", 1)[-1]

    # 1. Exact match (case-insensitive) on full path
    for p in blobs:
        if p.lower() == target_clean:
            return p

    # 2. Exact match (case-insensitive) on basename
    for p in blobs:
        base = p.rsplit("/", 1)[-1].lower()
        if base == target_base:
            return p

    # 3. Match without extension
    target_stem = get_stem(target_base).lower()
    candidates = []
    for p in blobs:
        base = p.rsplit("/", 1)[-1]
        base_stem = get_stem(base).lower()
        if base_stem == target_stem:
            candidates.append(p)

    if len(candidates) == 1:
        return candidates[0]

    return None


def find_file_in_other_repos(owner, current_repo, target_filename):
    """Search other public repositories of the user for the target file."""
    if not owner:
        return None, None
    try:
        repos_data = get_user_repos(owner)
        for r in repos_data:
            r_name = r.get("name")
            if not r_name or (current_repo and r_name.lower() == current_repo.lower()):
                continue
            default_branch = r.get("default_branch", "main")
            try:
                tree_data = get_repo_tree(owner, r_name, default_branch)
                match = resolve_file_in_tree(tree_data, target_filename)
                if match:
                    return r_name, match
            except Exception:
                continue
    except Exception:
        pass
    return None, None


def fetch_file(filename, owner=None, repo=None, branch=DEFAULT_BRANCH,
               show=False, output=None):
    """Fetch or download a file from GitHub."""
    if not owner or not repo:
        print("Error: No GitHub repository specified.\n")
        print("Usage:")
        print("  codefetch <owner>/<repo> <filename>")
        print("  codefetch -u <owner> -r <repo> <filename>\n")
        print("To set a default repository:")
        print("  codefetch --set-default <owner>/<repo>\n")
        print("Run 'codefetch --help' for more options.")
        return

    clean_filename = filename.strip("/\\")

    def download_url(url):
        req = urllib.request.Request(url, headers={"User-Agent": "codefetch"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")

    # 1. Direct raw fetch first (fastest, preserves GitHub API rate limit)
    raw_base = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    url = f"{raw_base}/{clean_filename}"

    content = None
    resolved_path = clean_filename

    try:
        content = download_url(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # 2. Direct fetch 404ed. Try smart resolution with repo tree
            try:
                tree_data = get_repo_tree(owner, repo, branch)
                matched = resolve_file_in_tree(tree_data, clean_filename)
                if matched:
                    resolved_path = matched
                    content = download_url(f"{raw_base}/{resolved_path}")
                    if resolved_path != clean_filename:
                        print(f"(Resolved '{clean_filename}' -> '{resolved_path}')")
                else:
                    # Check other public repositories for the same user
                    other_repo, other_match = find_file_in_other_repos(owner, repo, clean_filename)
                    if other_repo:
                        print(f"File not found: '{clean_filename}' in {owner}/{repo}.")
                        print(f"\n[Tip] Found '{other_match}' in repository '{other_repo}'!")
                        print(f"To fetch it, run:\n  codefetch {owner}/{other_repo} {other_match}")
                        return
                    else:
                        print(f"File not found: '{clean_filename}' in {owner}/{repo}.")
                        print(f"Run 'codefetch -l {owner}/{repo}' to see available files.")
                        return
            except Exception:
                print(f"File not found: '{clean_filename}' in {owner}/{repo}.")
                return
        else:
            print(f"Download failed: HTTP {e.code}")
            return
    except urllib.error.URLError:
        print("Could not connect to GitHub.")
        return
    except UnicodeDecodeError:
        print("The file is not UTF-8 text, so it cannot be displayed or saved as text.")
        return

    if content is None:
        return

    if show:
        print(content)
    else:
        out_name = output or resolved_path.rsplit("/", 1)[-1]
        try:
            with open(out_name, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Downloaded: {out_name} (from {owner}/{repo})")
        except Exception as e:
            print(f"Error saving file '{out_name}': {e}")


class CodefetchParser(argparse.ArgumentParser):
    """Custom parser providing clean, intuitive help formatting."""

    def format_help(self):
        return HELP_MESSAGE

    def error(self, message):
        sys.stderr.write(f"Error: {message}\n\nRun 'codefetch --help' for usage instructions.\n")
        sys.exit(2)


def build_parser():
    """Build argument parser with full CLI options."""
    parser = CodefetchParser(
        prog="codefetch",
        add_help=True,
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="Target specification: <owner>/<repo> <filename> or <filename>",
    )
    parser.add_argument(
        "-r", "--repo",
        default=None,
        help="Repository name or URL (e.g. repo or owner/repo)",
    )
    parser.add_argument(
        "-u", "--user",
        default=None,
        help="GitHub user/org name",
    )
    parser.add_argument(
        "-b", "--branch",
        default=None,
        help=f"Branch name (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List available code files in the repository",
    )
    parser.add_argument(
        "-R", "--repos",
        action="store_true",
        help="List all public repositories for a user",
    )
    parser.add_argument(
        "-s", "--show",
        action="store_true",
        help="Display file content in terminal without saving to disk",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Custom destination filename or output path",
    )
    parser.add_argument(
        "--set-default",
        metavar="REPO",
        help="Set persistent default repository in local config",
    )
    parser.add_argument(
        "--set-default-user",
        metavar="USER",
        help="Set persistent default GitHub user in local config",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Display current CodeFetch configuration",
    )
    parser.add_argument(
        "--reset-config",
        action="store_true",
        help="Reset configuration back to defaults",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="codefetch 1.2.2",
    )
    return parser


def resolve_invocation(positional_args, repo_flag, user_flag, branch_flag,
                       default_owner, default_repo, default_branch):
    """
    Resolve arguments into (owner, repo, branch, filename).
    """
    owner = user_flag or default_owner
    repo = default_repo
    branch = branch_flag or default_branch
    filename = None

    if repo_flag:
        flag_owner, flag_repo = parse_repo_identifier(repo_flag, default_owner=owner)
        owner = flag_owner
        repo = flag_repo
        if positional_args:
            filename = positional_args[0]
        return owner, repo, branch, filename

    if not positional_args:
        return owner, repo, branch, None

    if len(positional_args) >= 2:
        first, second = positional_args[0], positional_args[1]
        p_owner, p_repo = parse_repo_identifier(first, default_owner=owner)
        return p_owner, p_repo, branch, second

    target = positional_args[0].strip()

    # 1. Full GitHub web URL
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)$", target, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).removesuffix(".git"), m.group(3), m.group(4)

    # 2. Raw GitHub URL
    m = re.match(r"https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)$", target, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2), m.group(3), m.group(4)

    # 3. Colon syntax: user/repo:filename
    if ":" in target:
        repo_part, file_part = target.split(":", 1)
        p_owner, p_repo = parse_repo_identifier(repo_part, default_owner=owner)
        return p_owner, p_repo, branch, file_part

    # 4. Multi-part slash syntax: user/repo/filename
    parts = target.split("/")
    if len(parts) >= 3:
        return parts[0], parts[1], branch, "/".join(parts[2:])

    if len(parts) == 2:
        if owner:
            return owner, parts[0], branch, parts[1]
        else:
            return parts[0], parts[1], branch, None

    # Single filename, e.g. main.py (requires default_owner and default_repo)
    return owner, repo, branch, target


def main():
    parser = build_parser()
    args = parser.parse_args()

    config = load_config()
    default_owner = config.get("owner", DEFAULT_OWNER)
    default_repo = config.get("repo", DEFAULT_REPO)
    default_branch = config.get("branch", DEFAULT_BRANCH)

    # Handle --reset-config
    if args.reset_config:
        if CONFIG_FILE.exists():
            try:
                CONFIG_FILE.unlink()
            except Exception as e:
                print(f"Error removing config file: {e}")
                return
        print("Configuration reset to defaults (no default repository or user).")
        return

    # Handle --set-default-user
    if args.set_default_user:
        save_config(owner=args.set_default_user)
        print(f"Default user updated to: '{args.set_default_user}'")
        print(f"Saved to: {CONFIG_FILE}")
        return

    # Handle --set-default
    if args.set_default:
        owner_part, repo_part = parse_repo_identifier(args.set_default, default_owner=args.user)
        owner_to_save = owner_part or (args.user if args.user else None)
        save_config(owner=owner_to_save, repo=repo_part)
        print(f"Default repository updated to: '{repo_part}'")
        if owner_to_save:
            print(f"Default user updated to: '{owner_to_save}'")
        print(f"Saved to: {CONFIG_FILE}")
        return

    # Handle --config
    if args.config:
        print("CodeFetch Configuration:")
        print(f"  Default User:        {default_owner or 'None (not set)'}")
        print(f"  Default Repository:  {default_repo or 'None (not set)'}")
        print(f"  Default Branch:      {default_branch}")
        print(f"  Config File:         {CONFIG_FILE}")
        return

    owner = args.user or default_owner
    branch = args.branch or default_branch

    # Handle --repos (list repositories)
    if args.repos:
        target_owner = owner
        if args.args:
            target_owner = args.args[0]
        if not target_owner:
            print("Error: No GitHub user specified.\n")
            print("Usage:")
            print("  codefetch --repos <username>")
            print("  codefetch -R -u <username>")
            return
        list_repos(owner=target_owner, default_repo=default_repo)
        return

    # Handle --list
    if args.list:
        target_owner = owner
        target_repo = default_repo
        if args.repo:
            target_owner, target_repo = parse_repo_identifier(args.repo, default_owner=owner)
        elif args.args:
            target_owner, target_repo = parse_repo_identifier(args.args[0], default_owner=owner)
        if not target_owner or not target_repo:
            print("Error: No repository specified to list.\n")
            print("Usage:")
            print("  codefetch -l <owner>/<repo>")
            print("  codefetch -u <owner> -r <repo> -l")
            return
        list_files(owner=target_owner, repo=target_repo, branch=branch)
        return

    # If no action and no files provided, print the clean help guide
    if not args.args and not args.repo:
        parser.print_help()
        return

    resolved_owner, resolved_repo, resolved_branch, resolved_filename = resolve_invocation(
        args.args,
        args.repo,
        args.user,
        args.branch,
        default_owner,
        default_repo,
        default_branch,
    )

    if not resolved_filename:
        print("Error: No filename specified.\n")
        print("Usage:")
        print("  codefetch <owner>/<repo> <filename>")
        print("  codefetch --help                      View full guide and examples")
        return

    fetch_file(
        filename=resolved_filename,
        owner=resolved_owner,
        repo=resolved_repo,
        branch=resolved_branch,
        show=args.show,
        output=args.output,
    )


if __name__ == "__main__":
    main()
