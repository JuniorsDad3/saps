@app.route('/submit_case', methods=['POST'])
def submit_case():
    data = request.form
    file = request.files['file']
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    new_case = Case(
        CrimeType=data['crime_type'],
        Description=data['description'],
        IsLive=data['is_live'] == 'true'
    )
    db.session.add(new_case)
    db.session.commit()

    new_case.CaseNumber = f"CASE-{new_case.CaseID:05}"
    db.session.commit()

    return jsonify({"case_number": new_case.CaseNumber})
