@app.route('/log-case', methods=['GET', 'POST'])
def log_case():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        # Save to database
        new_case = Case(title=title, description=description)
        db.session.add(new_case)
        db.session.commit()

        flash('Case logged successfully!', 'success')
        return redirect('/log-case')

    return render_template('log_case.html')
