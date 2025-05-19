import subprocess
import re
import configparser

def load_config(path="config.ini"):
    config = configparser.ConfigParser()
    config.read(path)
    return config["settings"]

cfg = load_config()
INPUT_FILE = cfg["INPUT_FILE"]
OUTPUT_FILE = cfg["OUTPUT_FILE"]
TARGET_BRANCH_KEYWORD = cfg["TARGET_BRANCH_KEYWORD"]
AUTO_CONFIRM = cfg.getboolean("AUTO_CONFIRM", fallback=False)

def find_matching_branch(repo_url, keyword):
    """
    Use git ls-remote to find remote branches containing the keyword.
    """
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", repo_url],
            capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                branch = parts[1].replace("refs/heads/", "")
                if keyword in branch:
                    return branch
        return None
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git error: {e}")
        return None

def extract_moodle_version(branch_name):
    """
    Extract the numeric Moodle version (e.g. 500 from MOODLE_500_STABLE).
    Returns int or None.
    """
    match = re.search(r'(\d{3})', branch_name)
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
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', encoding='utf-8') as outfile:

        for line in infile:
            if line.strip().startswith("git submodule add"):
                # Match: -b <branch> <repo-url> <path>
                match = re.search(r'-b\s+(\S+)\s+(\S+)\s+(\S+)', line)
                if match:
                    old_branch, url, path = match.groups()
                    print(f"\n🔍 Checking {path} ({url})...")
                    target_branch = find_matching_branch(url, TARGET_BRANCH_KEYWORD)
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

if __name__ == "__main__":
    process_submodules(INPUT_FILE, OUTPUT_FILE)
    print(f"\n🎉 Done! Updated file written to: {OUTPUT_FILE}")
