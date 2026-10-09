"""
CodeFetch - Easily preview and download code files from GitHub repositories.

Usage in Python:
    import codefetch as cf

    # 1. Fetch file content as string:
    content = cf.get("torvalds/linux", "Makefile")
    # or shorthand target string:
    content = cf.get("torvalds/linux/Makefile")

    # 2. Download file to local disk:
    cf.download("torvalds/linux", "Makefile", output="linux_makefile.txt")

    # 3. List available code files:
    files = cf.list("torvalds/linux")
"""

__version__ = "1.2.6"


def get(target, filename=None, branch=None):
    """
    Fetch and return the text content of a file from GitHub.

    Args:
        target: 'owner/repo' or full path 'owner/repo/path/to/file' or full GitHub URL.
        filename: Optional path to file in repo if target is 'owner/repo'.
        branch: Branch name (default: None, automatically detects repo default branch).

    Returns:
        str: File content.

    Raises:
        FileNotFoundError: If the file does not exist in the repository.
        ValueError: If arguments cannot be resolved into a repository and filename.
    """
    import urllib.request
    from .cli import (
        get_default_branch,
        check_branch_exists,
        fetch_raw_single,
        get_repo_tree,
        resolve_file_in_tree,
        parse_repo_identifier,
        resolve_invocation,
    )

    if filename:
        owner, repo = parse_repo_identifier(target)
        file_path = filename.strip("/\\")
    else:
        owner, repo, resolved_branch, file_path = resolve_invocation(
            [target], None, None, branch, None, None
        )
        if resolved_branch:
            branch = resolved_branch

    if not owner or not repo or not file_path:
        raise ValueError(f"Could not resolve owner, repo, and filename from target='{target}', filename='{filename}'")

    target_branch = branch
    if not target_branch:
        target_branch = get_default_branch(owner, repo)
    elif not check_branch_exists(owner, repo, target_branch):
        target_branch = get_default_branch(owner, repo)

    # 1. Try fast direct raw fetch
    content = fetch_raw_single(owner, repo, target_branch, file_path)
    if content is not None:
        return content

    # 2. Try repository tree search
    tree_data = get_repo_tree(owner, repo, target_branch)
    matched = resolve_file_in_tree(tree_data, file_path)
    if matched:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{target_branch}/{matched}"
        req = urllib.request.Request(url, headers={"User-Agent": "codefetch"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")

    raise FileNotFoundError(f"File '{file_path}' not found in {owner}/{repo} ({target_branch})")


def download(target, filename=None, output=None, branch=None):
    """
    Download a file from GitHub and save it locally.

    Args:
        target: 'owner/repo' or full path 'owner/repo/path/to/file'.
        filename: Optional path to file in repo if target is 'owner/repo'.
        output: Destination filename/path on local disk (default: original filename).
        branch: Branch name (default: None, automatically detects repo default branch).

    Returns:
        str: Path to the downloaded file.
    """
    content = get(target, filename=filename, branch=branch)
    dest_name = output
    if not dest_name:
        resolved_file = filename if filename else target.rsplit("/", 1)[-1]
        dest_name = resolved_file.rsplit("/", 1)[-1]

    with open(dest_name, "w", encoding="utf-8") as f:
        f.write(content)

    return dest_name


def list(target, branch=None):
    """
    List supported code files in a repository.

    Args:
        target: 'owner/repo' or repository URL.
        branch: Branch name (default: None, automatically detects repo default branch).

    Returns:
        list[str]: Relative paths of code files in the repository.
    """
    from .cli import (
        parse_repo_identifier,
        get_default_branch,
        check_branch_exists,
        get_repo_tree,
        CODE_EXTENSIONS,
        NAMED_FILES,
    )

    owner, repo = parse_repo_identifier(target)
    if not owner or not repo:
        raise ValueError(f"Invalid repository identifier: '{target}'")

    target_branch = branch
    if not target_branch or not check_branch_exists(owner, repo, target_branch):
        target_branch = get_default_branch(owner, repo)

    tree_data = get_repo_tree(owner, repo, target_branch)
    files = []
    for item in tree_data.get("tree", []):
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
    return files


__all__ = [
    "__version__",
    "get",
    "download",
    "list",
]
