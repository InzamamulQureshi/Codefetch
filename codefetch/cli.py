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

__version__ = "1.2.3"

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
  codefetch <filename>                     Download a file (uses saved default repo)
  codefetch -s <owner>/<repo> <filename>   Preview file in terminal without saving
  codefetch -l <owner>/<repo>              List all code files in a repository
  codefetch -R <username>                  List public repositories for a user

POPULAR EXAMPLES:
  # Download from any repository:
  codefetch owner/repo main.py
  codefetch torvalds/linux Makefile

  # Preview code directly in terminal:
  codefetch -s owner/repo app.js
  codefetch -s torvalds/linux Makefile

  # Save with a custom name or path:
  codefetch owner/repo data.csv -o my_data.csv

  # Explore repositories and files:
  codefetch -l torvalds/linux              # list files in a repo
  codefetch -R torvalds                    # list repos belonging to user

SETTING A DEFAULT REPOSITORY (OPTIONAL):
  If you frequently work with the same repo, you can set it as default:
  codefetch --set-default owner/repo       # sets default repo
  codefetch script.py                      # now you don't need to type owner/repo!
  codefetch --config                       # view active configuration
  codefetch --reset-config                 # reset all defaults

FLAGS & OPTIONS:
  -s, --show                Print file content to terminal instead of downloading
  -o, --output <file>       Specify output filename or path
  -l, --list                List available code files in the repository
  -R, --repos               List public repositories for a GitHub user
  -r, --repo <repo>         Specify repository name or URL
  -u, --user <user>         Specify GitHub username / organization
  -b, --branch <branch>     Specify branch name (default: main)
  --set-default <repo>      Save default repository (e.g. owner/repo)
  --set-default-user <user> Save default user/organization
  --config                  Show current saved configuration
  --reset-config            Reset configuration back to defaults
  -v, --version             Show version number
  -h, --help                Show this help message
"""


def load_config():
    """Load user configuration from ~/.codefetch.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(owner=None, repo=None, branch=None):
    """Save user configuration to ~/.codefetch.json."""
    cfg = load_config()
    if owner is not None:
        cfg["owner"] = owner
    if repo is not None:
        cfg["repo"] = repo
    if branch is not None:
        cfg["branch"] = branch

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save configuration: {e}")


def get_headers():
    """Build request headers, attaching GITHUB_TOKEN if present in environment."""
    headers = {
        "User-Agent": "codefetch",
        "Accept": "application/vnd.github+json",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json(url):
    """Fetch JSON from GitHub API with rate limit handling."""
    req = urllib.request.Request(url, headers=get_headers())
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


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


def fetch_raw_direct(owner, repo, branch, clean_filename):
    """
    Direct raw fetch from raw.githubusercontent.com.
    Tries requested branch first. If branch is 'main', also tries 'master',
    and vice versa.
    Returns (branch_used, content_str) or (None, None).
    """
    branches_to_try = [branch]
    if branch == "main":
        branches_to_try.append("master")
    elif branch == "master":
        branches_to_try.append("main")

    for b in branches_to_try:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/{clean_filename}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "codefetch"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return b, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
    return None, None


def get_repo_tree_with_branch(owner, repo, branch="main"):
    """
    Fetch the Git tree for a repository, returning (actual_branch, tree_data).
    Tries branch first, then fallback to master/main, then checks repository info for default_branch.
    """
    branches_to_try = [branch]
    if branch == "main":
        branches_to_try.append("master")
    elif branch == "master":
        branches_to_try.append("main")

    for b in branches_to_try:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{b}?recursive=1"
        try:
            return b, get_json(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise

    # Query repository info to discover actual default branch (e.g. develop, trunk, etc.)
    try:
        info_url = f"https://api.github.com/repos/{owner}/{repo}"
        info = get_json(info_url)
        def_branch = info.get("default_branch")
        if def_branch and def_branch not in branches_to_try:
            url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{def_branch}?recursive=1"
            return def_branch, get_json(url)
    except Exception:
        pass

    raise urllib.error.HTTPError(
        f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}",
        404,
        "Branch tree not found",
        {},
        None,
    )


def get_repo_tree(owner, repo, branch="main"):
    """Fetch the Git tree for a repository (backwards compatible helper)."""
    _, tree_data = get_repo_tree_with_branch(owner, repo, branch)
    return tree_data


def get_user_repos(owner):
    """Fetch public repositories list for a user."""
    url = f"https://api.github.com/users/{owner}/repos?per_page=100&sort=updated"
    return get_json(url)


def list_repos(owner=None, default_repo=None):
    """List all public repositories for a GitHub user."""
    if not owner:
        print("Error: No GitHub username specified.")
        print("Usage: codefetch --repos <username>")
        return

    try:
        repos = get_user_repos(owner)
        if not repos:
            print(f"No public repositories found for user '{owner}'.")
            return

        print(f"Public repositories for '{owner}':\n")
        for i, r in enumerate(repos, 1):
            name = r.get("name", "")
            desc = r.get("description") or "No description"
            is_def = " (default)" if default_repo and name.lower() == default_repo.lower() else ""
            marker = "*" if is_def else "-"
            print(f"  {marker} {name:<22}{is_def}")
            if desc and desc != "No description":
                print(f"      {desc}")

        print(f"\nTotal: {len(repos)} repositories")
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
        actual_branch, data = get_repo_tree_with_branch(owner, repo, branch)
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
            print(f"No supported code files found in {owner}/{repo} ({actual_branch}).")
            return

        print(f"Available files in {owner}/{repo} ({actual_branch}):\n")
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

    content = None
    resolved_path = clean_filename
    actual_branch = branch

    # 1. Direct raw fetch first (fastest, preserves GitHub API rate limit)
    try:
        found_branch, raw_content = fetch_raw_direct(owner, repo, branch, clean_filename)
        if raw_content is not None:
            actual_branch = found_branch
            content = raw_content
    except UnicodeDecodeError:
        print("The file is not UTF-8 text, so it cannot be displayed or saved as text.")
        return
    except urllib.error.HTTPError as e:
        print(f"Download failed: HTTP {e.code}")
        return
    except urllib.error.URLError:
        print("Could not connect to GitHub.")
        return

    # 2. If direct fetch didn't find the file (404), fall back to smart repository tree search
    if content is None:
        try:
            actual_branch, tree_data = get_repo_tree_with_branch(owner, repo, branch)
            matched = resolve_file_in_tree(tree_data, clean_filename)
            if matched:
                resolved_path = matched
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{actual_branch}/{resolved_path}"
                content = download_url(raw_url)
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
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"Repository or branch not found: {owner}/{repo} ({branch})")
            else:
                print(f"Could not search repository: HTTP {e.code}")
            return
        except urllib.error.URLError:
            print("Could not connect to GitHub.")
            return
        except UnicodeDecodeError:
            print("The file is not UTF-8 text, so it cannot be displayed or saved as text.")
            return
        except Exception:
            print(f"File not found: '{clean_filename}' in {owner}/{repo}.")
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
            print(f"Downloaded: {out_name} (from {owner}/{repo}@{actual_branch})")
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
    parser = CodefetchParser(
        prog="codefetch",
        description="Fetch code files from GitHub repositories.",
        add_help=False,
    )

    parser.add_argument("args", nargs="*", help="Repository and filename targets")
    parser.add_argument("-s", "--show", action="store_true", help="Print file content to terminal")
    parser.add_argument("-l", "--list", action="store_true", help="List code files in repository")
    parser.add_argument("-R", "--repos", action="store_true", help="List public repositories for a user")
    parser.add_argument("-r", "--repo", type=str, help="Repository name or URL")
    parser.add_argument("-u", "--user", type=str, help="GitHub username")
    parser.add_argument("-b", "--branch", type=str, help="Branch name (default: main)")
    parser.add_argument("-o", "--output", type=str, help="Custom output filename or path")
    parser.add_argument("--set-default", type=str, help="Save default repository (e.g. owner/repo)")
    parser.add_argument("--set-default-user", type=str, help="Save default GitHub user")
    parser.add_argument("--config", action="store_true", help="Display active configuration")
    parser.add_argument("--reset-config", action="store_true", help="Reset configuration back to defaults")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-h", "--help", action="help", help="Show help message")

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
