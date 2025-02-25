@app.route('/upload_document', methods=['POST'])
def upload_document():
    data = request.form
    file = request.files['file']
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    document = Document(
        CaseID=data['case_id'],
        UploadedBy=data['user_id'],
        FilePath=file_path,
        FileType=file.content_type
    )
    db.session.add(document)
    db.session.commit()

    return jsonify({"message": "Document uploaded successfully"})
