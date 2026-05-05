import subprocess
import re
import configparser
import os

def load_config(path="config.ini"):
    if not os.path.exists(path):
        print(f"❌ Config file '{path}' not found.")
        print("Please create it based on config.ini.example or the README instructions.")
        raise SystemExit(1)
    config = configparser.ConfigParser()
    config.read(path)
    if "settings" not in config:
        print(f"❌ '{path}' is missing the [settings] section.")
        raise SystemExit(1)
    return config["settings"]

cfg = load_config()
INPUT_FILE = cfg["INPUT_FILE"]
OUTPUT_FILE = cfg["OUTPUT_FILE"]
TARGET_BRANCH_KEYWORD = cfg["TARGET_BRANCH_KEYWORD"]
AUTO_CONFIRM = cfg.getboolean("AUTO_CONFIRM", fallback=False)

def find_matching_branch(repo_url, keyword):
    """
    Use git ls-remote to find remote branches containing the keyword.
    If multiple branches match, ask the user to choose one.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()
        matching_branches = []
        for line in lines:
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                branch = parts[1].replace("refs/heads/", "")
                if keyword in branch:
                    matching_branches.append(branch)
        
        if not matching_branches:
            return None
        elif len(matching_branches) == 1:
            return matching_branches[0]
        else:
            return matching_branches  # Return all for user to choose
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git error: {e}")
        return None


def ask_branch_choice(branches, current_branch):
    """
    Ask the user to choose one branch from a list of matching branches.
    Returns the selected branch or None if skipped.
    """
    print(f"🔀 Multiple matching branches found:")
    for i, branch in enumerate(branches, 1):
        print(f"  {i}. {branch}")
    print(f"  0. Skip (keep {current_branch})")
    
    while True:
        choice = input("👉 Enter your choice: ").strip()
        if choice == "":
            return None
        if choice.isdigit():
            choice_num = int(choice)
            if choice_num == 0:
                return None
            elif 1 <= choice_num <= len(branches):
                return branches[choice_num - 1]
        print(f"Please enter a number between 0 and {len(branches)}.")

def extract_moodle_version(branch_name):
    """
    Extract the numeric Moodle version (e.g. 500 from MOODLE_500_STABLE).
    Returns int or None.
    """
    match = re.search(r'MOODLE_(\d+)_', branch_name, re.IGNORECASE)
    if not match:
        match = re.search(r'(\d{3,})', branch_name)
    return int(match.group(1)) if match else None

def ask_user(prompt):
    """
    Ask the user for confirmation. Returns True if yes, False if no.
    """
    while True:
        choice = input(prompt + " [y/n]: ").strip().lower()
        if choice in ("y", "n"):
            return choice == "y"
        print("Please enter 'y' for yes or 'n' for no.")

def process_submodules(input_file, output_file):
    """
    Read each line in the submodules.sh file, check if the MOODLE_500_STABLE
    branch exists, and interactively update the line if desired.
    """
    use_temp = input_file == output_file
    temp_output = output_file + ".tmp" if use_temp else output_file

    with open(input_file, 'r', encoding='utf-8') as infile, open(temp_output, 'w', encoding='utf-8') as outfile:
        for line in infile:
            if line.strip().startswith("git submodule add"):
                # Match: -b <branch> <repo-url> <path>
                match = re.search(r'-b\s+(\S+)\s+(\S+)\s+(\S+)', line)
                if match:
                    old_branch, url, path = match.groups()
                    print(f"\n🔍 Checking {path} ({url})...")
                    
                    # Skip if already on a branch containing the target keyword
                    if TARGET_BRANCH_KEYWORD in old_branch:
                        print(f"ℹ️ Already on target branch '{old_branch}' – no change needed.")
                        outfile.write(line)
                        continue
                    
                    target_branch = find_matching_branch(url, TARGET_BRANCH_KEYWORD)
                    
                    # Handle multiple matching branches
                    if isinstance(target_branch, list):
                        # Filter out the current branch from choices
                        other_branches = [b for b in target_branch if b != old_branch]
                        if not other_branches:
                            # Current branch is the only match, no change needed
                            print(f"ℹ️ Already on target branch '{old_branch}' – no change needed.")
                            outfile.write(line)
                            continue
                        elif len(other_branches) == 1:
                            target_branch = other_branches[0]
                        else:
                            target_branch = ask_branch_choice(other_branches, old_branch)
                    
                    if target_branch:
                        print(f"✅ Branch '{target_branch}' exists.")

                        old_version = extract_moodle_version(old_branch)
                        new_version = extract_moodle_version(target_branch)

                        if old_version and new_version and new_version < old_version:
                            print(f"⚠️  Skipping downgrade: {old_branch} → {target_branch}")
                            outfile.write(line)
                            continue

                        if old_branch != target_branch:
                            if AUTO_CONFIRM or ask_user(f"👉 Do you want to replace '{old_branch}' with '{target_branch}'?"):
                                new_line = line.replace(old_branch, target_branch)
                                outfile.write(new_line)
                                print("✅ Updated.")
                            else:
                                outfile.write(line)
                                print("⏭️  Skipped.")
                        else:
                            print(f"ℹ️ Already on target branch '{target_branch}' – no change needed.")
                            outfile.write(line)
                    else:
                        print(f"❌ Branch '{TARGET_BRANCH_KEYWORD}' not found – entry left unchanged.")
                        outfile.write(line)
                else:
                    print(f"⚠️ No valid submodule pattern found in line: {line.strip()}")
                    outfile.write(line)
            else:
                # Non-submodule lines are copied as is
                outfile.write(line)
    if use_temp:
        os.replace(temp_output, output_file)
    print(f"\n🎉 Done! Updated file written to: {OUTPUT_FILE}")


def verify_submodules(file_path):
    """
    Verify that all branches in the submodules file exist in their remote repositories.
    Returns True if all branches are valid, False otherwise.
    """
    print(f"\n🔎 Verifying submodules in '{file_path}'...")
    all_valid = True
    checked = 0
    failed = 0
    failed_entries = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith("git submodule add"):
                match = re.search(r'-b\s+(\S+)\s+(\S+)\s+(\S+)', line)
                if match:
                    branch, url, path = match.groups()
                    checked += 1
                    print(f"  🔍 Verifying {path}...", end=" ", flush=True)
                    
                    if branch_exists(url, branch):
                        print(f"✅ '{branch}' exists")
                    else:
                        print(f"❌ '{branch}' NOT FOUND")
                        all_valid = False
                        failed += 1
                        failed_entries.append((path, branch, url))
    
    if failed > 0:
        print("\n" + "=" * 60)
        print("🚨🚨🚨 VERIFICATION FAILED 🚨🚨🚨")
        print("=" * 60)
        print(f"\n❌ {failed} branch(es) not found:\n")
        for path, branch, url in failed_entries:
            print(f"  ⛔ {path}")
            print(f"     Branch: {branch}")
            print(f"     URL: {url}\n")
        print("=" * 60)
        print(f"⚠️  FIX THESE BEFORE PROCEEDING! ({failed}/{checked} failed)")
        print("=" * 60 + "\n")
    else:
        print(f"\n✅ Verification complete: {checked}/{checked} branches valid")
    
    return all_valid


def branch_exists(repo_url, branch_name):
    """
    Check if a specific branch exists in a remote repository.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url, branch_name],
            capture_output=True, text=True, check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False

if __name__ == "__main__":
    process_submodules(INPUT_FILE, OUTPUT_FILE)
    verify_submodules(OUTPUT_FILE)
