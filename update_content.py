import json

nb_path = 'Gewaechshaus_Simulation.ipynb'

def update_notebook():
    try:
        with open(nb_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)

        cells = nb['cells']
        modified = False

        teil_a_text = [
            "# Teil A: Konventionelles System\n",
            "\n",
            "Das konventionelle Gewächshaus bezieht:\n",
            "\n",
            "- Strom vollständig aus dem öffentlichen Netz (0,1361 €/kWh)\n",
            "- Wärme aus einem Gaskessel (Erdgas: 0,03 €/kWh, Wirkungsgrad: 95%)\n",
            "\n"
        ]

        teil_b_text = [
            "# Teil B: Zukunftssystem\n",
            "\n",
            "Das Zukunftssystem nutzt erneuerbare Energien:\n",
            "\n",
            "- Windkraftanlage zur Stromerzeugung (Nennleistung wird optimiert)\n",
            "- Wärmepumpe zur Umwandlung von Strom in Wärme (zeitabhängiger COP)\n",
            "- Stromspeicher zum Ausgleich der fluktuierenden Windenergie\n",
            "- Wärmespeicher zur zeitlichen Entkopplung von Wärmeproduktion und -bedarf\n",
            "- Netz-Import als Backup, wenn Wind + Speicher nicht ausreichen\n"
        ]

        for cell in cells:
            if cell['cell_type'] == 'markdown':
                source = cell['source']
                content = "".join(source)
                
                # Update Teil A
                if '# Teil A: Konventionelles System' in content:
                    print("Updating Teil A content...")
                    # Preserve attachment image if present
                    image_line = next((line for line in source if 'attachment:' in line), None)
                    
                    new_source = list(teil_a_text)
                    if image_line:
                        new_source.append(image_line)
                    
                    if cell['source'] != new_source:
                        cell['source'] = new_source
                        modified = True

                # Update Teil B
                if '# Teil B: Zukunftssystem' in content:
                    print("Updating Teil B content...")
                    # Check if there is an image to preserve (though user didn't mention one for B, good to be safe)
                    image_line = next((line for line in source if 'attachment:' in line), None)
                    
                    new_source = list(teil_b_text)
                    if image_line:
                         new_source.append(image_line)
                         
                    if cell['source'] != new_source:
                        cell['source'] = new_source
                        modified = True

        if modified:
            with open(nb_path, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=4, ensure_ascii=False)
            print("Notebook updated successfully.")
        else:
            print("No changes needed.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_notebook()
