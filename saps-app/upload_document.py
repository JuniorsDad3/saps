@app.route('/upload-document', methods=['GET', 'POST'])
def upload_document():
    if request.method == 'POST':
        file = request.files['document']
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            # Save document to database
            new_document = Document(filename=file.filename)
            db.session.add(new_document)
            db.session.commit()

            flash('Document uploaded successfully!', 'success')
            return redirect('/upload-document')

    return render_template('upload_document.html')
