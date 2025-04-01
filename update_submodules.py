import subprocess
import tempfile
import shutil
import re

# Input and output filenames
INPUT_FILE = "submodules.sh"
OUTPUT_FILE = "submodules_updated.sh"
TARGET_BRANCH = "MOODLE_500_STABLE"

def check_remote_branch_exists(repo_url, branch):
    """
    Clone the repository as a bare clone and check if the target branch exists.
    """
    tmp_dir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["git", "clone", "--bare", "--quiet", repo_url, tmp_dir],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        result = subprocess.run(
            ["git", "--git-dir", tmp_dir, "show-ref", "--verify", f"refs/heads/{branch}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False
    finally:
        shutil.rmtree(tmp_dir)

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
                    if check_remote_branch_exists(url, TARGET_BRANCH):
                        print(f"✅ Branch '{TARGET_BRANCH}' exists.")
                        if old_branch != TARGET_BRANCH:
                            if ask_user(f"👉 Do you want to replace '{old_branch}' with '{TARGET_BRANCH}'?"):
                                new_line = line.replace(old_branch, TARGET_BRANCH)
                                outfile.write(new_line)
                                print("✅ Updated.")
                            else:
                                outfile.write(line)
                                print("⏭️  Skipped.")
                        else:
                            print(f"ℹ️ Already on target branch '{TARGET_BRANCH}' – no change needed.")
                            outfile.write(line)
                    else:
                        print(f"❌ Branch '{TARGET_BRANCH}' not found – entry left unchanged.")
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
