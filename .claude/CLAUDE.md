# Instructions for LLMs 
*Such as Claude, CoPilot, etc*

## Specific to using claude on my local machine:

1. Don't mention to me about IDE spellchecker warnings in .md files, code files, or in comments. 
2. When writing a new code block or document, add a comment at the top that says, "Written by [LLM name] ([LLM Model]) on [dd MMM, yyyy], for Alex Larkin". When composing a markdown file, do the same string after the document title, with the prefix, "Note: ". Put the note in _italics_.
3. At the top of each file, include a comment that says, "LLMs: refer to instructions in `Instructions_for_LLMs.md`, located at the root of the current workspace. (If you can't find the file, ignore this note.)"
4. Whenever possible, I prefer to use GitHub Desktop over git via the terminal. 
5. Never hard-code file paths. Rather, use MacroUserDataManager.bas. See MacroUserDataManager_README.md for context. In a context where calling a macro from MacroUserDataManager.bas isn't practical, use Environmental variables. Include in comments (just once per file) how to set Environmental variables. 
6. All .mdata files should go in my `imakuna/Data_Files` folder
7. Most preferred language is Python. For projects involving Word, Excel, or PowerPoint, VBA is most preferred. PowerShell can also be used when needed. Feel free to suggest another language, but explain first why Python, VBA, and PowerShell wouldn't be good options. 
8. When I start a new chat with a Claude LLM and it's already set to Opus or Mythos, remind me at the end of your first answer that I'm on Claude (or Mythos). 

## Copied from Claude account settings:

Be to-the-point, but don't be afraid to make suggestions or supply context when relevant. If you have a better idea for approaching a programming task, suggest it. If you need more context to generate a good answer, just let me know.

Please take some extra time whenever needed to think carefully and develop a well thought-out and well-researched answer. Double-check your work and double-check your sources. 

When it comes to programming, take the attitude of a private tutor. Help me to learn and uncover my blind spots and holes in my knowledge.

I run Windows 11 and have an Android phone. When I ask for Regex help, know that I'm using Notepad++.

## User Data and Data File Protocol


### Quick Reference

**Python scripts** → Use YAML (`.yaml` files)  
**VBA macros** → Use custom `.mdata` files

### Why These Formats?

#### Python and PowerShell: YAML
- Supports comments with `#`
- Human-readable
- Built-in Python support via `pyyaml` library
- Industry standard for configuration files

#### VBA: Custom .mdata
- VBA predates modern formats (JSON, XML)
- No external dependencies
- Simple to parse (just read line-by-line)
- Full control over format

### Format Examples

#### YAML Example (Python)
```yaml
# Comments start with #
paths:
  input_directory: ./input
  output_directory: ./output

settings:
  language_code: qva
  encoding: utf-8
```

#### .mdata Example (VBA)
```
' Comments start with apostrophe (must be on own line)

{CategoryName}
[VariableName]
Value

{Paths}
[InputDirectory]
./input
```

### Core Implementation Rules

#### Both Formats Must:
1. **Auto-create** when missing (with sensible defaults), but not with personal info
2. **Use relative paths when possible** (`./folder`) not absolute (`C:\Users\...`)
3. **Include helpful comments** in generated defaults

#### Python Code Pattern
```python
import yaml
import os

def load_config(config_path='config.yaml'):
    if not os.path.exists(config_path):
        # Create with defaults
        default_config = {'paths': {'input': './input'}}
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f)
        return default_config
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
```

#### VBA Code Pattern
```vba
' Read a value - returns String, Collection, or Empty if not found
' File path is handled internally via %W_PROD% environment variable
Dim myValue As Variant
myValue = ReadDataValue("CategoryName", "VariableName")

If IsEmpty(myValue) Then
    ' Variable not found - optionally use ReadDataValueWithPrompt instead
    ' to auto-prompt user and save their input
End If

' Or use ReadDataValueWithPrompt for auto-prompting on missing values
myValue = ReadDataValueWithPrompt("MacroName", "CategoryName", "VariableName", _
    True, "Description of what this variable is for")
```
See **MacroUserDataManager.bas** and **MacroUserDataManager_README.md** for full instructions.

### GitHub Requirements

#### Never Commit:
- User-specific paths
- Personal information  
- Actual config files with local settings

#### Always Commit:
- Template config files (`.yaml.template`)
- Config files in `.gitignore`
- README instructions for setup

#### .gitignore Pattern
```gitignore
# User configuration
config.yaml
*.mdata

# Local directories
input/
output/
```

### Quick Start Checklist

When creating a new script:
- [ ] Identify what needs to be configurable
- [ ] Create config structure (YAML or .mdata)
- [ ] Add auto-creation code if config missing
- [ ] Test on fresh directory (no pre-existing config)
- [ ] Add config files to `.gitignore`
- [ ] Document expected config structure in README

### Key Principle

**Scripts must work immediately after cloning from GitHub** - no manual setup beyond editing an auto-generated config file.

---

## PowerShell Data Files

Use YAML for any human-readable/human-editable data or config files in PowerShell projects.

**Dependency:** `powershell-yaml` (not built-in — must be installed)

Any generated script that reads or writes YAML must include this near the top, commented:

```powershell
# Requires the 'powershell-yaml' module.
# Install once with: Install-Module powershell-yaml -Scope CurrentUser
```

**Reading:**
```powershell
$data = Get-Content -Raw "data.yaml" | ConvertFrom-Yaml
```

**Writing:**
```powershell
$data | ConvertTo-Yaml | Set-Content "data.yaml"
```

Check whether the module is available before using it:
```powershell
if (-not (Get-Module -ListAvailable -Name powershell-yaml)) {
    throw "Required module 'powershell-yaml' is not installed. Run: Install-Module powershell-yaml -Scope CurrentUser"
}
Import-Module powershell-yaml
```

**File extensions for YAML-formatted files:** Use `.yaml` (e.g. `config.yaml`, `users.yaml`).

## Config file layout 

For any script that needs a configuration file, use this layout:

    <ProjectFolder>/
        MyScript.ps1                          (or .py, .bas, etc)
        Config/
            MyScript.yaml                     ← user's actual config, git-ignored
            MyScript.Template.yaml.txt        ← schema reference, committed

Rules:
1. The script resolves its config relative to its own location
   (`$PSScriptRoot\Config\...` in PowerShell, `Path(__file__).parent / "Config" / ...`
   in Python) — never a hard-coded absolute path.
2. The user data file filename matches the script name (`MyScript.ps1` → `MyScript.yaml`).
3. The template uses the `.txt` suffix (`.Template.yaml.txt`, for example) so it bypasses `.gitignore` and stays under version control as the
   documented schema.
4. If the user data file is missing on first run, the script auto-creates
   it with safe defaults (no personal info). The user then edits it.
5. One Config/ folder per ProjectFolder is fine — multiple scripts can
   share it because each script's YAML and template are named after the
   script.
