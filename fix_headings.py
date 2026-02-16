import json

nb_path = 'Gewaechshaus_Simulation.ipynb'

try:
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    cells = nb['cells']
    modified = False

    for cell in cells:
        if cell['cell_type'] == 'markdown':
            source = cell['source']
            # Join source list to check content easily
            content = "".join(source)
            
            # Fix Teil A
            if 'attachment:Konventionell.png' in content:
                # Check if header already exists
                has_header = any('Teil A: Konventionelles System' in line for line in source)
                if not has_header:
                    print("Adding Teil A header...")
                    # Prepend header
                    new_source = ["# Teil A: Konventionelles System\n", "\n"] + source
                    cell['source'] = new_source
                    modified = True
            
            # Fix Teil B (ensure it has #)
            # Find the line with Teil B
            for i, line in enumerate(source):
                if 'Teil B: Zukunftssystem' in line:
                    if not line.strip().startswith('#'):
                        print("Formatting Teil B header...")
                        # Add # prefix
                        source[i] = "# " + line.lstrip() if not line.strip().startswith('#') else line
                        modified = True

    if modified:
        with open(nb_path, 'w', encoding='utf-8') as f:
            json.dump(nb, f, indent=4, ensure_ascii=False)
        print("Notebook updated successfully.")
    else:
        print("No changes required.")

except Exception as e:
    print(f"Error: {e}")
