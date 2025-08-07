from pathlib import Path


from flask import Flask, render_template, request
import json
import os
from collections import defaultdict
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Tab definitions in fixed order
tab_definitions = [
    ("Medikationsplan", ["MedicationStatement", "MedicationRequest"]),
    ("Allergien und Intoleranzen", ["AllergyIntolerance"]),
    ("Gesundheitsprobleme und Risiken", ["Condition"], "active"),
    ("Eingriffe und Therapien", ["Procedure"]),
    ("Implantate, medizinische Geräte und Heilbehelfe", ["Device"]),
    ("Impfungen", ["Immunization"]),
    ("Diagnostische Resultate", ["Observation"], "result"),
    ("Vitalparameter", ["Observation"], "vital-signs"),
    ("Vergangene Gesundheitsprobleme und Risiken", ["Condition"], "resolved"),
    ("Behandlungsplan", ["CarePlan", "Task", "Appointment", "ServiceRequest", "MedicationRequest", "NutritionOrder"]),
    ("Lebensstil / Soziale Umstände und Verhalten", ["Observation"], "social-history"),
    ("Administrative Informationen", ["Patient", "Practitioner", "Organization", "RelatedPerson"])
]

# Utility: categorize resource into a tab name
def categorize_resource(resource):
    resource_type = resource.get("resourceType")
    
    for tab_name, types, *extra in tab_definitions:
        if resource_type in types:
            if resource_type == "Condition" and extra:
                status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
                if status == extra[0]:
                    return tab_name
                continue
            if resource_type == "Observation" and extra:
                categories = [c.get("coding", [{}])[0].get("code") for c in resource.get("category", [])]
                if extra[0] in categories:
                    return tab_name
                continue
            return tab_name
    return "Weitere"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['bundle']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            with open(filepath, encoding='utf-8') as f:
                data = json.load(f)
            
            entries = data.get("entry", [])
            categorized = defaultdict(list)
            
            for entry in entries:
                resource = entry.get("resource")
                if resource:
                    tab = categorize_resource(resource)
                    categorized[tab].append(resource)

            # Sort tabs in order of tab_definitions, then add "Weitere" if exists
            ordered_tabs = []
            for name, *_ in tab_definitions:
                if name in categorized:
                    ordered_tabs.append((name, categorized[name]))
            if "Weitere" in categorized:
                ordered_tabs.append(("Weitere", categorized["Weitere"]))

            # Prepare summary tab
            summary = [(name, len(resources)) for name, resources in ordered_tabs]
            
            # Patient info
            patient = next((r for r in entries if r['resource']['resourceType'] == 'Patient'), None)
            patient_resource = patient['resource'] if patient else None

            return render_template(
                'viewer.html',
                filename=filename,
                tabs=ordered_tabs,
                summary=summary,
                patient=patient_resource
            )

    return render_template('index.html')


if __name__ == '__main__':
    app.run(port=8085, debug=True)