# moodle-submodule-updater

🔄 A CLI tool to check and update Git submodules of Moodle plugins to the `*500*` branch, with interactive confirmation for each change.

---

## 🚀 Features

- Parses a `.sh` file that adds Moodle plugin submodules (e.g. `git submodule add -b MOODLE_404_STABLE ...`)
- Checks if a `500` branch exists in each plugin repository
- Asks interactively before updating the submodule definition
- Writes the results to a new updated `.sh` file
- No changes are made without your confirmation

---

## 📂 Input Format

The tool expects a shell script file (`submodules.sh`) with lines like:

```bash
git submodule add -b MOODLE_404_STABLE https://github.com/BLC-FHGR/moodle-theme_boost_union.git theme/boost_union
```

---

## 🧰 Requirements

- Python 3.6+
- Git CLI installed and available in `$PATH`

---

## 📦 Installation

No installation needed. Just clone the repo and run the script:

```bash
git clone https://github.com/ramhee98/moodle-submodule-updater
cd moodle-submodule-updater
python3 update_submodules.py
```

---

## ⚙️ Configuration

The script reads settings from a `config.ini` file in the root folder. Example:

```ini
[settings]
INPUT_FILE = submodules.sh
OUTPUT_FILE = submodules_updated.sh
TARGET_BRANCH_KEYWORD = 500
AUTO_CONFIRM = False

```
- INPUT_FILE: Path to the shell script containing Moodle plugin submodules.
- OUTPUT_FILE: Path to the output file where updated entries will be written.
- TARGET_BRANCH_KEYWORD: The keyword used to detect target branches (e.g. 500 for MOODLE_500_STABLE, MOODLE500...).
- AUTO_CONFIRM: If set to `true`, all valid updates will be applied without prompting.

---

## 📝 Usage

1. Prepare your `submodules.sh` file with Moodle plugin submodules.
2. Adjust the `config.ini` file if needed.
3. Run the script:

   ```bash
   python3 update_submodules.py
   ```

4. For each plugin that has a `*500*` branch, you’ll be asked to replace the old branch with the new one:

   ```
   👉 Do you want to replace 'MOODLE_404_STABLE' with 'MOODLE_500_STABLE'? [y/n]:
   ```

5. A (new) file called `submodules_updated.sh` will be created with the updated lines.

---

## 🧪 Example Output

```
🔍 Checking theme/boost_union (https://github.com/BLC-FHGR/moodle-theme_boost_union.git)...
✅ Branch 'MOODLE_500_STABLE' exists.
👉 Do you want to replace 'MOODLE_404_STABLE' with 'MOODLE_500_STABLE'? [y/n]: y
✅ Updated.

🔍 Checking mod/checklist (https://github.com/sam/moodle-mod_checklist.git)...
❌ Branch 'MOODLE_500_STABLE' not found – entry left unchanged.
```

---

## ✅ License

**MIT License**  
Free to use, modify, and distribute.

---

## 🤝 Contributions

Pull requests welcome! If you find a bug or want a new feature, feel free to open an issue or fork the project.